"""
CoinDCX Futures Trading Module
Supports INR wallet balance (INR as collateral)
"""

import hmac
import hashlib
import json
import time
import requests
import asyncio
import socketio
import aiohttp
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET_ORDER = "market_order"
    LIMIT_ORDER = "limit_order"
    STOP_LIMIT = "stop_limit"
    STOP_MARKET = "stop_market"
    TAKE_PROFIT_LIMIT = "take_profit_limit"
    TAKE_PROFIT_MARKET = "take_profit_market"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    UNTRIGGERED = "untriggered"
    INITIAL = "initial"


class TimeInForce(Enum):
    GOOD_TILL_CANCEL = "good_till_cancel"
    IMMEDIATE_OR_CANCEL = "immediate_or_cancel"
    FILL_OR_KILL = "fill_or_kill"


@dataclass
class Order:
    id: str
    pair: str
    side: str
    status: str
    order_type: str
    price: float
    quantity: float
    leverage: float
    avg_price: float = 0.0
    remaining_quantity: float = 0.0
    fee_amount: float = 0.0


@dataclass
class Position:
    id: str
    pair: str
    active_pos: float
    avg_price: float
    liquidation_price: float
    locked_margin: float
    take_profit_trigger: float = 0.0
    stop_loss_trigger: float = 0.0


class CoinDCXFutures:
    """Main CoinDCX Futures Trading Class"""
    
    def __init__(self, api_key: str = None, secret_key: str = None):
        """
        Initialize CoinDCX Futures client
        
        Args:
            api_key: API key (if not provided, will load from .env)
            secret_key: Secret key (if not provided, will load from .env)
        """
        self.api_key = api_key or os.getenv('COINDCX_API_KEY')
        self.secret_key = secret_key or os.getenv('COINDCX_API_SECRET')
        
        if not self.api_key or not self.secret_key:
            raise ValueError("API credentials not provided. Please set COINDCX_API_KEY and COINDCX_SECRET_KEY")
        
        self.base_url = os.getenv('API_BASE_URL', 'https://api.coindcx.com')
        self.websocket_url = os.getenv('WEBSOCKET_URL', 'wss://stream.coindcx.com')
        
        # WebSocket client (will be initialized when needed)
        self.sio = None
        self.ws_connected = False
        
        # Store active subscriptions
        self.subscriptions = set()
        
        logger.info("CoinDCX Futures client initialized")
    
    def _generate_signature(self, body: dict) -> str:
        """Generate HMAC SHA256 signature for API requests"""
        secret_bytes = bytes(self.secret_key, encoding='utf-8')
        json_body = json.dumps(body, separators=(',', ':'))
        signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()
        return signature
    
    def _get_headers(self, signature: str) -> dict:
        """Get headers for API requests"""
        return {
            'Content-Type': 'application/json',
            'X-AUTH-APIKEY': self.api_key,
            'X-AUTH-SIGNATURE': signature
        }
    
    def _make_request(self, method: str, endpoint: str, body: dict = None) -> dict:
        """Make HTTP request to CoinDCX API"""
        url = f"{self.base_url}{endpoint}"
        
        if body is None:
            body = {}
        
        # Add timestamp to body
        body['timestamp'] = int(round(time.time() * 1000))
        
        # Generate signature
        signature = self._generate_signature(body)
        headers = self._get_headers(signature)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                json_body = json.dumps(body, separators=(',', ':'))
                response = requests.post(url, data=json_body, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    # ============= Public Market Data Methods =============
    
    def get_active_instruments(self) -> List[str]:
        """Get list of active futures instruments"""
        url = f"{self.base_url}/exchange/v1/derivatives/futures/data/active_instruments"
        response = requests.get(url)
        return response.json()
    
    def get_instrument_details(self, pair: str) -> dict:
        """Get details for a specific instrument"""
        url = f"{self.base_url}/exchange/v1/derivatives/futures/data/instrument?pair={pair}"
        response = requests.get(url)
        return response.json()
    
    def get_orderbook(self, pair: str, depth: int = 50) -> dict:
        """
        Get orderbook for an instrument
        
        Args:
            pair: Instrument pair (e.g., 'B-BTC_USDT')
            depth: Orderbook depth (10, 20, or 50)
        """
        url = f"https://public.coindcx.com/market_data/v3/orderbook/{pair}-futures/{depth}"
        response = requests.get(url)
        return response.json()
    
    def get_trades(self, pair: str) -> List[dict]:
        """Get recent trades for an instrument"""
        url = f"{self.base_url}/exchange/v1/derivatives/futures/data/trades?pair={pair}"
        response = requests.get(url)
        return response.json()
    
    def get_candlesticks(self, pair: str, resolution: str, from_time: int, to_time: int) -> dict:
        """
        Get candlestick data
        
        Args:
            pair: Instrument pair
            resolution: '1', '5', '60', or '1D' for 1min, 5min, 1hour, 1day
            from_time: Start timestamp (epoch seconds)
            to_time: End timestamp (epoch seconds)
        """
        url = "https://public.coindcx.com/market_data/candlesticks"
        params = {
            "pair": pair,
            "from": from_time,
            "to": to_time,
            "resolution": resolution,
            "pcode": "f"
        }
        response = requests.get(url, params=params)
        return response.json()
    
    # ============= Order Management Methods =============
    
    def place_order(self, 
                   pair: str,
                   side: Union[str, OrderSide],
                   order_type: Union[str, OrderType],
                   quantity: float,
                   leverage: int = 1,
                   price: float = None,
                   time_in_force: Union[str, TimeInForce] = TimeInForce.GOOD_TILL_CANCEL,
                   hidden: bool = False,
                   post_only: bool = False,
                   notification: str = "email_notification",
                   margin_currency: str = "INR",
                   position_margin_type: str = "isolated") -> dict:
        """
        Place a new order
        
        Args:
            pair: Instrument pair (e.g., 'B-BTC_USDT')
            side: 'buy' or 'sell'
            order_type: Type of order
            quantity: Order quantity
            leverage: Leverage (1-20 typically)
            price: Limit price (required for limit orders)
            time_in_force: Order time in force
            hidden: Hide order from orderbook
            post_only: Post-only order
            notification: Notification type
            margin_currency: Margin currency ("INR" or "USDT")
            position_margin_type: Margin type ("isolated" or "cross")
        """
        # Convert enums to strings if needed
        if isinstance(side, OrderSide):
            side = side.value
        if isinstance(order_type, OrderType):
            order_type = order_type.value
        if isinstance(time_in_force, TimeInForce):
            time_in_force = time_in_force.value
        
        body = {
            "order": {
                "pair": pair,
                "order_type": order_type,
                "notification": notification,
                "leverage": leverage,
                "margin_currency_short_name": margin_currency,
                "position_margin_type": position_margin_type,
                "side": side,
                "stop_loss_price": None,
                "take_profit_price": None,
                "time_in_force": time_in_force,
                "total_quantity": quantity
            }
        }
        
        # Add price for limit orders
        if order_type in ["limit_order", "stop_limit", "take_profit_limit"]:
            if price is None:
                raise ValueError(f"Price is required for {order_type}")
            body["order"]["price"] = str(price)
        
        result = self._make_request('POST', '/exchange/v1/derivatives/futures/orders/create', body)
        logger.info(f"Order placed: {result}")
        return result
    
    def cancel_order(self, order_id: str) -> dict:
        """Cancel a specific order"""
        body = {"id": order_id}
        result = self._make_request('POST', '/exchange/v1/derivatives/futures/orders/cancel', body)
        logger.info(f"Order cancelled: {order_id}")
        return result
    
    def cancel_all_orders(self) -> dict:
        """Cancel all open orders"""
        result = self._make_request('POST', '/exchange/v1/derivatives/futures/positions/cancel_all_open_orders')
        logger.info("All orders cancelled")
        return result
    
    def cancel_all_orders_for_position(self, position_id: str) -> dict:
        """Cancel all open orders for a specific position"""
        body = {"id": position_id}
        result = self._make_request('POST', '/exchange/v1/derivatives/futures/positions/cancel_all_open_orders_for_position', body)
        logger.info(f"All orders cancelled for position: {position_id}")
        return result
    
    def get_orders(self, status: str = "open", side: str = None, page: int = 1, size: int = 10) -> List[dict]:
        """
        Get list of orders
        
        Args:
            status: Order status filter (open, filled, cancelled)
            side: Order side filter (buy, sell)
            page: Page number
            size: Page size
        """
        body = {
            "status": status,
            "page": str(page),
            "size": str(size)
        }
        
        if side:
            body["side"] = side
        
        return self._make_request('POST', '/exchange/v1/derivatives/futures/orders', body)
    
    # ============= Position Management Methods =============
    
    def get_positions(self, page: int = 1, size: int = 10) -> List[Position]:
        """Get list of positions"""
        body = {
            "page": str(page),
            "size": str(size)
        }
        
        result = self._make_request('POST', '/exchange/v1/derivatives/futures/positions', body)
        
        # Convert to Position objects
        positions = []
        for pos_data in result:
            positions.append(Position(
                id=pos_data['id'],
                pair=pos_data['pair'],
                active_pos=pos_data['active_pos'],
                avg_price=pos_data['avg_price'],
                liquidation_price=pos_data['liquidation_price'],
                locked_margin=pos_data['locked_margin'],
                take_profit_trigger=pos_data.get('take_profit_trigger', 0.0),
                stop_loss_trigger=pos_data.get('stop_loss_trigger', 0.0)
            ))
        
        return positions
    
    def exit_position(self, position_id: str) -> dict:
        """Exit/Close a position"""
        body = {"id": position_id}
        result = self._make_request('POST', '/exchange/v1/derivatives/futures/positions/exit', body)
        logger.info(f"Position closed: {position_id}")
        return result
    
    def add_margin(self, position_id: str, amount: float) -> dict:
        """Add margin to a position"""
        body = {
            "id": position_id,
            "amount": amount
        }
        result = self._make_request('POST', '/exchange/v1/derivatives/futures/positions/add_margin', body)
        logger.info(f"Margin added to position {position_id}: {amount}")
        return result
    
    def remove_margin(self, position_id: str, amount: float) -> dict:
        """Remove margin from a position"""
        body = {
            "id": position_id,
            "amount": amount
        }
        result = self._make_request('POST', '/exchange/v1/derivatives/futures/positions/remove_margin', body)
        logger.info(f"Margin removed from position {position_id}: {amount}")
        return result
    
    def set_position_tpsl(self, 
                         position_id: str,
                         take_profit_price: float = None,
                         take_profit_limit_price: float = None,
                         stop_loss_price: float = None,
                         stop_loss_limit_price: float = None) -> dict:
        """
        Set Take Profit and Stop Loss for a position
        
        Args:
            position_id: Position ID
            take_profit_price: Take profit trigger price
            take_profit_limit_price: Take profit limit price (for TP limit orders)
            stop_loss_price: Stop loss trigger price
            stop_loss_limit_price: Stop loss limit price (for SL limit orders)
        """
        body = {"id": position_id}
        
        if take_profit_price:
            body["take_profit"] = {
                "stop_price": str(take_profit_price),
                "order_type": "take_profit_market"
            }
            if take_profit_limit_price:
                body["take_profit"]["limit_price"] = str(take_profit_limit_price)
                body["take_profit"]["order_type"] = "take_profit_limit"
        
        if stop_loss_price:
            body["stop_loss"] = {
                "stop_price": str(stop_loss_price),
                "order_type": "stop_market"
            }
            if stop_loss_limit_price:
                body["stop_loss"]["limit_price"] = str(stop_loss_limit_price)
                body["stop_loss"]["order_type"] = "stop_limit"
        
        result = self._make_request('POST', '/exchange/v1/derivatives/futures/positions/create_tpsl', body)
        logger.info(f"TP/SL set for position: {position_id}")
        return result
    
    # ============= Account & Wallet Methods =============
    
    def get_transactions(self, position_ids: str = None, stage: str = "all", page: int = 1, size: int = 10) -> List[dict]:
        """
        Get transactions
        
        Args:
            position_ids: Comma-separated position IDs
            stage: Transaction stage (all, default, funding)
            page: Page number
            size: Page size
        """
        body = {
            "stage": stage,
            "page": str(page),
            "size": str(size)
        }
        
        if position_ids:
            body["position_ids"] = position_ids
        
        return self._make_request('POST', '/exchange/v1/derivatives/futures/positions/transactions', body)
    
    def get_trade_history(self, 
                         pair: str = None,
                         order_id: str = None,
                         from_date: str = None,
                         to_date: str = None,
                         page: int = 1,
                         size: int = 10) -> List[dict]:
        """
        Get trade history
        
        Args:
            pair: Instrument pair filter
            order_id: Order ID filter
            from_date: Start date (YYYY-MM-DD format)
            to_date: End date (YYYY-MM-DD format)
            page: Page number
            size: Page size
        """
        body = {
            "page": str(page),
            "size": str(size)
        }
        
        if pair:
            body["pair"] = pair
        if order_id:
            body["order_id"] = order_id
        if from_date:
            body["from_date"] = from_date
        if to_date:
            body["to_date"] = to_date
        
        return self._make_request('POST', '/exchange/v1/derivatives/futures/trades', body)
    
    # ============= WebSocket Methods =============
    
    async def connect_websocket(self):
        """Connect to WebSocket for real-time data"""
        if self.sio is None:
            # Create AsyncClient with explicit aiohttp support
            self.sio = socketio.AsyncClient(
                logger=False,
                engineio_logger=False
            )
        
        if not self.ws_connected:
            try:
                # Ensure aiohttp is available for websocket transport
                try:
                    import aiohttp
                except ImportError as e:
                    logger.error(f"aiohttp is required for websocket connections: {e}")
                    raise ImportError("aiohttp package is required. Install with: pip install aiohttp")
                
                await self.sio.connect(self.websocket_url, transports=['websocket'])
                self.ws_connected = True
                logger.info("WebSocket connected")
                
                # Start ping task to keep connection alive
                asyncio.create_task(self._ping_task())
                
                # Subscribe to authenticated channel
                await self._subscribe_authenticated_channel()
                
            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}")
                raise
    
    async def _ping_task(self):
        """Send periodic ping to keep WebSocket alive"""
        while self.ws_connected:
            await asyncio.sleep(25)
            try:
                await self.sio.emit('ping', {'data': 'Ping message'})
            except Exception as e:
                logger.error(f"Ping failed: {e}")
    
    async def _subscribe_authenticated_channel(self):
        """Subscribe to authenticated coindcx channel"""
        body = {"channel": "coindcx"}
        signature = self._generate_signature(body)
        
        await self.sio.emit('join', {
            'channelName': 'coindcx',
            'authSignature': signature,
            'apiKey': self.api_key
        })
        
        self.subscriptions.add('coindcx')
        logger.info("Subscribed to authenticated channel")
    
    async def subscribe_orderbook(self, pair: str, depth: int = 50):
        """Subscribe to orderbook updates"""
        channel = f"{pair}@orderbook@{depth}-futures"
        await self.sio.emit('join', {'channelName': channel})
        self.subscriptions.add(channel)
        logger.info(f"Subscribed to orderbook: {channel}")
    
    async def subscribe_trades(self, pair: str):
        """Subscribe to trade updates"""
        channel = f"{pair}@trades-futures"
        await self.sio.emit('join', {'channelName': channel})
        self.subscriptions.add(channel)
        logger.info(f"Subscribed to trades: {channel}")
    
    async def subscribe_prices(self, pair: str):
        """Subscribe to price updates"""
        channel = f"{pair}@prices-futures"
        await self.sio.emit('join', {'channelName': channel})
        self.subscriptions.add(channel)
        logger.info(f"Subscribed to prices: {channel}")
    
    async def subscribe_candlesticks(self, pair: str, interval: str):
        """
        Subscribe to candlestick updates
        
        Args:
            pair: Instrument pair
            interval: '1m', '1h', or '1d'
        """
        channel = f"{pair}_{interval}-futures"
        await self.sio.emit('join', {'channelName': channel})
        self.subscriptions.add(channel)
        logger.info(f"Subscribed to candlesticks: {channel}")
    
    async def unsubscribe(self, channel: str):
        """Unsubscribe from a channel"""
        await self.sio.emit('leave', {'channelName': channel})
        self.subscriptions.discard(channel)
        logger.info(f"Unsubscribed from: {channel}")
    
    async def disconnect_websocket(self):
        """Disconnect WebSocket"""
        if self.sio and self.ws_connected:
            await self.sio.disconnect()
            self.ws_connected = False
            logger.info("WebSocket disconnected")
    
    # ============= WebSocket Event Handlers =============
    
    def on_position_update(self, callback):
        """Register callback for position updates"""
        if self.sio:
            @self.sio.on('df-position-update')
            async def handle_position_update(data):
                await callback(data)
    
    def on_order_update(self, callback):
        """Register callback for order updates"""
        if self.sio:
            @self.sio.on('df-order-update')
            async def handle_order_update(data):
                await callback(data)
    
    def on_balance_update(self, callback):
        """Register callback for balance updates"""
        if self.sio:
            @self.sio.on('balance-update')
            async def handle_balance_update(data):
                await callback(data)
    
    def on_price_change(self, callback):
        """Register callback for price changes"""
        if self.sio:
            @self.sio.on('price-change')
            async def handle_price_change(data):
                await callback(data)
    
    def on_new_trade(self, callback):
        """Register callback for new trades"""
        if self.sio:
            @self.sio.on('new-trade')
            async def handle_new_trade(data):
                await callback(data)
    
    def on_depth_update(self, callback):
        """Register callback for orderbook depth updates"""
        if self.sio:
            @self.sio.on('depth-update')
            async def handle_depth_update(data):
                await callback(data)
    
    def on_candlestick(self, callback):
        """Register callback for candlestick updates"""
        if self.sio:
            @self.sio.on('candlestick')
            async def handle_candlestick(data):
                await callback(data)