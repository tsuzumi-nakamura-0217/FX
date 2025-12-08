"""Notion APIクライアントモジュール"""
from notion_client import Client
from datetime import datetime
from typing import Dict, List, Optional


class NotionClient:
    """Notion APIとの連携を管理するクラス"""
    
    def __init__(self, api_key: str, database_id: str):
        """
        Args:
            api_key: Notion APIキー
            database_id: 書き込み先のデータベースID
        """
        self.client = Client(auth=api_key)
        self.database_id = database_id
    
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
            return response['id']
            
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
                
                response = self.client.databases.query(**query_params)
                
                for page in response['results']:
                    title_property = page['properties'].get('取引番号', {})
                    if 'title' in title_property and title_property['title']:
                        ticket = title_property['title'][0]['text']['content']
                        existing_tickets.append(ticket)
                
                has_more = response['has_more']
                start_cursor = response.get('next_cursor')
            
            print(f"Notionに既に {len(existing_tickets)} 件の取引が記録されています")
            return existing_tickets
            
        except Exception as e:
            print(f"既存データの取得エラー: {e}")
            return []
    
    def sync_trades(self, trades: List[Dict]) -> Dict[str, int]:
        """
        取引データをNotionに同期（重複チェック付き）
        
        Args:
            trades: 取引データのリスト
        
        Returns:
            同期結果の統計
        """
        # 既存の取引番号を取得
        existing_tickets = set(self.get_existing_tickets())
        
        stats = {
            'total': len(trades),
            'new': 0,
            'skipped': 0,
            'failed': 0
        }
        
        for trade in trades:
            ticket = str(trade['ticket'])
            
            # 既に存在する場合はスキップ
            if ticket in existing_tickets:
                stats['skipped'] += 1
                continue
            
            # 新規レコードを作成
            if self.create_trade_record(trade):
                stats['new'] += 1
            else:
                stats['failed'] += 1
        
        print(f"\n同期完了:")
        print(f"  - 合計: {stats['total']}件")
        print(f"  - 新規追加: {stats['new']}件")
        print(f"  - スキップ: {stats['skipped']}件")
        print(f"  - 失敗: {stats['failed']}件")
        
        return stats


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
