#!/usr/bin/env python3
"""
対話式ポジション計算機 (RR比、損失額、ポジションサイズ、利確位置)
使い方: スクリプトを実行して、指示に従って数値を入力してください。

注: パラメータの意味はプロンプト内に日本語で説明しています。
"""

import math


def to_float(s, default=None):
    try:
        return float(s)
    except Exception:
        return default


def calc_by_pips(balance, risk_pct, pip_diff, pip_value_per_lot, lot_unit=100000):
    """
    balance: 口座残高（通貨）
    risk_pct: リスク割合（%）
    pip_diff: 損切り幅（pips）
    pip_value_per_lot: 1ロットあたりの1pipの価値（口座通貨）
    lot_unit: 1ロットの基準単位（デフォルト 100000）
    """
    risk_amount = balance * (risk_pct / 100.0)
    if pip_diff <= 0 or pip_value_per_lot <= 0:
        raise ValueError("pip差またはpip価値は正の数にしてください")
    lots = risk_amount / (pip_diff * pip_value_per_lot)
    units = lots * lot_unit
    return {
        "risk_amount": risk_amount,
        "pip_diff": pip_diff,
        "lots": lots,
        "units": units,
    }


def calc_take_profit_price(entry_price, stop_price, rr):
    # entry_price と stop_price の関係から損切り幅をとり、RRに基づき利確価格を計算
    # ロング/ショートを自動判別
    if rr <= 0:
        raise ValueError("RRは正の数で入力してください")
    direction = "long" if entry_price > stop_price else "short" if entry_price < stop_price else None
    if direction is None:
        raise ValueError("Entry と Stop は異なる価格である必要があります")
    sl_dist = abs(entry_price - stop_price)
    tp_dist = sl_dist * rr
    if direction == "long":
        tp = entry_price + tp_dist
    else:
        tp = entry_price - tp_dist
    return tp, sl_dist, tp_dist, direction


def print_results(res, entry_price=None, stop_price=None, rr=None, pip_value_per_lot=None, lot_unit=100000):
    print('\n=== 計算結果 ===')
    print(f"リスク金額: {res['risk_amount']:.2f}")
    print(f"損切り(pips): {res['pip_diff']:.1f}")
    print(f"ポジション(ロット): {res['lots']:.6f}")
    print(f"ポジション(単位): {res['units']:.1f}")
    if pip_value_per_lot:
        # 想定損失額（チェック）： pip_diff * pip_value_per_lot * lots
        loss_check = res['pip_diff'] * pip_value_per_lot * res['lots']
        print(f"想定損失額(計算チェック): {loss_check:.2f}")
    if entry_price is not None and stop_price is not None and rr is not None:
        try:
            tp, sl_dist, tp_dist, direction = calc_take_profit_price(entry_price, stop_price, rr)
            print(f"ポジション方向: {direction}")
            print(f"損切り幅(価格差): {sl_dist:.6f}")
            print(f"目標利確幅(価格差): {tp_dist:.6f}")
            print(f"利確価格: {tp:.6f}")
            # 目標での想定利益額
            if pip_value_per_lot:
                # pipに変換するにはtp_distをpipsに合わせる必要があるが、ここではtp_dist/pip_sizeの事前変換をユーザに任せる
                pass
        except Exception as e:
            print(f"利確位置の計算でエラー: {e}")
    print('================\n')


def prompt_loop():
    print("対話式ポジション計算機")
    print("必要な値を入力してください。Enterで前回値を使うか、qで終了します。")

    prev = {}
    while True:
        s = input("--- 新規計算開始。続けるにはEnter --- (qで終了): ").strip()
        if s.lower() == 'q':
            break

        bal = to_float(input(f"口座残高 (前回: {prev.get('balance', '')}): "), prev.get('balance'))
        if bal is None:
            print("口座残高が必要です")
            continue
        prev['balance'] = bal

        risk = to_float(input(f"リスク割合 (%) (例: 1 = 1%) (前回: {prev.get('risk_pct', '')}): "), prev.get('risk_pct', 1.0))
        if risk is None:
            print("リスク割合が必要です")
            continue
        prev['risk_pct'] = risk

        mode = input("損切り幅を入力する単位を選択してください: 1) pips  2) 価格差 (price units) (デフォルト 1): ").strip() or '1'
        if mode not in ('1', '2'):
            mode = '1'

        if mode == '1':
            pip_diff = to_float(input(f"損切り幅 (pips) (前回: {prev.get('pip_diff','')}): "), prev.get('pip_diff'))
            prev['pip_diff'] = pip_diff
            pip_value = to_float(input(f"1pip当たりの価値（口座通貨、1ロットあたり） (例: 10) (前回: {prev.get('pip_value','')}): "), prev.get('pip_value'))
            if pip_value is None:
                print("pip価値が必要です")
                continue
            prev['pip_value'] = pip_value

            lot_unit = to_float(input(f"1ロットの基準単位 (デフォルト 100000): "), 100000) or 100000
            try:
                res = calc_by_pips(bal, risk, pip_diff, pip_value, lot_unit)
            except Exception as e:
                print(f"計算エラー: {e}")
                continue

            # RR入力オプション
            rr = to_float(input(f"利確のRR比を入力 (例: 2 = 2:1) (空白でスキップ) (前回: {prev.get('rr','')}): "), prev.get('rr'))
            if rr is not None:
                prev['rr'] = rr
                # entry/stop を聞いて価格で利確計算
                entry = to_float(input(f"エントリー価格 (任意、利確価格を計算したい場合): "), prev.get('entry'))
                stop = to_float(input(f"損切り価格 (任意、利確価格を計算したい場合): "), prev.get('stop'))
                prev['entry'] = entry
                prev['stop'] = stop
                print_results(res, entry_price=entry, stop_price=stop, rr=rr, pip_value_per_lot=pip_value, lot_unit=lot_unit)
            else:
                print_results(res, pip_value_per_lot=pip_value, lot_unit=lot_unit)

        else:
            # 価格差で入力する場合
            price_diff = to_float(input(f"損切り幅 (価格差) (前回: {prev.get('price_diff','')}): "), prev.get('price_diff'))
            prev['price_diff'] = price_diff
            # 1価格差当たりの1ロットの価値を入力
            value_per_price_unit = to_float(input(f"1価格差単位あたりの価値（口座通貨、1ロットあたり） (例: 1000): (前回: {prev.get('value_per_price','')}): "), prev.get('value_per_price'))
            prev['value_per_price'] = value_per_price_unit
            if price_diff is None or value_per_price_unit is None:
                print("必要な値が足りません")
                continue
            # このモードは内部的には pips モードと同じ計算を行う
            # price_diff を "pips" と見なして value_per_price を pip価値として扱う
            try:
                res = calc_by_pips(bal, risk, price_diff, value_per_price, lot_unit=prev.get('lot_unit', 100000))
            except Exception as e:
                print(f"計算エラー: {e}")
                continue

            rr = to_float(input(f"利確のRR比を入力 (空白でスキップ): "), prev.get('rr'))
            if rr is not None:
                entry = to_float(input(f"エントリー価格 (任意、利確価格を計算したい場合): "), prev.get('entry'))
                stop = to_float(input(f"損切り価格 (任意、利確価格を計算したい場合): "), prev.get('stop'))
                prev['entry'] = entry
                prev['stop'] = stop
                print_results(res, entry_price=entry, stop_price=stop, rr=rr, pip_value_per_lot=value_per_price, lot_unit=prev.get('lot_unit',100000))
            else:
                print_results(res, pip_value_per_lot=value_per_price, lot_unit=prev.get('lot_unit',100000))

    print("終了します。")


if __name__ == '__main__':
    try:
        prompt_loop()
    except KeyboardInterrupt:
        print('\nユーザー操作で中断されました。')
