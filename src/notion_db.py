"""Notion APIクライアントモジュール"""
from notion_client import Client
from datetime import datetime
from typing import Dict, List, Optional
import json
import os

# ローカルに作成済みチケットをキャッシュしておくファイル
CACHE_FILENAME = '.notion_ticket_cache.json'


class NotionClient:
    """Notion APIとの連携を管理するクラス"""
    
    def __init__(self, api_key: str, database_id: str):
        """
        Args:
            api_key: Notion APIキー
            database_id: 取引データベースID
        """
        self.client = Client(auth=api_key)
        self.database_id = database_id
        # ローカルキャッシュをロード
        self.cache_path = os.path.join(os.getcwd(), CACHE_FILENAME)
        self._load_local_cache()
    
    @staticmethod
    def get_page_url(page_id: str) -> str:
        """
        ページIDからNotionページURLを生成
        
        Args:
            page_id: NotionページID（ハイフンあり・なし両対応）
        
        Returns:
            NotionページURL
        """
        # ハイフンを削除して32文字のIDにする
        clean_id = page_id.replace('-', '')
        # NotionのページURL形式に変換
        return f"https://www.notion.so/{clean_id}"

    def _load_local_cache(self):
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self._local_ticket_to_url = json.load(f)
            else:
                self._local_ticket_to_url = {}
        except Exception:
            self._local_ticket_to_url = {}

    def _save_local_cache(self):
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self._local_ticket_to_url, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"キャッシュ保存エラー: {e}")
    
    def create_trade_record(self, trade: Dict) -> Optional[str]:
        """
        取引レコードをNotionに作成
        
        Args:
            trade: 取引データ
        
        Returns:
            作成されたページのID、失敗時はNone
        """
        try:
            # デバッグ: 取引データの内容を確認
            print(f"  取引データ: ticket={trade.get('ticket')}, symbol={trade.get('symbol')}, "
                  f"type={trade.get('type')}, volume={trade.get('volume')}, "
                  f"profit={trade.get('profit')}, pips={trade.get('pips')}, "
                  f"保有時間={trade.get('holding_time')}秒")
            # 既に同一取引番号のページが存在するか確認（ローカルキャッシュ優先）
            ticket_str = str(trade.get('ticket'))
            if ticket_str in getattr(self, '_local_ticket_to_url', {}):
                print(f"  ⊘ 取引 {ticket_str} はローカルキャッシュに存在します（スキップ）")
                return self._local_ticket_to_url.get(ticket_str)

            existing = self.find_page_by_ticket(ticket_str)
            if existing:
                page_id = existing.get('id')
                url = self.get_page_url(page_id)
                # キャッシュに登録
                try:
                    self._local_ticket_to_url[ticket_str] = url
                    self._save_local_cache()
                except Exception:
                    pass
                print(f"  ⊘ 取引 {ticket_str} は既にNotionに存在します（スキップ）")
                return page_id

            properties = {
                "取引番号": {
                    "title": [
                        {
                            "text": {
                                "content": str(trade['ticket'])
                            }
                        }
                    ]
                },
                "通貨ペア": {
                    "select": {
                        "name": trade['symbol']
                    }
                },
                "タイプ": {
                    "select": {
                        "name": trade['type']
                    }
                },
                "ロット": {
                    "number": trade['volume']
                },
                "日付": {
                    "date": {
                        "start": trade['open_time'].date().isoformat()
                    }
                },
                "pips from HTML": {
                    "number": trade.get('pips', 0.0)
                },
                "保有時間": {
                    "number": trade.get('holding_time', 0)
                }
            }
            
            # 損益の計算（利益 + 手数料 + スワップ）
            total_pnl = trade['profit'] + trade['commission'] + trade['swap']
            properties["損益 from HTML"] = {"number": total_pnl}
            
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            print(f"✓ 取引 {trade['ticket']} をNotionに記録しました")
            page_id = response['id']
            # キャッシュを更新
            try:
                self._local_ticket_to_url[ticket_str] = self.get_page_url(page_id)
                self._save_local_cache()
            except Exception:
                pass
            return page_id
            
        except Exception as e:
            print(f"✗ 取引 {trade['ticket']} の記録エラー: {e}")
            return None
    
    def get_existing_tickets(self) -> List[str]:
        """
        データベースに既に存在する取引番号を取得
        
        Returns:
            取引番号のリスト
        """
        try:
            existing_tickets = []
            has_more = True
            start_cursor = None
            
            while has_more:
                query_params = {
                    "database_id": self.database_id,
                    "page_size": 100
                }
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                # 正常なクライアントだと databases.query が使える
                try:
                    response = self.client.databases.query(**query_params)
                except AttributeError:
                    # 古い/新しいクライアント差分がある場合は search をフォールバックで利用
                    response = self._query_via_search(start_cursor=start_cursor, page_size=query_params['page_size'])
                
                for page in response['results']:
                    # プロパティを総当たりで探して取引番号を検出（表記ゆれに対応）
                    ticket = None
                    props = page.get('properties', {})
                    for prop in props.values():
                        # title
                        if isinstance(prop, dict) and 'title' in prop and prop.get('title'):
                            try:
                                ticket = prop['title'][0]['text']['content']
                            except Exception:
                                continue
                        # rich_text
                        if not ticket and isinstance(prop, dict) and 'rich_text' in prop and prop.get('rich_text'):
                            try:
                                ticket = prop['rich_text'][0]['text']['content']
                            except Exception:
                                continue
                        # number
                        if not ticket and isinstance(prop, dict) and 'number' in prop and prop.get('number') is not None:
                            ticket = str(prop['number'])
                        if ticket:
                            break

                    if ticket:
                        ticket_norm = str(ticket).strip()
                        existing_tickets.append(ticket_norm)

                has_more = response.get('has_more', False)
                start_cursor = response.get('next_cursor')
            
            print(f"Notionに既に {len(existing_tickets)} 件の取引が記録されています")
            return existing_tickets
            
        except Exception as e:
            print(f"既存データの取得エラー: {e}")
            return []
    
    def get_existing_tickets_with_urls(self) -> Dict[str, str]:
        """
        データベースに既に存在する取引番号とページURLを取得
        
        Returns:
            取引番号とNotionページURLの辞書
        """
        try:
            ticket_to_url = {}
            has_more = True
            start_cursor = None
            
            while has_more:
                query_params = {
                    "database_id": self.database_id,
                    "page_size": 100
                }
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                try:
                    response = self.client.databases.query(**query_params)
                except AttributeError:
                    response = self._query_via_search(start_cursor=start_cursor, page_size=query_params['page_size'])

                for page in response['results']:
                    # プロパティを総当たりで探して取引番号を検出（表記ゆれに対応）
                    ticket = None
                    props = page.get('properties', {})
                    for prop in props.values():
                        if isinstance(prop, dict) and 'title' in prop and prop.get('title'):
                            try:
                                ticket = prop['title'][0]['text']['content']
                            except Exception:
                                continue
                        if not ticket and isinstance(prop, dict) and 'rich_text' in prop and prop.get('rich_text'):
                            try:
                                ticket = prop['rich_text'][0]['text']['content']
                            except Exception:
                                continue
                        if not ticket and isinstance(prop, dict) and 'number' in prop and prop.get('number') is not None:
                            ticket = str(prop['number'])
                        if ticket:
                            break

                    if ticket:
                        page_id = page['id']
                        ticket_norm = str(ticket).strip()
                        ticket_to_url[ticket_norm] = self.get_page_url(page_id)

                has_more = response.get('has_more', False)
                start_cursor = response.get('next_cursor')
            
            # API取得に成功したらローカルキャッシュとマージして保存
            try:
                # マージ（API側を優先）
                if not hasattr(self, '_local_ticket_to_url'):
                    self._local_ticket_to_url = {}
                self._local_ticket_to_url.update(ticket_to_url)
                self._save_local_cache()
            except Exception:
                pass

            print(f"Notionに既に {len(ticket_to_url)} 件の取引が記録されています (API取得)")
            # API取得が0件の場合はローカルキャッシュを返す
            if not ticket_to_url and getattr(self, '_local_ticket_to_url', {}):
                print(f"ローカルキャッシュから {len(self._local_ticket_to_url)} 件を読み込みます")
                return dict(self._local_ticket_to_url)

            return ticket_to_url
            
        except Exception as e:
            print(f"既存データの取得エラー: {e}")
            return {}

    def find_page_by_ticket(self, ticket: str) -> Optional[Dict]:
        """
        データベース内で指定の取引番号のページを探して返す（見つからなければNone）
        """
        try:
            ticket_str = str(ticket).strip()

            # まず databases.query が使える場合はフィルタで絞る
            if hasattr(self.client.databases, 'query'):
                try:
                    resp = self.client.databases.query(
                        database_id=self.database_id,
                        page_size=1,
                        filter={"property": "取引番号", "title": {"equals": ticket_str}}
                    )
                    results = resp.get('results', [])
                    if results:
                        return results[0]
                except Exception:
                    # フィルタが効かない場合はフォールバックに進む
                    pass

            # search API でヒットするページを列挙し、親が対象データベースか確認する
            resp = self.client.search(query=ticket_str, filter={"property": "object", "value": "page"}, page_size=100)
            for page in resp.get('results', []):
                parent = page.get('parent', {})
                parent_db = parent.get('database_id')
                # データベースIDの形式差（ハイフンあり/なし）に対応して比較
                if not parent_db or parent_db.replace('-', '') != str(self.database_id).replace('-', ''):
                    continue

                # プロパティを総当たりで照合（title, rich_text, number）
                props = page.get('properties', {})
                for prop_name, prop in props.items():
                    # title
                    if isinstance(prop, dict) and 'title' in prop and prop.get('title'):
                        try:
                            val = prop['title'][0]['text']['content']
                            if str(val).strip() == ticket_str:
                                return page
                        except Exception:
                            pass
                    # rich_text
                    if isinstance(prop, dict) and 'rich_text' in prop and prop.get('rich_text'):
                        try:
                            val = prop['rich_text'][0]['text']['content']
                            if str(val).strip() == ticket_str:
                                return page
                        except Exception:
                            pass
                    # number
                    if isinstance(prop, dict) and 'number' in prop and prop.get('number') is not None:
                        try:
                            if str(prop['number']) == ticket_str:
                                return page
                        except Exception:
                            pass

        except Exception as e:
            print(f"既存ページ検索エラー: {e}")

        return None

    def _query_via_search(self, start_cursor: Optional[str] = None, page_size: int = 100):
        """
        databases.query が利用できない環境向けの簡易フォールバック。
        search API を使ってページを列挙し、データベースに属するページだけを返す（簡易実装）。
        """
        try:
            params = {"filter": {"property": "object", "value": "page"}, "page_size": page_size}
            if start_cursor:
                params['start_cursor'] = start_cursor

            resp = self.client.search(**params)
            results = []
            for page in resp.get('results', []):
                parent = page.get('parent', {})
                parent_db = parent.get('database_id')
                # ハイフンあり/なしの差異に対応
                if not parent_db or parent_db.replace('-', '') != str(self.database_id).replace('-', ''):
                    results.append(page)
            return {'results': results, 'has_more': resp.get('has_more', False), 'next_cursor': resp.get('next_cursor')}
        except Exception as e:
            print(f"searchによるフォールバック取得でエラー: {e}")
            return {'results': [], 'has_more': False}
    
    def sync_trades(self, trades: List[Dict]) -> tuple[Dict[str, int], Dict[str, str]]:
        """
        取引データをNotionに同期（重複チェック付き）
        
        Args:
            trades: 取引データのリスト
        
        Returns:
            (統計情報, 取引番号とNotionページURLの辞書)
        """
        # 既存の取引番号とURLを取得
        ticket_to_url = self.get_existing_tickets_with_urls()
        existing_tickets = set(ticket_to_url.keys())
        
        stats = {
            'total': len(trades),
            'new': 0,
            'skipped': 0,
            'failed': 0
        }
        
        for trade in trades:
            ticket = str(trade['ticket'])
            
            # 既に存在する場合はスキップ（URLは既に取得済み）
            if ticket in existing_tickets:
                stats['skipped'] += 1
                continue

            # 事前取得に失敗している可能性があるため、個別に存在確認を行う
            found_page = self.find_page_by_ticket(ticket)
            if found_page:
                page_id = found_page.get('id')
                stats['skipped'] += 1
                # 既存のページURLを登録しておく
                ticket_to_url[ticket] = self.get_page_url(page_id)
                continue

            # 新規レコードを作成
            page_id = self.create_trade_record(trade)
            if page_id:
                stats['new'] += 1
                # ページURLを生成して辞書に追加
                ticket_to_url[ticket] = self.get_page_url(page_id)
            else:
                stats['failed'] += 1
        
        print(f"\n同期完了:")
        print(f"  - 合計: {stats['total']}件")
        print(f"  - 新規追加: {stats['new']}件")
        print(f"  - スキップ: {stats['skipped']}件")
        print(f"  - 失敗: {stats['failed']}件")
        
        return stats, ticket_to_url


# テスト実行用
if __name__ == '__main__':
    from config import Config
    
    Config.validate()
    
    client = NotionClient(
        api_key=Config.NOTION_API_KEY,
        database_id=Config.NOTION_DATABASE_ID
    )
    
    # テスト用のダミーデータ
    test_trade = {
        'ticket': 999999999,
        'symbol': 'USDJPY',
        'type': 'BUY',
        'volume': 0.01,
        'open_time': datetime.now(),
        'close_time': datetime.now(),
        'open_price': 150.123,
        'close_price': 150.456,
        'commission': -0.50,
        'swap': 0.0,
        'profit': 3.30
    }
    
    # 既存チケットの確認
    existing = client.get_existing_tickets()
    print(f"既存の取引: {len(existing)}件")
