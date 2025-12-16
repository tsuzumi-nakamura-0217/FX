"""
Google Spreadsheetの初期セットアップを行うスクリプト
使い方: python setup_spreadsheet.py
"""
import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

def setup_spreadsheet():
    """スプレッドシートに正しいヘッダーを設定"""
    
    # 設定の読み込み
    credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'credentials.json')
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '')
    
    if not os.path.exists(credentials_file):
        print(f"❌ エラー: 認証ファイルが見つかりません: {credentials_file}")
        print("Google Cloud Consoleからサービスアカウントのキーをダウンロードしてください")
        return False
    
    if not spreadsheet_id:
        print("❌ エラー: スプレッドシートIDが設定されていません")
        print(".envファイルにGOOGLE_SHEETS_SPREADSHEET_IDを設定してください")
        return False
    
    print("📊 Google Spreadsheetのセットアップを開始します...")
    
    # 認証
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    try:
        creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        print(f"✅ スプレッドシート '{spreadsheet.title}' に接続しました")
        
        # 最初のシートを取得
        try:
            sheet = spreadsheet.sheet1
        except:
            print("📝 新しいシートを作成しています...")
            sheet = spreadsheet.add_worksheet(title="取引履歴", rows=1000, cols=20)
        
        print(f"✅ シート '{sheet.title}' を使用します")
        
        # 正しいヘッダーを設定
        headers = [
            "取引番号",
            "通貨ペア",
            "タイプ",
            "ロット",
            "開始時刻",
            "終了時刻",
            "日付",
            "損益",
            "pips",
            "保有時間(秒)",
            "手数料",
            "スワップ",
            "合計損益",
            "同期日時",
            "手法",
            "振り返りコメント"
        ]
        
        # 既存のデータを確認
        existing_data = sheet.get_all_values()
        
        if existing_data and len(existing_data) > 1:
            print("⚠️  警告: シートには既にデータが存在します")
            response = input("既存のヘッダー行を上書きしますか？ (y/n): ")
            
            if response.lower() != 'y':
                print("❌ キャンセルしました")
                return False
        
        # ヘッダー行を設定
        print("📝 ヘッダー行を設定しています...")
        sheet.update('A1:P1', [headers])
        
        # ヘッダー行のフォーマット
        print("🎨 フォーマットを適用しています...")
        sheet.format('A1:P1', {
            "textFormat": {
                "bold": True,
                "fontSize": 11
            },
            "backgroundColor": {
                "red": 0.2,
                "green": 0.4,
                "blue": 0.8
            },
            "textFormat": {
                "foregroundColor": {
                    "red": 1.0,
                    "green": 1.0,
                    "blue": 1.0
                },
                "bold": True
            },
            "horizontalAlignment": "CENTER"
        })
        
        # 列幅の調整
        print("📏 列幅を調整しています...")
        sheet.columns_auto_resize(0, 15)
        
        # 最初の行を固定
        sheet.freeze(rows=1)
        
        print("\n✅ セットアップが完了しました！")
        print(f"\n📋 設定されたヘッダー:")
        for i, header in enumerate(headers, 1):
            print(f"  {i}. {header}")
        
        print(f"\n🔗 スプレッドシートURL:")
        print(f"   https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
        
        print("\n💡 次のステップ:")
        print("1. スプレッドシートにトレードデータを入力")
        print("2. アプリを起動: streamlit run app.py")
        print("3. サンプルデータを生成: python generate_sample_data.py")
        
        return True
        
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ エラー: スプレッドシートが見つかりません (ID: {spreadsheet_id})")
        print("スプレッドシートIDが正しいか確認してください")
        return False
        
    except gspread.exceptions.APIError as e:
        print(f"❌ Google Sheets APIエラー: {e}")
        print("サービスアカウントにスプレッドシートへのアクセス権限があるか確認してください")
        return False
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return False


def main():
    """メイン処理"""
    print("=" * 60)
    print("   FXトレードアプリ - Google Spreadsheet セットアップ")
    print("=" * 60)
    print()
    
    success = setup_spreadsheet()
    
    if success:
        print("\n🎉 セットアップが成功しました！")
    else:
        print("\n😢 セットアップに失敗しました")
        print("\nトラブルシューティング:")
        print("1. credentials.json が存在するか確認")
        print("2. .env ファイルの設定を確認")
        print("3. サービスアカウントに共有権限があるか確認")


if __name__ == "__main__":
    main()
