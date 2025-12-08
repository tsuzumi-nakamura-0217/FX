"""MT5接続・データ取得モジュール"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class MT5Connector:
    """MT5との接続を管理し、取引履歴を取得するクラス"""
    
    def __init__(self, login: int, password: str, server: str):
        """
        Args:
            login: MT5アカウント番号
            password: MT5パスワード
            server: MT5サーバー名
        """
        self.login = login
        self.password = password
        self.server = server
        self.connected = False
    
    def connect(self) -> bool:
        """MT5に接続"""
        if not mt5.initialize():
            print(f"MT5初期化エラー: {mt5.last_error()}")
            return False
        
        authorized = mt5.login(
            login=self.login,
            password=self.password,
            server=self.server
        )
        
        if not authorized:
            print(f"MT5ログインエラー: {mt5.last_error()}")
            mt5.shutdown()
            return False
        
        self.connected = True
        print(f"MT5に接続しました: アカウント {self.login}")
        return True
    
    def disconnect(self):
        """MT5から切断"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("MT5から切断しました")
    
    def get_deals(self, days: int = 7) -> List[Dict]:
        """
        指定期間の取引履歴を取得
        
        Args:
            days: 過去何日分の取引を取得するか（デフォルト: 7日）
        
        Returns:
            取引データのリスト
        """
        if not self.connected:
            raise ConnectionError("MT5に接続されていません")
        
        # 日付範囲の設定
        date_to = datetime.now()
        date_from = date_to - timedelta(days=days)
        
        # 取引履歴を取得
        deals = mt5.history_deals_get(date_from, date_to)
        
        if deals is None:
            print(f"取引履歴の取得エラー: {mt5.last_error()}")
            return []
        
        if len(deals) == 0:
            print("取引履歴が見つかりませんでした")
            return []
        
        # データを辞書形式に変換
        deals_list = []
        for deal in deals:
            deal_dict = {
                'ticket': deal.ticket,
                'order': deal.order,
                'time': datetime.fromtimestamp(deal.time),
                'type': self._get_deal_type_name(deal.type),
                'entry': self._get_entry_type_name(deal.entry),
                'symbol': deal.symbol,
                'volume': deal.volume,
                'price': deal.price,
                'commission': deal.commission,
                'swap': deal.swap,
                'profit': deal.profit,
                'fee': deal.fee,
                'comment': deal.comment
            }
            deals_list.append(deal_dict)
        
        print(f"{len(deals_list)}件の取引を取得しました")
        return deals_list
    
    def get_closed_positions(self, days: int = 7) -> List[Dict]:
        """
        決済済みポジションの情報を取得（エントリーとクローズをペアにする）
        
        Args:
            days: 過去何日分の取引を取得するか
        
        Returns:
            決済済みポジションのリスト
        """
        deals = self.get_deals(days)
        
        # ポジションをグループ化
        positions = {}
        
        for deal in deals:
            order = deal['order']
            
            if order not in positions:
                positions[order] = {
                    'order': order,
                    'symbol': deal['symbol'],
                    'entry_deal': None,
                    'exit_deal': None
                }
            
            # エントリー（IN）とクローズ（OUT）を分類
            if deal['entry'] == 'IN':
                positions[order]['entry_deal'] = deal
            elif deal['entry'] == 'OUT':
                positions[order]['exit_deal'] = deal
        
        # エントリーとクローズが両方あるもののみを抽出
        closed_positions = []
        for pos in positions.values():
            if pos['entry_deal'] and pos['exit_deal']:
                entry = pos['entry_deal']
                exit_deal = pos['exit_deal']
                
                closed_position = {
                    'ticket': pos['order'],
                    'symbol': pos['symbol'],
                    'type': entry['type'],
                    'volume': entry['volume'],
                    'open_time': entry['time'],
                    'close_time': exit_deal['time'],
                    'open_price': entry['price'],
                    'close_price': exit_deal['price'],
                    'commission': entry['commission'] + exit_deal['commission'],
                    'swap': entry['swap'] + exit_deal['swap'],
                    'profit': exit_deal['profit']
                }
                closed_positions.append(closed_position)
        
        print(f"{len(closed_positions)}件の決済済みポジションを取得しました")
        return closed_positions
    
    @staticmethod
    def _get_deal_type_name(deal_type: int) -> str:
        """取引タイプを文字列に変換"""
        types = {
            0: 'BUY',
            1: 'SELL',
            2: 'BALANCE',
            3: 'CREDIT',
            4: 'CHARGE',
            5: 'CORRECTION',
            6: 'BONUS',
            7: 'COMMISSION',
            8: 'COMMISSION_DAILY',
            9: 'COMMISSION_MONTHLY',
            10: 'AGENT_DAILY',
            11: 'AGENT_MONTHLY',
            12: 'INTERESTRATE',
            13: 'BUY_CANCELED',
            14: 'SELL_CANCELED',
            15: 'DIVIDEND',
            16: 'DIVIDEND_FRANKED',
            17: 'TAX'
        }
        return types.get(deal_type, f'UNKNOWN({deal_type})')
    
    @staticmethod
    def _get_entry_type_name(entry: int) -> str:
        """エントリータイプを文字列に変換"""
        types = {
            0: 'IN',
            1: 'OUT',
            2: 'INOUT',
            3: 'OUT_BY'
        }
        return types.get(entry, f'UNKNOWN({entry})')


# テスト実行用
if __name__ == '__main__':
    from config import Config
    
    Config.validate()
    
    connector = MT5Connector(
        login=Config.MT5_LOGIN,
        password=Config.MT5_PASSWORD,
        server=Config.MT5_SERVER
    )
    
    if connector.connect():
        try:
            positions = connector.get_closed_positions(days=30)
            for pos in positions[:5]:  # 最新5件を表示
                print(f"\n取引番号: {pos['ticket']}")
                print(f"通貨ペア: {pos['symbol']}")
                print(f"タイプ: {pos['type']}")
                print(f"ロット: {pos['volume']}")
                print(f"開始: {pos['open_time']} @ {pos['open_price']}")
                print(f"終了: {pos['close_time']} @ {pos['close_price']}")
                print(f"損益: {pos['profit']}")
        finally:
            connector.disconnect()
