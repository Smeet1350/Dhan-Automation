# Dhan Portfolio Dashboard

A **secure, modern portfolio monitoring** Flask application to connect to Dhan API and display portfolio data with **real-time processing** and **position management capabilities**.

## ✨ Features

- 🔒 **Secure API Connection** - HMAC signature verification and timestamp validation
- ⚡ **Ultra-Fast Performance** - Optimized data processing and caching
- 📊 **Portfolio Monitoring** - Real-time portfolio value and P&L tracking
- 🎨 **Modern UI/UX** - Beautiful, responsive dashboard with gradient design
- 📈 **Position Management** - Square off individual positions or all at once
- 🔄 **Auto-Refresh** - Automatic data updates every 2 minutes
- 📱 **Mobile Responsive** - Works perfectly on all devices
- 🛡️ **Security Features** - Request signature verification, rate limiting
- 🚨 **Emergency Exit** - Quick square-off all positions for risk management

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Test Connection

First, test if your Dhan API credentials work:

```bash
python test_connection.py
```

This will test all API endpoints and show you if the connection is working.

### 3. Run the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

## 🔧 Configuration

Your Dhan API credentials are configured in `config.py`:

- `DHAN_CLIENT_ID`: Your Dhan client ID
- `DHAN_ACCESS_TOKEN`: Your Dhan access token
- `API_SECRET`: Secret key for request signature verification
- `ENABLE_SIGNATURE_VERIFICATION`: Enable/disable security verification

## 🛡️ Security Features

### Request Signature Verification
- HMAC-SHA256 signature validation
- Timestamp-based request expiration (5 minutes)
- Prevents replay attacks and unauthorized access

### Rate Limiting
- Built-in request throttling
- Prevents API abuse and ensures stability

### Secure Logging
- UTF-8 encoded log files
- No sensitive data in logs
- Structured error handling

## 📊 Portfolio Management

The system provides comprehensive portfolio monitoring and position management:

### Portfolio Summary
- Total investment value
- Current market value
- Overall P&L (amount and percentage)
- Number of holdings and active positions

### Holdings Analysis
- Individual stock P&L calculations
- Average cost vs current price
- Total value calculations
- Color-coded profit/loss indicators

### Position Management
- **Individual Square-Off**: Square off specific positions at market price
- **Bulk Square-Off**: Square off all positions at once
- **Emergency Exit**: Quick risk management tool for all positions

### Trade History
- Formatted timestamps
- Transaction type badges
- Total value calculations
- Brokerage and tax details

## 🚀 Deploy on Render (Recommended for TradingView Webhooks)

### Why Render?
- **Public URL**: TradingView webhooks can reach your application
- **Always Online**: 24/7 availability for trading alerts
- **Free Tier**: Available for personal use
- **Easy Setup**: One-click deployment

### Quick Deploy Steps:

1. **Fork this repository** to your GitHub account
2. **Connect to Render**:
   - Go to [render.com](https://render.com)
   - Sign up with GitHub
   - Click "New Web Service"
3. **Select your forked repository**
4. **Configure the service**:
   - **Name**: `dhan-automation-dashboard`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`

### Environment Variables (Required):

| Variable | Description | Example |
|----------|-------------|---------|
| `DHAN_CLIENT_ID` | Your Dhan client ID | `1107860004` |
| `DHAN_ACCESS_TOKEN` | Your Dhan access token | `your_token_here` |
| `WEBHOOK_SECRET` | Secret for TradingView webhooks | `your_webhook_secret` |
| `API_SECRET` | Secret for API requests | `your_api_secret` |
| `FLASK_ENV` | Set to `production` | `production` |

### After Deployment:
1. Copy your Render URL (e.g., `https://your-app.onrender.com`)
2. Use this URL in TradingView webhook settings
3. Set the webhook secret in both Render and TradingView

## 🎯 API Endpoints

- `GET /` - Main portfolio dashboard
- `GET /api/connection` - Check connection status
- `GET /api/data` - Get processed Dhan data
- `GET /api/refresh` - Refresh connection
- `GET /api/health` - Health check
- `GET /api/portfolio-summary` - Get portfolio summary
- `POST /api/square-off` - Square off individual position
- `POST /api/square-off-all` - Square off all positions

## 📈 Performance Metrics

- **API Response Time**: < 2 seconds average
- **Data Processing**: Real-time formatting
- **Auto-refresh**: Every 2 minutes
- **Connection Monitoring**: Every 30 seconds

## 🗂️ Files Structure

```
├── app.py              # Main Flask application with portfolio management
├── config.py           # Configuration with Dhan credentials
├── data_processor.py   # Data processing and formatting
├── test_connection.py  # Connection test script
├── requirements.txt    # Python dependencies
├── templates/
│   └── dashboard.html # Modern portfolio dashboard template
└── logs/
    └── app.log        # Application logs (UTF-8)
```

## 🔍 Data Processing Pipeline

1. **Raw API Fetch** - Get data from Dhan API
2. **Data Processing** - Clean and format data
3. **Calculations** - P&L, totals, percentages
4. **Frontend Display** - Beautiful tables and cards

## 🚨 Position Management

### Square Off Individual Position
- Select specific position to close
- Market order execution
- Immediate position closure
- Confirmation dialog for safety

### Square Off All Positions
- Bulk position closure
- Market order execution
- Confirmation required
- Batch processing with status updates

### Emergency Exit
- Double confirmation required
- Immediate closure of all positions
- Risk management tool
- Use with caution

## 🎨 Modern UI/UX Features

- **Gradient Background**: Beautiful purple-blue gradient design
- **Card-based Layout**: Clean, organized information display
- **Responsive Design**: Works on all screen sizes
- **Interactive Elements**: Hover effects and smooth transitions
- **Color Coding**: Green/red for profit/loss indicators
- **Loading States**: Smooth loading animations
- **Error Handling**: User-friendly error messages

## 🔄 Auto-Refresh Features

- **Connection Status**: Updates every 30 seconds
- **Portfolio Data**: Updates every 2 minutes
- **Manual Refresh**: Available via dashboard buttons
- **Performance Monitoring**: Real-time response time tracking

## 🔒 Security Best Practices

- **Environment Variables**: Use for sensitive data
- **Request Validation**: All API calls validated
- **Error Handling**: No sensitive data in error messages
- **Logging**: Secure logging without credentials
- **Rate Limiting**: Prevents API abuse

## 📱 Mobile Optimization

- **Responsive Design**: Works on all screen sizes
- **Touch-Friendly**: Optimized for mobile devices
- **Fast Loading**: Optimized for mobile networks
- **Offline Handling**: Graceful error handling

## 🚫 Removed Features

The following trading features have been removed for safety:
- Manual order placement
- Order modification
- Order cancellation
- Basket order placement
- Real-time trading

## 🎯 Focus Areas

The application now focuses on:
- Portfolio monitoring and analysis
- Position management and square-off
- Risk management tools
- Performance tracking
- Data visualization

---

**🎨 Modern Portfolio Dashboard** - Built for monitoring and managing your investments with a focus on safety and ease of use. 