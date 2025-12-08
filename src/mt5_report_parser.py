"""MT5レポートファイル（HTML/CSV）パーサー"""
import re
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from bs4 import BeautifulSoup
import os


class MT5ReportParser:
    """MT5のレポートファイルから取引データを抽出するクラス"""
    
    @staticmethod
    def parse_html_report(file_path: str) -> List[Dict]:
        """
        MT5のHTMLレポートから取引履歴を抽出
        
        MT5アプリで「ファイル」→「レポートを保存」→「HTMLレポート」を選択して
        エクスポートしたファイルを読み込みます。
        
        Args:
            file_path: HTMLレポートファイルのパス
        
        Returns:
            取引データのリスト（決済済み取引のみ）
        """
        try:
            # 複数のエンコーディングを試行
            encodings = ['utf-8', 'utf-16', 'shift-jis', 'cp1252', 'latin-1']
            html_content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        html_content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if html_content is None:
                raise ValueError("ファイルのエンコーディングを判別できませんでした")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 取引テーブルを探す（bgcolorがある行がデータ行）
            tables = soup.find_all('table')
            trades = []
            
            for table in tables:
                # テーブル内の全tr要素を順番に処理
                all_rows = table.find_all('tr')
                in_positions_section = False
                
                for row in all_rows:
                    # セクションヘッダーをチェック
                    headers = row.find_all('th', attrs={'colspan': True})
                    for header in headers:
                        text = header.get_text(strip=True)
                        if 'ポジション一覧' in text or 'Closed Trades' in text:
                            in_positions_section = True
                        elif in_positions_section and ('注文' in text or 'Orders' in text or '約定' in text or 'Deals' in text):
                            # 次のセクションに入ったら終了
                            in_positions_section = False
                    
                    # ポジション一覧セクション内のデータ行のみ処理
                    if in_positions_section and row.get('bgcolor'):
                        # hiddenクラスの要素を除外してデータを取得
                        tds = row.find_all('td')
                        cols = []
                        for td in tds:
                            # hiddenクラスを持つ要素はスキップ
                            if 'hidden' not in td.get('class', []):
                                cols.append(td.get_text(strip=True))
                        
                        if len(cols) >= 13:  # 決済済み取引の最低限のカラム数
                            try:
                                trade = MT5ReportParser._parse_html_trade_row(cols)
                                if trade:
                                    trades.append(trade)
                            except Exception as e:
                                print(f"行の解析エラー: {e}, データ: {cols[:5]}")
                                continue
            
            print(f"HTMLレポートから {len(trades)} 件の取引を抽出しました")
            return trades
            
        except Exception as e:
            print(f"HTMLレポートの読み込みエラー: {e}")
            return []
    
    @staticmethod
    def parse_csv_report(file_path: str) -> List[Dict]:
        """
        MT5のCSVレポートから取引履歴を抽出
        
        Args:
            file_path: CSVレポートファイルのパス
        
        Returns:
            取引データのリスト
        """
        try:
            # CSVファイルを読み込む（エンコーディングを試行）
            encodings = ['utf-8', 'utf-16', 'shift-jis', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except:
                    continue
            
            if df is None:
                raise ValueError("CSVファイルを読み込めませんでした")
            
            trades = []
            
            # カラム名を正規化
            df.columns = df.columns.str.strip()
            
            for _, row in df.iterrows():
                try:
                    trade = MT5ReportParser._parse_csv_row(row)
                    if trade:
                        trades.append(trade)
                except Exception as e:
                    print(f"行の解析エラー: {e}")
                    continue
            
            print(f"CSVレポートから {len(trades)} 件の取引を抽出しました")
            return trades
            
        except Exception as e:
            print(f"CSVレポートの読み込みエラー: {e}")
            return []
    
    @staticmethod
    def _parse_html_trade_row(cols: List[str]) -> Dict:
        """
        HTMLテーブルの行から取引データを抽出
        
        MT5 HTMLレポートの標準フォーマット:
        [0] 開始時刻, [1] チケット, [2] シンボル, [3] タイプ, [4] ロット,
        [5] 開始価格, [6] S/L, [7] T/P, [8] 終了時刻, [9] 終了価格,
        [10] 手数料, [11] スワップ, [12] 損益
        """
        try:
            # 基本的な検証
            if len(cols) < 13:
                return None
            
            # buy/sellが含まれているか確認（取引行の識別）
            type_str = cols[3].lower()
            if type_str not in ['buy', 'sell']:
                return None
            
            open_time = MT5ReportParser._parse_datetime(cols[0])
            close_time = MT5ReportParser._parse_datetime(cols[8])
            
            trade = {
                'ticket': int(re.sub(r'[^\d]', '', cols[1])),
                'symbol': cols[2],
                'type': type_str,
                'volume': MT5ReportParser._parse_float(cols[4]),
                'open_time': open_time,
                'close_time': close_time,
                'open_price': MT5ReportParser._parse_float(cols[5]),
                'close_price': MT5ReportParser._parse_float(cols[9]),
                'commission': MT5ReportParser._parse_float(cols[10]),
                'swap': MT5ReportParser._parse_float(cols[11]),
                'profit': MT5ReportParser._parse_float(cols[12]),
            }
            
            # pipsを計算
            trade['pips'] = MT5ReportParser._calculate_pips(
                trade['symbol'],
                trade['open_price'],
                trade['close_price'],
                trade['type']
            )
            
            # 保有時間（秒）を計算
            trade['holding_time'] = int((close_time - open_time).total_seconds())
            
            return trade if trade['ticket'] and trade['symbol'] else None
            
        except Exception as e:
            print(f"取引データの解析エラー: {e}")
            return None
    
    @staticmethod
    def _parse_trade_row(cols: List[str], headers: List[str]) -> Dict:
        """HTMLテーブルの行から取引データを抽出（旧形式用）"""
        # カラムとヘッダーのマッピング
        data = dict(zip(headers, cols))
        
        # 必要なデータを抽出（柔軟に対応）
        ticket = None
        for key in ['Order', 'Ticket', 'チケット', '注文']:
            if key in data:
                ticket = int(re.sub(r'[^\d]', '', data[key]))
                break
        
        if not ticket:
            return None
        
        trade = {
            'ticket': ticket,
            'symbol': MT5ReportParser._find_value(data, ['Symbol', 'シンボル', '通貨ペア']),
            'type': MT5ReportParser._find_value(data, ['Type', 'タイプ', '種別']),
            'volume': MT5ReportParser._parse_float(
                MT5ReportParser._find_value(data, ['Volume', 'Lots', 'ロット', '数量'])
            ),
            'open_time': MT5ReportParser._parse_datetime(
                MT5ReportParser._find_value(data, ['Time', 'Open Time', '開始時刻'])
            ),
            'close_time': MT5ReportParser._parse_datetime(
                MT5ReportParser._find_value(data, ['Close Time', '終了時刻'])
            ),
            'open_price': MT5ReportParser._parse_float(
                MT5ReportParser._find_value(data, ['Price', 'Open Price', '開始価格'])
            ),
            'close_price': MT5ReportParser._parse_float(
                MT5ReportParser._find_value(data, ['Close Price', 'S/L', '終了価格'])
            ),
            'commission': MT5ReportParser._parse_float(
                MT5ReportParser._find_value(data, ['Commission', '手数料'])
            ),
            'swap': MT5ReportParser._parse_float(
                MT5ReportParser._find_value(data, ['Swap', 'スワップ'])
            ),
            'profit': MT5ReportParser._parse_float(
                MT5ReportParser._find_value(data, ['Profit', '損益', '利益'])
            ),
        }
        
        # pipsを計算
        trade['pips'] = MT5ReportParser._calculate_pips(
            trade['symbol'],
            trade['open_price'],
            trade['close_price'],
            trade['type']
        )
        
        return trade if all([trade['ticket'], trade['symbol']]) else None
    
    @staticmethod
    def _parse_csv_row(row: pd.Series) -> Dict:
        """CSVの行から取引データを抽出"""
        try:
            trade = {
                'ticket': int(MT5ReportParser._find_value(
                    row.to_dict(), ['Order', 'Ticket', 'チケット', 'Deal']
                )),
                'symbol': MT5ReportParser._find_value(
                    row.to_dict(), ['Symbol', 'シンボル']
                ),
                'type': MT5ReportParser._find_value(
                    row.to_dict(), ['Type', 'タイプ']
                ),
                'volume': MT5ReportParser._parse_float(
                    MT5ReportParser._find_value(row.to_dict(), ['Volume', 'ロット'])
                ),
                'open_time': MT5ReportParser._parse_datetime(
                    MT5ReportParser._find_value(row.to_dict(), ['Time', 'Open Time'])
                ),
                'close_time': MT5ReportParser._parse_datetime(
                    MT5ReportParser._find_value(row.to_dict(), ['Time', 'Close Time'])
                ),
                'open_price': MT5ReportParser._parse_float(
                    MT5ReportParser._find_value(row.to_dict(), ['Price', 'Open Price'])
                ),
                'close_price': MT5ReportParser._parse_float(
                    MT5ReportParser._find_value(row.to_dict(), ['Price', 'Close Price'])
                ),
                'commission': MT5ReportParser._parse_float(
                    MT5ReportParser._find_value(row.to_dict(), ['Commission', '手数料'])
                ),
                'swap': MT5ReportParser._parse_float(
                    MT5ReportParser._find_value(row.to_dict(), ['Swap', 'スワップ'])
                ),
                'profit': MT5ReportParser._parse_float(
                    MT5ReportParser._find_value(row.to_dict(), ['Profit', '損益'])
                ),
            }
            
            # pipsを計算
            trade['pips'] = MT5ReportParser._calculate_pips(
                trade['symbol'],
                trade['open_price'],
                trade['close_price'],
                trade['type']
            )
            
            return trade if trade['ticket'] and trade['symbol'] else None
        except:
            return None
    
    @staticmethod
    def _find_value(data: Dict, keys: List[str]) -> str:
        """複数のキー候補から値を探す"""
        for key in keys:
            if key in data:
                value = str(data[key]).strip()
                if value and value != 'nan':
                    return value
        return ''
    
    @staticmethod
    def _parse_float(value: str) -> float:
        """文字列をfloatに変換"""
        if not value or value == 'nan':
            return 0.0
        try:
            # カンマや空白を除去
            cleaned = re.sub(r'[,\s]', '', str(value))
            return float(cleaned)
        except:
            return 0.0
    
    @staticmethod
    def _calculate_pips(symbol: str, open_price: float, close_price: float, trade_type: str) -> float:
        """
        pips数を計算
        
        Args:
            symbol: 通貨ペア
            open_price: 開始価格
            close_price: 終了価格
            trade_type: 取引タイプ (BUY/SELL)
        
        Returns:
            pips数
        """
        if not open_price or not close_price:
            return 0.0
        
        # 価格差を計算
        price_diff = close_price - open_price
        
        # SELLの場合は符号を反転
        if 'SELL' in trade_type.upper():
            price_diff = -price_diff
        
        # JPYペアの場合は小数点第2位がpips
        # その他の通貨ペアは小数点第4位がpips
        if 'JPY' in symbol.upper():
            pips = price_diff * 100
        else:
            pips = price_diff * 10000
        
        return round(pips, 2)
    
    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        """文字列をdatetimeに変換（日本時間として扱う）"""
        if not value or value == 'nan':
            return datetime.now()
        
        try:
            # 日本時間のタイムゾーン (UTC+9)
            jst = timezone(timedelta(hours=9))
            
            # 様々な日時フォーマットに対応
            formats = [
                '%Y.%m.%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y.%m.%d %H:%M',
                '%Y-%m-%d %H:%M',
                '%d.%m.%Y %H:%M:%S',
                '%d/%m/%Y %H:%M:%S',
            ]
            
            for fmt in formats:
                try:
                    # タイムゾーン情報なしでパース
                    dt = datetime.strptime(value.strip(), fmt)
                    # 日本時間として扱う
                    return dt.replace(tzinfo=jst)
                except:
                    continue
            
            return datetime.now(jst)
        except:
            return datetime.now()


# テスト実行用
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
        if file_path.endswith('.html'):
            parser = MT5ReportParser()
            trades = parser.parse_html_report(file_path)
        elif file_path.endswith('.csv'):
            parser = MT5ReportParser()
            trades = parser.parse_csv_report(file_path)
        else:
            print("サポートされているファイル形式: .html, .csv")
            sys.exit(1)
        
        # 結果を表示
        for trade in trades[:5]:
            print(f"\n取引番号: {trade['ticket']}")
            print(f"通貨ペア: {trade['symbol']}")
            print(f"タイプ: {trade['type']}")
            print(f"ロット: {trade['volume']}")
            print(f"損益: {trade['profit']}")
    else:
        print("使用方法: python mt5_report_parser.py <レポートファイル.html または .csv>")
