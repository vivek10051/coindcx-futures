"""
Test script for placing limit orders on CoinDCX Futures
Uses INR wallet balance as collateral
"""

from coindcx_futures import CoinDCXFutures, OrderSide, OrderType, TimeInForce
import time
import sys


def get_current_price(client, pair):
    """Get current market price for a pair"""
    orderbook = client.get_orderbook(pair, depth=1)
    if orderbook and 'bids' in orderbook and 'asks' in orderbook:
        best_bid = float(list(orderbook['bids'].keys())[0])
        best_ask = float(list(orderbook['asks'].keys())[0])
        mid_price = (best_bid + best_ask) / 2
        return {
            'bid': best_bid,
            'ask': best_ask,
            'mid': mid_price,
            'spread': best_ask - best_bid
        }
    return None


def place_limit_buy_order(client, pair, percentage_below_market=5, quantity=0.001, leverage=1):
    """Place a limit buy order below market price"""
    print("\n" + "="*60)
    print("PLACING LIMIT BUY ORDER")
    print("="*60)
    
    # Get current market price
    price_info = get_current_price(client, pair)
    if not price_info:
        print("Error: Could not fetch market price")
        return None
    
    print(f"\nCurrent Market Price for {pair}:")
    print(f"  Best Bid: ${price_info['bid']:,.2f}")
    print(f"  Best Ask: ${price_info['ask']:,.2f}")
    print(f"  Mid Price: ${price_info['mid']:,.2f}")
    print(f"  Spread: ${price_info['spread']:.2f}")
    
    # Calculate limit price (below market)
    limit_price = price_info['bid'] * (1 - percentage_below_market/100)
    
    print(f"\nOrder Details:")
    print(f"  Pair: {pair}")
    print(f"  Side: BUY")
    print(f"  Type: LIMIT ORDER")
    print(f"  Quantity: {quantity}")
    print(f"  Limit Price: ${limit_price:,.2f} ({percentage_below_market}% below bid)")
    print(f"  Leverage: {leverage}x")
    print(f"  Collateral: INR wallet balance")
    print(f"  Time in Force: GOOD_TILL_CANCEL")
    
    # Confirm before placing
    confirm = input("\nPlace this order? (yes/no): ").lower()
    if confirm != 'yes':
        print("Order cancelled by user")
        return None
    
    try:
        # Place the order
        print("\nPlacing order...")
        order_response = client.place_order(
            pair=pair,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT_ORDER,
            quantity=quantity,
            price=limit_price,
            leverage=leverage,
            time_in_force=TimeInForce.GOOD_TILL_CANCEL
        )
        
        if order_response and len(order_response) > 0:
            order = order_response[0]
            order_id = order['id']
            print(f"\n[SUCCESS] Order placed successfully!")
            print(f"  Order ID: {order_id}")
            print(f"  Status: {order.get('status')}")
            print(f"  Created at: {order.get('created_at')}")
            return order_id
        else:
            print("[ERROR] Order placement failed - no order ID returned")
            return None
            
    except Exception as e:
        print(f"[ERROR] Failed to place order: {e}")
        return None


def place_limit_sell_order(client, pair, percentage_above_market=5, quantity=0.001, leverage=1):
    """Place a limit sell order above market price"""
    print("\n" + "="*60)
    print("PLACING LIMIT SELL ORDER")
    print("="*60)
    
    # Get current market price
    price_info = get_current_price(client, pair)
    if not price_info:
        print("Error: Could not fetch market price")
        return None
    
    print(f"\nCurrent Market Price for {pair}:")
    print(f"  Best Bid: ${price_info['bid']:,.2f}")
    print(f"  Best Ask: ${price_info['ask']:,.2f}")
    print(f"  Mid Price: ${price_info['mid']:,.2f}")
    print(f"  Spread: ${price_info['spread']:.2f}")
    
    # Calculate limit price (above market)
    limit_price = price_info['ask'] * (1 + percentage_above_market/100)
    
    print(f"\nOrder Details:")
    print(f"  Pair: {pair}")
    print(f"  Side: SELL")
    print(f"  Type: LIMIT ORDER")
    print(f"  Quantity: {quantity}")
    print(f"  Limit Price: ${limit_price:,.2f} ({percentage_above_market}% above ask)")
    print(f"  Leverage: {leverage}x")
    print(f"  Collateral: INR wallet balance")
    print(f"  Time in Force: GOOD_TILL_CANCEL")
    
    # Confirm before placing
    confirm = input("\nPlace this order? (yes/no): ").lower()
    if confirm != 'yes':
        print("Order cancelled by user")
        return None
    
    try:
        # Place the order
        print("\nPlacing order...")
        order_response = client.place_order(
            pair=pair,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT_ORDER,
            quantity=quantity,
            price=limit_price,
            leverage=leverage,
            time_in_force=TimeInForce.GOOD_TILL_CANCEL
        )
        
        if order_response and len(order_response) > 0:
            order = order_response[0]
            order_id = order['id']
            print(f"\n[SUCCESS] Order placed successfully!")
            print(f"  Order ID: {order_id}")
            print(f"  Status: {order.get('status')}")
            print(f"  Created at: {order.get('created_at')}")
            return order_id
        else:
            print("[ERROR] Order placement failed - no order ID returned")
            return None
            
    except Exception as e:
        print(f"[ERROR] Failed to place order: {e}")
        return None


def check_order_status(client, order_id):
    """Check the status of an order"""
    print(f"\nChecking status of order {order_id}...")
    
    try:
        orders = client.get_orders(status="open")
        for order in orders:
            if order.get('id') == order_id:
                print(f"Order Status: {order.get('status')}")
                print(f"  Remaining Quantity: {order.get('remaining_quantity')}")
                print(f"  Filled Quantity: {order.get('filled_quantity', 0)}")
                return order
        
        print("Order not found in open orders (may be filled or cancelled)")
        return None
        
    except Exception as e:
        print(f"Error checking order status: {e}")
        return None


def cancel_order(client, order_id):
    """Cancel an order"""
    print(f"\nCancelling order {order_id}...")
    
    try:
        result = client.cancel_order(order_id)
        print(f"Cancel result: {result}")
        return True
    except Exception as e:
        print(f"Error cancelling order: {e}")
        return False


def main():
    """Main test function for limit orders"""
    print("\n" + "="*60)
    print("COINDCX FUTURES - LIMIT ORDER TEST")
    print("="*60)
    print("\nThis script will help you place limit orders on CoinDCX Futures")
    print("Using INR wallet balance as collateral")
    
    # Initialize client
    print("\nInitializing CoinDCX client...")
    client = CoinDCXFutures()
    print("Client initialized successfully!")
    
    # Choose trading pair
    print("\nAvailable popular pairs:")
    print("1. B-BTC_USDT (Bitcoin)")
    print("2. B-ETH_USDT (Ethereum)")
    print("3. B-SOL_USDT (Solana)")
    print("4. B-MATIC_USDT (Polygon)")
    print("5. Custom pair")
    
    choice = input("\nSelect pair (1-5): ")
    
    pair_map = {
        '1': 'B-BTC_USDT',
        '2': 'B-ETH_USDT',
        '3': 'B-SOL_USDT',
        '4': 'B-MATIC_USDT'
    }
    
    if choice in pair_map:
        pair = pair_map[choice]
    elif choice == '5':
        pair = input("Enter pair (e.g., B-BTC_USDT): ")
    else:
        print("Invalid choice")
        return
    
    print(f"\nSelected pair: {pair}")
    
    # Get instrument details
    details = client.get_instrument_details(pair)
    if details and 'instrument' in details:
        inst = details['instrument']
        print(f"\nInstrument Details:")
        print(f"  Min Trade Size: {inst.get('min_trade_size')}")
        print(f"  Max Leverage: {inst.get('max_leverage_long')}x")
        print(f"  Maker Fee: {inst.get('maker_fee')}%")
        print(f"  Taker Fee: {inst.get('taker_fee')}%")
    
    # Main menu
    while True:
        print("\n" + "="*60)
        print("ACTIONS:")
        print("1. Place LIMIT BUY order (below market)")
        print("2. Place LIMIT SELL order (above market)")
        print("3. Check open orders")
        print("4. Cancel an order")
        print("5. Check positions")
        print("6. Exit")
        
        action = input("\nSelect action (1-6): ")
        
        if action == '1':
            # Place buy order
            try:
                qty = float(input("Enter quantity (default 0.001): ") or "0.001")
                pct = float(input("Percentage below market (default 5%): ") or "5")
                lev = int(input("Leverage (1-20, default 1): ") or "1")
                
                order_id = place_limit_buy_order(client, pair, pct, qty, lev)
                if order_id:
                    print(f"\nOrder ID {order_id} saved for tracking")
                    
            except ValueError:
                print("Invalid input")
                
        elif action == '2':
            # Place sell order
            try:
                qty = float(input("Enter quantity (default 0.001): ") or "0.001")
                pct = float(input("Percentage above market (default 5%): ") or "5")
                lev = int(input("Leverage (1-20, default 1): ") or "1")
                
                order_id = place_limit_sell_order(client, pair, pct, qty, lev)
                if order_id:
                    print(f"\nOrder ID {order_id} saved for tracking")
                    
            except ValueError:
                print("Invalid input")
                
        elif action == '3':
            # Check open orders
            print("\nFetching open orders...")
            try:
                orders = client.get_orders(status="open")
                if orders:
                    print(f"\nFound {len(orders)} open orders:")
                    for order in orders:
                        print(f"\n  Order ID: {order.get('id')}")
                        print(f"    Pair: {order.get('pair')}")
                        print(f"    Side: {order.get('side')}")
                        print(f"    Price: ${order.get('price')}")
                        print(f"    Quantity: {order.get('total_quantity')}")
                        print(f"    Remaining: {order.get('remaining_quantity')}")
                else:
                    print("No open orders")
            except Exception as e:
                print(f"Error fetching orders: {e}")
                
        elif action == '4':
            # Cancel order
            order_id = input("Enter order ID to cancel: ")
            if order_id:
                cancel_order(client, order_id)
                
        elif action == '5':
            # Check positions
            print("\nFetching positions...")
            try:
                positions = client.get_positions()
                active = [p for p in positions if p.active_pos != 0]
                
                if active:
                    print(f"\nActive positions:")
                    for pos in active:
                        print(f"\n  {pos.pair}:")
                        print(f"    Size: {pos.active_pos}")
                        print(f"    Avg Price: ${pos.avg_price}")
                        print(f"    Mark Price: ${pos.mark_price}")
                        print(f"    Liquidation: ${pos.liquidation_price}")
                        print(f"    Margin (INR): {pos.locked_margin}")
                        print(f"    PnL: {pos.pnl}")
                else:
                    print("No active positions")
            except Exception as e:
                print(f"Error fetching positions: {e}")
                
        elif action == '6':
            print("\nExiting...")
            break
        else:
            print("Invalid choice")
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60)


if __name__ == "__main__":
    main()