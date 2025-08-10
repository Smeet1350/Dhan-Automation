import os

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'flask-secret-key-q9Z7fhYEdo2Ah0njIXYQUJq0KlSD4Zmv')
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # Dhan API Configuration - Direct credentials
    DHAN_CLIENT_ID = os.environ.get('DHAN_CLIENT_ID', "1107860004")
    DHAN_ACCESS_TOKEN = os.environ.get('DHAN_ACCESS_TOKEN', "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU2ODM2NDA4LCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNzg2MDAwNCJ9.3cuzgiY0Qm2Id8wpMW0m90_ZxJ0TJRTV5fZ0tpAwWo3S1Mv5HbpcDNwXxXVepnOUHMRDck_AbArIoVOmlA68Dg")
    
    # Trading Configuration
    DEFAULT_QUANTITY = 1
    MAX_QUANTITY = 100
    

    # Webhook Security
    WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'dhan-trading-webhook-secret-Yt0xGC0TtsOMmI4NTN67CEmBqIoB0W57')
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///trading_automation.db')
    
    # Risk Management
    MAX_DAILY_TRADES = 10
    MAX_DAILY_LOSS = 5000.0
    STOP_LOSS_PERCENTAGE = 2.0
    TAKE_PROFIT_PERCENTAGE = 3.0
    
    # Connection Status
    DHAN_CONNECTION_STATUS = False
    LAST_CONNECTION_CHECK = None
    
    # Server Configuration
    PORT = 5000
    
    # Security Configuration
    API_SECRET = os.environ.get('API_SECRET', 'dhan-api-secret-key-2024')
    ENABLE_SIGNATURE_VERIFICATION = os.environ.get('ENABLE_SIGNATURE_VERIFICATION', 'false').lower() == 'true' 