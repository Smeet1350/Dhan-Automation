#!/usr/bin/env python3
"""
Simple Dhan API Connection Test
Using the exact pattern from the working example
"""

from dhanhq import dhanhq
from config import Config
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_dhan_connection():
    """Test Dhan API connection using the working example pattern"""
    
    print("🚀 Starting Dhan API Connection Test")
    print("=" * 50)
    
    # Your real credentials from config
    client_id = Config.DHAN_CLIENT_ID
    access_token = Config.DHAN_ACCESS_TOKEN
    
    print(f"📋 Client ID: {client_id}")
    print(f"🔑 Access Token: {'*' * 20}...{access_token[-10:]}")
    print()
    
    try:
        # Initialize SDK - exactly as in your working example
        print("🔄 Initializing Dhan SDK...")
        dhan = dhanhq(client_id, access_token)
        print("✅ Dhan SDK initialized successfully!")
        print()
        
        # Test 1: Fund Limits
        print("1. 🪙 Testing Fund Limits...")
        fund_limits = dhan.get_fund_limits()
        print(f"✅ Fund Limits Response: {fund_limits}")
        print()
        
        # Test 2: Order List
        print("2. 📋 Testing Order List...")
        orders = dhan.get_order_list()
        print(f"✅ Order List Response: {orders}")
        print()
        
        # Test 3: Positions
        print("3. 📊 Testing Positions...")
        positions = dhan.get_positions()
        print(f"✅ Positions Response: {positions}")
        print()
        
        # Test 4: Holdings
        print("4. 📦 Testing Holdings...")
        holdings = dhan.get_holdings()
        print(f"✅ Holdings Response: {holdings}")
        print()
        
        # Test 5: Trade History
        print("5. 📜 Testing Trade History...")
        from datetime import datetime, timedelta
        to_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        trade_history = dhan.get_trade_history(from_date, to_date)
        print(f"✅ Trade History Response: {trade_history}")
        print()
        
        print("🎉 ALL TESTS PASSED! Dhan API connection is working perfectly!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        print("=" * 50)
        return False

if __name__ == "__main__":
    success = test_dhan_connection()
    if success:
        print("✅ Connection test successful! You can now run the Flask app.")
    else:
        print("❌ Connection test failed! Please check your credentials.")
