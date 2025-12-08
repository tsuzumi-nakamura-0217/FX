"""設定管理モジュール"""
import os
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

class Config:
    """環境変数から設定を読み込むクラス"""
    
    # Notion設定
    NOTION_API_KEY = os.getenv('NOTION_API_KEY', '')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID', '')
    
    # Google Sheets設定
    GOOGLE_SHEETS_ENABLED = os.getenv('GOOGLE_SHEETS_ENABLED', 'false').lower() == 'true'
    GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'credentials.json')
    GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '')
    
    @classmethod
    def validate(cls):
        """設定値の検証"""
        errors = []
        
        if not cls.NOTION_API_KEY:
            errors.append('NOTION_API_KEYが設定されていません')
        if not cls.NOTION_DATABASE_ID:
            errors.append('NOTION_DATABASE_IDが設定されていません')
        
        if errors:
            raise ValueError('設定エラー:\n' + '\n'.join(errors))
        
        return True
