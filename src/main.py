#!/usr/bin/env python3
"""
XMTrading MT5 → Notion 自動同期スクリプト

MT5から取引履歴を取得し、Notionデータベースに自動で記録します。
"""
import sys
import os
from datetime import datetime
from config import Config
from mt5_report_parser import MT5ReportParser
from notion_db import NotionClient
from sheets_client import SheetsClient

def find_latest_report(reports_dir: str = 'reports') -> str:
    """最新のMT5レポートファイルを探す"""
    if not os.path.exists(reports_dir):
        return None
    
    files = []
    for file in os.listdir(reports_dir):
        if file.endswith(('.html', '.csv')):
            file_path = os.path.join(reports_dir, file)
            mtime = os.path.getmtime(file_path)
            files.append((file_path, mtime))
    
    if not files:
        return None
    
    # 最新のファイルを返す
    files.sort(key=lambda x: x[1], reverse=True)
    return files[0][0]


def main(report_file: str = None):
    """メイン処理"""
    print("=" * 60)
    print("XMTrading MT5 → Notion 自動同期")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 設定の検証（NotionのみでOK）
        print("\n[1/3] 設定を確認中...")
        if not Config.NOTION_API_KEY or not Config.NOTION_DATABASE_ID:
            raise ValueError("NOTION_API_KEYとNOTION_DATABASE_IDが必要です")
        print("✓ 設定OK")
        
        # レポートファイルを探す
        print("\n[2/3] MT5レポートファイルを読み込み中...")
        
        if not report_file:
            report_file = find_latest_report()
        
        if not report_file:
            print("✗ レポートファイルが見つかりません")
            print("\nMT5で以下の手順でレポートをエクスポートしてください：")
            print("1. MT5アプリを開く")
            print("2. 「ターミナル」→「口座履歴」タブを選択")
            print("3. 右クリック→「期間のカスタム設定」で期間を選択")
            print("4. 右クリック→「レポートの保存」→「Detailed Statement (HTML)」")
            print("5. reports/ フォルダに保存")
            print("\nまたは、ファイルパスを指定して実行:")
            print("  python src/main.py /path/to/report.html")
            return 1
        
        print(f"レポートファイル: {report_file}")
        
        # レポートを解析
        parser = MT5ReportParser()
        
        if report_file.endswith('.html'):
            trades = parser.parse_html_report(report_file)
        elif report_file.endswith('.csv'):
            trades = parser.parse_csv_report(report_file)
        else:
            print("✗ サポートされていないファイル形式です")
            print("対応形式: .html, .csv")
            return 1
        
        if not trades:
            print("取引データが見つかりませんでした")
            return 0
        
        # Notionに同期
        print("\n[3/3] Notionに同期中...")
        notion = NotionClient(
            api_key=Config.NOTION_API_KEY,
            database_id=Config.NOTION_DATABASE_ID
        )
        
        stats, ticket_to_url = notion.sync_trades(trades)
        
        # 結果表示
        print("\n" + "=" * 60)
        print("【Notion同期結果】")
        if stats['new'] > 0:
            print(f"✓ {stats['new']}件の新しい取引を記録しました")
        else:
            print("新しい取引はありませんでした")
        print("=" * 60)
        
        # Google Sheetsに同期（オプション）
        if Config.GOOGLE_SHEETS_ENABLED:
            print("\n[4/4] Google Sheetsに同期中...")
            try:
                if not Config.GOOGLE_SHEETS_SPREADSHEET_ID:
                    print("⚠ GOOGLE_SHEETS_SPREADSHEET_IDが設定されていません（スキップ）")
                elif not Config.GOOGLE_SHEETS_CREDENTIALS_FILE:
                    print("⚠ GOOGLE_SHEETS_CREDENTIALS_FILEが設定されていません（スキップ）")
                else:
                    sheets = SheetsClient(
                        credentials_file=Config.GOOGLE_SHEETS_CREDENTIALS_FILE,
                        spreadsheet_id=Config.GOOGLE_SHEETS_SPREADSHEET_ID
                    )
                    
                    # NotionページURLのマッピングを渡す
                    sheets_stats = sheets.sync_trades(trades, ticket_to_url)
                    
                    print("\n" + "=" * 60)
                    print("【Google Sheets同期結果】")
                    if sheets_stats['new'] > 0:
                        print(f"✓ {sheets_stats['new']}件の新しい取引を記録しました")
                        if ticket_to_url:
                            print(f"  ({len(ticket_to_url)}件にNotionリンクを設定)")
                    else:
                        print("新しい取引はありませんでした")
                    print("=" * 60)
                    
            except FileNotFoundError as e:
                print(f"⚠ 認証ファイルが見つかりません: {e}")
                print("  Google Sheets連携の設定を確認してください")
            except Exception as e:
                print(f"⚠ Google Sheets同期でエラーが発生しました: {e}")
                print("  Notionへの同期は完了しています")
        
        return 0
    
    except ValueError as e:
        print(f"\n✗ {e}")
        print("\n.envファイルを確認してください。")
        print("詳細はREADME.mdを参照してください。")
        return 1
    
    except Exception as e:
        print(f"\n✗ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    # コマンドライン引数からレポートファイルパスを取得
    report_file = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(main(report_file))
