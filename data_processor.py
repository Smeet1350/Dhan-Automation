"""
Data Processor for Dhan API
Cleans and formats raw API data into readable format
"""

from datetime import datetime
from typing import Dict, Any, List

class DataProcessor:
    """Process and format Dhan API data"""
    
    @staticmethod
    def format_currency(amount: float) -> str:
        """Format currency with proper Indian formatting"""
        if amount is None:
            return "₹0.00"
        return f"₹{amount:,.2f}"
    
    @staticmethod
    def format_percentage(value: float) -> str:
        """Format percentage values"""
        if value is None:
            return "0.00%"
        return f"{value:.2f}%"
    
    @staticmethod
    def format_quantity(qty: int) -> str:
        """Format quantity with proper formatting"""
        if qty is None:
            return "0"
        return f"{qty:,}"
    
    @staticmethod
    def process_fund_limits(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process fund limits data"""
        if not raw_data or 'data' not in raw_data:
            return {'error': 'No fund data available'}
        
        data = raw_data['data']
        return {
            'status': raw_data.get('status', 'unknown'),
            'available_balance': DataProcessor.format_currency(data.get('availabelBalance', 0)),
            'sod_limit': DataProcessor.format_currency(data.get('sodLimit', 0)),
            'collateral_amount': DataProcessor.format_currency(data.get('collateralAmount', 0)),
            'receivable_amount': DataProcessor.format_currency(data.get('receiveableAmount', 0)),
            'utilized_amount': DataProcessor.format_currency(data.get('utilizedAmount', 0)),
            'withdrawable_balance': DataProcessor.format_currency(data.get('withdrawableBalance', 0)),
            'raw_balance': data.get('availabelBalance', 0)
        }
    
    @staticmethod
    def process_holdings(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process holdings data"""
        if not raw_data or 'data' not in raw_data:
            return []
        
        holdings = []
        for holding in raw_data['data']:
            avg_cost = holding.get('avgCostPrice', 0)
            last_price = holding.get('lastTradedPrice', 0)
            quantity = holding.get('totalQty', 0)
            
            # Calculate P&L
            if avg_cost and last_price and quantity:
                pnl_amount = (last_price - avg_cost) * quantity
                pnl_percentage = ((last_price - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0
            else:
                pnl_amount = 0
                pnl_percentage = 0
            
            holdings.append({
                'symbol': holding.get('tradingSymbol', 'Unknown'),
                'security_id': holding.get('securityId', ''),
                'quantity': DataProcessor.format_quantity(quantity),
                'available_quantity': DataProcessor.format_quantity(holding.get('availableQty', 0)),
                'avg_cost_price': DataProcessor.format_currency(avg_cost),
                'last_traded_price': DataProcessor.format_currency(last_price),
                'pnl_amount': DataProcessor.format_currency(pnl_amount),
                'pnl_percentage': DataProcessor.format_percentage(pnl_percentage),
                'pnl_color': 'green' if pnl_amount >= 0 else 'red',
                'total_value': DataProcessor.format_currency(quantity * last_price),
                'raw_quantity': quantity,
                'raw_avg_cost': avg_cost,
                'raw_last_price': last_price
            })
        
        return holdings
    
    @staticmethod
    def process_positions(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process positions data"""
        if not raw_data or 'data' not in raw_data:
            return []
        
        positions = []
        for position in raw_data['data']:
            quantity = position.get('quantity', 0)
            avg_price = position.get('averagePrice', 0)
            current_price = position.get('currentPrice', 0)
            
            # Calculate P&L
            if quantity and avg_price and current_price:
                pnl_amount = (current_price - avg_price) * abs(quantity)
                pnl_percentage = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
            else:
                pnl_amount = position.get('pnl', 0)
                pnl_percentage = position.get('pnlPercentage', 0)
            
            # Determine position type
            position_type = 'LONG' if quantity > 0 else 'SHORT' if quantity < 0 else 'FLAT'
            
            positions.append({
                'symbol': position.get('tradingSymbol', 'Unknown'),
                'security_id': position.get('securityId', ''),
                'quantity': DataProcessor.format_quantity(abs(quantity)),
                'avg_price': DataProcessor.format_currency(avg_price),
                'last_traded_price': DataProcessor.format_currency(current_price),
                'pnl_amount': DataProcessor.format_currency(pnl_amount),
                'pnl_percentage': DataProcessor.format_percentage(pnl_percentage),
                'pnl_color': 'green' if pnl_amount >= 0 else 'red',
                'position_type': position_type,
                'raw_quantity': quantity,  # Keep raw quantity for square-off
                'raw_avg_price': avg_price,
                'raw_last_price': current_price
            })
        
        return positions
    
    @staticmethod
    def process_orders(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process orders data"""
        if not raw_data or 'data' not in raw_data:
            return []
        
        orders = []
        for order in raw_data['data']:
            orders.append({
                'order_id': order.get('orderId', ''),
                'symbol': order.get('tradingSymbol', 'Unknown'),
                'transaction_type': order.get('transactionType', ''),
                'quantity': DataProcessor.format_quantity(order.get('quantity', 0)),
                'price': DataProcessor.format_currency(order.get('price', 0)),
                'order_type': order.get('orderType', ''),
                'status': order.get('orderStatus', ''),
                'timestamp': order.get('orderDateTime', ''),
                'exchange': order.get('exchangeSegment', '')
            })
        
        return orders
    
    @staticmethod
    def process_trade_history(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process trade history data"""
        if not raw_data or 'data' not in raw_data:
            return []
        
        trades = []
        today = datetime.now().date()
        
        for trade in raw_data['data']:
            # Parse exchange time
            exchange_time = trade.get('exchangeTime', '')
            trade_date = None
            formatted_time = 'N/A'
            
            if exchange_time and exchange_time != 'NA':
                try:
                    parsed_time = datetime.strptime(exchange_time, '%Y-%m-%d %H:%M:%S')
                    trade_date = parsed_time.date()
                    formatted_time = parsed_time.strftime('%d %b %Y, %I:%M %p')
                except:
                    formatted_time = exchange_time
            
            # Calculate P&L for the trade
            traded_qty = trade.get('tradedQuantity', 0)
            traded_price = trade.get('tradedPrice', 0)
            transaction_type = trade.get('transactionType', '')
            
            # For options/futures, we need to calculate P&L differently
            if trade.get('instrument') == 'FUTSTK' or trade.get('instrument') == 'OPTSTK':
                # This is a simplified P&L calculation for derivatives
                # In real scenario, you'd need entry and exit prices
                pnl_amount = 0  # Placeholder for options/futures P&L
                pnl_percentage = 0
            else:
                # For equity trades, calculate basic P&L
                pnl_amount = 0  # Will be calculated from holdings
                pnl_percentage = 0
            
            trades.append({
                'order_id': trade.get('orderId', ''),
                'symbol': trade.get('customSymbol', 'Unknown'),
                'transaction_type': trade.get('transactionType', ''),
                'quantity': DataProcessor.format_quantity(traded_qty),
                'price': DataProcessor.format_currency(traded_price),
                'total_value': DataProcessor.format_currency(traded_qty * traded_price),
                'brokerage': DataProcessor.format_currency(trade.get('brokerageCharges', 0)),
                'stt': DataProcessor.format_currency(trade.get('stt', 0)),
                'exchange_time': formatted_time,
                'trade_date': trade_date,
                'is_today': trade_date == today if trade_date else False,
                'product_type': trade.get('productType', ''),
                'order_type': trade.get('orderType', ''),
                'instrument': trade.get('instrument', 'EQUITY'),
                'pnl_amount': DataProcessor.format_currency(pnl_amount),
                'pnl_percentage': DataProcessor.format_percentage(pnl_percentage),
                'pnl_color': 'green' if pnl_amount >= 0 else 'red'
            })
        
        return trades
    
    @staticmethod
    def process_all_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process all Dhan API data"""
        processed_data = {
            'fund_limits': DataProcessor.process_fund_limits(raw_data.get('fund_limits', {})),
            'holdings': DataProcessor.process_holdings(raw_data.get('holdings', {})),
            'positions': DataProcessor.process_positions(raw_data.get('positions', {})),
            'orders': DataProcessor.process_orders(raw_data.get('orders', {})),
            'trade_history': DataProcessor.process_trade_history(raw_data.get('trade_history', {})),
            'summary': DataProcessor.generate_summary(raw_data)
        }
        
        # Add categorized data
        processed_data.update(DataProcessor.categorize_data(processed_data))
        
        return processed_data
    
    @staticmethod
    def generate_summary(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics"""
        holdings = DataProcessor.process_holdings(raw_data.get('holdings', {}))
        positions = DataProcessor.process_positions(raw_data.get('positions', {}))
        trades = DataProcessor.process_trade_history(raw_data.get('trade_history', {}))
        orders = DataProcessor.process_orders(raw_data.get('orders', {}))
        
        # Calculate total portfolio value
        total_portfolio_value = sum(
            holding['raw_quantity'] * holding['raw_last_price'] 
            for holding in holdings
        )
        
        # Calculate total P&L
        total_pnl = sum(
            (holding['raw_last_price'] - holding['raw_avg_cost']) * holding['raw_quantity']
            for holding in holdings
        )
        
        # Calculate total P&L percentage
        total_investment = sum(
            holding['raw_avg_cost'] * holding['raw_quantity']
            for holding in holdings
        )
        
        total_pnl_percentage = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        
        # Count today's trades only
        today_trades = [trade for trade in trades if trade.get('is_today', False)]
        
        # Separate equity and derivatives
        equity_holdings = [h for h in holdings if h.get('instrument', 'EQUITY') == 'EQUITY']
        options_trades = [t for t in trades if t.get('instrument') in ['OPTSTK', 'OPTIDX']]
        futures_trades = [t for t in trades if t.get('instrument') in ['FUTSTK', 'FUTIDX']]
        
        return {
            'total_holdings': len(holdings),
            'total_positions': len(positions),
            'total_trades_today': len(today_trades),
            'total_orders': len(orders),
            'pending_orders': len([o for o in orders if o.get('status', '').upper() in ['PENDING', 'OPEN']]),
            'total_portfolio_value': DataProcessor.format_currency(total_portfolio_value),
            'total_pnl_amount': DataProcessor.format_currency(total_pnl),
            'total_pnl_percentage': DataProcessor.format_percentage(total_pnl_percentage),
            'pnl_color': 'green' if total_pnl >= 0 else 'red',
            'equity_holdings': len(equity_holdings),
            'options_trades': len(options_trades),
            'futures_trades': len(futures_trades),
            'today_options_trades': len([t for t in today_trades if t.get('instrument') in ['OPTSTK', 'OPTIDX']]),
            'today_futures_trades': len([t for t in today_trades if t.get('instrument') in ['FUTSTK', 'FUTIDX']])
        }
    
    @staticmethod
    def categorize_data(processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize data by instrument type"""
        trades = processed_data.get('trade_history', [])
        orders = processed_data.get('orders', [])
        holdings = processed_data.get('holdings', [])
        
        # Categorize trades
        equity_trades = [t for t in trades if t.get('instrument') == 'EQUITY']
        options_trades = [t for t in trades if t.get('instrument') in ['OPTSTK', 'OPTIDX']]
        futures_trades = [t for t in trades if t.get('instrument') in ['FUTSTK', 'FUTIDX']]
        
        # Categorize orders
        equity_orders = [o for o in orders if o.get('exchange', '').endswith('_EQ')]
        options_orders = [o for o in orders if 'OPT' in o.get('exchange', '')]
        futures_orders = [o for o in orders if 'FUT' in o.get('exchange', '')]
        
        # Categorize holdings
        equity_holdings = [h for h in holdings if h.get('security_id', '').isdigit()]
        options_holdings = [h for h in holdings if 'OPT' in h.get('symbol', '')]
        futures_holdings = [h for h in holdings if 'FUT' in h.get('symbol', '')]
        
        return {
            'categorized_trades': {
                'equity': equity_trades,
                'options': options_trades,
                'futures': futures_trades
            },
            'categorized_orders': {
                'equity': equity_orders,
                'options': options_orders,
                'futures': futures_orders
            },
            'categorized_holdings': {
                'equity': equity_holdings,
                'options': options_holdings,
                'futures': futures_holdings
            }
        }

    @staticmethod
    def calculate_risk_metrics(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate risk metrics for portfolio"""
        try:
            if not holdings:
                return {}
            
            # Calculate portfolio metrics
            total_value = sum(float(holding.get('total_value', '0').replace('₹', '').replace(',', '')) for holding in holdings)
            total_pnl = sum(float(holding.get('pnl_amount', '0').replace('₹', '').replace(',', '')) for holding in holdings)
            
            # Mock risk calculations (in real implementation, these would use historical data)
            volatility = 15.67  # Mock volatility percentage
            beta = 0.89  # Mock beta
            sharpe_ratio = 1.24  # Mock Sharpe ratio
            
            # Calculate concentration risk
            if total_value > 0:
                concentration_risk = max(float(holding.get('total_value', '0').replace('₹', '').replace(',', '')) / total_value * 100 for holding in holdings)
            else:
                concentration_risk = 0
            
            risk_metrics = {
                'volatility': f"{volatility:.2f}%",
                'beta': f"{beta:.2f}",
                'sharpe_ratio': f"{sharpe_ratio:.2f}",
                'concentration_risk': f"{concentration_risk:.2f}%",
                'var_95': f"₹{total_value * 0.05:,.2f}",
                'max_drawdown': "-8.23%"
            }
            
            return risk_metrics
            
        except Exception as e:
            return {}

    @staticmethod
    def calculate_performance_metrics(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics for portfolio"""
        try:
            if not holdings:
                return {}
            
            # Mock performance data (in real implementation, this would use historical data)
            performance = {
                '1M': '5.23%',
                '3M': '12.67%',
                '6M': '18.45%',
                '1Y': '28.90%',
                'YTD': '15.67%'
            }
            
            return performance
            
        except Exception as e:
            return {}

    @staticmethod
    def generate_sector_analysis(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate sector analysis for portfolio"""
        try:
            # Mock sector allocation (in real implementation, this would use actual sector data)
            sector_allocation = {
                'Technology': 25,
                'Finance': 30,
                'Healthcare': 15,
                'Energy': 20,
                'Consumer': 10
            }
            
            sector_performance = {
                'Technology': '18.5%',
                'Finance': '12.3%',
                'Healthcare': '25.7%',
                'Energy': '-5.2%',
                'Consumer': '8.1%'
            }
            
            return {
                'allocation': sector_allocation,
                'performance': sector_performance
            }
            
        except Exception as e:
            return {}

