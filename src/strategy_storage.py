"""手法データのローカルJSON管理モジュール"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime


class StrategyStorage:
    """手法データをJSONファイルで管理するクラス"""
    
    def __init__(self, json_path: str = "strategies.json"):
        """
        Args:
            json_path: JSONファイルのパス
        """
        self.json_path = json_path
        self.strategies = {}
        self._load_from_file()
    
    def _load_from_file(self):
        """JSONファイルから手法データを読み込む"""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    self.strategies = json.load(f)
                print(f"✓ {len(self.strategies)}件の手法を読み込みました（{self.json_path}）")
            except Exception as e:
                print(f"手法データの読み込みエラー: {e}")
                self.strategies = {}
        else:
            print(f"手法データファイルが存在しません。新規作成します: {self.json_path}")
            self.strategies = {}
            self._save_to_file()
    
    def _save_to_file(self):
        """JSONファイルに手法データを保存"""
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.strategies, f, ensure_ascii=False, indent=2)
            print(f"✓ 手法データを保存しました（{self.json_path}）")
            return True
        except Exception as e:
            print(f"手法データの保存エラー: {e}")
            return False
    
    def get_all_strategies(self) -> Dict[str, Dict]:
        """
        全ての手法を取得
        
        Returns:
            手法名をキーとした辞書 {手法名: {name, rules, created_time, last_edited_time}}
        """
        return self.strategies.copy()
    
    def create_strategy(self, strategy_name: str, rules: str = "") -> bool:
        """
        新しい手法を作成
        
        Args:
            strategy_name: 手法名
            rules: 手法のルール・説明
        
        Returns:
            成功時True、失敗時False
        """
        if strategy_name in self.strategies:
            print(f"手法 '{strategy_name}' は既に存在します")
            return False
        
        now = datetime.now().isoformat()
        self.strategies[strategy_name] = {
            'name': strategy_name,
            'rules': rules,
            'created_time': now,
            'last_edited_time': now
        }
        
        if self._save_to_file():
            print(f"✓ 手法 '{strategy_name}' を作成しました")
            return True
        return False
    
    def update_strategy_rules(self, strategy_name: str, rules: str) -> bool:
        """
        既存の手法のルールを更新
        
        Args:
            strategy_name: 手法名
            rules: 新しいルール内容
        
        Returns:
            成功時True、失敗時False
        """
        if strategy_name not in self.strategies:
            print(f"手法 '{strategy_name}' が見つかりません")
            return False
        
        self.strategies[strategy_name]['rules'] = rules
        self.strategies[strategy_name]['last_edited_time'] = datetime.now().isoformat()
        
        if self._save_to_file():
            print(f"✓ 手法 '{strategy_name}' のルールを更新しました")
            return True
        return False
    
    def sync_strategy(self, strategy_name: str, rules: str = "") -> bool:
        """
        手法を同期（存在しない場合は作成、存在する場合はルールを更新）
        
        Args:
            strategy_name: 手法名
            rules: ルール内容
        
        Returns:
            成功時True、失敗時False
        """
        if strategy_name in self.strategies:
            return self.update_strategy_rules(strategy_name, rules)
        else:
            return self.create_strategy(strategy_name, rules)
    
    def delete_strategy(self, strategy_name: str) -> bool:
        """
        手法を削除
        
        Args:
            strategy_name: 手法名
        
        Returns:
            成功時True、失敗時False
        """
        if strategy_name not in self.strategies:
            print(f"手法 '{strategy_name}' が見つかりません")
            return False
        
        del self.strategies[strategy_name]
        
        if self._save_to_file():
            print(f"✓ 手法 '{strategy_name}' を削除しました")
            return True
        return False
    
    def get_strategy_rules(self, strategy_name: str) -> str:
        """
        特定の手法のルールを取得
        
        Args:
            strategy_name: 手法名
        
        Returns:
            ルール内容（存在しない場合は空文字列）
        """
        if strategy_name in self.strategies:
            return self.strategies[strategy_name].get('rules', '')
        return ''
