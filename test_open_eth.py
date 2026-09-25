import os
import requests
import urllib3
from src.execution_engine import BinanceExecutionEngine

urllib3.disable_warnings()

def open_eth_position(usdt_amount=100.0, side="BUY"):
    engine = BinanceExecutionEngine()
    print("=== BINANCE DEMO (TESTNET) ORDER EXECUTION ===")
    
    # 1. Check current balance
    bal = engine.get_account_balance()
    print(f"Current Balance: ${bal.get('total_wallet_balance')} USDT | Available: ${bal.get('available_balance')} USDT")
    
    # 2. Get current ETH price
    res = requests.get("https://testnet.binancefuture.com/fapi/v1/ticker/price?symbol=ETHUSDT", verify=False, timeout=8)
    price_data = res.json()
    eth_price = float(price_data.get("price", 2500.0))
    print(f"Current ETH Price on Testnet: ${eth_price:.2f}")
    
    # 3. Set leverage 3x
    engine.set_leverage("ETHUSDT", 3)
    
    # 4. Calculate Quantity for $100 notional (step size for ETH is 0.001)
    qty = round(usdt_amount / eth_price, 3)
    if qty < 0.001:
        qty = 0.001
        
    notional = qty * eth_price
    print(f"Opening {side} {qty} ETH (~${notional:.2f} Notional / ~${notional/3:.2f} Margin at 3x)...")
    
    # Optional TP / SL (e.g. 2% SL, 4% TP)
    if side == "BUY":
        sl = round(eth_price * 0.98, 2)
        tp = round(eth_price * 1.04, 2)
    else:
        sl = round(eth_price * 1.02, 2)
        tp = round(eth_price * 0.96, 2)
        
    order_res = engine.place_order(
        symbol="ETHUSDT",
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
    open_eth_position(100.0, "BUY")
