"""FXトレード記録・資産管理アプリケーション（メインファイル）"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
from src.data_manager import TradeDataManager, TradeAnalyzer, StrategyManager
from src.config import Config
from src.strategy_storage import StrategyStorage
from src.strategy_page import strategy_management_page_new

# ページ設定（最初に一度だけ呼ばれる）
st.set_page_config(
    page_title="FXトレード分析アプリ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッションステートの初期化
if 'strategy_rules' not in st.session_state:
    st.session_state.strategy_rules = {}
if 'strategy_templates' not in st.session_state:
    st.session_state.strategy_templates = {}
if 'strategy_manager' not in st.session_state:
    st.session_state.strategy_manager = None
if 'strategy_storage' not in st.session_state:
    st.session_state.strategy_storage = None

# カスタムCSS - 最新モダンデザイン
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Streamlitデフォルト要素を非表示 */
    header[data-testid="stHeader"] {
        display: none;
    }
    
    .main .block-container {
        padding-top: 0;
        padding-bottom: 4rem;
        max-width: 100%;
    }
    
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }
    
    /* スティッキーヘッダー */
    .fixed-header-container {
        position: -webkit-sticky !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 9999 !important;
        background: rgba(255, 255, 255, 0.98) !important;
        backdrop-filter: blur(25px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(25px) saturate(180%) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1) !important;
        border-bottom: 1px solid rgba(226, 232, 240, 0.5) !important;
        padding: 1rem 3rem !important;
        margin: -2rem -3rem 2rem -3rem !important;
        width: calc(100% + 6rem) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    /* スクロール時のヘッダースタイル */
    .fixed-header-container.scrolled {
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15) !important;
        background: rgba(255, 255, 255, 1) !important;
    }

    /* marker自体は高さを取らない */
    .fixed-header-container > div[data-testid="stMarkdown"] {
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* ヘッダー行（columnsの横並び）を"header-content"相当に整形 */
    .fixed-header-container > div[data-testid="stHorizontalBlock"] {
        max-width: 1800px;
        margin: 0 auto;
        min-height: 72px;
        align-items: center !important;
        gap: 2rem;
    }
    
    .header-brand {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-shrink: 0;
    }
    
    .brand-logo {
        font-size: 1.75rem;
        filter: drop-shadow(0 2px 4px rgba(102, 126, 234, 0.3));
    }
    
    .brand-title {
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.03em;
        margin: 0;
        white-space: nowrap;
    }
    
    .header-center {
        flex: 1;
        display: flex;
        justify-content: center;
    }
    
    .header-actions {
        flex-shrink: 0;
    }
    
    /* ヘッダー内のナビゲーション（radio） */
    .fixed-header-container .stRadio > div {
        background: rgba(249, 250, 251, 0.8);
        padding: 0.375rem;
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }

    .fixed-header-container .stRadio [role="radiogroup"] {
        gap: 0.5rem;
        display: flex;
        flex-wrap: nowrap;
        justify-content: center;
    }

    .fixed-header-container .stRadio [role="radiogroup"] > label {
        background: transparent;
        padding: 0.55rem 1.0rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        color: #6b7280;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        border: none;
        white-space: nowrap;
    }

    .fixed-header-container .stRadio [role="radiogroup"] > label:hover {
        background: rgba(255, 255, 255, 0.8);
        color: #111827;
        transform: translateY(-1px);
    }

    .fixed-header-container .stRadio [role="radiogroup"] > label[data-checked="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* ヘッダー内の更新ボタン */
    .fixed-header-container .stButton > button {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 0.875rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);
        white-space: nowrap;
    }

    .fixed-header-container .stButton > button:hover {
        background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(245, 158, 11, 0.4);
    }

    
    /* スペーサー */
    .header-spacer {
        height: 88px;
    }
    
    /* コンテンツエリア */
    .content-wrapper {
        max-width: 1800px;
        margin: 0 auto;
        padding: 2rem 3rem;
    }
    
    /* カード */
    .modern-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.18);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .modern-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 30px 80px rgba(0, 0, 0, 0.16);
    }
    
    /* タイトル */
    h1 {
        color: #ffffff;
        font-weight: 800;
        font-size: 2.5rem;
        letter-spacing: -0.03em;
        margin-bottom: 1.5rem;
        text-shadow: 0 2px 20px rgba(0, 0, 0, 0.15);
    }
    
    h2 {
        color: #111827;
        font-weight: 700;
        font-size: 1.75rem;
        letter-spacing: -0.025em;
        margin-top: 2.5rem;
        margin-bottom: 1.25rem;
    }
    
    h3 {
        color: #374151;
        font-weight: 600;
        font-size: 1.25rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    
    /* メトリック */
    [data-testid="stMetricValue"] {
        font-size: 2.25rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    [data-testid="stMetricLabel"] {
        color: #6b7280;
        font-size: 0.8125rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    
    .stMetric {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        padding: 1.75rem;
        border-radius: 16px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.18);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .stMetric:hover {
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 20px 60px rgba(102, 126, 234, 0.2);
    }
    
    /* 通常ボタン */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 0.875rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        letter-spacing: -0.0125em;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* データフレーム */
    [data-testid="stDataFrame"] {
        background: white;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(226, 232, 240, 0.8);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
    }
    
    [data-testid="stDataFrame"] th {
        background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%) !important;
        color: #374151 !important;
        font-weight: 700 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        padding: 1rem !important;
        border-bottom: 2px solid #e5e7eb !important;
    }
    
    [data-testid="stDataFrame"] td {
        padding: 0.875rem !important;
        border-bottom: 1px solid #f3f4f6 !important;
        font-size: 0.875rem;
    }
    
    /* タブ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(255, 255, 255, 0.6);
        padding: 0.5rem;
        border-radius: 12px;
        border: none;
        backdrop-filter: blur(10px);
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.875rem 1.5rem;
        font-weight: 600;
        font-size: 0.875rem;
        color: #6b7280;
        border-radius: 8px;
        border: none;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #111827;
        background: rgba(255, 255, 255, 0.8);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    /* インプット */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div,
    .stDateInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #e5e7eb;
        font-size: 0.875rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        background: white;
        padding: 0.75rem 1rem;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div:focus,
    .stDateInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: 12px;
        font-weight: 600;
        color: #374151;
        padding: 1rem 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .streamlit-expanderHeader:hover {
        background: white;
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }
    
    /* Divider */
    hr {
        margin: 3rem 0;
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
    }
    
    /* アラート */
    [data-testid="stInfo"],
    [data-testid="stWarning"],
    [data-testid="stError"],
    [data-testid="stSuccess"] {
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        border: 1px solid;
        backdrop-filter: blur(10px);
        font-weight: 500;
    }
    
    [data-testid="stInfo"] {
        background: rgba(239, 246, 255, 0.9);
        border-color: #93c5fd;
        color: #1e40af;
    }
    
    [data-testid="stWarning"] {
        background: rgba(254, 243, 199, 0.9);
        border-color: #fcd34d;
        color: #92400e;
    }
    
    [data-testid="stError"] {
        background: rgba(254, 226, 226, 0.9);
        border-color: #fca5a5;
        color: #991b1b;
    }
    
    [data-testid="stSuccess"] {
        background: rgba(209, 250, 229, 0.9);
        border-color: #6ee7b7;
        color: #065f46;
    }
    
    /* Plotlyチャート */
    .js-plotly-plot {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_data_manager():
    """データマネージャーのシングルトンインスタンスを取得"""
    credentials_file = Config.GOOGLE_SHEETS_CREDENTIALS_FILE
    spreadsheet_id = Config.GOOGLE_SHEETS_SPREADSHEET_ID
    
    if not os.path.exists(credentials_file):
        st.error(f"認証ファイルが見つかりません: {credentials_file}")
        return None
    
    if not spreadsheet_id:
        st.error("スプレッドシートIDが設定されていません")
        return None
    
    return TradeDataManager(credentials_file, spreadsheet_id)


@st.cache_resource
def get_strategy_storage():
    """StrategyStorageのシングルトンインスタンスを取得"""
    try:
        print("StrategyStorageを初期化中...")
        storage = StrategyStorage(json_path="strategies.json")
        print("✓ StrategyStorage初期化完了")
        return storage
    except Exception as e:
        st.error(f"StrategyStorage初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_strategy_manager():
    """StrategyManagerのインスタンスを取得（キャッシュ付き）"""
    if st.session_state.strategy_manager is None:
        print("StrategyManagerを初期化中...")
        strategy_storage = get_strategy_storage()
        data_manager = get_data_manager()
        
        if strategy_storage:
            print("  ✓ StrategyStorage: 有効")
        else:
            print("  ✗ StrategyStorage: 無効")
        
        if data_manager:
            print("  ✓ データマネージャー: 有効")
        else:
            print("  ✗ データマネージャー: 無効")
        
        st.session_state.strategy_manager = StrategyManager(strategy_storage, data_manager)
        print("✓ StrategyManager初期化完了")
    
    return st.session_state.strategy_manager


def load_data():
    """データを読み込む"""
    data_manager = get_data_manager()
    if data_manager is None:
        return None
    
    try:
        with st.spinner('データを読み込んでいます...'):
            df = data_manager.load_data()
            
        # データの検証
        if df is not None and not df.empty:
            st.success(f"✅ {len(df)}件のトレードデータを読み込みました")
        
        return df
    except Exception as e:
        st.error(f"❌ データ読み込みエラー: {str(e)}")
        
        # 詳細なエラーメッセージ
        with st.expander("🔍 トラブルシューティング"):
            st.write("**考えられる原因:**")
            st.write("1. スプレッドシートのヘッダー行が正しく設定されていない")
            st.write("2. 空の列がヘッダー行に含まれている")
            st.write("3. サービスアカウントに権限がない")
            st.write("")
            st.write("**解決方法:**")
            st.write("1. スプレッドシートの1行目に以下のヘッダーを設定:")
            st.code("取引番号, 通貨ペア, タイプ, ロット, 開始時刻, 終了時刻, 日付, 損益, pips, 保有時間(秒), 手数料, スワップ, 合計損益, 同期日時, 手法, 振り返りコメント")
            st.write("2. 空の列を削除")
            st.write("3. サービスアカウントに編集権限を付与")
            st.write("")
            st.write(f"**エラー詳細:** {str(e)}")
        
        return None


def dashboard_page():
    """ダッシュボードページ"""
    st.title("📊 ダッシュボード")
    
    df = load_data()
    if df is None:
        return
    
    if df.empty:
        st.warning("⚠️ データがありません。")
        st.info("""
        **次のステップ:**
        1. Google Spreadsheetにトレードデータを入力
        2. サイドバーの「🔄 データ更新」ボタンをクリック
        
        **サンプルデータを生成する場合:**
        ```bash
        python generate_sample_data.py
        ```
        """)
        return
    
    analyzer = TradeAnalyzer(df)
    metrics = analyzer.calculate_metrics()
    
    # メトリクス表示
    st.subheader("📈 主要メトリクス")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="総取引回数",
            value=f"{metrics['total_trades']:,}回"
        )
        st.metric(
            label="勝率",
            value=f"{metrics['win_rate']:.2f}%"
        )
    
    with col2:
        profit_color = "normal" if metrics['total_net_profit'] >= 0 else "inverse"
        st.metric(
            label="総損益",
            value=f"¥{metrics['total_net_profit']:,.0f}",
            delta=None,
            delta_color=profit_color
        )
        st.metric(
            label="プロフィットファクター",
            value=f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] != float('inf') else "∞"
        )
    
    with col3:
        st.metric(
            label="平均獲得pips",
            value=f"{metrics['avg_pips']:.2f}"
        )
        st.metric(
            label="最大ドローダウン",
            value=f"¥{metrics['max_drawdown']:,.0f}"
        )
    
    with col4:
        st.metric(
            label="勝ちトレード",
            value=f"{metrics['winning_trades']:,}回"
        )
        st.metric(
            label="負けトレード",
            value=f"{metrics['losing_trades']:,}回"
        )
    
    st.divider()
    
    # 累積損益グラフ
    st.subheader("💰 累積損益推移（資産曲線）")
    
    if 'cumulative_profit' in analyzer.df.columns and 'date' in analyzer.df.columns:
        fig = go.Figure()
        
        df_sorted = analyzer.df.sort_values('date')
        
        fig.add_trace(go.Scatter(
            x=df_sorted['date'],
            y=df_sorted['cumulative_profit'],
            mode='lines+markers',
            name='累積損益',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=6),
            hovertemplate='<b>日付</b>: %{x}<br><b>累積損益</b>: ¥%{y:,.0f}<extra></extra>'
        ))
        
        # ゼロライン
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig.update_layout(
            title="累積損益の推移",
            xaxis_title="日付",
            yaxis_title="累積損益 (円)",
            hovermode='x unified',
            height=500,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # グラフ上のポイントをクリックした際の詳細（インタラクティブ機能の提案）
        st.info("💡 ヒント: グラフをズームしたり、特定の期間を選択して詳細を確認できます。")
    else:
        st.warning("累積損益データがありません")
    
    st.divider()
    
    # 月次損益
    st.subheader("📅 月次損益")
    monthly_data = analyzer.analyze_by_time_period('M')
    
    if not monthly_data.empty:
        fig = go.Figure()
        
        colors = ['green' if x >= 0 else 'red' for x in monthly_data['合計損益']]
        
        fig.add_trace(go.Bar(
            x=monthly_data.index.astype(str),
            y=monthly_data['合計損益'],
            marker_color=colors,
            hovertemplate='<b>月</b>: %{x}<br><b>損益</b>: ¥%{y:,.0f}<br><b>取引数</b>: %{customdata[0]}<br><b>勝率</b>: %{customdata[1]:.1f}%<extra></extra>',
            customdata=monthly_data[['取引数', '勝率']].values
        ))
        
        fig.update_layout(
            title="月次損益",
            xaxis_title="月",
            yaxis_title="損益 (円)",
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 最近のトレード
    st.divider()
    st.subheader("🕐 最近のトレード")
    
    recent_trades = df.sort_values('date', ascending=False)
    
    # 表示用にカラムを選択
    display_cols = ['trade_id', 'date', 'currency_pair', 'type', 'lot', 
                   'pips', 'net_profit_loss_jpy', 'strategy']
    
    if all(col in recent_trades.columns for col in display_cols):
        display_df = recent_trades[display_cols].copy()
        
        # 日付を文字列形式に変換
        if 'date' in display_df.columns:
            display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
        
        # ロット数とpips数を小数第二位まで表示
        if 'lot' in display_df.columns:
            display_df['lot'] = display_df['lot'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else x)
        if 'pips' in display_df.columns:
            display_df['pips'] = display_df['pips'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else x)
        
        # カラム名を日本語に変更
        display_df.columns = ['取引番号', '日付', '通貨ペア', 'タイプ', 'ロット', 
                             'pips', '合計損益', '手法']
        
        # スタイリング
        def highlight_profit(val):
            if isinstance(val, (int, float)):
                color = 'color: green' if val > 0 else 'color: red' if val < 0 else ''
                return color
            return ''
        
        styled_df = display_df.style.applymap(
            highlight_profit, 
            subset=['合計損益', 'pips']
        )
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)


def analysis_page():
    """詳細分析ページ"""
    st.title("🔍 詳細分析レポート")
    
    df = load_data()
    if df is None or df.empty:
        st.warning("データがありません。")
        return
    
    analyzer = TradeAnalyzer(df)
    
    # タブで分析を分割
    tab1, tab2, tab3, tab4 = st.tabs([
        "手法別分析", "通貨ペア別分析", "時間軸分析", "保有時間分析"
    ])
    
    with tab1:
        st.subheader("📊 手法別パフォーマンス")
        strategy_analysis = analyzer.analyze_by_strategy()
        
        if not strategy_analysis.empty:
            # テーブル表示
            st.dataframe(strategy_analysis, use_container_width=True)
            
            # グラフ表示
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    strategy_analysis.reset_index(),
                    x='strategy',
                    y='合計損益',
                    title='手法別合計損益',
                    color='合計損益',
                    color_continuous_scale=['red', 'yellow', 'green']
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    strategy_analysis.reset_index(),
                    x='strategy',
                    y='勝率',
                    title='手法別勝率',
                    color='勝率',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(height=400, yaxis_range=[0, 100])
                st.plotly_chart(fig, use_container_width=True)
            
            # パフォーマンスが悪い手法のフィルタリング
            st.subheader("⚠️ 改善が必要な手法")
            poor_strategies = strategy_analysis[strategy_analysis['合計損益'] < 0]
            
            if not poor_strategies.empty:
                st.dataframe(poor_strategies, use_container_width=True)
                
                # その手法のトレード詳細へのリンク
                st.info("これらの手法を使用したトレードの詳細は「トレードログ」ページで確認できます。")
            else:
                st.success("すべての手法がプラス収支です！")
        else:
            st.warning("手法データがありません")
    
    with tab2:
        st.subheader("💱 通貨ペア別パフォーマンス")
        pair_analysis = analyzer.analyze_by_currency_pair()
        
        if not pair_analysis.empty:
            st.dataframe(pair_analysis, use_container_width=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    pair_analysis.reset_index(),
                    x='currency_pair',
                    y='合計損益',
                    title='通貨ペア別合計損益',
                    color='合計損益',
                    color_continuous_scale=['red', 'yellow', 'green']
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.pie(
                    pair_analysis.reset_index(),
                    values='取引数',
                    names='currency_pair',
                    title='通貨ペア別取引数割合'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("通貨ペアデータがありません")
    
    with tab3:
        st.subheader("📆 時間軸別分析")
        
        # 月次分析
        st.write("**月次損益**")
        monthly_data = analyzer.analyze_by_time_period('M')
        
        if not monthly_data.empty:
            st.dataframe(monthly_data, use_container_width=True)
        
        # 曜日別分析
        st.write("**曜日別パフォーマンス**")
        dow_analysis = analyzer.analyze_by_day_of_week()
        
        if not dow_analysis.empty:
            st.dataframe(dow_analysis, use_container_width=True)
            
            fig = px.bar(
                dow_analysis.reset_index(),
                x='day_name',
                y='合計損益',
                title='曜日別合計損益',
                color='合計損益',
                color_continuous_scale=['red', 'yellow', 'green']
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # 市場セッション別分析
        st.write("**市場セッション別パフォーマンス**")
        session_analysis = analyzer.analyze_by_market_session()
        
        if not session_analysis.empty:
            st.dataframe(session_analysis, use_container_width=True)
            
            fig = px.bar(
                session_analysis.reset_index(),
                x='market_session',
                y='合計損益',
                title='市場セッション別合計損益',
                color='勝率',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.subheader("⏱️ 保有時間別分析")
        holding_analysis = analyzer.analyze_by_holding_time()
        
        if not holding_analysis.empty:
            st.dataframe(holding_analysis, use_container_width=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    holding_analysis.reset_index(),
                    x='holding_category',
                    y='合計損益',
                    title='保有時間別合計損益',
                    color='合計損益',
                    color_continuous_scale=['red', 'yellow', 'green']
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    holding_analysis.reset_index(),
                    x='holding_category',
                    y='勝率',
                    title='保有時間別勝率',
                    color='勝率',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(height=400, yaxis_range=[0, 100])
                st.plotly_chart(fig, use_container_width=True)
            
            st.info("💡 最適な保有時間を見つけて、トレード戦略を最適化しましょう！")
        else:
            st.warning("保有時間データがありません")


def trade_log_page():
    """トレードログページ"""
    st.title("📋 トレードログ")
    
    df = load_data()
    if df is None or df.empty:
        st.warning("データがありません。")
        return
    
    analyzer = TradeAnalyzer(df)
    
    # フィルター
    st.subheader("🔎 フィルター")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 通貨ペアの選択肢（データは既にクリーニング済み）
        if 'currency_pair' in df.columns:
            valid_pairs = df['currency_pair'].dropna().unique()
            valid_pairs = [str(p) for p in valid_pairs if p and str(p).strip()]
            currency_pairs = ['すべて'] + sorted(set(valid_pairs))
        else:
            currency_pairs = ['すべて']
        selected_pair = st.selectbox("通貨ペア", currency_pairs)
    
    with col2:
        # タイプの選択肢（データは既にクリーニング済み）
        if 'type' in df.columns:
            valid_types = df['type'].dropna().unique()
            valid_types = [str(t) for t in valid_types if t and str(t).strip()]
            types = ['すべて'] + sorted(set(valid_types))
        else:
            types = ['すべて']
        selected_type = st.selectbox("タイプ", types)
    
    with col3:
        # 手法の選択肢（トレード履歴 + 保存済みテンプレートをマージ）
        df_strategies = []
        if 'strategy' in df.columns:
            df_strategies = df['strategy'].dropna().unique().tolist()

        if not st.session_state.get('strategy_storage'):
            try:
                st.session_state.strategy_storage = StrategyStorage()
            except Exception:
                st.session_state.strategy_storage = None

        storage_strategies = []
        try:
            if st.session_state.get('strategy_storage'):
                storage_strategies = list(st.session_state.strategy_storage.get_all_strategies().keys())
        except Exception:
            storage_strategies = []

        combined = list(df_strategies) + list(storage_strategies)
        cleaned = [str(s).strip() for s in combined if pd.notna(s) and str(s).strip() and str(s).strip().lower() not in ['nan', 'none', '']]
        strategies = ['すべて'] + sorted(list(set(cleaned))) if cleaned else ['すべて']
        selected_strategy = st.selectbox("手法", strategies)
    
    col4, col5 = st.columns(2)
    
    with col4:
        use_date_filter = st.checkbox("日付でフィルター", value=False)
        
        if use_date_filter:
            # 日付の範囲を取得（NaNを除外）
            if 'date' in df.columns and not df['date'].isna().all():
                valid_dates = pd.to_datetime(df['date']).dropna()
                if not valid_dates.empty:
                    min_date = valid_dates.min()
                    max_date = valid_dates.max()
                    # pd.Timestampをdatetime.dateに変換
                    if hasattr(min_date, 'date'):
                        min_date = min_date.date()
                    if hasattr(max_date, 'date'):
                        max_date = max_date.date()
                else:
                    min_date = datetime.now().date()
                    max_date = datetime.now().date()
            else:
                min_date = datetime.now().date()
                max_date = datetime.now().date()
            
            date_range = st.date_input(
                "期間",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        else:
            date_range = None
    
    with col5:
        only_losses = st.checkbox("負けトレードのみ表示")
    
    # フィルター適用
    filters = {
        'currency_pair': selected_pair,
        'type': selected_type,
        'strategy': selected_strategy,
        'date_range': date_range if (use_date_filter and date_range and len(date_range) == 2) else None,
        'only_losses': only_losses
    }
    
    filtered_df = analyzer.get_filtered_trades(filters)
    
    # デバッグ: フィルター結果を確認
    print(f"[app.py] フィルター適用後のDataFrame行数: {len(filtered_df)}")
    
    st.divider()
    
    # 統計情報
    result_count = len(filtered_df) if filtered_df is not None else 0
    print(f"[app.py] 表示する件数: {result_count}")
    
    # 件数を大きく表示
    st.markdown(f"### 📊 フィルター結果: **{result_count}** 件")
    
    if not filtered_df.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_profit = filtered_df['net_profit_loss_jpy'].sum()
            st.metric("合計損益", f"¥{total_profit:,.0f}")
        
        with col2:
            win_rate = (filtered_df['is_win'].sum() / len(filtered_df) * 100)
            st.metric("勝率", f"{win_rate:.2f}%")
        
        with col3:
            avg_pips = filtered_df['pips'].mean()
            st.metric("平均pips", f"{avg_pips:.2f}")
        
        st.divider()
        
        # トレード一覧
        st.subheader("📝 トレード一覧")
        
        # 表示用カラムの選択
        display_cols = ['trade_id', 'date', 'currency_pair', 'type', 'lot', 
                       'start_time', 'end_time', 'pips', 'net_profit_loss_jpy', 
                       'strategy', 'review_comment']
        
        available_cols = [col for col in display_cols if col in filtered_df.columns]
        display_df = filtered_df[available_cols].copy()
        
        # 日付・時刻を文字列形式に変換
        if 'date' in display_df.columns:
            display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
        if 'start_time' in display_df.columns:
            display_df['start_time'] = pd.to_datetime(display_df['start_time']).dt.strftime('%Y-%m-%d %H:%M')
        if 'end_time' in display_df.columns:
            display_df['end_time'] = pd.to_datetime(display_df['end_time']).dt.strftime('%Y-%m-%d %H:%M')
        
        # ロット数とpips数を小数第二位まで表示
        if 'lot' in display_df.columns:
            display_df['lot'] = display_df['lot'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else x)
        if 'pips' in display_df.columns:
            display_df['pips'] = display_df['pips'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else x)
        
        # ソート（元のdateカラムでソート後に変換）
        display_df = display_df.sort_values('date', ascending=False)
        
        # スタイリング関数（損益とpipsに色を付ける）
        def color_profit_pips(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return 'background-color: #d4edda; color: #155724'
                elif val < 0:
                    return 'background-color: #f8d7da; color: #721c24'
            # 文字列の場合（小数第二位に変換後）
            elif isinstance(val, str):
                try:
                    num_val = float(val)
                    if num_val > 0:
                        return 'background-color: #d4edda; color: #155724'
                    elif num_val < 0:
                        return 'background-color: #f8d7da; color: #721c24'
                except:
                    pass
            return ''
        
        # インタラクティブなテーブル（編集可能）
        st.write("💡 **ヒント:** strategyやreview_commentセルをダブルクリックすると、その場で編集できます")
        
        # 手法の選択肢を取得（編集用）: トレード履歴 + 保存済みテンプレートをマージ
        # StrategyStorage に保存された手法も含めることで、過去に未使用の手法も選べるようにする
        df_strategies = []
        if 'strategy' in df.columns:
            df_strategies = df['strategy'].dropna().unique().tolist()

        # ストレージから手法を取得（セッションに存在しなければ初期化）
        if not st.session_state.get('strategy_storage'):
            try:
                st.session_state.strategy_storage = StrategyStorage()
            except Exception:
                st.session_state.strategy_storage = None

        storage_strategies = []
        try:
            if st.session_state.get('strategy_storage'):
                storage_dict = st.session_state.strategy_storage.get_all_strategies()
                storage_strategies = list(storage_dict.keys())
        except Exception:
            storage_strategies = []

        combined = list(df_strategies) + list(storage_strategies)
        # クリーンアップ: NaN/None/empty/'none'を除外、重複削除、ソート
        all_strategies = [str(s).strip() for s in combined if pd.notna(s) and str(s).strip() and str(s).strip().lower() not in ['nan', 'none', '']]
        all_strategies = sorted(list(set(all_strategies)))
        
        # データエディターで編集可能にする
        editable_columns = ['strategy', 'review_comment']
        disabled_columns = [col for col in display_df.columns if col not in editable_columns]
        
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=600,
            disabled=disabled_columns,
            column_config={
                'strategy': st.column_config.SelectboxColumn(
                    'strategy',
                    help='手法を選択できます',
                    options=all_strategies,
                    required=False
                ),
                'review_comment': st.column_config.TextColumn(
                    'review_comment',
                    help='ダブルクリックして編集できます',
                    max_chars=500,
                    width='large'
                )
            },
            key='trade_table_editor'
        )
        
        # 変更があれば保存ボタンを表示
        if not edited_df.equals(display_df):
            st.warning("⚠️ 変更が保存されていません")
            if st.button("💾 変更を保存", type="primary", key="save_review_changes"):
                data_manager = get_data_manager()
                if data_manager:
                    with st.spinner('保存中...'):
                        try:
                            # 変更されたデータを取得
                            changes_count = 0
                            for idx in edited_df.index:
                                # review_commentの変更をチェック
                                if edited_df.loc[idx, 'review_comment'] != display_df.loc[idx, 'review_comment']:
                                    trade_id = int(edited_df.loc[idx, 'trade_id'])
                                    new_comment = edited_df.loc[idx, 'review_comment']
                                    if data_manager.update_review_comment(trade_id, new_comment):
                                        changes_count += 1
                                
                                # strategyの変更をチェック
                                if edited_df.loc[idx, 'strategy'] != display_df.loc[idx, 'strategy']:
                                    trade_id = int(edited_df.loc[idx, 'trade_id'])
                                    new_strategy = edited_df.loc[idx, 'strategy']
                                    if data_manager.update_strategy(trade_id, new_strategy):
                                        changes_count += 1
                            
                            if changes_count > 0:
                                st.success(f"✅ {changes_count}件の変更を保存しました！")
                                st.cache_resource.clear()
                                import time
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ 変更の保存に失敗しました")
                        except Exception as e:
                            st.error(f"❌ エラーが発生しました: {e}")
                else:
                    st.error("❌ データマネージャーの初期化に失敗しました")
        
        # CSV エクスポート
        csv = display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv,
            file_name=f"trade_log_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("条件に一致するトレードがありません")


def review_page():
    """振り返りページ"""
    st.title("🔄 振り返り機能")
    
    df = load_data()
    if df is None or df.empty:
        st.warning("データがありません。")
        return
    
    analyzer = TradeAnalyzer(df)
    
    # タブで機能を分割
    tab1, tab2, tab3 = st.tabs([
        "パターン分析", "振り返りコメント編集", "負けトレード分析"
    ])
    
    with tab1:
        st.subheader("📊 敗因/勝因パターン自動抽出")
        
        # 連続損失分析
        st.write("**🔴 連続損失分析**")
        max_consecutive, max_loss, streaks = analyzer.get_consecutive_losses()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("最大連続敗北回数", f"{max_consecutive}回")
        with col2:
            st.metric("その際の合計損失", f"¥{max_loss:,.0f}")
        
        if streaks:
            st.write("**連続損失の履歴（3回以上）:**")
            for i, streak in enumerate(streaks, 1):
                with st.expander(f"連敗#{i}: {streak['count']}回連続 (損失: ¥{streak['total_loss']:,.0f})"):
                    streak_df = pd.DataFrame(streak['trades'])
                    if not streak_df.empty:
                        display_cols = ['trade_id', 'date', 'currency_pair', 'strategy', 'net_profit_loss_jpy']
                        available_cols = [col for col in display_cols if col in streak_df.columns]
                        st.dataframe(streak_df[available_cols], use_container_width=True, hide_index=True)
        
        st.divider()
        
        # 最大損失トレード
        st.write("**💸 損失額トップ5**")
        top_losses = analyzer.get_top_losses(5)
        
        if not top_losses.empty:
            display_cols = ['trade_id', 'date', 'currency_pair', 'type', 'strategy', 
                          'net_profit_loss_jpy', 'review_comment']
            available_cols = [col for col in display_cols if col in top_losses.columns]
            st.dataframe(top_losses[available_cols], use_container_width=True, hide_index=True)
        
        st.divider()
        
        # 時間帯別分析
        st.write("**🕐 時間帯別パフォーマンス**")
        session_analysis = analyzer.analyze_by_market_session()
        
        if not session_analysis.empty:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=session_analysis.index,
                y=session_analysis['合計損益'],
                name='合計損益',
                marker_color=['green' if x >= 0 else 'red' for x in session_analysis['合計損益']]
            ))
            
            fig.update_layout(
                title='市場セッション別合計損益',
                xaxis_title='市場セッション',
                yaxis_title='損益 (円)',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(session_analysis, use_container_width=True)
        
        # 曜日別分析
        st.write("**📅 曜日別パフォーマンス**")
        dow_analysis = analyzer.analyze_by_day_of_week()
        
        if not dow_analysis.empty:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=dow_analysis.index,
                y=dow_analysis['勝率'],
                name='勝率',
                marker_color='lightblue'
            ))
            
            fig.update_layout(
                title='曜日別勝率',
                xaxis_title='曜日',
                yaxis_title='勝率 (%)',
                height=400,
                yaxis_range=[0, 100]
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(dow_analysis, use_container_width=True)
    
    with tab2:
        st.subheader("✏️ 振り返りコメント編集")
        
        st.info("各トレードに対して振り返りコメントを追加・編集できます。反省点や気づき、市場の状況などを記録しましょう。")
        
        # トレード選択
        trade_ids = sorted(df['trade_id'].unique(), reverse=True)
        selected_trade_id = st.selectbox("トレードを選択", trade_ids)
        
        if selected_trade_id:
            trade_row = df[df['trade_id'] == selected_trade_id].iloc[0]
            
            # トレード詳細表示
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**取引番号:** {trade_row['trade_id']}")
                # 日付を文字列形式で表示
                trade_date = pd.to_datetime(trade_row['date']).strftime('%Y-%m-%d') if pd.notna(trade_row['date']) else 'N/A'
                st.write(f"**日付:** {trade_date}")
                st.write(f"**通貨ペア:** {trade_row['currency_pair']}")
                st.write(f"**タイプ:** {trade_row['type']}")
                st.write(f"**手法:** {trade_row['strategy']}")
            
            with col2:
                st.write(f"**ロット:** {trade_row['lot']}")
                st.write(f"**pips:** {trade_row['pips']}")
                
                profit_loss = trade_row['net_profit_loss_jpy']
                color = "green" if profit_loss >= 0 else "red"
                st.markdown(f"**合計損益:** <span style='color:{color}'>¥{profit_loss:,.0f}</span>", 
                           unsafe_allow_html=True)
            
            st.divider()
            
            # コメント編集
            current_comment = trade_row.get('review_comment', '')
            new_comment = st.text_area(
                "振り返りコメント",
                value=current_comment if current_comment and current_comment != 'nan' else "",
                height=200,
                placeholder="このトレードについての反省点、気づき、市場の状況などを記入してください..."
            )
            
            if st.button("💾 コメントを保存", type="primary"):
                data_manager = get_data_manager()
                if data_manager:
                    with st.spinner('保存中...'):
                        try:
                            success = data_manager.update_review_comment(int(selected_trade_id), new_comment)
                            if success:
                                st.success("✅ コメントを保存しました！")
                                # データを再読み込み
                                st.cache_resource.clear()
                                import time
                                time.sleep(1)  # Google Sheets APIの反映を待つ
                                st.rerun()
                            else:
                                st.error("❌ コメントの保存に失敗しました")
                                st.info("ターミナルのログを確認してください。")
                        except Exception as e:
                            st.error(f"❌ エラーが発生しました: {e}")
                else:
                    st.error("❌ データマネージャーの初期化に失敗しました")
    
    with tab3:
        st.subheader("🔍 負けトレード分析")
        
        st.info("負けトレードを分析して、共通点や改善点を見つけましょう。")
        
        # 負けトレードのみ抽出
        losing_trades = df[df['net_profit_loss_jpy'] < 0].copy()
        
        if not losing_trades.empty:
            st.write(f"**負けトレード数:** {len(losing_trades)}件")
            
            # 統計
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_loss = losing_trades['net_profit_loss_jpy'].sum()
                st.metric("総損失", f"¥{total_loss:,.0f}")
            
            with col2:
                avg_loss = losing_trades['net_profit_loss_jpy'].mean()
                st.metric("平均損失", f"¥{avg_loss:,.0f}")
            
            with col3:
                worst_loss = losing_trades['net_profit_loss_jpy'].min()
                st.metric("最大損失", f"¥{worst_loss:,.0f}")
            
            st.divider()
            
            # フィルター
            st.write("**フィルター**")
            col1, col2 = st.columns(2)
            
            with col1:
                # 手法の選択肢: トレード履歴 + 保存済みテンプレートをマージ（NaN/None除外）
                df_strategies = []
                if 'strategy' in df.columns:
                    df_strategies = df['strategy'].dropna().unique().tolist()

                if not st.session_state.get('strategy_storage'):
                    try:
                        st.session_state.strategy_storage = StrategyStorage()
                    except Exception:
                        st.session_state.strategy_storage = None

                storage_strategies = []
                try:
                    if st.session_state.get('strategy_storage'):
                        storage_strategies = list(st.session_state.strategy_storage.get_all_strategies().keys())
                except Exception:
                    storage_strategies = []

                combined = list(df_strategies) + list(storage_strategies)
                valid_strategies = [str(s).strip() for s in combined if pd.notna(s) and str(s).strip() and str(s).strip().lower() not in ['nan', 'none', '']]
                strategies = ['すべて'] + sorted(list(set(valid_strategies))) if valid_strategies else ['すべて']
                selected_strategy = st.selectbox("手法でフィルター", strategies, key="losing_strategy")
            
            with col2:
                # 通貨ペアの選択肢（NaNや空文字列を除外）
                valid_pairs = losing_trades['currency_pair'].dropna().unique()
                valid_pairs = [str(p).strip() for p in valid_pairs if p and str(p).strip() and str(p).lower() != 'nan']
                pairs = ['すべて'] + sorted(valid_pairs)
                selected_pair = st.selectbox("通貨ペアでフィルター", pairs, key="losing_pair")
            
            # フィルター適用
            filtered_losses = losing_trades.copy()
            if selected_strategy != 'すべて':
                filtered_losses = filtered_losses[
                    filtered_losses['strategy'].astype(str).str.strip() == str(selected_strategy).strip()
                ]
            if selected_pair != 'すべて':
                filtered_losses = filtered_losses[
                    filtered_losses['currency_pair'].astype(str).str.strip() == str(selected_pair).strip()
                ]
            
            st.write(f"**フィルター結果:** {len(filtered_losses)}件")
            
            # テーブル表示
            display_cols = ['trade_id', 'date', 'currency_pair', 'type', 'strategy', 
                          'net_profit_loss_jpy', 'pips', 'review_comment']
            available_cols = [col for col in display_cols if col in filtered_losses.columns]
            
            # 表示用のコピーを作成
            display_losses = filtered_losses[available_cols].copy()
            
            # 日付を文字列形式に変換
            if 'date' in display_losses.columns:
                display_losses['date'] = pd.to_datetime(display_losses['date']).dt.strftime('%Y-%m-%d')
            
            # ソート
            display_losses = display_losses.sort_values('net_profit_loss_jpy')
            
            # 手法の選択肢を取得（編集用）: トレード履歴 + 保存済みテンプレートをマージ
            df_strategies = []
            if 'strategy' in df.columns:
                df_strategies = df['strategy'].dropna().unique().tolist()

            if not st.session_state.get('strategy_storage'):
                try:
                    st.session_state.strategy_storage = StrategyStorage()
                except Exception:
                    st.session_state.strategy_storage = None

            storage_strategies = []
            try:
                if st.session_state.get('strategy_storage'):
                    storage_dict = st.session_state.strategy_storage.get_all_strategies()
                    storage_strategies = list(storage_dict.keys())
            except Exception:
                storage_strategies = []

            combined = list(df_strategies) + list(storage_strategies)
            all_strategies = [str(s).strip() for s in combined if pd.notna(s) and str(s).strip() and str(s).strip().lower() not in ['nan', 'none', '']]
            all_strategies = sorted(list(set(all_strategies)))
            
            # 編集可能なデータエディター
            st.write("💡 **ヒント:** strategyやreview_commentセルをダブルクリックすると、編集できます")
            
            editable_columns = ['strategy', 'review_comment']
            disabled_columns = [col for col in display_losses.columns if col not in editable_columns]
            
            edited_losses = st.data_editor(
                display_losses,
                use_container_width=True,
                hide_index=True,
                height=500,
                disabled=disabled_columns,
                column_config={
                    'strategy': st.column_config.SelectboxColumn(
                        'strategy',
                        help='手法を選択できます',
                        options=all_strategies,
                        required=False
                    ),
                    'review_comment': st.column_config.TextColumn(
                        'review_comment',
                        help='ダブルクリックして編集できます',
                        max_chars=500,
                        width='large'
                    )
                },
                key='losing_trades_editor'
            )
            
            # 変更があれば保存ボタンを表示
            if not edited_losses.equals(display_losses):
                st.warning("⚠️ 変更が保存されていません")
                if st.button("💾 変更を保存", type="primary", key="save_losing_review_changes"):
                    data_manager = get_data_manager()
                    if data_manager:
                        with st.spinner('保存中...'):
                            try:
                                changes_count = 0
                                for idx in edited_losses.index:
                                    # review_commentの変更をチェック
                                    if edited_losses.loc[idx, 'review_comment'] != display_losses.loc[idx, 'review_comment']:
                                        trade_id = int(edited_losses.loc[idx, 'trade_id'])
                                        new_comment = edited_losses.loc[idx, 'review_comment']
                                        if data_manager.update_review_comment(trade_id, new_comment):
                                            changes_count += 1
                                    
                                    # strategyの変更をチェック
                                    if edited_losses.loc[idx, 'strategy'] != display_losses.loc[idx, 'strategy']:
                                        trade_id = int(edited_losses.loc[idx, 'trade_id'])
                                        new_strategy = edited_losses.loc[idx, 'strategy']
                                        if data_manager.update_strategy(trade_id, new_strategy):
                                            changes_count += 1
                                
                                if changes_count > 0:
                                    st.success(f"✅ {changes_count}件の変更を保存しました！")
                                    st.cache_resource.clear()
                                    import time
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ 変更の保存に失敗しました")
                            except Exception as e:
                                st.error(f"❌ エラーが発生しました: {e}")
                    else:
                        st.error("❌ データマネージャーの初期化に失敗しました")
            
            # 共通点の分析
            st.divider()
            st.write("**📊 負けトレードの共通点**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 手法別の負け率
                strategy_losses = filtered_losses.groupby('strategy').size()
                fig = px.pie(
                    values=strategy_losses.values,
                    names=strategy_losses.index,
                    title='手法別負けトレード割合'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # 通貨ペア別の負け率
                pair_losses = filtered_losses.groupby('currency_pair').size()
                fig = px.pie(
                    values=pair_losses.values,
                    names=pair_losses.index,
                    title='通貨ペア別負けトレード割合'
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("負けトレードがありません！すばらしい成績です！")


def strategy_management_page():
    """手法管理ページ"""
    st.title("📚 手法管理")
    
    st.info("トレード手法を記録・管理し、各手法のルールを明確化することで、一貫性のあるトレードを実現します。")
    
    # タブで機能を分割
    tab1, tab2, tab3 = st.tabs([
        "手法一覧", "手法登録・編集", "手法パフォーマンス"
    ])
    
    with tab1:
        st.subheader("📋 登録済み手法一覧")
        
        df = load_data()
        if df is not None and not df.empty:
            # TradeAnalyzerを使用して手法を取得
            try:
                analyzer = TradeAnalyzer(df)
                strategy_stats = analyzer.analyze_by_strategy()
                # デバッグ情報
                # st.write(f"Debug: strategy_stats shape: {strategy_stats.shape}")
                # st.write(f"Debug: strategy_stats index: {strategy_stats.index.tolist()}")
            except Exception as e:
                st.error(f"分析エラー: {e}")
                strategy_stats = pd.DataFrame()
            
            strategies = []
            if not strategy_stats.empty:
                strategies = sorted(strategy_stats.index.tolist())

            # フォールバック/補完: analyzerで取得した手法にストレージの手法をマージ
            df_strategies = []
            if 'strategy' in df.columns:
                df_strategies = df['strategy'].dropna().unique().tolist()

            if not st.session_state.get('strategy_storage'):
                try:
                    st.session_state.strategy_storage = StrategyStorage()
                except Exception:
                    st.session_state.strategy_storage = None

            storage_strategies = []
            try:
                if st.session_state.get('strategy_storage'):
                    storage_strategies = list(st.session_state.strategy_storage.get_all_strategies().keys())
            except Exception:
                storage_strategies = []

            # combine: strategy_stats (優先) + df + storage
            combined = list(strategies) + list(df_strategies) + list(storage_strategies)
            strategies = [str(s).strip() for s in combined if pd.notna(s) and str(s).strip() and str(s).strip().lower() not in ['nan', 'none', '']]
            strategies = sorted(list(dict.fromkeys(strategies)))
            
            if strategies:
                st.write(f"**登録済み手法数:** {len(strategies)}件")
                
                if not strategy_stats.empty:
                    st.dataframe(strategy_stats, use_container_width=True)
                else:
                    st.info("手法の統計データはありませんが、以下の手法が見つかりました。")
                    st.write(", ".join(strategies))
                    
                # 手法の詳細を選択
                st.divider()
                selected_strategy = st.selectbox("詳細を表示する手法を選択", [''] + strategies)
                
                if selected_strategy:
                        st.subheader(f"📖 手法詳細: {selected_strategy}")
                        
                        # この手法を使用したトレードを抽出
                        strategy_trades = df[df['strategy'] == selected_strategy]
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            total_trades = len(strategy_trades)
                            st.metric("総トレード数", f"{total_trades}回")
                        
                        with col2:
                            wins = len(strategy_trades[strategy_trades['net_profit_loss_jpy'] > 0])
                            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
                            st.metric("勝率", f"{win_rate:.1f}%")
                        
                        with col3:
                            total_profit = strategy_trades['net_profit_loss_jpy'].sum()
                            st.metric("累積損益", f"¥{total_profit:,.0f}")
                        
                        with col4:
                            avg_profit = strategy_trades['net_profit_loss_jpy'].mean()
                            st.metric("平均損益", f"¥{avg_profit:,.0f}")
                        
                        # 手法のルール説明欄
                        st.divider()
                        st.write("**手法のルール・メモ**")
                        
                        # セッションステートで手法ルールを管理
                        if 'strategy_rules' not in st.session_state:
                            st.session_state.strategy_rules = {}
                        
                        current_rule = st.session_state.strategy_rules.get(selected_strategy, "")
                        
                        with st.expander("✏️ 手法ルールを編集", expanded=False):
                            st.write("この手法のエントリー条件、イグジット条件、リスク管理ルールなどを記録できます。")
                            
                            rule_text = st.text_area(
                                "手法ルール",
                                value=current_rule,
                                height=300,
                                placeholder="例：\n【エントリー条件】\n・移動平均線のゴールデンクロス\n・RSI < 30\n\n【イグジット条件】\n・利益確定: +20pips\n・損切り: -10pips\n\n【リスク管理】\n・1トレードあたり資金の2%まで"
                            )
                            
                            if st.button("💾 ルールを保存", key=f"save_rule_{selected_strategy}"):
                                st.session_state.strategy_rules[selected_strategy] = rule_text
                                st.success("✅ ルールを保存しました！")
                        
                        if current_rule:
                            st.markdown("**現在のルール:**")
                            st.info(current_rule)
                        
                        # この手法のトレード一覧
                        st.divider()
                        st.write(f"**この手法のトレード一覧（全{len(strategy_trades)}件）**")
                        
                        all_strategy_trades = strategy_trades.sort_values('date', ascending=False)
                        display_cols = ['trade_id', 'date', 'currency_pair', 'type', 'pips', 'net_profit_loss_jpy', 'review_comment']
                        available_cols = [col for col in display_cols if col in all_strategy_trades.columns]
                        
                        display_df = all_strategy_trades[available_cols].copy()
                        if 'date' in display_df.columns:
                            display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
                        
                        # 編集可能なデータエディター
                        st.write("💡 **ヒント:** review_commentセルをダブルクリックすると、編集できます")
                        
                        editable_columns = ['review_comment']
                        disabled_columns = [col for col in display_df.columns if col not in editable_columns]
                        
                        edited_strategy_df = st.data_editor(
                            display_df,
                            use_container_width=True,
                            hide_index=True,
                            height=600,
                            disabled=disabled_columns,
                            column_config={
                                'review_comment': st.column_config.TextColumn(
                                    'review_comment',
                                    help='ダブルクリックして編集できます',
                                    max_chars=500,
                                    width='large'
                                )
                            },
                            key='strategy_trades_editor'
                        )
                        
                        # 変更があれば保存ボタンを表示
                        if not edited_strategy_df.equals(display_df):
                            st.warning("⚠️ 変更が保存されていません")
                            if st.button("💾 変更を保存", type="primary", key="save_strategy_review_changes"):
                                data_manager = get_data_manager()
                                if data_manager:
                                    with st.spinner('保存中...'):
                                        try:
                                            changes_count = 0
                                            for idx in edited_strategy_df.index:
                                                # review_commentの変更をチェック
                                                if edited_strategy_df.loc[idx, 'review_comment'] != display_df.loc[idx, 'review_comment']:
                                                    trade_id = int(edited_strategy_df.loc[idx, 'trade_id'])
                                                    new_comment = edited_strategy_df.loc[idx, 'review_comment']
                                                    if data_manager.update_review_comment(trade_id, new_comment):
                                                        changes_count += 1
                                            
                                            if changes_count > 0:
                                                st.success(f"✅ {changes_count}件の変更を保存しました！")
                                                st.cache_resource.clear()
                                                import time
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("❌ 変更の保存に失敗しました")
                                        except Exception as e:
                                            st.error(f"❌ エラーが発生しました: {e}")
                                else:
                                    st.error("❌ データマネージャーの初期化に失敗しました")
                else:
                    st.warning("手法データがありません")
            else:
                st.warning("まだ手法が登録されていません。トレードログに手法を入力してください。")
        else:
            st.warning("データがありません")
    
    with tab2:
        st.subheader("✏️ 手法テンプレート登録")
        
        st.write("新しい手法のテンプレートを作成します。")
        
        with st.form("strategy_template_form"):
            st.write("**基本情報**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                strategy_name = st.text_input(
                    "手法名 *", 
                    placeholder="例: トレンドフォロー、レンジブレイク",
                    help="トレードログで使用する手法名"
                )
                
                strategy_type = st.selectbox(
                    "手法タイプ",
                    ["トレンドフォロー", "レンジ取引", "ブレイクアウト", "逆張り", "スキャルピング", "その他"]
                )
            
            with col2:
                time_frame = st.selectbox(
                    "推奨時間足",
                    ["1分足", "5分足", "15分足", "30分足", "1時間足", "4時間足", "日足", "週足"]
                )
                
                suitable_pairs = st.multiselect(
                    "適した通貨ペア",
                    ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "EURUSD", "GBPUSD", "AUDUSD", "その他"]
                )
            
            st.divider()
            
            st.write("**エントリールール**")
            entry_conditions = st.text_area(
                "エントリー条件",
                height=150,
                placeholder="エントリーする際の条件を具体的に記述\n例:\n・移動平均線（20MA, 50MA）のゴールデンクロス\n・RSIが30以下から上昇\n・サポートラインでの反発確認"
            )
            
            entry_indicators = st.multiselect(
                "使用するインジケーター",
                ["移動平均線", "RSI", "MACD", "ボリンジャーバンド", "ストキャスティクス", "フィボナッチ", "一目均衡表", "その他"]
            )
            
            st.divider()
            
            st.write("**イグジットルール**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                take_profit = st.text_input(
                    "利益確定ルール",
                    placeholder="例: +20pips, リスクリワード比1:2"
                )
            
            with col2:
                stop_loss = st.text_input(
                    "損切りルール",
                    placeholder="例: -10pips, 直近安値の下"
                )
            
            exit_conditions = st.text_area(
                "その他のイグジット条件",
                height=100,
                placeholder="時間による決済、トレイリングストップなど"
            )
            
            st.divider()
            
            st.write("**リスク管理**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                position_size = st.text_input(
                    "ポジションサイズルール",
                    placeholder="例: 資金の2%、固定0.1ロット"
                )
            
            with col2:
                max_daily_loss = st.text_input(
                    "1日の最大損失",
                    placeholder="例: 資金の5%、-10,000円"
                )
            
            risk_notes = st.text_area(
                "リスク管理の補足",
                height=100,
                placeholder="連敗時のルール、重要指標発表時の対応など"
            )
            
            st.divider()
            
            st.write("**注意点・メモ**")
            notes = st.text_area(
                "その他の注意点",
                height=150,
                placeholder="この手法を使う際の注意点、市場環境、避けるべき時間帯など"
            )
            
            submitted = st.form_submit_button("💾 テンプレートを保存", use_container_width=True)
            
            if submitted:
                if not strategy_name:
                    st.error("❌ 手法名は必須です")
                else:
                    # セッションステートに保存
                    if 'strategy_templates' not in st.session_state:
                        st.session_state.strategy_templates = {}
                    
                    st.session_state.strategy_templates[strategy_name] = {
                        'name': strategy_name,
                        'type': strategy_type,
                        'time_frame': time_frame,
                        'suitable_pairs': suitable_pairs,
                        'entry_conditions': entry_conditions,
                        'entry_indicators': entry_indicators,
                        'take_profit': take_profit,
                        'stop_loss': stop_loss,
                        'exit_conditions': exit_conditions,
                        'position_size': position_size,
                        'max_daily_loss': max_daily_loss,
                        'risk_notes': risk_notes,
                        'notes': notes
                    }
                    
                    st.success(f"✅ 手法テンプレート「{strategy_name}」を保存しました！")
                    st.info("💡 トレードログでこの手法名を使用してください。")
        
        # 保存済みテンプレートの表示
        if 'strategy_templates' in st.session_state and st.session_state.strategy_templates:
            st.divider()
            st.subheader("📚 保存済みテンプレート")
            
            for name, template in st.session_state.strategy_templates.items():
                with st.expander(f"📖 {name}"):
                    st.write(f"**タイプ:** {template['type']}")
                    st.write(f"**推奨時間足:** {template['time_frame']}")
                    if template['suitable_pairs']:
                        st.write(f"**通貨ペア:** {', '.join(template['suitable_pairs'])}")
                    
                    if template['entry_conditions']:
                        st.write("**エントリー条件:**")
                        st.info(template['entry_conditions'])
                    
                    if template['entry_indicators']:
                        st.write(f"**インジケーター:** {', '.join(template['entry_indicators'])}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if template['take_profit']:
                            st.write(f"**利益確定:** {template['take_profit']}")
                    with col2:
                        if template['stop_loss']:
                            st.write(f"**損切り:** {template['stop_loss']}")
                    
                    if template['position_size']:
                        st.write(f"**ポジションサイズ:** {template['position_size']}")
    
    with tab3:
        st.subheader("📊 手法別パフォーマンス比較")
        
        df = load_data()
        if df is not None and not df.empty:
            analyzer = TradeAnalyzer(df)
            strategy_stats = analyzer.analyze_by_strategy()
            
            if not strategy_stats.empty:
                # グラフで比較
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.bar(
                        strategy_stats.reset_index(),
                        x='strategy',
                        y='合計損益',
                        title='手法別累積損益',
                        color='合計損益',
                        color_continuous_scale=['red', 'yellow', 'green']
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.scatter(
                        strategy_stats.reset_index(),
                        x='勝率',
                        y='平均損益',
                        size='取引数',
                        text='strategy',
                        title='手法別: 勝率 vs 平均損益',
                        color='合計損益',
                        color_continuous_scale='RdYlGn'
                    )
                    fig.update_traces(textposition='top center')
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                # ランキング
                st.divider()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**🏆 累積損益ランキング**")
                    top_profit = strategy_stats.nlargest(5, '合計損益')[['合計損益', '勝率']]
                    for idx, (strategy, row) in enumerate(top_profit.iterrows(), 1):
                        emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "📊"
                        st.write(f"{emoji} {strategy}: ¥{row['合計損益']:,.0f} (勝率{row['勝率']:.1f}%)")
                
                with col2:
                    st.write("**🎯 勝率ランキング**")
                    top_winrate = strategy_stats.nlargest(5, '勝率')[['勝率', '取引数']]
                    for idx, (strategy, row) in enumerate(top_winrate.iterrows(), 1):
                        emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "📊"
                        st.write(f"{emoji} {strategy}: {row['勝率']:.1f}% ({row['取引数']:.0f}回)")
                
                with col3:
                    st.write("**💰 平均損益ランキング**")
                    top_avg = strategy_stats.nlargest(5, '平均損益')[['平均損益', '取引数']]
                    for idx, (strategy, row) in enumerate(top_avg.iterrows(), 1):
                        emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "📊"
                        st.write(f"{emoji} {strategy}: ¥{row['平均損益']:,.0f} ({row['取引数']:.0f}回)")
                
                # 推奨とワーニング
                st.divider()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.success("**✅ 推奨手法**")
                    # 勝率50%以上かつプラス収支の手法
                    recommended = strategy_stats[
                        (strategy_stats['勝率'] >= 50) & 
                        (strategy_stats['合計損益'] > 0)
                    ]
                    if not recommended.empty:
                        for strategy in recommended.index[:3]:
                            st.write(f"• {strategy}")
                    else:
                        st.write("該当なし")
                
                with col2:
                    st.warning("**⚠️ 改善が必要な手法**")
                    # マイナス収支の手法
                    needs_improvement = strategy_stats[strategy_stats['合計損益'] < 0]
                    if not needs_improvement.empty:
                        for strategy in needs_improvement.index[:3]:
                            st.write(f"• {strategy}")
                    else:
                        st.write("該当なし")
            else:
                st.warning("手法データがありません")
        else:
            st.warning("データがありません")


def main():
    """メイン関数"""
    # ページ状態の初期化
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0

    pages = ["📊 ダッシュボード", "🔍 詳細分析", "📋 トレードログ", "📚 手法管理", "🔄 振り返り"]

    # ヘッダー（containerをCSSで固定し、その中にナビを配置）
    header = st.container()
    with header:
        st.markdown('<div class="app-header-marker" id="header-marker"></div>', unsafe_allow_html=True)

        col_brand, col_right = st.columns([2, 7])

        with col_brand:
            st.markdown(
                """
                <div class="header-brand">
                    <span class="brand-logo">📈</span>
                    <h1 class="brand-title">FX</h1>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_right:
            nav_col, action_col = st.columns([6, 1])

            with nav_col:
                st.markdown('<div class="header-nav-container">', unsafe_allow_html=True)
                page = st.radio(
                    "ナビゲーション",
                    pages,
                    index=st.session_state.current_page,
                    horizontal=True,
                    label_visibility="collapsed",
                    key="page_nav",
                )
                st.markdown('</div>', unsafe_allow_html=True)
                st.session_state.current_page = pages.index(page)

            with action_col:
                st.markdown('<div class="header-refresh-btn">', unsafe_allow_html=True)
                if st.button("🔄 更新", key="refresh_data", use_container_width=True):
                    st.cache_resource.clear()
                    if 'strategy_manager' in st.session_state:
                        st.session_state.strategy_manager = None
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # JavaScriptでヘッダーにスクロールエフェクトを追加
    st.markdown("""
    <script>
        (function initStickyHeader() {
            const marker = document.getElementById('header-marker');
            if (!marker) {
                setTimeout(initStickyHeader, 100);
                return;
            }

            // マーカーから親コンテナを探す
            let container = marker;
            let attempts = 0;
            while (container && attempts < 20) {
                const isVertical = container.getAttribute && container.getAttribute('data-testid') === 'stVerticalBlock';
                const hasBrand = container.querySelector && container.querySelector('.header-brand');
                if (isVertical && hasBrand) {
                    break;
                }
                container = container.parentElement;
                attempts++;
            }

            if (!container) {
                setTimeout(initStickyHeader, 100);
                return;
            }

            // スティッキーヘッダークラスを追加
            container.classList.add('fixed-header-container');
            console.log('✓ スティッキーヘッダーを初期化しました');

            // スクロールイベントでスタイル切り替え
            let lastScroll = 0;
            function handleScroll() {
                const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
                
                if (currentScroll > 10) {
                    container.classList.add('scrolled');
                } else {
                    container.classList.remove('scrolled');
                }
                
                lastScroll = currentScroll;
            }

            window.addEventListener('scroll', handleScroll, { passive: true });
            handleScroll(); // 初回実行
        })();
    </script>
    """, unsafe_allow_html=True)
    
    # コンテンツエリア
    st.markdown('<div class="content-wrapper">', unsafe_allow_html=True)
    
    # ページ名を抽出
    page_name = page.split(' ', 1)[1]

    # ページルーティング
    if page_name == "ダッシュボード":
        dashboard_page()
    elif page_name == "詳細分析":
        analysis_page()
    elif page_name == "トレードログ":
        trade_log_page()
    elif page_name == "手法管理":
        strategy_management_page_new(load_data, get_strategy_manager)
    elif page_name == "振り返り":
        review_page()
    
    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
