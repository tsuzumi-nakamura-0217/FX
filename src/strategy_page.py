"""手法管理ページ - 独立モジュール"""
import streamlit as st
import pandas as pd
import plotly.express as px


def strategy_management_page_new(load_data_func, get_strategy_manager_func):
    """手法管理ページ（新バージョン）"""
    st.title("📚 手法管理")
    
    st.info("トレード手法を記録・管理し、各手法のルールを明確化することで、一貫性のあるトレードを実現します。ローカルJSONファイルで管理されます。")
    
    # StrategyManagerの初期化
    strategy_manager = get_strategy_manager_func()
    
    # 手法をロード
    with st.spinner('手法を読み込んでいます...'):
        strategies_data = strategy_manager.load_all_strategies()
        strategies = strategy_manager.get_strategy_list()
        
        # Google Sheetsのプルダウンを更新
        if strategies and strategy_manager.sheets_manager:
            try:
                if hasattr(strategy_manager.sheets_manager, 'update_strategy_dropdown'):
                    strategy_manager.sheets_manager.update_strategy_dropdown(strategies)
                else:
                    st.warning("Google Sheetsのプルダウン更新機能が利用できません。アプリを再起動してください。")
            except Exception as e:
                st.warning(f"Google Sheetsのプルダウン更新に失敗しました: {e}")
    
    # タブで機能を分割
    tab1, tab2, tab3 = st.tabs([
        "📋 手法一覧", "➕ 手法を追加", "📊 パフォーマンス分析"
    ])
    
    with tab1:
        _render_strategy_list_tab(strategies, strategies_data, strategy_manager, load_data_func)
    
    with tab2:
        _render_add_strategy_tab(strategy_manager, strategies)
    
    with tab3:
        _render_performance_tab(load_data_func)


def _render_strategy_list_tab(strategies, strategies_data, strategy_manager, load_data_func):
    """手法一覧タブ"""
    st.subheader("📋 登録済み手法一覧")
    
    if strategies:
        st.write(f"**登録済み手法数:** {len(strategies)}件")
        
        # 手法リストを表形式で表示（ソースカラムを削除、ルール全体を表示）
        strategy_list = []
        for strategy_name in strategies:
            strategy_info = strategies_data.get(strategy_name, {})
            rules = strategy_info.get('rules', '')
            strategy_list.append({
                '手法名': strategy_name,
                'ルール': rules if rules else '（未設定）'
            })
        
        st.dataframe(pd.DataFrame(strategy_list), use_container_width=True, hide_index=True)
        
        # 手法の詳細を選択
        st.divider()
        selected_strategy = st.selectbox("詳細を表示・編集する手法を選択", [''] + strategies)
        
        if selected_strategy:
            _render_strategy_detail(selected_strategy, strategy_manager, load_data_func)
    else:
        st.warning("まだ手法が登録されていません。「手法を追加」タブから新しい手法を登録してください。")


def _render_strategy_detail(selected_strategy, strategy_manager, load_data_func):
    """手法詳細の表示"""
    st.subheader(f"📖 手法詳細: {selected_strategy}")
    
    # トレードデータがあればパフォーマンスを表示
    df = load_data_func()
    if df is not None and not df.empty and 'strategy' in df.columns:
        strategy_trades = df[df['strategy'] == selected_strategy]
        
        if not strategy_trades.empty:
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
            
            st.divider()
        else:
            st.info("この手法でのトレード実績はまだありません。")
    
    # 手法のルール表示・編集
    st.write("**手法のルール・メモ**")
    
    current_rules = strategy_manager.get_strategy_rules(selected_strategy)
    
    with st.expander("✏️ 手法ルールを編集", expanded=not current_rules):
        st.write("この手法のエントリー条件、イグジット条件、リスク管理ルールなどを記録できます。")
        st.info("💡 保存するとNotionに自動的に同期されます。")
        
        rule_text = st.text_area(
            "手法ルール",
            value=current_rules,
            height=300,
            placeholder="例：\n【エントリー条件】\n・移動平均線のゴールデンクロス\n・RSI < 30\n\n【イグジット条件】\n・利益確定: +20pips\n・損切り: -10pips\n\n【リスク管理】\n・1トレードあたり資金の2%まで",
            key=f"rules_edit_{selected_strategy}"
        )
        
        col_save, col_cancel = st.columns([1, 4])
        with col_save:
            if st.button("💾 Notionに保存", key=f"save_rule_{selected_strategy}", type="primary"):
                with st.spinner('Notionに保存しています...'):
                    success = strategy_manager.save_strategy_rules(selected_strategy, rule_text)
                if success:
                    st.success("✅ ルールをNotionに保存しました！")
                    st.rerun()
                else:
                    st.error("❌ 保存に失敗しました")
    
    if current_rules:
        st.markdown("**現在のルール:**")
        st.info(current_rules)
    else:
        st.warning("まだルールが設定されていません。上記の編集フォームからルールを追加してください。")
    
    # 最近のトレード
    if df is not None and not df.empty and 'strategy' in df.columns:
        strategy_trades = df[df['strategy'] == selected_strategy]
        if not strategy_trades.empty:
            st.divider()
            st.write("**最近のトレード（直近10件）**")
            
            recent_strategy_trades = strategy_trades.sort_values('date', ascending=False).head(10)
            display_cols = ['trade_id', 'date', 'currency_pair', 'type', 'pips', 'net_profit_loss_jpy', 'review_comment']
            available_cols = [col for col in display_cols if col in recent_strategy_trades.columns]
            
            display_df = recent_strategy_trades[available_cols].copy()
            if 'date' in display_df.columns:
                display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)


def _render_add_strategy_tab(strategy_manager, strategies):
    """手法追加タブ"""
    st.subheader("➕ 新しい手法を追加")
    
    st.write("新しい手法を作成し、Notionに保存します。")
    
    with st.form("new_strategy_form", clear_on_submit=True):
        strategy_name = st.text_input(
            "手法名 *", 
            placeholder="例: トレンドフォロー戦略1、レンジブレイク",
            help="トレードログで使用する手法名（一意である必要があります）"
        )
        
        strategy_rules = st.text_area(
            "手法のルール・説明",
            height=300,
            placeholder="例：\n【エントリー条件】\n・移動平均線のゴールデンクロス\n・RSI < 30\n・トレンド方向への押し目\n\n【イグジット条件】\n・利益確定: +20pips\n・損切り: -10pips\n・トレイリングストップ使用\n\n【リスク管理】\n・1トレードあたり資金の2%まで\n・最大同時ポジション3つまで"
        )
        
        submitted = st.form_submit_button("📝 手法を登録", type="primary")
        
        if submitted:
            if not strategy_name or not strategy_name.strip():
                st.error("手法名を入力してください")
            elif strategy_name.strip() in strategies:
                st.error(f"手法 '{strategy_name.strip()}' は既に存在します")
            else:
                with st.spinner('Notionに保存しています...'):
                    success = strategy_manager.add_new_strategy(strategy_name.strip(), strategy_rules)
                
                if success:
                    st.success(f"✅ 手法 '{strategy_name.strip()}' を登録しました！")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ 手法の登録に失敗しました")
    
    st.divider()
    st.info("""
    **💡 ヒント:**
    - 手法名は一意である必要があります
    - 登録した手法は、トレードログの「手法」列で選択できるようになります
    - ルールは後から編集できます
    - Notionと自動同期されるため、Notionからも確認・編集が可能です
    """)


def _render_performance_tab(load_data_func):
    """パフォーマンス分析タブ"""
    from src.data_manager import TradeAnalyzer
    
    st.subheader("📊 手法別パフォーマンス分析")
    
    df = load_data_func()
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
