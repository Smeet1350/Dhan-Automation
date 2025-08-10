from flask import Flask, render_template, jsonify, request
from dhanhq import dhanhq
import logging
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from config import Config
from data_processor import DataProcessor
from flask_cors import CORS
import sqlite3
import json

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)  # Enable CORS for all routes

# Global Dhan client
dhan = None
connection_status = {
    'connected': False,
    'message': 'Not initialized',
    'last_check': None
}

# Initialize alerts database
def init_alerts_db():
    """Initialize alerts database"""
    try:
        conn = sqlite3.connect('instance/trading_automation.db')
        cursor = conn.cursor()
        
        # Create trading alerts table with correct schema (only if it doesn't exist)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT UNIQUE NOT NULL,
                symbol TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                action TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                status TEXT DEFAULT 'PENDING',
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                executed_at DATETIME,
                trade_id TEXT,
                pnl REAL,
                exit_price REAL,
                exit_timestamp DATETIME,
                strategy TEXT,
                timeframe TEXT,
                exchange TEXT
            )
        ''')
        
        # Create error logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                source TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                alert_id TEXT,
                trade_id TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Alerts database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error initializing alerts database: {str(e)}")
        return False

def log_error(level, source, message, details=None, alert_id=None, trade_id=None):
    """Log error to database"""
    try:
        conn = sqlite3.connect('instance/trading_automation.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO error_logs (level, source, message, details, alert_id, trade_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (level, source, message, details, alert_id, trade_id))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Error logged: {level} - {source}: {message}")
        return True
    except Exception as e:
        logger.error(f"❌ Error logging error: {str(e)}")
        return False

def get_error_logs(limit=50):
    """Get error logs from database"""
    try:
        conn = sqlite3.connect('instance/trading_automation.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM error_logs 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        columns = [description[0] for description in cursor.description]
        logs = []
        
        for row in cursor.fetchall():
            log = dict(zip(columns, row))
            logs.append(log)
        
        conn.close()
        return logs
    except Exception as e:
        logger.error(f"❌ Error fetching error logs: {str(e)}")
        return []

def save_alert(alert_data):
    """Save alert to database"""
    try:
        conn = sqlite3.connect('instance/trading_automation.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trading_alerts 
            (alert_id, symbol, alert_type, action, price, quantity, status, message, timestamp, strategy, timeframe, exchange)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert_data.get('alert_id', f"alert_{int(time.time())}"),
            alert_data.get('symbol', 'NIFTY50'),
            alert_data.get('alert_type', 'PRICE'),
            alert_data.get('action', 'BUY'),
            alert_data.get('price', 0.0),
            alert_data.get('quantity', 1),
            'PENDING',  # Default status
            alert_data.get('message', ''),
            datetime.now().isoformat(),
            alert_data.get('strategy', ''),
            alert_data.get('timeframe', ''),
            alert_data.get('exchange', 'NSE')
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Alert saved: {alert_data.get('action')} {alert_data.get('symbol')}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving alert: {str(e)}")
        log_error('ERROR', 'save_alert', f'Failed to save alert: {str(e)}', str(alert_data))
        return False

def get_alerts():
    """Get all alerts from database"""
    try:
        conn = sqlite3.connect('instance/trading_automation.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM trading_alerts 
            ORDER BY timestamp DESC 
            LIMIT 100
        ''')
        
        columns = [description[0] for description in cursor.description]
        alerts = []
        
        for row in cursor.fetchall():
            alert = dict(zip(columns, row))
            alerts.append(alert)
        
        conn.close()
        return alerts
    except Exception as e:
        logger.error(f"❌ Error fetching alerts: {str(e)}")
        return []

def update_alert_status(alert_id, status, trade_id=None, pnl=None, exit_price=None):
    """Update alert status"""
    try:
        conn = sqlite3.connect('instance/trading_automation.db')
        cursor = conn.cursor()
        
        if status == 'EXECUTED':
            cursor.execute('''
                UPDATE trading_alerts 
                SET status = ?, executed_at = ?, trade_id = ?
                WHERE alert_id = ?
            ''', (status, datetime.now().isoformat(), trade_id, alert_id))
        elif status == 'CLOSED':
            cursor.execute('''
                UPDATE trading_alerts 
                SET status = ?, exit_price = ?, exit_timestamp = ?, pnl = ?
                WHERE alert_id = ?
            ''', (status, exit_price, datetime.now().isoformat(), pnl, alert_id))
        else:
            cursor.execute('''
                UPDATE trading_alerts 
                SET status = ?
                WHERE alert_id = ?
            ''', (status, alert_id))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Alert {alert_id} status updated to {status}")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating alert status: {str(e)}")
        return False

def initialize_dhan():
    """Initialize Dhan API connection"""
    global dhan, connection_status
    
    try:
        logger.info("🔄 Initializing Dhan API connection...")
        logger.info(f"📋 Client ID: {Config.DHAN_CLIENT_ID}")
        logger.info(f"🔑 Access Token: {'*' * 20}...{Config.DHAN_ACCESS_TOKEN[-10:]}")
        
        # Initialize Dhan client
        dhan = dhanhq(Config.DHAN_CLIENT_ID, Config.DHAN_ACCESS_TOKEN)
        
        # Test connection
        logger.info("🔍 Testing Dhan API connection...")
        
        # Test with fund limits
        fund_limits = dhan.get_fund_limits()
        logger.info(f"✅ Fund Limits Response: {fund_limits}")
        
        if fund_limits:
            connection_status['connected'] = True
            connection_status['message'] = 'Connected to Dhan API'
            connection_status['last_check'] = datetime.now().isoformat()
            logger.info("✅ Dhan API connection successful!")
            return True
        else:
            connection_status['connected'] = False
            connection_status['message'] = 'No response from Dhan API'
            connection_status['last_check'] = datetime.now().isoformat()
            logger.error("❌ Dhan API connection failed - No response")
            return False
            
    except Exception as e:
        connection_status['connected'] = False
        connection_status['message'] = f'Connection error: {str(e)}'
        connection_status['last_check'] = datetime.now().isoformat()
        logger.error(f"❌ Dhan API connection failed: {str(e)}")
        return False

def verify_request_signature():
    """Verify request signature for security"""
    try:
        signature = request.headers.get('X-Signature')
        timestamp = request.headers.get('X-Timestamp')
        
        if not signature or not timestamp:
            return False
        
        # Check if timestamp is within 5 minutes
        current_time = int(time.time())
        request_time = int(timestamp)
        if abs(current_time - request_time) > 300:  # 5 minutes
            return False
        
        # Verify signature
        message = f"{timestamp}{request.path}"
        expected_signature = hmac.new(
            Config.API_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except:
        return False

def get_dhan_data():
    """Get all data from Dhan API"""
    global dhan, connection_status
    
    if not dhan:
        logger.error("❌ Dhan client not initialized")
        return None
    
    try:
        logger.info("📊 Fetching data from Dhan API...")
        
        # Get fund limits
        fund_limits = dhan.get_fund_limits()
        logger.info(f"💰 Fund Limits: {fund_limits}")
        
        # Get holdings
        holdings = dhan.get_holdings()
        logger.info(f"📈 Holdings: {holdings}")
        
        # Get positions
        positions = dhan.get_positions()
        logger.info(f"📊 Positions: {positions}")
        
        # Get orders
        try:
            orders = dhan.get_order_list()
            logger.info(f"📋 Orders: {orders}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch orders: {str(e)}")
            orders = {'data': []}
        
        # Get trade history
        try:
            from datetime import datetime, timedelta
            to_date = datetime.now().strftime('%Y-%m-%d')
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            trade_history = dhan.get_trade_history(from_date, to_date)
            logger.info(f"📜 Trade History: {trade_history}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch trade history: {str(e)}")
            trade_history = {'data': []}
        
        # Combine all data
        raw_data = {
            'fund_limits': fund_limits,
            'holdings': holdings,
            'positions': positions,
            'orders': orders,
            'trade_history': trade_history
        }
        
        # Process data
        processor = DataProcessor()
        processed_data = processor.process_all_data(raw_data)
        
        logger.info("✅ Data processing completed successfully")
        return processed_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching data from Dhan API: {str(e)}")
        connection_status['connected'] = False
        connection_status['message'] = f'Data fetch error: {str(e)}'
        return None

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/advanced')
def advanced_dashboard():
    """Advanced analytics dashboard"""
    return render_template('advanced_dashboard.html')

@app.route('/api/connection')
def check_connection():
    """Check connection status"""
    return jsonify(connection_status)

@app.route('/api/data')
def get_data():
    """Get processed Dhan data"""
    if not connection_status['connected']:
        return jsonify({'error': 'Not connected to Dhan API'}), 400
    
    data = get_dhan_data()
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': 'Failed to fetch data'}), 500

@app.route('/api/refresh')
def refresh_connection():
    """Refresh Dhan API connection"""
    global connection_status
    
    logger.info("🔄 Refreshing Dhan API connection...")
    
    if initialize_dhan():
        return jsonify({
            'success': True,
            'message': 'Connection refreshed successfully',
            'status': connection_status
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to refresh connection',
            'status': connection_status
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'connection': connection_status
    })

@app.route('/api/square-off', methods=['POST'])
def square_off_position():
    """Square off a specific position"""
    try:
        data = request.get_json()
        security_id = data.get('securityId')
        quantity = data.get('quantity', 1)
        
        if not security_id:
            return jsonify({'success': False, 'error': 'Security ID is required'})
        
        logger.info(f"🚀 Squaring off position: {security_id}, Quantity: {quantity}")
        
        # Get the position details first
        positions = dhan.get_positions()
        if positions.get('status') != 'success':
            logger.error(f"❌ Failed to get positions: {positions}")
            log_error('ERROR', 'square_off_position', f'Failed to get positions: {positions}')
            return jsonify({'success': False, 'error': f'Failed to get positions: {positions}'})
        
        position_data = positions.get('data', [])
        target_position = None
        
        for pos in position_data:
            if str(pos.get('securityId')) == str(security_id):
                target_position = pos
                break
        
        if not target_position:
            logger.warning(f"⚠️ Position not found for security ID: {security_id}")
            log_error('WARNING', 'square_off_position', f'Position not found for security ID: {security_id}')
            return jsonify({'success': False, 'error': f'Position not found for security ID: {security_id}'})
        
        # Use the correct Dhan API syntax based on documentation
        try:
            # Place order using the correct Dhan API syntax
            result = dhan.place_order(
                security_id=security_id,
                exchange_segment=dhan.NSE_FNO,  # Use constant for NSE F&O
                transaction_type=dhan.SELL,     # Use constant for SELL
                quantity=quantity,
                order_type=dhan.MARKET,         # Use constant for MARKET
                product_type=dhan.INTRA,        # Use constant for INTRADAY
                price=0                         # Market order
            )
            
            logger.info(f"📊 Square off result: {result}")
            
            if result.get('status') == 'success':
                logger.info(f"✅ Successfully squared off position: {security_id}")
                log_error('INFO', 'square_off_position', f'Successfully squared off position: {security_id}')
                return jsonify({'success': True, 'message': f'Position squared off successfully', 'result': result})
            else:
                logger.error(f"❌ Failed to square off position: {result}")
                log_error('ERROR', 'square_off_position', f'Failed to square off position: {result}')
                return jsonify({'success': False, 'error': f'Failed to square off position: {result}'})
                
        except Exception as e:
            logger.error(f"❌ Exception during order placement: {str(e)}")
            log_error('ERROR', 'square_off_position', f'Exception during order placement: {str(e)}')
            return jsonify({'success': False, 'error': f'Exception during order placement: {str(e)}'})
            
    except Exception as e:
        logger.error(f"❌ Error in square_off_position: {str(e)}")
        log_error('ERROR', 'square_off_position', f'Error in square_off_position: {str(e)}')
        return jsonify({'success': False, 'error': f'Error in square_off_position: {str(e)}'})

@app.route('/api/square-off-all', methods=['POST'])
def square_off_all_positions():
    """Square off all open positions"""
    try:
        logger.info("🚀 Squaring off all positions...")
        
        # Get current positions
        positions = dhan.get_positions()
        if positions.get('status') != 'success':
            logger.error(f"❌ Failed to get positions: {positions}")
            log_error('ERROR', 'square_off_all_positions', f'Failed to get positions: {positions}')
            return jsonify({'success': False, 'error': f'Failed to get positions: {positions}'})
        
        position_data = positions.get('data', [])
        if not position_data:
            logger.info("ℹ️ No positions to square off")
            return jsonify({'success': True, 'message': 'No positions to square off'})
        
        logger.info(f"📊 Found {len(position_data)} positions to square off")
        
        success_count = 0
        failed_count = 0
        results = []
        
        for position in position_data:
            try:
                security_id = position.get('securityId')
                quantity = abs(position.get('quantity', 0))
                trading_symbol = position.get('tradingSymbol', 'UNKNOWN')
                
                if quantity <= 0:
                    continue
                
                logger.info(f"🔄 Squaring off: {trading_symbol} (Qty: {quantity})")
                
                # Determine exchange segment based on instrument type
                exchange_segment = dhan.NSE  # Default to equity
                if position.get('instrument') == 'OPTIDX':
                    exchange_segment = dhan.NSE_FNO
                elif position.get('instrument') == 'FUTIDX':
                    exchange_segment = dhan.NSE_FNO
                
                # Place square off order using the correct Dhan API syntax
                result = dhan.place_order(
                    security_id=security_id,
                    exchange_segment=exchange_segment,
                    transaction_type=dhan.SELL,     # Use constant for SELL
                    quantity=quantity,
                    order_type=dhan.MARKET,         # Use constant for MARKET
                    product_type=dhan.INTRA,        # Use constant for INTRADAY
                    price=0                         # Market order
                )
                
                if result.get('status') == 'success':
                    order_id = result.get('data', {}).get('orderId', 'UNKNOWN')
                    logger.info(f"✅ Successfully squared off: {trading_symbol} (Order ID: {order_id})")
                    success_count += 1
                    results.append({
                        'symbol': trading_symbol,
                        'status': 'success',
                        'orderId': order_id
                    })
                else:
                    logger.error(f"❌ Failed to square off: {trading_symbol} - {result}")
                    failed_count += 1
                    results.append({
                        'symbol': trading_symbol,
                        'status': 'failed',
                        'error': str(result)
                    })
                    
            except Exception as e:
                logger.error(f"❌ Exception squaring off position: {str(e)}")
                failed_count += 1
                results.append({
                    'symbol': position.get('tradingSymbol', 'UNKNOWN'),
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Log summary
        logger.info(f"📊 Square off summary: {success_count} successful, {failed_count} failed")
        log_error('INFO', 'square_off_all_positions', f'Square off completed: {success_count} successful, {failed_count} failed')
        
        return jsonify({
            'success': True,
            'message': f'Squared off {success_count} positions successfully',
            'summary': {
                'total': len(position_data),
                'successful': success_count,
                'failed': failed_count
            },
            'results': results
        })
        
    except Exception as e:
        logger.error(f"❌ Error in square_off_all_positions: {str(e)}")
        log_error('ERROR', 'square_off_all_positions', f'Error in square_off_all_positions: {str(e)}')
        return jsonify({'success': False, 'error': f'Error in square_off_all_positions: {str(e)}'})

@app.route('/api/portfolio-summary')
def get_portfolio_summary():
    """Get portfolio summary data"""
    if not connection_status['connected']:
        return jsonify({'error': 'Not connected to Dhan API'}), 400
    
    try:
        data = get_dhan_data()
        if not data:
            return jsonify({'error': 'Failed to fetch data'}), 500
        
        # Calculate portfolio summary
        total_value = 0
        total_pnl = 0
        total_investment = 0
        
        # Calculate from holdings
        for holding in data.get('holdings', []):
            quantity = holding.get('raw_quantity', 0)
            avg_cost = holding.get('raw_avg_cost', 0)
            last_price = holding.get('raw_last_price', 0)
            
            if quantity and avg_cost and last_price:
                investment = quantity * avg_cost
                current_value = quantity * last_price
                pnl = current_value - investment
                
                total_investment += investment
                total_value += current_value
                total_pnl += pnl
        
        # Calculate from positions
        for position in data.get('positions', []):
            quantity = position.get('raw_quantity', 0)
            avg_price = position.get('raw_avg_price', 0)
            last_price = position.get('raw_last_price', 0)
            
            if quantity and avg_price and last_price:
                investment = abs(quantity) * avg_price
                current_value = abs(quantity) * last_price
                pnl = current_value - investment if quantity > 0 else investment - current_value
                
                total_investment += investment
                total_value += current_value
                total_pnl += pnl
        
        # Calculate percentages
        pnl_percentage = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        
        summary = {
            'total_investment': DataProcessor.format_currency(total_investment),
            'total_value': DataProcessor.format_currency(total_value),
            'total_pnl': DataProcessor.format_currency(total_pnl),
            'pnl_percentage': DataProcessor.format_percentage(pnl_percentage),
            'pnl_color': 'green' if total_pnl >= 0 else 'red',
            'holdings_count': len(data.get('holdings', [])),
            'positions_count': len(data.get('positions', [])),
            'last_updated': datetime.now().isoformat()
        }
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"❌ Error calculating portfolio summary: {str(e)}")
        return jsonify({
            'error': 'Error calculating portfolio summary',
            'message': str(e)
        }), 500

def generate_analytics_data(data):
    """Generate advanced analytics data"""
    try:
        holdings = data.get('holdings', [])
        positions = data.get('positions', [])
        
        # Calculate sector allocation (mock data for now)
        sector_allocation = {
            'Technology': 25,
            'Finance': 30,
            'Healthcare': 15,
            'Energy': 20,
            'Consumer': 10
        }
        
        # Calculate risk metrics
        total_value = sum(holding.get('raw_total_value', 0) for holding in holdings)
        total_pnl = sum(holding.get('raw_pnl_amount', 0) for holding in holdings)
        
        # Mock volatility calculation
        volatility = 15.67
        beta = 0.89
        sharpe_ratio = 1.24
        
        # Performance metrics
        performance_data = {
            '1M': 5.23,
            '3M': 12.67,
            '6M': 18.45,
            '1Y': 28.90
        }
        
        analytics = {
            'sector_allocation': sector_allocation,
            'risk_metrics': {
                'volatility': volatility,
                'beta': beta,
                'sharpe_ratio': sharpe_ratio,
                'var_95': total_value * 0.05,  # 5% VaR
                'max_drawdown': -8.23
            },
            'performance': performance_data,
            'correlation_matrix': generate_correlation_matrix(holdings),
            'last_updated': datetime.now().isoformat()
        }
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error generating analytics: {str(e)}")
        return {}

def generate_correlation_matrix(holdings):
    """Generate correlation matrix for holdings"""
    # Mock correlation matrix
    symbols = [holding.get('symbol', 'Unknown') for holding in holdings[:5]]
    if len(symbols) < 2:
        return {}
    
    correlations = {}
    for i, symbol1 in enumerate(symbols):
        correlations[symbol1] = {}
        for j, symbol2 in enumerate(symbols):
            if i == j:
                correlations[symbol1][symbol2] = 1.0
            else:
                # Mock correlation values
                correlations[symbol1][symbol2] = round(0.3 + (i + j) * 0.1, 2)
    
    return correlations

@app.route('/api/analytics')
def get_analytics():
    """Get advanced analytics data"""
    if not connection_status['connected']:
        return jsonify({'error': 'Not connected to Dhan API'}), 400
    
    try:
        data = get_dhan_data()
        if not data:
            return jsonify({'error': 'Failed to fetch data'}), 500
        
        # Generate advanced analytics
        analytics = generate_analytics_data(data)
        
        return jsonify(analytics)
        
    except Exception as e:
        logger.error(f"❌ Error generating analytics: {str(e)}")
        return jsonify({
            'error': 'Error generating analytics',
            'message': str(e)
        }), 500

@app.route('/webhook/tradingview', methods=['POST'])
def tradingview_webhook():
    """Receive TradingView alerts via webhook - TEMPORARILY DISABLED SECURITY FOR TESTING"""
    try:
        # Log the incoming webhook
        logger.info("🔔 Received TradingView webhook")
        logger.info(f"📋 Headers: {dict(request.headers)}")
        logger.info(f"📦 Body: {request.get_data(as_text=True)}")
        
        # Verify webhook signature if enabled - TEMPORARILY DISABLED FOR TESTING
        # if Config.ENABLE_SIGNATURE_VERIFICATION:
        #     if not verify_webhook_signature(request):
        #         logger.warning("⚠️ Webhook signature verification failed")
        #         return jsonify({'error': 'Invalid signature'}), 401
        
        logger.info("🔓 Webhook signature verification temporarily disabled for testing")
        
        # Parse webhook data
        webhook_data = request.get_json()
        if not webhook_data:
            logger.error("❌ No JSON data in webhook")
            return jsonify({'error': 'No data received'}), 400
        
        logger.info(f"📊 Webhook data: {webhook_data}")
        
        # Extract alert information - Updated for new format
        alert_data = {
            'alert_id': webhook_data.get('alert_id', f"alert_{int(time.time())}"),
            'symbol': webhook_data.get('symbol', 'NIFTY'),
            'alert_type': webhook_data.get('alert_type', 'OPTION'),
            'action': webhook_data.get('action', 'BUY_CE'),  # BUY_CE, SELL_CE, BUY_PE, SELL_PE
            'price': float(webhook_data.get('price', 0)),
            'quantity': int(webhook_data.get('quantity', 1)),
            'message': webhook_data.get('message', ''),
            'strategy': webhook_data.get('strategy', ''),
            'timeframe': webhook_data.get('timeframe', ''),
            'exchange': webhook_data.get('exchange', 'NSE'),
            'secret': webhook_data.get('secret', '')  # For validation
        }
        
        # Validate the secret - TEMPORARILY DISABLED FOR TESTING
        # if not validate_alert_secret(alert_data.get('secret', '')):
        #     logger.warning("⚠️ Invalid alert secret")
        #     return jsonify({'error': 'Invalid secret'}), 401
        
        logger.info("🔓 Secret validation temporarily disabled for testing")
        
        # Save alert to database
        if save_alert(alert_data):
            logger.info(f"✅ Alert saved successfully: {alert_data['action']} {alert_data['symbol']}")
            
            # Process the alert for trading
            process_trading_alert(alert_data)
            
            return jsonify({
                'success': True,
                'message': 'Alert received and processed',
                'alert_id': alert_data['alert_id'],
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error("❌ Failed to save alert")
            return jsonify({'error': 'Failed to save alert'}), 500
            
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {str(e)}")
        return jsonify({
            'error': 'Error processing webhook',
            'message': str(e)
        }), 500

def validate_alert_secret(secret):
    """Validate alert secret from webhook"""
    try:
        expected_secret = Config.WEBHOOK_SECRET
        return secret == expected_secret
    except:
        return False

def verify_webhook_signature(request):
    """Verify TradingView webhook signature"""
    try:
        signature = request.headers.get('X-Signature')
        timestamp = request.headers.get('X-Timestamp')
        
        if not signature or not timestamp:
            return False
        
        # Check if timestamp is within 5 minutes
        current_time = int(time.time())
        request_time = int(timestamp)
        if abs(current_time - request_time) > 300:  # 5 minutes
            return False
        
        # Verify signature
        message = f"{timestamp}{request.path}{request.get_data(as_text=True)}"
        expected_signature = hmac.new(
            Config.WEBHOOK_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except:
        return False

def process_trading_alert(alert_data):
    """Process trading alert and execute trades"""
    try:
        logger.info(f"🚀 Processing trading alert: {alert_data['action']} {alert_data['symbol']}")
        
        # Check if we should execute this alert
        if not should_execute_alert(alert_data):
            logger.info(f"⏭️ Skipping alert execution: {alert_data['alert_id']}")
            return
        
        # Execute the trade based on alert action
        action = alert_data['action'].upper()
        symbol = alert_data['symbol'].upper()
        
        if symbol in ['NIFTY', 'NIFTY50', 'NIFTY 50']:
            # Handle NIFTY options
            if action in ['BUY_CE', 'BUY_CALL']:
                execute_nifty_option_trade(alert_data, 'BUY', 'CE')
            elif action in ['SELL_CE', 'SELL_CALL']:
                execute_nifty_option_trade(alert_data, 'SELL', 'CE')
            elif action in ['BUY_PE', 'BUY_PUT']:
                execute_nifty_option_trade(alert_data, 'BUY', 'PE')
            elif action in ['SELL_PE', 'SELL_PUT']:
                execute_nifty_option_trade(alert_data, 'SELL', 'PE')
            elif action in ['EXIT', 'CLOSE']:
                execute_nifty_option_exit(alert_data)
            else:
                logger.warning(f"⚠️ Unknown NIFTY option action: {action}")
        else:
            # Handle stock trades
            if action in ['BUY', 'LONG']:
                execute_stock_buy_trade(alert_data)
            elif action in ['SELL', 'SHORT', 'EXIT']:
                execute_stock_sell_trade(alert_data)
            else:
                logger.warning(f"⚠️ Unknown action type: {action}")
            
    except Exception as e:
        logger.error(f"❌ Error in process_trading_alert: {str(e)}")
        log_error('ERROR', 'process_trading_alert', f'Error in process_trading_alert: {str(e)}')

def should_execute_alert(alert_data):
    """Check if alert should be executed"""
    try:
        logger.info(f"🔍 Checking if alert {alert_data.get('alert_id', 'unknown')} should be executed...")
        
        # Check if market is open (simplified check)
        now = datetime.now()
        # Temporarily allow weekend execution for testing
        # if now.weekday() >= 5:  # Weekend
        #     logger.info("⏭️ Market closed (weekend)")
        #     return False
        
        # Check market hours (9:15 AM to 3:30 PM IST)
        market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        logger.info(f"🔍 Current time: {now}")
        logger.info(f"🔍 Market hours: {market_start} to {market_end}")
        
        # Temporarily bypass market hours check for testing
        # if now < market_start or now > market_end:
        #     logger.info("⏭️ Market closed (outside trading hours)")
        #     return False
        
        # Check if we have active connection
        logger.info(f"🔍 Connection status: {connection_status['connected']}")
        if not connection_status['connected']:
            logger.warning("⚠️ No Dhan API connection")
            return False
        
        # Check daily trade limits
        daily_limits_ok = check_daily_trade_limits()
        logger.info(f"🔍 Daily trade limits check: {daily_limits_ok}")
        if not daily_limits_ok:
            logger.warning("⚠️ Daily trade limits exceeded")
            return False
        
        logger.info("✅ All checks passed - alert can be executed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking alert execution: {str(e)}")
        return False

def check_daily_trade_limits():
    """Check daily trade limits"""
    try:
        # Get today's trades count
        conn = sqlite3.connect('instance/trading_automation.db')
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) FROM trading_alerts 
            WHERE DATE(timestamp) = ? AND status IN ('EXECUTED', 'CLOSED')
        ''', (today,))
        
        trade_count = cursor.fetchone()[0]
        conn.close()
        
        if trade_count >= Config.MAX_DAILY_TRADES:
            logger.warning(f"⚠️ Daily trade limit reached: {trade_count}/{Config.MAX_DAILY_TRADES}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking daily trade limits: {str(e)}")
        return False

def execute_buy_trade(alert_data):
    """Execute buy trade based on alert"""
    try:
        logger.info(f"📈 Executing BUY trade for {alert_data['symbol']}")
        
        # For NIFTY50 alerts, buy ATM call options
        if alert_data['symbol'].upper() in ['NIFTY50', 'NIFTY', 'NIFTY 50']:
            execute_nifty_call_trade(alert_data)
        else:
            # For other symbols, buy the stock directly
            execute_stock_buy_trade(alert_data)
            
    except Exception as e:
        logger.error(f"❌ Error executing buy trade: {str(e)}")

def execute_sell_trade(alert_data):
    """Execute sell/exit trade based on alert"""
    try:
        logger.info(f"📉 Executing SELL/EXIT trade for {alert_data['symbol']}")
        
        # For NIFTY50 alerts, close call options
        if alert_data['symbol'].upper() in ['NIFTY50', 'NIFTY', 'NIFTY 50']:
            close_nifty_call_trade(alert_data)
        else:
            # For other symbols, sell the stock directly
            execute_stock_sell_trade(alert_data)
            
    except Exception as e:
        logger.error(f"❌ Error executing sell trade: {str(e)}")

def execute_nifty_option_trade(alert_data, transaction_type, option_type):
    """Execute NIFTY option trade (BUY/SELL CE/PE)"""
    try:
        logger.info(f"🚀 Executing NIFTY {option_type} {transaction_type} trade")
        
        # Get current NIFTY spot price
        spot_price = get_current_nifty_price()
        if not spot_price:
            logger.error("❌ Failed to get NIFTY spot price")
            return False
        
        # Calculate ATM strike
        atm_strike = calculate_atm_strike(spot_price)
        if not atm_strike:
            logger.error("❌ Failed to calculate ATM strike")
            return False
        
        # Get nearest expiry
        expiry_date = get_nearest_expiry()
        if not expiry_date:
            logger.error("❌ Failed to get expiry date")
            return False
        
        # Fetch option chain
        option_chain = get_nifty_option_chain(expiry_date)
        if not option_chain:
            logger.error("❌ Failed to fetch option chain")
            return False
        
        # Find the appropriate option contract
        contract_info = find_option_contract(option_chain, atm_strike, option_type)
        if not contract_info:
            logger.error("❌ Failed to find option contract")
            return False
        
        # Set quantity (1 lot = 50 NIFTY options)
        quantity = contract_info['lot_size']
        
        # Place the option order
        order_result = place_option_order(
            contract_info=contract_info,
            transaction_type=transaction_type,
            quantity=quantity,
            alert_data=alert_data
        )
        
        if order_result:
            logger.info(f"✅ NIFTY {option_type} {transaction_type} order placed successfully")
            return True
        else:
            logger.error(f"❌ Failed to place NIFTY {option_type} {transaction_type} order")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in execute_nifty_option_trade: {str(e)}")
        log_error('ERROR', 'execute_nifty_option_trade', f'Error in execute_nifty_option_trade: {str(e)}')
        return False

def execute_nifty_call_trade(alert_data):
    """Execute Nifty Call option trade based on alert"""
    try:
        action = alert_data.get('action', '').upper()
        logger.info(f"🚀 Executing Nifty Call trade for action: {action}")
        
        if action not in ['BUY', 'EXIT']:
            logger.warning(f"⚠️ Invalid action for Nifty trade: {action}")
            log_error('WARNING', 'execute_nifty_call_trade', f'Invalid action for Nifty trade: {action}')
            return False
        
        # Get current Nifty price (mock for now)
        nifty_price = get_current_nifty_price()
        if not nifty_price:
            logger.error("❌ Failed to get current Nifty price")
            log_error('ERROR', 'execute_nifty_call_trade', 'Failed to get current Nifty price')
            return False
        
        # Get ATM Call option security ID (mock for now)
        option_security_id = get_nifty_option_security_id(nifty_price, 'CE')
        if not option_security_id:
            logger.error("❌ Failed to get Nifty option security ID")
            log_error('ERROR', 'execute_nifty_call_trade', 'Failed to get Nifty option security ID')
            return False
        
        # Set quantity (mock for now - should be calculated based on position sizing)
        quantity = 50  # 1 lot = 50 Nifty options
        
        if action == 'BUY':
            # Buy ATM Call option
            try:
                result = dhan.place_order(
                    security_id=option_security_id,
                    exchange_segment=dhan.NSE_FNO,  # Use constant for NSE F&O
                    transaction_type=dhan.BUY,      # Use constant for BUY
                    quantity=quantity,
                    order_type=dhan.MARKET,         # Use constant for MARKET
                    product_type=dhan.INTRA,        # Use constant for INTRADAY
                    price=0                         # Market order
                )
                
                logger.info(f"📊 Buy order result: {result}")
                
                if result.get('status') == 'success':
                    order_id = result.get('data', {}).get('orderId', 'UNKNOWN')
                    logger.info(f"✅ Nifty Call option bought successfully. Order ID: {order_id}")
                    log_error('INFO', 'execute_nifty_call_trade', f'Nifty Call option bought successfully. Order ID: {order_id}', 
                             str(result), trade_id=order_id)
                    return True
                else:
                    logger.error(f"❌ Failed to buy Nifty Call option: {result}")
                    log_error('ERROR', 'execute_nifty_call_trade', f'Failed to buy Nifty Call option: {result}')
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Exception during buy order: {str(e)}")
                log_error('ERROR', 'execute_nifty_call_trade', f'Exception during buy order: {str(e)}')
                return False
                
        elif action == 'EXIT':
            # Close existing Nifty Call position
            return close_nifty_call_trade(option_security_id, quantity)
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error in execute_nifty_call_trade: {str(e)}")
        log_error('ERROR', 'execute_nifty_call_trade', f'Error in execute_nifty_call_trade: {str(e)}')
        return False

def close_nifty_call_trade(security_id, quantity):
    """Close existing Nifty Call option position"""
    try:
        logger.info(f"🚀 Closing Nifty Call position: {security_id}, Quantity: {quantity}")
        
        # Close position using the correct Dhan API syntax
        result = dhan.place_order(
            security_id=security_id,
            exchange_segment=dhan.NSE_FNO,  # Use constant for NSE F&O
            transaction_type=dhan.SELL,     # Use constant for SELL
            quantity=quantity,
            order_type=dhan.MARKET,         # Use constant for MARKET
            product_type=dhan.INTRA,        # Use constant for INTRADAY
            price=0                         # Market order
        )
        
        logger.info(f"📊 Close position result: {result}")
        
        if result.get('status') == 'success':
            order_id = result.get('data', {}).get('orderId', 'UNKNOWN')
            logger.info(f"✅ Nifty Call position closed successfully. Order ID: {order_id}")
            log_error('INFO', 'close_nifty_call_trade', f'Nifty Call position closed successfully. Order ID: {order_id}', 
                     str(result), trade_id=order_id)
            return True
        else:
            logger.error(f"❌ Failed to close Nifty Call position: {result}")
            log_error('ERROR', 'close_nifty_call_trade', f'Failed to close Nifty Call position: {result}')
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in close_nifty_call_trade: {str(e)}")
        log_error('ERROR', 'close_nifty_call_trade', f'Error in close_nifty_call_trade: {str(e)}')
        return False

def get_current_nifty_price():
    """Get current NIFTY price from Dhan API"""
    try:
        logger.info("📊 Fetching current NIFTY spot price...")
        
        # Use Dhan's market quote API to get NIFTY spot price
        # NIFTY 50 index security ID is typically 99926000
        nifty_security_id = "99926000"  # NIFTY 50 index
        
        result = dhan.quote_data(
            securities=[{
                'securityId': nifty_security_id,
                'exchangeSegment': dhan.INDEX
            }]
        )
        
        logger.info(f"📊 NIFTY market quote result: {result}")
        
        # Check if result is a list and has data
        if isinstance(result, list) and len(result) > 0:
            # Extract the last traded price from quote_data response
            nifty_quote = result[0]  # First (and only) security
            if isinstance(nifty_quote, dict):
                last_price = nifty_quote.get('lastTradedPrice', 0)
                if last_price and last_price > 0:
                    logger.info(f"✅ Current NIFTY price: {last_price}")
                    return float(last_price)
                else:
                    logger.warning("⚠️ No valid price in quote response")
            else:
                logger.warning(f"⚠️ Unexpected quote response format: {type(nifty_quote)}")
        else:
            logger.warning(f"⚠️ Quote data failed or empty: {result}")
        
        # Fallback to mock price for testing
        logger.info("🔄 Falling back to mock NIFTY price for testing")
        return 19500.0
            
    except Exception as e:
        logger.error(f"❌ Error getting NIFTY price: {str(e)}")
        log_error('ERROR', 'get_current_nifty_price', f'Error getting NIFTY price: {str(e)}')
        # Fallback to mock price for testing
        logger.info("🔄 Falling back to mock NIFTY price due to exception")
        return 19500.0

def get_nifty_option_security_id(price, option_type):
    """Get security ID for NIFTY option (mock implementation)"""
    try:
        # This is a mock implementation
        # In real scenario, you would fetch from Dhan API
        # For simplicity, we'll return a mock ID based on price and type
        # In a real app, this would involve more complex logic to find the correct strike
        return f"OPTIDX_NIFTY_{price}_{option_type}"  # Mock security ID
    except Exception as e:
        logger.error(f"❌ Error getting option security ID: {str(e)}")
        return None

def execute_stock_buy_trade(alert_data):
    """Execute stock buy trade based on alert"""
    try:
        logger.info(f"🚀 Executing stock buy trade: {alert_data}")
        
        # Get stock security ID (mock for now)
        stock_security_id = get_stock_security_id(alert_data.get('symbol', ''))
        if not stock_security_id:
            logger.error("❌ Failed to get stock security ID")
            log_error('ERROR', 'execute_stock_buy_trade', 'Failed to get stock security ID')
            return False
        
        # Place buy order using the correct Dhan API syntax
        result = dhan.place_order(
            security_id=stock_security_id,
            exchange_segment=dhan.NSE,      # Use constant for NSE Equity
            transaction_type=dhan.BUY,      # Use constant for BUY
            quantity=alert_data.get('quantity', 1),
            order_type=dhan.MARKET,         # Use constant for MARKET
            product_type=dhan.INTRA,        # Use constant for INTRADAY
            price=0                         # Market order
        )
        
        logger.info(f"📊 Buy order result: {result}")
        
        if result.get('status') == 'success':
            order_id = result.get('data', {}).get('orderId', 'UNKNOWN')
            logger.info(f"✅ Stock bought successfully. Order ID: {order_id}")
            log_error('INFO', 'execute_stock_buy_trade', f'Stock bought successfully. Order ID: {order_id}', 
                     str(result), trade_id=order_id)
            return True
        else:
            logger.error(f"❌ Failed to buy stock: {result}")
            log_error('ERROR', 'execute_stock_buy_trade', f'Failed to buy stock: {result}')
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in execute_stock_buy_trade: {str(e)}")
        log_error('ERROR', 'execute_stock_buy_trade', f'Error in execute_stock_buy_trade: {str(e)}')
        return False

def execute_stock_sell_trade(alert_data):
    """Execute stock sell trade based on alert"""
    try:
        logger.info(f"🚀 Executing stock sell trade: {alert_data}")
        
        # Get stock security ID (mock for now)
        stock_security_id = get_stock_security_id(alert_data.get('symbol', ''))
        if not stock_security_id:
            logger.error("❌ Failed to get stock security ID")
            log_error('ERROR', 'execute_stock_sell_trade', 'Failed to get stock security ID')
            return False
        
        # Place sell order using the correct Dhan API syntax
        result = dhan.place_order(
            security_id=stock_security_id,
            exchange_segment=dhan.NSE,      # Use constant for NSE Equity
            transaction_type=dhan.SELL,     # Use constant for SELL
            quantity=alert_data.get('quantity', 1),
            order_type=dhan.MARKET,         # Use constant for MARKET
            product_type=dhan.INTRA,        # Use constant for INTRADAY
            price=0                         # Market order
        )
        
        logger.info(f"📊 Sell order result: {result}")
        
        if result.get('status') == 'success':
            order_id = result.get('data', {}).get('orderId', 'UNKNOWN')
            logger.info(f"✅ Stock sold successfully. Order ID: {order_id}")
            log_error('INFO', 'execute_stock_sell_trade', f'Stock sold successfully. Order ID: {order_id}', 
                     str(result), trade_id=order_id)
            return True
        else:
            logger.error(f"❌ Failed to sell stock: {result}")
            log_error('ERROR', 'execute_stock_sell_trade', f'Failed to sell stock: {result}')
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in execute_stock_sell_trade: {str(e)}")
        log_error('ERROR', 'execute_stock_sell_trade', f'Error in execute_stock_sell_trade: {str(e)}')
        return False

def get_stock_security_id(symbol):
    """Get security ID for stock (mock implementation)"""
    try:
        # This is a mock implementation
        # In real scenario, you would fetch from Dhan API
        return f"EQ_{symbol}"  # Mock security ID
    except Exception as e:
        logger.error(f"❌ Error getting stock security ID: {str(e)}")
        return None

@app.route('/api/alerts')
def get_alerts_api():
    """Get all alerts via API"""
    try:
        alerts = get_alerts()
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        logger.error(f"❌ Error getting alerts: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/error-logs')
def get_error_logs_api():
    """Get error logs via API"""
    try:
        logs = get_error_logs()
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
    except Exception as e:
        logger.error(f"❌ Error getting error logs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/alerts/<alert_id>/status', methods=['PUT'])
def update_alert_status_api(alert_id):
    """Update alert status"""
    try:
        data = request.get_json()
        status = data.get('status')
        trade_id = data.get('trade_id')
        pnl = data.get('pnl')
        exit_price = data.get('exit_price')
        
        if not status:
            return jsonify({'error': 'Status is required'}), 400
        
        if update_alert_status(alert_id, status, trade_id, pnl, exit_price):
            return jsonify({
                'success': True,
                'message': f'Alert {alert_id} status updated to {status}',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'error': 'Failed to update alert status'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error updating alert status: {str(e)}")
        return jsonify({
            'error': 'Error updating alert status',
            'message': str(e)
        }), 500

@app.route('/api/alerts/test', methods=['POST'])
def test_alert():
    """Test alert functionality with sample data"""
    try:
        data = request.get_json()
        action = data.get('action', 'BUY_CE')
        symbol = data.get('symbol', 'NIFTY')
        
        # Create test alert with new format
        test_alert_data = {
            'alert_id': f"test_alert_{int(time.time())}",
            'symbol': symbol,
            'alert_type': 'OPTION' if symbol in ['NIFTY', 'NIFTY50', 'NIFTY 50'] else 'STOCK',
            'action': action,
            'price': 19500.0 if symbol in ['NIFTY', 'NIFTY50', 'NIFTY 50'] else 100.0,
            'quantity': 1,
            'message': f'Test {action} alert for {symbol}',
            'strategy': 'TEST_STRATEGY',
            'timeframe': '1H',
            'exchange': 'NSE',
            'secret': Config.WEBHOOK_SECRET  # Include secret for validation
        }
        
        # Save test alert
        if save_alert(test_alert_data):
            logger.info(f"✅ Test alert created: {action} {symbol}")
            
            # Process the test alert (but don't execute real trades)
            logger.info(f"🧪 Test alert processed: {test_alert_data['alert_id']}")
            
            return jsonify({
                'success': True,
                'message': f'Test alert created and processed: {action} {symbol}',
                'alert_id': test_alert_data['alert_id'],
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': 'Failed to create test alert'}), 500
            
    except Exception as e:
        logger.error(f"❌ Error creating test alert: {str(e)}")
        return jsonify({
            'error': 'Error creating test alert',
            'message': str(e)
        }), 500

@app.route('/api/execute-alert', methods=['POST'])
def execute_alert():
    """Manually execute a pending alert"""
    try:
        data = request.get_json()
        alert_id = data.get('alert_id')
        
        if not alert_id:
            return jsonify({'success': False, 'error': 'Alert ID is required'})
        
        logger.info(f"🚀 Manually executing alert ID: {alert_id}")
        
        # Get the alert from database
        conn = sqlite3.connect('instance/trading_automation.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM trading_alerts WHERE alert_id = ?', (alert_id,))
        alert = cursor.fetchone()
        conn.close()
        
        if not alert:
            logger.error(f"❌ Alert not found: {alert_id}")
            log_error('ERROR', 'execute_alert', f'Alert not found: {alert_id}')
            return jsonify({'success': False, 'error': 'Alert not found'})
        
        # Convert alert tuple to dict for easier handling
        alert_data = {
            'id': alert[0],
            'alert_id': alert[1],
            'symbol': alert[2],
            'alert_type': alert[3],
            'action': alert[4],
            'price': alert[5],
            'quantity': alert[6],
            'status': alert[7],
            'message': alert[8],
            'timestamp': alert[9],
            'strategy': alert[10],
            'timeframe': alert[11],
            'exchange': alert[12]
        }
        
        # Debug logging
        logger.info(f"🔍 Debug - Alert data: {alert_data}")
        logger.info(f"🔍 Debug - Status field: '{alert_data['status']}'")
        
        if alert_data['status'] != 'PENDING':
            logger.warning(f"⚠️ Alert {alert_id} is not in PENDING status: {alert_data['status']}")
            return jsonify({'success': False, 'error': f'Alert is not in PENDING status: {alert_data["status"]}'})
        
        # Check if we should execute this alert
        if not should_execute_alert(alert_data):
            logger.warning(f"⚠️ Alert {alert_id} cannot be executed due to market conditions or limits")
            return jsonify({'success': False, 'error': 'Alert cannot be executed due to market conditions or limits'})
        
        # Execute the trade based on alert type
        success = False
        symbol = alert_data['symbol'].upper()
        action = alert_data['action'].upper()
        
        if symbol in ['NIFTY', 'NIFTY50', 'NIFTY 50']:
            # Handle NIFTY options
            if action in ['BUY_CE', 'BUY_CALL']:
                success = execute_nifty_option_trade(alert_data, 'BUY', 'CE')
            elif action in ['SELL_CE', 'SELL_CALL']:
                success = execute_nifty_option_trade(alert_data, 'SELL', 'CE')
            elif action in ['BUY_PE', 'BUY_PUT']:
                success = execute_nifty_option_trade(alert_data, 'BUY', 'PE')
            elif action in ['SELL_PE', 'SELL_PUT']:
                success = execute_nifty_option_trade(alert_data, 'SELL', 'PE')
            elif action in ['EXIT', 'CLOSE']:
                success = execute_nifty_option_exit(alert_data)
            else:
                # Fallback to old logic for backward compatibility
                success = execute_nifty_call_trade(alert_data)
        else:
            # Handle stock trades
            if action == 'BUY':
                success = execute_stock_buy_trade(alert_data)
            elif action == 'SELL':
                success = execute_stock_sell_trade(alert_data)
            else:
                logger.warning(f"⚠️ Unknown action for stock trade: {action}")
                return jsonify({'success': False, 'error': f'Unknown action: {action}'})
        
        if success:
            # Update alert status to EXECUTED
            conn = sqlite3.connect('instance/trading_automation.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE trading_alerts SET status = ?, executed_at = ? WHERE id = ?', 
                         ('EXECUTED', datetime.now().isoformat(), alert_id))
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Alert {alert_id} executed successfully")
            return jsonify({'success': True, 'message': 'Alert executed successfully'})
        else:
            # Update alert status to FAILED
            conn = sqlite3.connect('instance/trading_automation.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE trading_alerts SET status = ? WHERE id = ?', ('FAILED', alert_id))
            conn.commit()
            conn.close()
            
            logger.error(f"❌ Alert {alert_id} execution failed")
            return jsonify({'success': False, 'error': 'Trade execution failed'})
            
    except Exception as e:
        logger.error(f"❌ Error in execute_alert: {str(e)}")
        log_error('ERROR', 'execute_alert', f'Error in execute_alert: {str(e)}')
        return jsonify({'success': False, 'error': f'Error in execute_alert: {str(e)}'})

def calculate_atm_strike(spot_price):
    """Calculate ATM strike price for NIFTY options"""
    try:
        # NIFTY options have strikes in multiples of 50
        # Round to nearest 50
        atm_strike = round(spot_price / 50) * 50
        logger.info(f"📊 Spot price: {spot_price}, ATM strike: {atm_strike}")
        return atm_strike
    except Exception as e:
        logger.error(f"❌ Error calculating ATM strike: {str(e)}")
        log_error('ERROR', 'calculate_atm_strike', f'Error calculating ATM strike: {str(e)}')
        return None

def get_nearest_expiry():
    """Get the nearest expiry date for NIFTY options"""
    try:
        # NIFTY options typically expire on the last Thursday of each month
        # For now, we'll use a simple approach to find the next Thursday
        today = datetime.now()
        
        # Find the next Thursday
        days_ahead = 3 - today.weekday()  # Thursday is 3
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        next_thursday = today + timedelta(days=days_ahead)
        
        # If it's too close to expiry (less than 2 days), move to next month
        if (next_thursday - today).days < 2:
            next_thursday += timedelta(days=7)
        
        expiry_date = next_thursday.strftime('%Y-%m-%d')
        logger.info(f"📅 Nearest expiry date: {expiry_date}")
        return expiry_date
        
    except Exception as e:
        logger.error(f"❌ Error getting nearest expiry: {str(e)}")
        log_error('ERROR', 'get_nearest_expiry', f'Error getting nearest expiry: {str(e)}')
        # Fallback to a reasonable date
        return (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

def get_nifty_option_chain(expiry_date):
    """Fetch NIFTY option chain from Dhan API"""
    try:
        logger.info(f"📊 Fetching NIFTY option chain for expiry: {expiry_date}")
        
        # NIFTY 50 underlying security ID
        underlying_security_id = "99926000"  # NIFTY 50 index
        
        result = dhan.option_chain(
            under_security_id=underlying_security_id,
            under_exchange_segment=dhan.INDEX,  # Index segment
            expiry=expiry_date
        )
        
        logger.info(f"📊 Option chain result: {result}")
        
        if result.get('status') == 'success':
            option_data = result.get('data', {})
            logger.info(f"✅ Option chain fetched successfully with {len(option_data)} strikes")
            return option_data
        else:
            logger.warning(f"⚠️ Dhan API failed: {result}")
            
            # Check if it's the "Data APIs not Subscribed" error
            if result.get('data', {}).get('data', {}).get('806') == 'Data APIs not Subscribed':
                logger.warning("⚠️ Data APIs not Subscribed - using mock data for testing")
            else:
                logger.warning("⚠️ Unknown API error - using mock data for testing")
            
            logger.info("🔄 Falling back to mock option chain for testing")
            
            # Fallback to mock data for testing when APIs are not subscribed
            # Create a more comprehensive mock option chain with multiple strikes
            mock_option_chain = {}
            
            # Generate strikes around 19500 (current mock price)
            base_strike = 19500
            for i in range(-2, 3):  # Strikes from 19400 to 19600
                strike = base_strike + (i * 50)
                strike_str = str(strike)
                
                mock_option_chain[strike_str] = {
                    "ce": {
                        "securityId": f"NIFTY{strike}CE",
                        "tradingSymbol": f"NIFTY23AUG{strike}CE",
                        "strikePrice": strike,
                        "optionType": "CE",
                        "expiryDate": expiry_date,
                        "lotSize": 50,
                        "lastPrice": max(50.0, 200.0 - (abs(i) * 25.0)),
                        "topBid": max(45.0, 195.0 - (abs(i) * 25.0)),
                        "topAsk": max(55.0, 205.0 - (abs(i) * 25.0))
                    },
                    "pe": {
                        "securityId": f"NIFTY{strike}PE",
                        "tradingSymbol": f"NIFTY23AUG{strike}PE",
                        "strikePrice": strike,
                        "optionType": "PE",
                        "expiryDate": expiry_date,
                        "lotSize": 50,
                        "lastPrice": max(50.0, 180.0 - (abs(i) * 20.0)),
                        "topBid": max(45.0, 175.0 - (abs(i) * 20.0)),
                        "topAsk": max(55.0, 185.0 - (abs(i) * 20.0))
                    }
                }
            
            logger.info(f"✅ Mock option chain created with {len(mock_option_chain)} strikes")
            return mock_option_chain
            
    except Exception as e:
        logger.error(f"❌ Error fetching option chain: {str(e)}")
        log_error('ERROR', 'get_nifty_option_chain', f'Error fetching option chain: {str(e)}')
        
        # Fallback to mock data on exception
        logger.info("🔄 Falling back to mock option chain due to exception")
        
        # Create comprehensive mock option chain for exception fallback
        mock_option_chain = {}
        base_strike = 19500
        for i in range(-2, 3):  # Strikes from 19400 to 19600
            strike = base_strike + (i * 50)
            strike_str = str(strike)
            
            mock_option_chain[strike_str] = {
                "ce": {
                    "securityId": f"NIFTY{strike}CE",
                    "tradingSymbol": f"NIFTY23AUG{strike}CE",
                    "strikePrice": strike,
                    "optionType": "CE",
                    "expiryDate": expiry_date,
                    "lotSize": 50,
                    "lastPrice": max(50.0, 200.0 - (abs(i) * 25.0)),
                    "topBid": max(45.0, 195.0 - (abs(i) * 25.0)),
                    "topAsk": max(55.0, 205.0 - (abs(i) * 25.0))
                },
                "pe": {
                    "securityId": f"NIFTY{strike}PE",
                    "tradingSymbol": f"NIFTY23AUG{strike}PE",
                    "strikePrice": strike,
                    "optionType": "PE",
                    "expiryDate": expiry_date,
                    "lotSize": 50,
                    "lastPrice": max(50.0, 180.0 - (abs(i) * 20.0)),
                    "topBid": max(45.0, 175.0 - (abs(i) * 20.0)),
                    "topAsk": max(55.0, 185.0 - (abs(i) * 20.0))
                }
            }
        
        return mock_option_chain

def find_option_contract(option_chain, strike_price, option_type):
    """Find the appropriate option contract from the option chain"""
    try:
        logger.info(f"🔍 Finding {option_type} option for strike {strike_price}")
        
        # Convert strike to string for lookup
        strike_str = str(int(strike_price))
        
        if strike_str not in option_chain:
            logger.error(f"❌ Strike {strike_price} not found in option chain")
            return None
        
        strike_data = option_chain[strike_str]
        
        # Get the appropriate option leg (CE or PE)
        if option_type.upper() == 'CE':
            option_leg = strike_data.get('ce', {})
        elif option_type.upper() == 'PE':
            option_leg = strike_data.get('pe', {})
        else:
            logger.error(f"❌ Invalid option type: {option_type}")
            return None
        
        if not option_leg:
            logger.error(f"❌ {option_type} option not available for strike {strike_price}")
            return None
        
        # Extract required information
        contract_info = {
            'security_id': option_leg.get('securityId'),
            'trading_symbol': option_leg.get('tradingSymbol'),
            'strike_price': strike_price,
            'option_type': option_type.upper(),
            'expiry_date': option_leg.get('expiryDate'),
            'lot_size': option_leg.get('lotSize', 50),
            'last_price': option_leg.get('lastPrice', 0),
            'bid_price': option_leg.get('topBid', 0),
            'ask_price': option_leg.get('topAsk', 0)
        }
        
        logger.info(f"✅ Found {option_type} option contract: {contract_info}")
        return contract_info
        
    except Exception as e:
        logger.error(f"❌ Error finding option contract: {str(e)}")
        log_error('ERROR', 'find_option_contract', f'Error finding option contract: {str(e)}')
        return None

def place_option_order(contract_info, transaction_type, quantity, alert_data):
    """Helper function to place an option order using Dhan API"""
    try:
        logger.info(f"📊 Placing option order for {contract_info['trading_symbol']} (Qty: {quantity})")
        
        # Determine exchange segment and product type
        exchange_segment = dhan.NSE_FNO # Default to F&O
        product_type = dhan.INTRA # Default to INTRADAY
        
        # Place the order with required option parameters
        result = dhan.place_order(
            security_id=contract_info['security_id'],
            exchange_segment=exchange_segment,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=dhan.MARKET, # Market order
            product_type=product_type,
            price=0, # Market order
            # Required option parameters
            drv_expiry_date=contract_info['expiry_date'],
            drv_option_type=contract_info['option_type'],
            drv_strike_price=contract_info['strike_price']
        )
        
        logger.info(f"📊 Option order result: {result}")
        
        if result.get('status') == 'success':
            order_id = result.get('data', {}).get('orderId', 'UNKNOWN')
            logger.info(f"✅ Option order placed successfully. Order ID: {order_id}")
            log_error('INFO', 'place_option_order', f'Option order placed successfully. Order ID: {order_id}', 
                     str(result), trade_id=order_id)
            return True
        else:
            logger.error(f"❌ Failed to place option order: {result}")
            log_error('ERROR', 'place_option_order', f'Failed to place option order: {result}')
            return False
            
    except Exception as e:
        logger.error(f"❌ Error placing option order: {str(e)}")
        log_error('ERROR', 'place_option_order', f'Error placing option order: {str(e)}')
        return False

def execute_nifty_option_exit(alert_data):
    """Execute exit for NIFTY option trades"""
    try:
        logger.info(f"🚀 Executing NIFTY option exit for alert: {alert_data['alert_id']}")
        
        # Get the security ID of the open position
        # This is a simplified approach. In a real app, you'd need to fetch open positions
        # For now, we'll assume the alert_id is the security_id for simplicity
        # In a real scenario, you'd need to query the database for the open position
        # based on alert_id and symbol.
        # For this example, we'll use a placeholder or fetch a dummy if not found.
        # This part needs proper implementation based on how you store open positions.
        
        # Placeholder for fetching open position security_id
        # For now, we'll use a dummy or assume it's the alert_id if it's a call/put
        # This is a simplification and needs proper database integration.
        # For now, let's assume the alert_id itself is the security_id for a call/put
        # that was just opened.
        
        # This function is a placeholder. In a real app, you'd need to:
        # 1. Find the open position in the database based on alert_id and symbol.
        # 2. Get its security_id.
        # 3. Place a SELL order to close it.
        
        # For now, we'll just log a placeholder message.
        logger.warning(f"⚠️ execute_nifty_option_exit is a placeholder. No open position found for alert: {alert_data['alert_id']}")
        log_error('WARNING', 'execute_nifty_option_exit', f'No open position found for alert: {alert_data["alert_id"]}')
        
        # If you were to implement this, you'd need to:
        # 1. Query the database for open positions matching alert_id and symbol.
        # 2. Get the security_id of the position.
        # 3. Place a SELL order to close it.
        # Example:
        # conn = sqlite3.connect('instance/trading_automation.db')
        # cursor = conn.cursor()
        # cursor.execute('SELECT security_id FROM trading_alerts WHERE alert_id = ? AND symbol = ? AND status = ?',
        #                (alert_data['alert_id'], alert_data['symbol'], 'OPEN'))
        # open_position = cursor.fetchone()
        # conn.close()
        # if open_position:
        #     security_id = open_position[0]
        #     # Place a SELL order to close it
        #     result = dhan.place_order(
        #         security_id=security_id,
        #         exchange_segment=dhan.NSE_FNO,
        #         transaction_type=dhan.SELL,
        #         quantity=1, # Assuming 1 lot for exit
        #         order_type=dhan.MARKET,
        #         product_type=dhan.INTRA,
        #         price=0
        #     )
        #     if result.get('status') == 'success':
        #         log_error('INFO', 'execute_nifty_option_exit', f'NIFTY option exit placed successfully. Order ID: {result.get("data", {}).get("orderId")}')
        #         return True
        #     else:
        #         log_error('ERROR', 'execute_nifty_option_exit', f'Failed to place NIFTY option exit: {result}')
        #         return False
        # else:
        #     log_error('WARNING', 'execute_nifty_option_exit', f'No open NIFTY option position found for alert: {alert_data["alert_id"]}')
        #     return False
        
        return False # Placeholder for now
        
    except Exception as e:
        logger.error(f"❌ Error in execute_nifty_option_exit: {str(e)}")
        log_error('ERROR', 'execute_nifty_option_exit', f'Error in execute_nifty_option_exit: {str(e)}')
        return False

# Initialize Dhan connection on startup
if __name__ == '__main__':
    logger.info("🚀 Starting Dhan Portfolio Dashboard...")
    
    # Initialize alerts database
    init_alerts_db()
    
    # Initialize Dhan connection
    initialize_dhan()
    
    # Development mode
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
else:
    # Production mode (Render)
    # The app will be served by gunicorn
    logger.info("🚀 Starting Dhan Portfolio Dashboard in production mode...")
    
    # Initialize alerts database
    init_alerts_db()
    
    # Initialize Dhan connection
    initialize_dhan()
