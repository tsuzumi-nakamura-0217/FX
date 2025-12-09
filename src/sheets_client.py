"""Google Sheets APIクライアントモジュール"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Dict, List, Optional


class SheetsClient:
    """Google Sheets APIとの連携を管理するクラス"""
    
    def __init__(self, credentials_file: str, spreadsheet_id: str):
        """
        Args:
            credentials_file: Google Cloud サービスアカウントのJSONキーファイルパス
            spreadsheet_id: 書き込み先のスプレッドシートID
        """
        # Google Sheets APIのスコープ
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # 認証情報の設定
        creds = Credentials.from_service_account_file(
            credentials_file, 
            scopes=scopes
        )
        
        self.gc = gspread.authorize(creds)
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
        
        # デフォルトは最初のシート
        try:
            self.sheet = self.spreadsheet.sheet1
        except Exception:
            # シートがない場合は新規作成
            self.sheet = self.spreadsheet.add_worksheet(title="取引履歴", rows=100, cols=20)
        
        # ヘッダー行を初期化
        self._initialize_headers()
    
    def _initialize_headers(self):
        """スプレッドシートのヘッダー行を初期化"""
        headers = [
            "取引番号", "通貨ペア", "タイプ", "ロット", 
            "開始時刻", "終了時刻", "日付",
            "損益", "pips", "保有時間(秒)",
            "手数料", "スワップ", "合計損益",
            "同期日時"
        ]
        
        # 既存のヘッダーを確認
        try:
            existing_headers = self.sheet.row_values(1)
            if not existing_headers or existing_headers[0] != "取引番号":
                # ヘッダーがない、または異なる場合は設定
                self.sheet.update('A1', [headers])
                # ヘッダー行を太字にフォーマット
                self.sheet.format('A1:N1', {
                    "textFormat": {"bold": True},
                    "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
                })
        except Exception as e:
            # エラーの場合もヘッダーを設定
            self.sheet.update('A1', [headers])
    
    def sync_trades(self, trades: List[Dict], ticket_to_url: Optional[Dict[str, str]] = None) -> Dict[str, int]:
        """
        取引データをスプレッドシートに同期
        
        Args:
            trades: 取引データのリスト
            ticket_to_url: 取引番号とNotionページURLのマッピング（オプション）
        
        Returns:
            統計情報 (new: 新規追加数, existing: 既存数)
        """
        stats = {'new': 0, 'existing': 0}
        
        # 既存の取引番号を取得
        existing_tickets = self.get_existing_tickets()
        
        print(f"スプレッドシートの既存取引: {len(existing_tickets)}件")
        
        # ticket_to_urlがnoneの場合は空の辞書を使用
        if ticket_to_url is None:
            ticket_to_url = {}
        
        # 各取引を処理
        for trade in trades:
            ticket = str(trade['ticket'])
            
            if ticket in existing_tickets:
                print(f"  ⊘ 取引 {ticket} は既に存在します（スキップ）")
                stats['existing'] += 1
            else:
                # Notion URLがあれば渡す
                notion_url = ticket_to_url.get(ticket)
                if self.add_trade_row(trade, notion_url):
                    stats['new'] += 1
        
        return stats
    
    def get_existing_tickets(self) -> List[str]:
        """
        スプレッドシートに既に存在する取引番号を取得
        
        Returns:
            取引番号のリスト
        """
        try:
            # A列（取引番号）の全データを取得（ヘッダーを除く）
            tickets_column = self.sheet.col_values(1)[1:]  # 1行目はヘッダー
            return [str(ticket) for ticket in tickets_column if ticket]
        except Exception as e:
            print(f"既存取引の取得エラー: {e}")
            return []
    
    def add_trade_row(self, trade: Dict, notion_url: Optional[str] = None) -> bool:
        """
        取引データを新しい行として追加
        
        Args:
            trade: 取引データ
            notion_url: NotionページのURL（オプション）
        
        Returns:
            成功時True、失敗時False
        """
        try:
            # 損益の計算（利益 + 手数料 + スワップ）
            total_pnl = trade['profit'] + trade['commission'] + trade['swap']
            
            # 日付フォーマット
            open_time_str = trade['open_time'].strftime('%Y-%m-%d %H:%M:%S')
            close_time_str = trade['close_time'].strftime('%Y-%m-%d %H:%M:%S')
            date_str = trade['open_time'].strftime('%Y-%m-%d')
            sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            ticket_str = str(trade['ticket'])
            
            # Notionリンクがある場合はHYPERLINK関数を使用
            if notion_url:
                ticket_cell_value = f'=HYPERLINK("{notion_url}", "{ticket_str}")'
            else:
                ticket_cell_value = ticket_str
            
            # 行データを作成
            row_data = [
                ticket_cell_value,              # 取引番号（リンク付き）
                trade['symbol'],                # 通貨ペア
                trade['type'],                  # タイプ
                trade['volume'],                # ロット
                open_time_str,                  # 開始時刻
                close_time_str,                 # 終了時刻
                date_str,                       # 日付
                trade['profit'],                # 損益
                trade.get('pips', 0.0),        # pips
                trade.get('holding_time', 0),  # 保有時間
                trade['commission'],            # 手数料
                trade['swap'],                  # スワップ
                total_pnl,                      # 合計損益
                sync_time                       # 同期日時
            ]
            
            # 次の空行の行番号を取得（A列基準）
            next_row = len(self.sheet.col_values(1)) + 1
            # A列から明示的に範囲を指定して追加
            range_name = f'A{next_row}:N{next_row}'
            self.sheet.update(range_name, [row_data], value_input_option='USER_ENTERED')
            
            if notion_url:
                print(f"✓ 取引 {ticket_str} をスプレッドシートに記録しました（Notionリンク付き）")
            else:
                print(f"✓ 取引 {ticket_str} をスプレッドシートに記録しました")
            
            return True
            
        except Exception as e:
            print(f"✗ 取引 {trade['ticket']} の記録エラー: {e}")
            return False
    
    def clear_all_data(self):
        """すべてのデータをクリア（ヘッダーは残す）"""
        try:
            # 2行目以降をクリア
            self.sheet.delete_rows(2, self.sheet.row_count)
            print("✓ スプレッドシートのデータをクリアしました")
        except Exception as e:
            print(f"✗ データクリアエラー: {e}")
    
    def get_trade_count(self) -> int:
        """スプレッドシートの取引件数を取得"""
        try:
            # ヘッダーを除いた行数
            return len(self.sheet.col_values(1)) - 1
        except Exception:
            return 0
