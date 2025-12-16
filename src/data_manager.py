"""トレードデータ管理モジュール"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import gspread
from google.oauth2.service_account import Credentials


class TradeDataManager:
    """Google Spreadsheetからトレードデータを読み込み、分析用に処理するクラス"""
    
    # 列名マッピング（システム名 → 日本語）
    COLUMN_MAPPING = {
        'trade_id': '取引番号',
        'currency_pair': '通貨ペア',
        'type': 'タイプ',
        'lot': 'ロット',
        'start_time': '開始時刻',
        'end_time': '終了時刻',
        'date': '日付',
        'profit_loss_jpy': '損益',
        'pips': 'pips',
        'holding_time_sec': '保有時間(秒)',
        'commission': '手数料',
        'swap': 'スワップ',
        'net_profit_loss_jpy': '合計損益',
        'sync_time': '同期日時',
        'strategy': '手法',
        'review_comment': '振り返りコメント'
    }
    
    def __init__(self, credentials_file: str, spreadsheet_id: str, sheet_name: str = None):
        """
        Args:
            credentials_file: Google Cloud サービスアカウントのJSONキーファイルパス
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名（Noneの場合は最初のシート）
        """
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        self.gc = gspread.authorize(creds)
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
        
        if sheet_name:
            self.sheet = self.spreadsheet.worksheet(sheet_name)
        else:
            self.sheet = self.spreadsheet.sheet1
        
        self.df = None
    
    def load_data(self) -> pd.DataFrame:
        """Google Spreadsheetからデータを読み込み、DataFrameとして返す"""
        try:
            # ヘッダー行と全データを取得
            headers = self.sheet.row_values(1)
            
            # 空の列名を除外し、重複を処理
            cleaned_headers = []
            seen = {}
            for i, header in enumerate(headers):
                if header and header.strip():  # 空でない場合のみ
                    header = header.strip()
                    # 重複がある場合は番号を付ける
                    if header in seen:
                        seen[header] += 1
                        cleaned_headers.append(f"{header}_{seen[header]}")
                    else:
                        seen[header] = 0
                        cleaned_headers.append(header)
            
            # データが空の場合
            if not cleaned_headers:
                return pd.DataFrame(columns=list(self.COLUMN_MAPPING.keys()))
            
            # すべてのレコードを取得（expected_headersを使用）
            all_values = self.sheet.get_all_values()
            
            print(f"=== Google Sheets データ読み込み ===")
            print(f"全行数（ヘッダー含む）: {len(all_values)}")
            
            if len(all_values) <= 1:
                # ヘッダーのみでデータがない場合
                return pd.DataFrame(columns=list(self.COLUMN_MAPPING.keys()))
            
            # DataFrameに変換（ヘッダー行をスキップ）
            df = pd.DataFrame(all_values[1:], columns=cleaned_headers)
            print(f"DataFrame作成後の行数: {len(df)}")
            
            # 空の行を削除
            df = df.replace('', np.nan)
            df = df.dropna(how='all')
            print(f"空行削除後の行数: {len(df)}")
            
            # 列名を英語（システム名）に変換
            reverse_mapping = {v: k for k, v in self.COLUMN_MAPPING.items()}
            df.rename(columns=reverse_mapping, inplace=True)
            
            # 必要な列が存在しない場合は追加
            for sys_name in self.COLUMN_MAPPING.keys():
                if sys_name not in df.columns:
                    df[sys_name] = ''
            
            # データ型の変換
            df = self._convert_data_types(df)
            
            # 追加のデータクリーニング
            df = self._clean_data(df)
            
            print(f"最終的なデータ行数: {len(df)}")
            print(f"=== データ読み込み完了 ===\n")
            
            # キャッシュ
            self.df = df
            return df
            
        except Exception as e:
            raise Exception(f"データ読み込みエラー: {str(e)}")
    
    def _convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """データ型を適切な形式に変換"""
        if df.empty:
            return df
        
        # 数値型の変換
        numeric_cols = ['trade_id', 'lot', 'profit_loss_jpy', 'pips', 
                       'holding_time_sec', 'commission', 'swap', 'net_profit_loss_jpy']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 純利益の符号確認（デバッグ用）
        if 'net_profit_loss_jpy' in df.columns:
            print(f"\n=== 純利益の統計情報 ===")
            print(f"平均: {df['net_profit_loss_jpy'].mean():.2f}")
            print(f"最小: {df['net_profit_loss_jpy'].min():.2f}")
            print(f"最大: {df['net_profit_loss_jpy'].max():.2f}")
            print(f"正の値の数: {(df['net_profit_loss_jpy'] > 0).sum()}")
            print(f"負の値の数: {(df['net_profit_loss_jpy'] < 0).sum()}")
            print("========================\n")
        
        # 日時型の変換
        datetime_cols = ['start_time', 'end_time', 'sync_time']
        for col in datetime_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # 日付型の変換（datetimeのまま保持してソート・フィルタリングを可能に）
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # 文字列型の変換とクリーニング
        string_cols = ['currency_pair', 'type', 'strategy', 'review_comment']
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).replace('nan', '')
                # 通貨ペアとタイプから不正な文字（#など）を除去
                if col in ['currency_pair', 'type']:
                    df[col] = df[col].str.replace('#', '', regex=False).str.strip()
        
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """データのクリーニング（不正な文字の除去など）"""
        if df.empty:
            return df
        
        print("=== _clean_data() 開始 ===")
        
        # 通貨ペアのクリーニング
        if 'currency_pair' in df.columns:
            print(f"クリーニング前のcurrency_pair: {df['currency_pair'].unique()}")
            # '#'や余分な空白を除去
            df['currency_pair'] = df['currency_pair'].astype(str).str.replace('#', '', regex=False)
            df['currency_pair'] = df['currency_pair'].str.strip()
            df['currency_pair'] = df['currency_pair'].str.upper()  # 大文字に統一
            # 空文字列をNaNに変換
            df.loc[df['currency_pair'] == '', 'currency_pair'] = None
            print(f"クリーニング後のcurrency_pair: {df['currency_pair'].unique()}")
        
        # タイプのクリーニング
        if 'type' in df.columns:
            print(f"クリーニング前のtype: {df['type'].unique()}")
            # '#'を除去
            df['type'] = df['type'].astype(str).str.replace('#', '', regex=False)
            df['type'] = df['type'].str.strip()
            df['type'] = df['type'].str.lower()  # 小文字に統一
            # 空文字列をNaNに変換
            df.loc[df['type'] == '', 'type'] = None
            print(f"クリーニング後のtype: {df['type'].unique()}")
        
        # 手法のクリーニング
        if 'strategy' in df.columns:
            df['strategy'] = df['strategy'].astype(str).str.strip()
            # 空文字列やnanをNaNに変換
            df.loc[df['strategy'].isin(['', 'nan', 'None']), 'strategy'] = None
        
        print("=== _clean_data() 完了 ===")
        return df
    
    def update_review_comment(self, trade_id: int, comment: str) -> bool:
        """
        特定のトレードの振り返りコメントを更新
        
        Args:
            trade_id: 取引番号
            comment: 振り返りコメント
        
        Returns:
            成功した場合True
        """
        try:
            # すべてのデータを取得
            all_data = self.sheet.get_all_values()
            
            if not all_data or len(all_data) < 2:
                print("データが見つかりません")
                return False
            
            # ヘッダー行
            headers = all_data[0]
            
            # 振り返りコメント列のインデックス
            if '振り返りコメント' not in headers:
                # 列が存在しない場合は追加
                self._add_review_column()
                headers = self.sheet.row_values(1)
            
            if '振り返りコメント' not in headers:
                print("振り返りコメント列の追加に失敗しました")
                return False
            
            comment_col_idx = headers.index('振り返りコメント') + 1
            
            # 取引番号列のインデックス
            if '取引番号' not in headers:
                print("取引番号列が見つかりません")
                return False
            
            trade_id_col_idx = headers.index('取引番号')
            
            # 該当行を探す
            target_row = None
            for row_idx, row_data in enumerate(all_data[1:], start=2):  # ヘッダーをスキップ
                if row_idx <= len(all_data):
                    try:
                        # 取引番号を比較（文字列・数値両方に対応）
                        if trade_id_col_idx < len(row_data):
                            cell_value = str(row_data[trade_id_col_idx]).strip()
                            if cell_value == str(trade_id):
                                target_row = row_idx
                                break
                    except (ValueError, IndexError):
                        continue
            
            if target_row is None:
                print(f"取引番号 {trade_id} が見つかりません")
                return False
            
            # コメントを更新
            self.sheet.update_cell(target_row, comment_col_idx, comment)
            print(f"取引番号 {trade_id} のコメントを更新しました（行: {target_row}, 列: {comment_col_idx}）")
            return True
            
        except Exception as e:
            print(f"コメント更新エラー: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _add_review_column(self):
        """振り返りコメント列を追加"""
        headers = self.sheet.row_values(1)
        if '振り返りコメント' not in headers:
            col_idx = len(headers) + 1
            self.sheet.update_cell(1, col_idx, '振り返りコメント')
    
    def update_strategy_dropdown(self, strategies: List[str]):
        """
        手法列にデータ検証（プルダウン）を設定
        
        Args:
            strategies: 手法名のリスト
        """
        try:
            headers = self.sheet.row_values(1)
            
            # 手法列のインデックスを取得
            if '手法' not in headers:
                # 手法列がなければ追加
                col_idx = len(headers) + 1
                self.sheet.update_cell(1, col_idx, '手法')
                strategy_col_idx = col_idx
            else:
                strategy_col_idx = headers.index('手法') + 1  # gspreadは1ベース
            
            if not strategies:
                print("手法リストが空です")
                return False
            
            # 列の文字（A, B, C...）に変換
            col_letter = chr(64 + strategy_col_idx)  # A=65
            
            # データ検証のルールを設定（2行目以降の全行）
            last_row = max(1000, len(self.sheet.col_values(1)) + 100)  # 余裕を持たせる
            range_name = f'{col_letter}2:{col_letter}{last_row}'
            
            # データ検証を設定
            validation_rule = {
                "requests": [
                    {
                        "setDataValidation": {
                            "range": {
                                "sheetId": self.sheet.id,
                                "startRowIndex": 1,  # 2行目から（0ベース）
                                "endRowIndex": last_row,
                                "startColumnIndex": strategy_col_idx - 1,
                                "endColumnIndex": strategy_col_idx
                            },
                            "rule": {
                                "condition": {
                                    "type": "ONE_OF_LIST",
                                    "values": [{"userEnteredValue": strategy} for strategy in strategies]
                                },
                                "showCustomUi": True,
                                "strict": False
                            }
                        }
                    }
                ]
            }
            
            self.spreadsheet.batch_update(validation_rule)
            print(f"✓ 手法列にプルダウンを設定しました（{len(strategies)}件）")
            print(f"  手法: {', '.join(strategies[:5])}{'...' if len(strategies) > 5 else ''}")
            return True
            
        except Exception as e:
            print(f"プルダウン設定エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_cached_data(self) -> pd.DataFrame:
        """キャッシュされたデータを返す（なければ読み込み）"""
        if self.df is None:
            return self.load_data()
        return self.df
    
    def refresh_data(self) -> pd.DataFrame:
        """データを再読み込み"""
        return self.load_data()


class TradeAnalyzer:
    """トレードデータの分析を行うクラス"""
    
    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: トレードデータのDataFrame
        """
        print(f"TradeAnalyzer初期化: 元データ行数 = {len(df)}")
        self.df = df.copy()
        self._prepare_data()
        print(f"TradeAnalyzer初期化完了: 準備後のデータ行数 = {len(self.df)}")
    
    def _prepare_data(self):
        """分析用のデータを準備"""
        if self.df.empty:
            return
        
        # 勝ち/負けのフラグ
        self.df['is_win'] = self.df['net_profit_loss_jpy'] > 0
        
        # 日時関連の特徴量
        if 'start_time' in self.df.columns:
            self.df['hour'] = pd.to_datetime(self.df['start_time']).dt.hour
            self.df['day_of_week'] = pd.to_datetime(self.df['start_time']).dt.dayofweek
            self.df['day_name'] = pd.to_datetime(self.df['start_time']).dt.day_name()
            
            # 市場時間帯の判定
            self.df['market_session'] = self.df['hour'].apply(self._get_market_session)
        
        # 保有時間のカテゴリ化
        if 'holding_time_sec' in self.df.columns:
            self.df['holding_category'] = self.df['holding_time_sec'].apply(
                self._categorize_holding_time
            )
        
        # 累積損益
        if 'net_profit_loss_jpy' in self.df.columns and 'date' in self.df.columns:
            self.df = self.df.sort_values('date')
            self.df['cumulative_profit'] = self.df['net_profit_loss_jpy'].cumsum()
    
    @staticmethod
    def _get_market_session(hour: int) -> str:
        """時間帯から市場セッションを判定（UTC+9基準）"""
        if 9 <= hour < 15:
            return '東京'
        elif 16 <= hour < 24:
            return 'ロンドン'
        elif 0 <= hour < 6 or 22 <= hour < 24:
            return 'ニューヨーク'
        else:
            return 'その他'
    
    @staticmethod
    def _categorize_holding_time(seconds: float) -> str:
        """保有時間をカテゴリ化"""
        if pd.isna(seconds):
            return '不明'
        minutes = seconds / 60
        if minutes < 5:
            return '5分未満'
        elif minutes < 30:
            return '5分〜30分'
        elif minutes < 60:
            return '30分〜1時間'
        else:
            return '1時間以上'
    
    def calculate_metrics(self) -> Dict:
        """主要メトリクスを計算"""
        if self.df.empty:
            return {}
        
        total_trades = len(self.df)
        winning_trades = len(self.df[self.df['is_win']])
        losing_trades = total_trades - winning_trades
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = self.df[self.df['is_win']]['net_profit_loss_jpy'].sum()
        total_loss = abs(self.df[~self.df['is_win']]['net_profit_loss_jpy'].sum())
        
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
        
        avg_pips = self.df['pips'].mean() if 'pips' in self.df.columns else 0
        
        # 最大ドローダウンの計算
        if 'cumulative_profit' in self.df.columns:
            cumulative = self.df['cumulative_profit']
            running_max = cumulative.cummax()
            drawdown = cumulative - running_max
            max_drawdown = abs(drawdown.min())
        else:
            max_drawdown = 0
        
        total_net_profit = self.df['net_profit_loss_jpy'].sum()
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_pips': avg_pips,
            'max_drawdown': max_drawdown,
            'total_net_profit': total_net_profit,
            'total_profit': total_profit,
            'total_loss': total_loss
        }
    
    def analyze_by_strategy(self) -> pd.DataFrame:
        """手法別の分析"""
        if self.df.empty or 'strategy' not in self.df.columns:
            return pd.DataFrame()
        
        # NaNや空文字列を除外
        df_valid = self.df.copy()
        df_valid = df_valid[df_valid['strategy'].notna()]
        df_valid = df_valid[df_valid['strategy'].astype(str).str.strip() != '']
        df_valid = df_valid[df_valid['strategy'].astype(str).str.lower() != 'nan']
        
        if df_valid.empty:
            return pd.DataFrame()
        
        grouped = df_valid.groupby('strategy').agg({
            'net_profit_loss_jpy': ['sum', 'mean', 'count'],
            'pips': 'mean',
            'is_win': 'mean'
        }).round(2)
        
        grouped.columns = ['合計損益', '平均損益', '取引数', '平均pips', '勝率']
        grouped['勝率'] = (grouped['勝率'] * 100).round(2)
        
        return grouped.sort_values('合計損益', ascending=False)
    
    def analyze_by_currency_pair(self) -> pd.DataFrame:
        """通貨ペア別の分析"""
        if self.df.empty or 'currency_pair' not in self.df.columns:
            return pd.DataFrame()
        
        grouped = self.df.groupby('currency_pair').agg({
            'net_profit_loss_jpy': ['sum', 'mean', 'count'],
            'pips': 'mean',
            'is_win': 'mean'
        }).round(2)
        
        grouped.columns = ['合計損益', '平均損益', '取引数', '平均pips', '勝率']
        grouped['勝率'] = (grouped['勝率'] * 100).round(2)
        
        return grouped.sort_values('合計損益', ascending=False)
    
    def analyze_by_time_period(self, period: str = 'M') -> pd.DataFrame:
        """時間軸別の分析（月次/年次）"""
        if self.df.empty or 'date' not in self.df.columns:
            return pd.DataFrame()
        
        df_temp = self.df.copy()
        df_temp['date'] = pd.to_datetime(df_temp['date'])
        df_temp.set_index('date', inplace=True)
        
        grouped = df_temp.resample(period).agg({
            'net_profit_loss_jpy': ['sum', 'count'],
            'is_win': 'mean'
        }).round(2)
        
        grouped.columns = ['合計損益', '取引数', '勝率']
        grouped['勝率'] = (grouped['勝率'] * 100).round(2)
        
        return grouped
    
    def analyze_by_holding_time(self) -> pd.DataFrame:
        """保有時間別の分析"""
        if self.df.empty or 'holding_category' not in self.df.columns:
            return pd.DataFrame()
        
        grouped = self.df.groupby('holding_category').agg({
            'net_profit_loss_jpy': ['sum', 'mean', 'count'],
            'is_win': 'mean'
        }).round(2)
        
        grouped.columns = ['合計損益', '平均損益', '取引数', '勝率']
        grouped['勝率'] = (grouped['勝率'] * 100).round(2)
        
        # カテゴリの順序を設定
        category_order = ['5分未満', '5分〜30分', '30分〜1時間', '1時間以上', '不明']
        grouped = grouped.reindex([c for c in category_order if c in grouped.index])
        
        return grouped
    
    def analyze_by_day_of_week(self) -> pd.DataFrame:
        """曜日別の分析"""
        if self.df.empty or 'day_of_week' not in self.df.columns:
            return pd.DataFrame()
        
        grouped = self.df.groupby('day_name').agg({
            'net_profit_loss_jpy': ['sum', 'mean', 'count'],
            'is_win': 'mean'
        }).round(2)
        
        grouped.columns = ['合計損益', '平均損益', '取引数', '勝率']
        grouped['勝率'] = (grouped['勝率'] * 100).round(2)
        
        # 曜日の順序を設定
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        grouped = grouped.reindex([d for d in day_order if d in grouped.index])
        
        return grouped
    
    def analyze_by_market_session(self) -> pd.DataFrame:
        """市場セッション別の分析"""
        if self.df.empty or 'market_session' not in self.df.columns:
            return pd.DataFrame()
        
        grouped = self.df.groupby('market_session').agg({
            'net_profit_loss_jpy': ['sum', 'mean', 'count'],
            'is_win': 'mean'
        }).round(2)
        
        grouped.columns = ['合計損益', '平均損益', '取引数', '勝率']
        grouped['勝率'] = (grouped['勝率'] * 100).round(2)
        
        return grouped.sort_values('合計損益', ascending=False)
    
    def get_consecutive_losses(self) -> Tuple[int, float, List[Dict]]:
        """連続損失の分析"""
        if self.df.empty:
            return 0, 0, []
        
        df_sorted = self.df.sort_values('date')
        
        max_consecutive = 0
        current_consecutive = 0
        max_loss_amount = 0
        current_loss_amount = 0
        
        loss_streaks = []
        current_streak = []
        
        for idx, row in df_sorted.iterrows():
            if not row['is_win']:
                current_consecutive += 1
                current_loss_amount += abs(row['net_profit_loss_jpy'])
                current_streak.append(row.to_dict())
            else:
                if current_consecutive > 0:
                    if current_consecutive > max_consecutive:
                        max_consecutive = current_consecutive
                        max_loss_amount = current_loss_amount
                    
                    if current_consecutive >= 3:  # 3連敗以上を記録
                        loss_streaks.append({
                            'count': current_consecutive,
                            'total_loss': current_loss_amount,
                            'trades': current_streak.copy()
                        })
                
                current_consecutive = 0
                current_loss_amount = 0
                current_streak = []
        
        # 最後が連敗で終わった場合の処理
        if current_consecutive > 0:
            if current_consecutive > max_consecutive:
                max_consecutive = current_consecutive
                max_loss_amount = current_loss_amount
            
            if current_consecutive >= 3:
                loss_streaks.append({
                    'count': current_consecutive,
                    'total_loss': current_loss_amount,
                    'trades': current_streak.copy()
                })
        
        return max_consecutive, max_loss_amount, loss_streaks
    
    def get_top_losses(self, n: int = 5) -> pd.DataFrame:
        """損失額トップNのトレード"""
        if self.df.empty:
            return pd.DataFrame()
        
        losing_trades = self.df[~self.df['is_win']].copy()
        top_losses = losing_trades.nsmallest(n, 'net_profit_loss_jpy')
        
        return top_losses
    
    def get_filtered_trades(self, filters: Dict) -> pd.DataFrame:
        """フィルタ条件に基づいてトレードを抽出"""
        filtered_df = self.df.copy()
        original_count = len(filtered_df)
        
        print(f"=== フィルター開始 ===")
        print(f"元データ行数: {original_count}")
        print(f"適用するフィルター: {filters}")
        
        # データの実際の値を確認（先頭5行）
        if 'currency_pair' in filtered_df.columns:
            print(f"currency_pair列の実際の値（ユニーク）: {filtered_df['currency_pair'].unique()}")
        
        # 通貨ペアでフィルター
        if 'currency_pair' in filters and filters['currency_pair']:
            if filters['currency_pair'] != 'すべて':
                before_count = len(filtered_df)
                # データは既にクリーニング済みなので直接比較
                filtered_df = filtered_df[
                    filtered_df['currency_pair'] == filters['currency_pair']
                ]
                print(f"通貨ペアフィルター '{filters['currency_pair']}': {before_count} → {len(filtered_df)}")
        
        # タイプでフィルター
        if 'type' in filters and filters['type']:
            if filters['type'] != 'すべて':
                before_count = len(filtered_df)
                # データは既にクリーニング済みなので直接比較
                filtered_df = filtered_df[
                    filtered_df['type'] == filters['type']
                ]
                print(f"タイプフィルター '{filters['type']}': {before_count} → {len(filtered_df)}")
        
        # 手法でフィルター
        if 'strategy' in filters and filters['strategy']:
            if filters['strategy'] != 'すべて':
                before_count = len(filtered_df)
                # データは既にクリーニング済みなので直接比較
                filtered_df = filtered_df[
                    filtered_df['strategy'] == filters['strategy']
                ]
                print(f"手法フィルター '{filters['strategy']}': {before_count} → {len(filtered_df)}")
        
        # 日付範囲でフィルター
        if 'date_range' in filters and filters['date_range']:
            before_count = len(filtered_df)
            start_date, end_date = filters['date_range']
            
            # デバッグ: 日付データの確認
            print(f"日付フィルター範囲: {start_date} ~ {end_date}")
            print(f"データの日付範囲: {pd.to_datetime(filtered_df['date']).min()} ~ {pd.to_datetime(filtered_df['date']).max()}")
            print(f"範囲外の行数: {len(filtered_df[(pd.to_datetime(filtered_df['date']) < pd.to_datetime(start_date)) | (pd.to_datetime(filtered_df['date']) > pd.to_datetime(end_date))])}")
            
            filtered_df = filtered_df[
                (pd.to_datetime(filtered_df['date']) >= pd.to_datetime(start_date)) &
                (pd.to_datetime(filtered_df['date']) <= pd.to_datetime(end_date))
            ]
            print(f"日付フィルター {start_date} ~ {end_date}: {before_count} → {len(filtered_df)}")
        
        if 'profit_range' in filters and filters['profit_range']:
            min_profit, max_profit = filters['profit_range']
            filtered_df = filtered_df[
                (filtered_df['net_profit_loss_jpy'] >= min_profit) &
                (filtered_df['net_profit_loss_jpy'] <= max_profit)
            ]
        
        if 'only_losses' in filters and filters['only_losses']:
            before_count = len(filtered_df)
            filtered_df = filtered_df[~filtered_df['is_win']]
            print(f"負けトレードのみフィルター: {before_count} → {len(filtered_df)}")
        
        print(f"=== フィルター完了: 最終結果 {len(filtered_df)}件 ===\n")
        return filtered_df


class StrategyManager:
    """手法管理クラス - ローカルJSONとGoogle Sheetsの手法を統合管理"""
    
    def __init__(self, strategy_storage=None, sheets_manager=None):
        """
        Args:
            strategy_storage: StrategyStorageインスタンス
            sheets_manager: TradeDataManagerインスタンス
        """
        self.strategy_storage = strategy_storage
        self.sheets_manager = sheets_manager
        self.strategies = {}  # {手法名: {source, rules, ...}}
    
    def load_all_strategies(self) -> Dict[str, Dict]:
        """
        ローカルJSONとGoogle Sheetsから全ての手法を読み込み
        
        Returns:
            統合された手法データ {手法名: {source, rules, ...}}
        """
        self.strategies = {}
        
        print("=== 手法の読み込み開始 ===")
        
        # ローカルJSONから手法を取得
        if self.strategy_storage:
            print("ローカルJSONから手法を取得中...")
            local_strategies = self.strategy_storage.get_all_strategies()
            print(f"ローカルJSONから {len(local_strategies)} 件の手法を取得")
            for name, data in local_strategies.items():
                self.strategies[name] = {
                    'source': 'local',
                    'rules': data.get('rules', ''),
                    'created_time': data.get('created_time'),
                    'last_edited_time': data.get('last_edited_time')
                }
                rules_length = len(data.get('rules', ''))
                print(f"  - {name} (ルール: {rules_length}文字)")
        else:
            print("警告: StrategyStorageが初期化されていません")
        
        # Google Sheetsから手法を取得（トレードデータから抽出）
        if self.sheets_manager and self.sheets_manager.df is not None:
            df = self.sheets_manager.df
            if 'strategy' in df.columns:
                gsheet_strategies = df['strategy'].dropna().unique()
                print(f"Google Sheetsから {len(gsheet_strategies)} 件の手法を発見")
                for strategy_name in gsheet_strategies:
                    strategy_name = str(strategy_name).strip()
                    if strategy_name and strategy_name.lower() != 'nan':
                        # ローカルJSONに既にある場合はスキップ（ローカルを優先）
                        if strategy_name not in self.strategies:
                            self.strategies[strategy_name] = {
                                'source': 'sheets',
                                'rules': '',
                            }
                            print(f"  - {strategy_name} (Google Sheetsのみ)")
        
        print(f"=== 手法を {len(self.strategies)} 件読み込みました ===")
        return self.strategies
    
    def get_strategy_list(self) -> List[str]:
        """手法名のリストを取得"""
        return sorted(list(self.strategies.keys()))
    
    def get_strategy_rules(self, strategy_name: str) -> str:
        """特定の手法のルールを取得"""
        if strategy_name in self.strategies:
            return self.strategies[strategy_name].get('rules', '')
        return ''
    
    def save_strategy_rules(self, strategy_name: str, rules: str) -> bool:
        """
        手法のルールを保存（ローカルJSONに保存）
        
        Args:
            strategy_name: 手法名
            rules: ルール内容
        
        Returns:
            成功時True
        """
        if not self.strategy_storage:
            print("エラー: StrategyStorageが初期化されていません")
            return False
        
        print(f"手法 '{strategy_name}' のルールを保存中...")
        print(f"  ルールの長さ: {len(rules)}文字")
        
        # ローカルJSONに保存
        success = self.strategy_storage.sync_strategy(strategy_name, rules)
        
        if success:
            # ローカルキャッシュも更新
            if strategy_name not in self.strategies:
                self.strategies[strategy_name] = {'source': 'local'}
            self.strategies[strategy_name]['rules'] = rules
            print(f"✓ ルールの保存に成功しました")
            
            # Google Sheetsのプルダウンを更新
            self._update_sheets_dropdown()
        else:
            print(f"✗ ルールの保存に失敗しました")
        
        return success
    
    def add_new_strategy(self, strategy_name: str, rules: str = "") -> bool:
        """
        新しい手法を追加
        
        Args:
            strategy_name: 手法名
            rules: ルール内容
        
        Returns:
            成功時True
        """
        if not strategy_name or not strategy_name.strip():
            return False
        
        strategy_name = strategy_name.strip()
        
        # 既に存在する場合
        if strategy_name in self.strategies:
            print(f"手法 '{strategy_name}' は既に存在します")
            return False
        
        # ローカルJSONに追加
        if self.strategy_storage:
            success = self.strategy_storage.create_strategy(strategy_name, rules)
            if success:
                self.strategies[strategy_name] = {
                    'source': 'local',
                    'rules': rules
                }
                
                # Google Sheetsのプルダウンを更新
                self._update_sheets_dropdown()
                
                return True
        
        return False
    
    def _update_sheets_dropdown(self):
        """Google Sheetsの手法プルダウンを更新"""
        if self.sheets_manager:
            try:
                strategies_list = self.get_strategy_list()
                if strategies_list:
                    self.sheets_manager.update_strategy_dropdown(strategies_list)
                else:
                    print("手法リストが空のため、プルダウン更新をスキップしました")
            except AttributeError as e:
                print(f"警告: sheets_managerにupdate_strategy_dropdownメソッドがありません: {e}")
            except Exception as e:
                print(f"警告: プルダウン更新中にエラーが発生しました: {e}")
        else:
            print("sheets_managerが設定されていないため、プルダウン更新をスキップしました")
