"""
Hummingbot Original Script: Simple Pure Market Making (simple_pmm.py)
Source: hummingbot/scripts/simple_pmm.py from official Hummingbot repository.

Pure Market Making is a strategy where Hummingbot posts limit buy (bid) and limit sell (ask)
orders around the current mid price to earn the bid-ask spread and exchange maker rebates.
"""

from decimal import Decimal
from typing import Dict, List, Optional
import time

class SimplePMMParameters:
    """
    Original Hummingbot Pure Market Making Configuration Parameters
    """
    exchange: str = "binance_perpetual"
    trading_pair: str = "ETH-USDT"
    
    # Distance from mid-price to place orders (e.g. 0.5% = 0.005)
    bid_spread: Decimal = Decimal("0.005")
    ask_spread: Decimal = Decimal("0.005")
    
    # Size of each order
    order_amount: Decimal = Decimal("0.1")
    
    # Interval in seconds to cancel old orders and place new ones based on updated mid price
    order_refresh_time: float = 30.0
    
    # Order refresh tolerance in pct
    order_refresh_tolerance_pct: Decimal = Decimal("0.001")
    
    # Stop loss spread
    stop_loss_spread: Optional[Decimal] = Decimal("0.02")
    
    # Inventory skew: adjust spreads based on held inventory ratio
    inventory_skew_enabled: bool = True
    inventory_target_base_pct: Decimal = Decimal("0.5")


class SimplePureMarketMaking:
    """
    Official Hummingbot Pure Market Making Execution Algorithm (Core Logic)
    """
    def __init__(self, params: SimplePMMParameters = SimplePMMParameters()):
        self.p = params
        self.last_order_refresh_timestamp = 0.0
        self.active_bid_order = None
        self.active_ask_order = None
        
    def calculate_order_prices(self, mid_price: Decimal, base_balance: Decimal, quote_balance: Decimal) -> Dict[str, Decimal]:
        """
        Calculates the buy (bid) and sell (ask) prices.
        Includes Hummingbot's inventory skew logic if enabled.
        """
        bid_spread = self.p.bid_spread
        ask_spread = self.p.ask_spread
        
        # Hummingbot Inventory Skew Mechanism:
        # If holding too much base asset -> widen bid spread (buy less) and tighten ask spread (sell faster)
        if self.p.inventory_skew_enabled:
            total_value = (base_balance * mid_price) + quote_balance
            if total_value > Decimal("0"):
                current_base_ratio = (base_balance * mid_price) / total_value
                skew_delta = current_base_ratio - self.p.inventory_target_base_pct
                
                # Adjust spreads dynamically
                bid_spread = max(Decimal("0.001"), self.p.bid_spread + (skew_delta * Decimal("0.01")))
                ask_spread = max(Decimal("0.001"), self.p.ask_spread - (skew_delta * Decimal("0.01")))
        
        # Calculate limit order prices
        bid_price = mid_price * (Decimal("1") - bid_spread)
        ask_price = mid_price * (Decimal("1") + ask_spread)
        
        return {
            "bid_price": bid_price,
            "ask_price": ask_price,
            "bid_spread": bid_spread,
            "ask_spread": ask_spread
        }

    def on_tick(self, current_time: float, mid_price: Decimal, base_balance: Decimal, quote_balance: Decimal):
        """
        Called on every tick / second by Hummingbot clock engine.
        Cancels stale orders and places fresh dual-sided limit orders.
        """
        if current_time - self.last_order_refresh_timestamp < self.p.order_refresh_time:
            return None # Wait for refresh time

        self.last_order_refresh_timestamp = current_time
        prices = self.calculate_order_prices(mid_price, base_balance, quote_balance)
        
        return {
            "action": "refresh_orders",
            "cancel_active_orders": True,
            "new_bid": {
                "price": float(prices["bid_price"]),
                "amount": float(self.p.order_amount),
                "type": "LIMIT_MAKER"
            },
            "new_ask": {
                "price": float(prices["ask_price"]),
                "amount": float(self.p.order_amount),
                "type": "LIMIT_MAKER"
            }
        }
