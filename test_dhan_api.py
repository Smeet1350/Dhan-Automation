#!/usr/bin/env python3
"""
Test script to discover Dhan API methods and parameters
"""
from dhanhq import dhanhq

def test_dhan_api():
    """Test Dhan API methods"""
    try:
        # Create a test instance
        d = dhanhq('test', 'test')
        
        print("🔍 Available Dhan API methods:")
        print("=" * 50)
        
        # Get all methods
        methods = [attr for attr in dir(d) if not attr.startswith('_') and callable(getattr(d, attr))]
        
        for method in sorted(methods):
            print(f"📋 {method}")
            
        print("\n🔍 Methods containing 'market':")
        market_methods = [attr for attr in dir(d) if 'market' in attr.lower() and callable(getattr(d, attr))]
        for method in market_methods:
            print(f"📊 {method}")
            
        print("\n🔍 Methods containing 'option':")
        option_methods = [attr for attr in dir(d) if 'option' in attr.lower() and callable(getattr(d, attr))]
        for method in option_methods:
            print(f"📈 {method}")
            
        print("\n🔍 Methods containing 'quote':")
        quote_methods = [attr for attr in dir(d) if 'quote' in attr.lower() and callable(getattr(d, attr))]
        for method in quote_methods:
            print(f"💹 {method}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_dhan_api()
