import os
import requests
import urllib3
from src.execution_engine import BinanceExecutionEngine

urllib3.disable_warnings()

def open_xrp_position(usdt_amount=100.0, side="BUY"):
    engine = BinanceExecutionEngine()
    print("=== BINANCE DEMO (TESTNET) XRP ORDER EXECUTION ===")
    
    # 1. Check current balance
    bal = engine.get_account_balance()
    print(f"Current Balance: ${bal.get('total_wallet_balance')} USDT | Available: ${bal.get('available_balance')} USDT")
    
    # 2. Get current XRP price
    res = requests.get("https://testnet.binancefuture.com/fapi/v1/ticker/price?symbol=XRPUSDT", verify=False, timeout=8)
    price_data = res.json()
    xrp_price = float(price_data.get("price", 0.60))
    print(f"Current XRP Price on Testnet: ${xrp_price:.4f}")
    
    # 3. Set leverage 3x
    engine.set_leverage("XRPUSDT", 3)
    
    # 4. Calculate Quantity for $100 notional (step size for XRP is 0.1)
    qty = round(usdt_amount / xrp_price, 1)
    if qty < 1.0:
        qty = 1.0
        
    notional = qty * xrp_price
    print(f"Opening {side} {qty} XRP (~${notional:.2f} Notional / ~${notional/3:.2f} Margin at 3x)...")
    
    # Optional TP / SL (e.g. 2.5% SL, 5% TP)
    if side == "BUY":
        sl = round(xrp_price * 0.975, 4)
        tp = round(xrp_price * 1.050, 4)
    else:
        sl = round(xrp_price * 1.025, 4)
        tp = round(xrp_price * 0.950, 4)
        
    order_res = engine.place_order(
        symbol="XRPUSDT",
        side=side,
        quantity=qty,
        stop_loss_price=sl,
        take_profit_price=tp
    )
    print("Order Response:", order_res)
    
    # 5. Check Open Positions
    positions = engine.get_open_positions()
    print(f"\nActive Open Positions ({len(positions)}):")
    for p in positions:
        print(f"-> {p['symbol']} | Side: {p['side']} | Qty: {p['position_amt']} | Entry: ${p['entry_price']} | Mark: ${p['mark_price']} | PnL: ${p['unrealized_pnl']} | Liq: ${p['liquidation_price']}")

if __name__ == "__main__":
    open_xrp_position(100.0, "BUY")
