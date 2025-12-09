# XMTrading MT5 → Notion 自動同期システム

## 概要
XMTrading（MT5）の取引記録を自動でNotionに同期するPythonアプリケーション

**macOS対応**: MT5のレポートファイル（HTML/CSV）を読み込んで同期します

## 機能
- MT5レポートファイル（HTML/CSV）から取引履歴を解析
- Notionデータベースへの自動記録
- 重複チェック（既存の取引はスキップ）
- 定期実行のサポート

## セットアップ

### 1. 必要なパッケージのインストール
```bash


```

### 2. 環境変数の設定
`.env`ファイルを作成し、以下の情報を設定：

# Notion API情報
NOTION_API_KEY=your_notion_integration_token
NOTION_DATABASE_ID=your_database_id

# Google Sheets連携（オプション）
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id


### 3. Notion設定

#### 3.1 Notionインテグレーションの作成
1. https://www.notion.so/my-integrations にアクセス
2. 「新しいインテグレーション」を作成
3. トークンをコピーして`.env`に設定

#### 3.2 Notionデータベースの作成
データベースには以下のプロパティを作成してください：
- **取引番号** (タイトル)
- **通貨ペア** (セレクト)
- **タイプ** (セレクト: Buy/Sell)
- **ロット** (数値)
- **開始時刻** (日付)
- **終了時刻** (日付)
- **損益** (数値)


#### 3.3 データベースIDの取得
1. Notionでデータベースを開く
2. URLから`https://www.notion.so/workspace/{database_id}?v=...`の`database_id`部分をコピー
3. `.env`に設定

#### 3.4 インテグレーションへのアクセス許可
1. データベースページの右上「...」→「接続」
2. 作成したインテグレーションを選択

### 4. Google Sheets設定（オプション）

NotionだけでなくGoogle Spreadsheetsにも同期したい場合は以下を設定してください。

#### 4.1 Google Cloud プロジェクトの作成
1. https://console.cloud.google.com/ にアクセス
2. 新しいプロジェクトを作成
3. 「APIとサービス」→「ライブラリ」で以下のAPIを有効化：
   - Google Sheets API
   - Google Drive API

#### 4.2 サービスアカウントの作成
1. 「APIとサービス」→「認証情報」
2. 「認証情報を作成」→「サービスアカウント」
3. サービスアカウント名を入力して作成
4. 作成したサービスアカウントをクリック
5. 「キー」タブ→「鍵を追加」→「新しい鍵を作成」
6. JSON形式を選択してダウンロード
7. ダウンロードしたファイルを`credentials.json`という名前でプロジェクトルートに保存

#### 4.3 スプレッドシートの準備
1. Google Sheetsで新しいスプレッドシートを作成
2. URLから`https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit`の`spreadsheet_id`部分をコピー
3. `.env`に設定
4. スプレッドシートを開き、右上の「共有」ボタンをクリック
5. サービスアカウントのメールアドレス（`xxx@xxx.iam.gserviceaccount.com`）を追加
6. 「編集者」権限を付与

#### 4.4 .envファイルに設定を追加
```bash
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```

**注意**: `credentials.json`はGitにコミットしないでください（`.gitignore`に追加推奨）

## 使い方

### 手動実行
```bash
python src/main.py
```
## 使い方

### MT5からレポートをエクスポート

1. **MT5アプリを開く**
2. **「ターミナル」→「口座履歴」タブ** を選択
3. 右クリック→**「期間のカスタム設定」** で期間を選択
### 定期実行（自動化）

#### 方法1: launchd（macOS推奨）
## ファイル構成

FX/
├── src/
│   ├── main.py              # メインスクリプト
│   ├── mt5_report_parser.py # MT5レポートパーサー
│   ├── notion_client.py     # Notion API クライアント
│   └── config.py            # 設定管理
├── reports/                 # MT5レポートファイル保存先
├── logs/                    # ログファイル
├── .env                     # 環境変数（要作成）
├── requirements.txt         # 依存パッケージ
└── README.md

## トラブルシューティング

### レポートファイルが見つからない
1. `reports/` フォルダを作成: `mkdir reports`
2. MT5からHTMLレポートをエクスポート
3. `reports/` フォルダに保存

### レポートが正しく解析されない
- MT5で「Detailed Statement (HTML)」形式を選択してください
- CSVフォーマットも対応していますが、HTMLの方が推奨です

### Notionに書き込めない
- インテグレーショントークンが正しいか確認
- データベースIDが正しいか確認
- インテグレーションがデータベースへのアクセス権を持っているか確認

### Google Sheetsに同期できない
- `GOOGLE_SHEETS_ENABLED=true`が設定されているか確認
- `credentials.json`ファイルがプロジェクトルートに存在するか確認
- スプレッドシートIDが正しいか確認
- サービスアカウントがスプレッドシートへの編集権限を持っているか確認
- Google Sheets APIとGoogle Drive APIが有効化されているか確認

### macOSでの注意点
- MetaTrader5 Pythonパッケージは使用しません（Windows専用のため）
- レポートファイルベースの同期方式です
- MT5アプリは必要ですが、Python経由での直接接続は不要です

## ファイル構成
```
FX/
├── src/
│   ├── main.py              # メインスクリプト
│   ├── mt5_connector.py     # MT5接続・データ取得
│   ├── notion_client.py     # Notion API クライアント
│   └── config.py            # 設定管理
├── logs/                    # ログファイル
├── .env                     # 環境変数（要作成）
├── .env.example            # 環境変数のサンプル
├── requirements.txt         # 依存パッケージ
└── README.md
```

## トラブルシューティング

### MT5に接続できない
- MT5アプリケーションが起動しているか確認
- ログイン情報が正しいか確認
- サーバー名が正しいか確認（XMTrading-MT5の後に数字がつく場合があります）

### Notionに書き込めない
- インテグレーショントークンが正しいか確認
- データベースIDが正しいか確認
- インテグレーションがデータベースへのアクセス権を持っているか確認
