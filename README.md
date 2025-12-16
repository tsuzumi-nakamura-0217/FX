# FXトレード記録・資産管理アプリケーション

## 概要
MT5の取引記録を分析・可視化するStreamlitベースのWebアプリケーション

**macOS対応**: MT5のレポートファイル（HTML/CSV）を読み込んで分析します

## 主な機能
- 📊 トレード履歴の可視化とダッシュボード表示
- 📈 損益チャートと統計分析
- 💼 資産推移のトラッキング
- 📝 トレード戦略の管理とテンプレート化
- 🔄 Notionデータベースとの連携
- 📄 Google Sheetsへのエクスポート（オプション）
- 📑 MT5レポートファイル（HTML/CSV）の自動解析

## セットアップ

### 1. 必要なパッケージのインストール
```bash
# 仮想環境の作成（推奨）
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 依存パッケージのインストール
pip install -r requirements.txt
```

### 2. 環境変数の設定
`.env`ファイルを作成し、以下の情報を設定：

```bash
# Notion API情報（オプション）
NOTION_API_KEY=your_notion_integration_token
NOTION_DATABASE_ID=your_database_id

# Google Sheets連携（オプション）
GOOGLE_SHEETS_ENABLED=false
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```


### 3. Notion設定（オプション）

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

## 使い方

### アプリケーションの起動
```bash
# 仮想環境をアクティベート（未アクティベートの場合）
source .venv/bin/activate

# Streamlitアプリの起動
streamlit run app.py
```

ブラウザが自動的に開き、`http://localhost:8501`でアプリが表示されます。

### MT5からレポートをエクスポート

1. **MT5アプリを開く**
2. **「ターミナル」→「口座履歴」タブ** を選択
3. 右クリック→**「期間のカスタム設定」** で期間を選択
4. 右クリック→**「レポートの保存」**
5. HTML形式またはCSV形式で保存
6. 保存したファイルを`reports/`フォルダに配置

### アプリの機能

#### 📊 ダッシュボード
- トレード統計の概要表示
- 損益チャート
- 通貨ペア別パフォーマンス

#### 📈 トレード分析
- 個別トレードの詳細表示
- フィルタリングと検索機能
- データのエクスポート

#### 💼 資産管理
- 資産推移のトラッキング
- 入出金履歴の記録

#### 📝 戦略管理
- トレード戦略のテンプレート作成
- 戦略ルールの定義と保存
- 戦略別パフォーマンス分析
## ファイル構成

```
FX/
├── app.py                    # Streamlitメインアプリケーション
├── src/
│   ├── main.py              # バックエンドメインスクリプト
│   ├── data_manager.py      # データ管理・分析クラス
│   ├── mt5_report_parser.py # MT5レポートパーサー
│   ├── mt5_connector.py     # MT5データ取得
│   ├── notion_db.py         # Notion API クライアント
│   ├── sheets_client.py     # Google Sheets クライアント
│   ├── strategy_storage.py  # 戦略データ保存
│   ├── strategy_page.py     # 戦略管理UI
│   └── config.py            # 設定管理
├── reports/                 # MT5レポートファイル保存先
├── logs/                    # ログファイル
├── strategies.json          # 戦略データ保存
├── .env                     # 環境変数（要作成）
├── credentials.json         # Google認証情報（オプション）
├── requirements.txt         # 依存パッケージ
├── setup_spreadsheet.py     # Google Sheets初期設定スクリプト
└── README.md
```

## トラブルシューティング

### アプリが起動しない
- Python仮想環境がアクティベートされているか確認
- `pip install -r requirements.txt`で依存パッケージがインストールされているか確認
- ポート8501が既に使用されていないか確認

### レポートファイルが見つからない
1. `reports/` フォルダを作成: `mkdir reports`
2. MT5からHTMLまたはCSVレポートをエクスポート
3. `reports/` フォルダに保存

### レポートが正しく解析されない
- MT5で「Detailed Statement (HTML)」形式を選択してください
- CSV形式も対応していますが、HTML形式の方が推奨です

### Notionに書き込めない
- `.env`ファイルにNotionの設定が正しく記載されているか確認
- インテグレーショントークンが有効か確認
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
- レポートファイルベースの分析方式です
- MT5アプリは必要ですが、Python経由での直接接続は不要です

## 依存パッケージ

主要なパッケージ：
- **streamlit**: Webアプリケーションフレームワーク
- **pandas**: データ分析
- **plotly**: インタラクティブなグラフ作成
- **notion-client**: Notion API連携
- **gspread**: Google Sheets連携
- その他の詳細は[requirements.txt](requirements.txt)を参照

## ライセンス

このプロジェクトは個人使用を目的としています。

## お問い合わせ

問題が発生した場合は、GitHubのIssuesで報告してください。
