#!/usr/bin/env python3
"""
Test script for TradingView webhook with NIFTY options trading
"""

import requests
import json
import time

# Configuration
WEBHOOK_URL = "http://localhost:5000/webhook/tradingview"
SECRET = "dhan-trading-webhook-secret-Yt0xGC0TtsOMmI4NTN67CEmBqIoB0W57"

def test_nifty_option_alert(action, symbol="NIFTY"):
    """Test NIFTY option alert"""
    alert_data = {
        "alert_id": f"nifty_{action.lower()}_{int(time.time())}",
        "symbol": symbol,
        "action": action,
        "price": 19500.0,
        "quantity": 1,
        "message": f"{action} signal for {symbol}",
        "strategy": "BREAKOUT",
        "timeframe": "1H",
        "exchange": "NSE",
        "secret": SECRET
    }
    
    print(f"🚀 Testing {action} alert for {symbol}...")
    
    try:
        response = requests.post(WEBHOOK_URL, json=alert_data, headers={
            'Content-Type': 'application/json'
        })
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {response.json()}")
        
        if response.status_code == 200:
            print(f"✅ {action} alert sent successfully!")
        else:
            print(f"❌ {action} alert failed!")
            
    except Exception as e:
        print(f"❌ Error sending {action} alert: {str(e)}")
    
    print("-" * 50)

def test_stock_alert(action, symbol="RELIANCE"):
    """Test stock alert"""
    alert_data = {
        "alert_id": f"stock_{action.lower()}_{int(time.time())}",
        "symbol": symbol,
        "action": action,
        "price": 2500.0,
        "quantity": 10,
        "message": f"{action} signal for {symbol}",
        "strategy": "MOMENTUM",
        "timeframe": "15M",
        "exchange": "NSE",
        "secret": SECRET
    }
    
    print(f"🚀 Testing {action} alert for {symbol}...")
    
    try:
        response = requests.post(WEBHOOK_URL, json=alert_data, headers={
            'Content-Type': 'application/json'
        })
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {response.json()}")
        
        if response.status_code == 200:
            print(f"✅ {action} alert sent successfully!")
        else:
            print(f"❌ {action} alert failed!")
            
    except Exception as e:
        print(f"❌ Error sending {action} alert: {str(e)}")
    
    print("-" * 50)

def main():
    """Main test function"""
    print("🧪 Testing TradingView Webhook with NIFTY Options Trading")
    print("=" * 60)
    
    # Test NIFTY option alerts
    print("\n📈 Testing NIFTY Option Alerts:")
    test_nifty_option_alert("BUY_CE", "NIFTY")
    time.sleep(2)
    
    test_nifty_option_alert("SELL_CE", "NIFTY")
    time.sleep(2)
    
    test_nifty_option_alert("BUY_PE", "NIFTY")
    time.sleep(2)
    
    test_nifty_option_alert("SELL_PE", "NIFTY")
    time.sleep(2)
    
    test_nifty_option_alert("EXIT", "NIFTY")
    time.sleep(2)
    
    # Test stock alerts
    print("\n📊 Testing Stock Alerts:")
    test_stock_alert("BUY", "RELIANCE")
    time.sleep(2)
    
    test_stock_alert("SELL", "TATASTEEL")
    time.sleep(2)
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
