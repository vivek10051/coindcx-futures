"""
Example usage of CoinDCX Futures Module
Shows basic operations like getting market data, placing orders, managing positions
"""

from coindcx_futures import CoinDCXFutures, OrderSide, OrderType, TimeInForce
import asyncio
from datetime import datetime


def example_market_data():
    """Example: Get market data (no authentication required)"""
    print("\n" + "="*60)
    print("MARKET DATA EXAMPLE")
    print("="*60)
    
    client = CoinDCXFutures()
    
    # Get active instruments
    instruments = client.get_active_instruments()
    print(f"\nTotal active instruments: {len(instruments)}")
    print(f"Popular pairs: {[i for i in instruments if 'BTC' in i or 'ETH' in i][:5]}")
    
    # Get BTC/USDT orderbook
    pair = "B-BTC_USDT"
    orderbook = client.get_orderbook(pair, depth=5)
    
    if orderbook and 'bids' in orderbook and 'asks' in orderbook:
        bids = orderbook['bids']
        asks = orderbook['asks']
        if bids and asks:
            best_bid = list(bids.keys())[0]
            best_ask = list(asks.keys())[0]
            print(f"\n{pair} Orderbook:")
            print(f"  Best Bid: ${best_bid}")
            print(f"  Best Ask: ${best_ask}")
            print(f"  Spread: ${float(best_ask) - float(best_bid):.2f}")
    
    # Get recent trades
    trades = client.get_trades(pair)
    if trades and len(trades) > 0:
        latest_trade = trades[0]
        print(f"\nLatest Trade:")
        print(f"  Price: ${latest_trade.get('price')}")
        print(f"  Quantity: {latest_trade.get('quantity')}")


def example_account_info():
    """Example: Get account information (requires authentication)"""
    print("\n" + "="*60)
    print("ACCOUNT INFORMATION EXAMPLE")
    print("="*60)
    
    client = CoinDCXFutures()
    
    try:
        # Get current positions
        positions = client.get_positions()
        print(f"\nTotal positions: {len(positions)}")
        
        # Show active positions
        active_positions = [p for p in positions if p.active_pos != 0]
        if active_positions:
            print("\nActive Positions:")
            for pos in active_positions:
                print(f"  {pos.pair}:")
                print(f"    Size: {pos.active_pos}")
                print(f"    Avg Price: {pos.avg_price}")
                print(f"    Liquidation Price: {pos.liquidation_price}")
                print(f"    Locked Margin (INR): {pos.locked_margin}")
                print(f"    PnL: {pos.pnl}")
        else:
            print("  No active positions")
        
        # Get open orders
        orders = client.get_orders(status="open")
        print(f"\nOpen orders: {len(orders)}")
        
    except Exception as e:
        print(f"Error accessing account: {e}")


def example_place_order(pair=None, side=None, order_type=None, quantity=None, price=None, 
                      leverage=10, time_in_force=TimeInForce.GOOD_TILL_CANCEL, 
                      margin_currency="INR", position_margin_type="isolated"):
    """Example: Place an order (limit or market) with authentication
    
    Args:
        pair: Trading pair (default: B-BTC_USDT)
        side: OrderSide.BUY or OrderSide.SELL (default: BUY)
        order_type: OrderType.LIMIT_ORDER or OrderType.MARKET_ORDER (default: LIMIT_ORDER)
        quantity: Order quantity (default: 0.004 for BTC)
        price: Order price (required for limit orders, ignored for market orders)
        leverage: Leverage multiplier (default: 10)
        time_in_force: Order time in force (default: GOOD_TILL_CANCEL)
        margin_currency: Collateral currency (default: INR)
        position_margin_type: Margin type (default: isolated)
    """
    print("\n" + "="*60)
    print("PLACE ORDER EXAMPLE")
    print("="*60)
    
    client = CoinDCXFutures()
    
    try:
        # Set defaults if not provided
        if pair is None:
            pair = "B-BTC_USDT"
        if side is None:
            side = OrderSide.BUY
        if order_type is None:
            order_type = OrderType.LIMIT_ORDER
            
        # Get current market price for reference
        orderbook = client.get_orderbook(pair, depth=10)
        
        if orderbook and 'bids' in orderbook and orderbook['bids']:
            best_bid = float(list(orderbook['bids'].keys())[0])
            best_ask = float(list(orderbook['asks'].keys())[0]) if 'asks' in orderbook and orderbook['asks'] else best_bid
            
            # Set defaults based on order type
            if quantity is None:
                quantity = 0.004  # Minimum quantity for BTC
                
            # Handle pricing based on order type
            if order_type == OrderType.MARKET_ORDER:
                # Market orders don't need price
                price = None
                print(f"\nPlacing MARKET order:")
                print(f"  Current Market Price: ${best_ask:.2f} (ask) / ${best_bid:.2f} (bid)")
            else:
                # Limit orders need price
                if price is None:
                    # Default to 50% below market for buy, 50% above for sell
                    if side == OrderSide.BUY:
                        price = best_bid * 0.5
                    else:
                        price = best_ask * 1.5
                print(f"\nPlacing LIMIT order:")
                print(f"  Order Price: ${price:.2f}")
                print(f"  Current Market: ${best_ask:.2f} (ask) / ${best_bid:.2f} (bid)")
            
            print(f"  Pair: {pair}")
            print(f"  Side: {side.name}")
            print(f"  Type: {order_type.name}")
            print(f"  Quantity: {quantity}")
            print(f"  Leverage: {leverage}x")
            print(f"  Collateral: {margin_currency}")
            print(f"  Margin Type: {position_margin_type}")
            
            # Build order parameters
            order_params = {
                "pair": pair,
                "side": side,
                "order_type": order_type,
                "quantity": quantity,
                "leverage": leverage,
                "time_in_force": time_in_force,
                "margin_currency": margin_currency,
                "position_margin_type": position_margin_type
            }
            
            # Only add price for limit orders
            if order_type != OrderType.MARKET_ORDER and price is not None:
                order_params["price"] = price
            
            order = client.place_order(**order_params)
            
            if order and len(order) > 0:
                order_id = order[0]['id']
                print(f"\nOrder placed successfully!")
                print(f"  Order ID: {order_id}")
                return order
            else:
                print("\nNo order returned")
                return None
            
    except Exception as e:
        print(f"Error placing order: {e}")
        return None


def example_cancel_order(order_id=None, pair=None):
    """Example: Cancel an order
    
    Args:
        order_id: Order ID to cancel (if None, cancels most recent open order)
        pair: Trading pair (default: B-BTC_USDT)
    """
    print("\n" + "="*60)
    print("CANCEL ORDER EXAMPLE")
    print("="*60)
    
    client = CoinDCXFutures()
    
    try:
        if pair is None:
            pair = "B-BTC_USDT"
            
        # If no order_id provided, get the most recent open order
        if order_id is None:
            print("No order ID provided, fetching open orders...")
            open_orders = client.get_orders(status="open")
            
            if not open_orders:
                print("No open orders to cancel")
                return None
                
            # Filter for the specified pair if there are orders
            pair_orders = [o for o in open_orders if o.pair == pair]
            
            if pair_orders:
                order_to_cancel = pair_orders[0]  # Most recent order for this pair
            else:
                order_to_cancel = open_orders[0]  # Most recent order overall
                
            order_id = order_to_cancel.id
            print(f"Found open order: {order_id}")
            print(f"  Pair: {order_to_cancel.pair}")
            print(f"  Side: {order_to_cancel.side}")
            print(f"  Price: {order_to_cancel.price}")
            print(f"  Quantity: {order_to_cancel.total_quantity}")
        
        print(f"\nCancelling order: {order_id}")
        
        # Cancel the order
        result = client.cancel_order(order_id)
        
        if result:
            print(f"Order cancelled successfully!")
            print(f"  Order ID: {order_id}")
            return result
        else:
            print("Failed to cancel order")
            return None
            
    except Exception as e:
        print(f"Error cancelling order: {e}")
        return None


def example_cancel_all_orders(pair=None):
    """Example: Cancel all open orders
    
    Args:
        pair: Trading pair to cancel orders for (if None, cancels all)
    """
    print("\n" + "="*60)
    print("CANCEL ALL ORDERS EXAMPLE")
    print("="*60)
    
    client = CoinDCXFutures()
    
    try:
        # Get all open orders
        open_orders = client.get_orders(status="open")
        
        if not open_orders:
            print("No open orders to cancel")
            return []
            
        # Filter by pair if specified
        if pair:
            orders_to_cancel = [o for o in open_orders if o.pair == pair]
            print(f"Found {len(orders_to_cancel)} open orders for {pair}")
        else:
            orders_to_cancel = open_orders
            print(f"Found {len(orders_to_cancel)} open orders total")
        
        cancelled_orders = []
        
        # Cancel each order
        for order in orders_to_cancel:
            print(f"\nCancelling order {order.id[:8]}...")
            print(f"  Pair: {order.pair}, Side: {order.side}, Price: {order.price}")
            
            try:
                result = client.cancel_order(order.id)
                if result:
                    cancelled_orders.append(order.id)
                    print(f"  ✓ Cancelled successfully")
                else:
                    print(f"  ✗ Failed to cancel")
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        print(f"\n{len(cancelled_orders)} orders cancelled successfully")
        return cancelled_orders
        
    except Exception as e:
        print(f"Error cancelling orders: {e}")
        return []


async def example_websocket():
    """Example: WebSocket for order and account updates with auto-reconnect"""
    print("\n" + "="*60)
    print("WEBSOCKET ORDER & ACCOUNT UPDATES (24/7)")
    print("="*60)
    
    client = CoinDCXFutures()
    reconnect_delay = 5  # Start with 5 seconds
    max_reconnect_delay = 60  # Max 60 seconds between reconnects
    
    # Define callbacks outside the loop so they persist
    async def on_order_update(data):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[ORDER UPDATE] {timestamp}")
        
        if isinstance(data, dict) and 'data' in data:
            try:
                import json
                orders = json.loads(data['data'])
                for order in orders:
                    print(f"  Order ID: {order.get('id', 'N/A')[:8]}...")
                    print(f"  Symbol: {order.get('pair', 'N/A')}")
                    print(f"  Side: {order.get('side', 'N/A').upper()}")
                    print(f"  Status: {order.get('status', 'N/A').upper()}")
                    print(f"  Type: {order.get('order_type', 'N/A')}")
                    print(f"  Price: ₹{order.get('price', 'N/A')}")
                    print(f"  Quantity: {order.get('total_quantity', 'N/A')}")
                    print(f"  Remaining: {order.get('remaining_quantity', 'N/A')}")
                    print(f"  Leverage: {order.get('leverage', 'N/A')}x")
                    print(f"  Margin: ₹{order.get('locked_margin', 'N/A')}")
                    if order.get('display_message'):
                        print(f"  Message: {order.get('display_message')}")
            except Exception as e:
                print(f"  Raw data: {data}")
        else:
            print(f"  Raw data: {data}")
    
    async def on_balance_update(data):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[BALANCE UPDATE] {timestamp}")
        
        if isinstance(data, dict) and 'data' in data:
            try:
                import json
                balances = json.loads(data['data'])
                for balance in balances:
                    print(f"  Currency: {balance.get('currency', 'N/A')}")
                    print(f"  Available: {balance.get('available_balance', 'N/A')}")
                    print(f"  Locked: {balance.get('locked_balance', 'N/A')}")
            except:
                print(f"  Raw data: {data}")
        else:
            print(f"  Raw data: {data}")
    
    async def on_position_update(data):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[POSITION UPDATE] {timestamp}")
        
        if isinstance(data, dict) and 'data' in data:
            try:
                import json
                positions = json.loads(data['data'])
                for pos in positions:
                    print(f"  Symbol: {pos.get('pair', 'N/A')}")
                    print(f"  Active Position: {pos.get('active_pos', 'N/A')}")
                    print(f"  Inactive Buy: {pos.get('inactive_pos_buy', 'N/A')}")
                    print(f"  Inactive Sell: {pos.get('inactive_pos_sell', 'N/A')}")
                    print(f"  Avg Price: {pos.get('avg_price', 'N/A')}")
                    print(f"  Leverage: {pos.get('leverage', 'N/A')}x")
                    print(f"  Locked Margin: ₹{pos.get('locked_order_margin', 'N/A')}")
            except:
                print(f"  Raw data: {data}")
        else:
            print(f"  Raw data: {data}")
    
    # Infinite loop for automatic reconnection
    while True:
        try:
            # Connect to WebSocket
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Connecting to WebSocket...")
            await client.connect_websocket()
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Connected! (Authenticated channel)")
            
            # Reset reconnect delay on successful connection
            reconnect_delay = 5
            
            # Register callbacks
            client.on_order_update(on_order_update)
            client.on_balance_update(on_balance_update)
            client.on_position_update(on_position_update)
            
            print("\n[OK] Listening for order updates (authenticated)")
            print("[OK] Listening for balance updates (authenticated)")
            print("[OK] Listening for position updates (authenticated)")
            print("\n[INFO] WebSocket running 24/7 with auto-reconnect")
            print("[TIP] Place, modify, or cancel orders to see real-time updates!")
            
            # Keep the connection alive forever
            while True:
                # Check connection every 30 seconds
                await asyncio.sleep(30)
                
                # Check if still connected
                if not client.sio or not client.sio.connected:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"\n[{timestamp}] Connection lost, reconnecting...")
                    break
                else:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] Heartbeat: Connection active")
                    
        except Exception as e:
            print(f"\n[ERROR] WebSocket error: {e}")
            print(f"[INFO] Reconnecting in {reconnect_delay} seconds...")
            
            # Try to disconnect cleanly
            try:
                await client.disconnect_websocket()
            except:
                pass
            
            # Wait before reconnecting with exponential backoff
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("COINDCX FUTURES MODULE - EXAMPLES")
    print("="*60)
    print("\nNote: Using INR wallet balance as collateral")
    
    # # Example 1: Market Data (Public)
    # example_market_data()
    
    # # Example 2: Account Information
    # example_account_info()
    
    # Example 3: Place Orders
    
    # LIMIT ORDER EXAMPLE
    # example_place_order(
    #     pair="B-BTC_USDT",
    #     side=OrderSide.BUY,
    #     order_type=OrderType.LIMIT_ORDER,
    #     quantity=0.025,
    #     price=5000  # Low price so it won't fill
    # )
    
    # MARKET ORDER EXAMPLE
    # example_place_order(
    #     pair="B-BTC_USDT",
    #     side=OrderSide.BUY,
    #     order_type=OrderType.MARKET_ORDER,  # Market order - no price needed
    #     quantity=0.004
    # )
    
    # CANCEL ORDER EXAMPLE
    # example_cancel_order()  # Cancels most recent open order
    # example_cancel_order(order_id="your-order-id-here")  # Cancel specific order
    
    # CANCEL ALL ORDERS EXAMPLE
    # example_cancel_all_orders()  # Cancel all open orders
    # example_cancel_all_orders(pair="B-BTC_USDT")  # Cancel all BTC orders
    
    # # Example 4: WebSocket
    # print("\n[Skipping WebSocket example - run separately with asyncio.run()]")
    # # To run WebSocket example:
    # asyncio.run(example_websocket())
    
    # print("\n" + "="*60)
    # print("EXAMPLES COMPLETED")
    # print("="*60)


if __name__ == "__main__":
    main()