# 📊 TradingView Webhook Setup Guide

This guide will help you set up TradingView alerts to automatically trigger trades through your Dhan automation dashboard.

## 🎯 Prerequisites

- ✅ Dhan automation dashboard deployed on Render
- ✅ TradingView Pro account (required for webhooks)
- ✅ Dhan trading account with API access

## 🔗 Step 1: Get Your Webhook URL

After deploying on Render, your webhook URL will be:
```
https://your-app-name.onrender.com/webhook/tradingview
```

**Replace `your-app-name` with your actual Render app name.**

## ⚙️ Step 2: Configure TradingView Alert

### 2.1 Create a New Alert
1. Open TradingView and go to your chart
2. Click the **"Alert"** button (bell icon)
3. Set your **alert conditions** (price, indicator, etc.)
4. Click **"Create"**

### 2.2 Configure Webhook Settings
1. In the alert settings, scroll down to **"Webhook URL"**
2. Paste your webhook URL: `https://your-app-name.onrender.com/webhook/tradingview`
3. Set **"Webhook Headers"**:
   ```
   Content-Type: application/json
   X-Signature: your_webhook_secret_here
   X-Timestamp: {{time}}
   ```

### 2.3 Set Alert Message
Use this JSON format for your alert message:

```json
{
  "alert_id": "{{strategy.order.id}}",
  "symbol": "{{ticker}}",
  "action": "BUY_CE",
  "price": {{close}},
  "quantity": 1,
  "strategy": "{{strategy.name}}",
  "timeframe": "{{timeframe}}",
  "exchange": "NSE",
  "secret": "your_webhook_secret_here"
}
```

## 🎯 Step 3: Supported Alert Actions

### NIFTY Options Trading:
```json
// Buy NIFTY Call
{
  "action": "BUY_CE",
  "symbol": "NIFTY"
}

// Sell NIFTY Put
{
  "action": "SELL_PE", 
  "symbol": "NIFTY"
}

// Exit NIFTY Position
{
  "action": "EXIT",
  "symbol": "NIFTY"
}
```

### Stock Trading:
```json
// Buy Stock
{
  "action": "BUY",
  "symbol": "RELIANCE"
}

// Sell Stock
{
  "action": "SELL",
  "symbol": "RELIANCE"
}
```

## 🔒 Step 4: Security Setup

### 4.1 Set Webhook Secret
1. In your Render dashboard, set the `WEBHOOK_SECRET` environment variable
2. Use the **same secret** in your TradingView alert message
3. **Never share this secret** - it verifies that alerts come from TradingView

### 4.2 Example Secret
```
WEBHOOK_SECRET=my_super_secret_key_12345
```

Then in TradingView:
```json
{
  "secret": "my_super_secret_key_12345"
}
```

## 📱 Step 5: Test Your Setup

### 5.1 Create Test Alert
1. Create a simple price alert (e.g., when NIFTY crosses 19,500)
2. Set the webhook URL and message
3. Trigger the alert manually or wait for it to trigger

### 5.2 Check Dashboard
1. Go to your deployed dashboard
2. Check the **Alerts** section for new alerts
3. Check the **Error Logs** section for any issues

### 5.3 Monitor Logs
Your dashboard will show:
- ✅ **Successful alerts**: New trading alerts received
- ❌ **Failed alerts**: Webhook errors or validation failures
- 📊 **Trade execution**: Orders placed and results

## 🚨 Troubleshooting

### Common Issues:

#### 1. Webhook Not Receiving Alerts
- ✅ Check webhook URL is correct
- ✅ Verify TradingView Pro subscription
- ✅ Check Render app is running
- ✅ Test with a simple alert first

#### 2. "Invalid Secret" Errors
- ✅ Ensure `WEBHOOK_SECRET` matches in both places
- ✅ Check for extra spaces or characters
- ✅ Restart Render app after changing secrets

#### 3. "Alert Validation Failed"
- ✅ Check JSON format is correct
- ✅ Verify all required fields are present
- ✅ Ensure `secret` field matches

#### 4. Render App Not Starting
- ✅ Check build logs in Render dashboard
- ✅ Verify environment variables are set
- ✅ Check `requirements.txt` has all dependencies

## 📋 Alert Message Templates

### Template 1: Simple NIFTY Call
```json
{
  "alert_id": "nifty_call_{{time}}",
  "symbol": "NIFTY",
  "action": "BUY_CE",
  "price": {{close}},
  "quantity": 1,
  "strategy": "NIFTY_STRATEGY",
  "timeframe": "{{timeframe}}",
  "exchange": "NSE",
  "secret": "your_secret_here"
}
```

### Template 2: Stock Breakout
```json
{
  "alert_id": "{{ticker}}_breakout_{{time}}",
  "symbol": "{{ticker}}",
  "action": "BUY",
  "price": {{close}},
  "quantity": 100,
  "strategy": "BREAKOUT_STRATEGY",
  "timeframe": "{{timeframe}}",
  "exchange": "NSE",
  "secret": "your_secret_here"
}
```

### Template 3: Exit Signal
```json
{
  "alert_id": "exit_{{ticker}}_{{time}}",
  "symbol": "{{ticker}}",
  "action": "EXIT",
  "price": {{close}},
  "quantity": 1,
  "strategy": "EXIT_STRATEGY",
  "timeframe": "{{timeframe}}",
  "exchange": "NSE",
  "secret": "your_secret_here"
}
```

## 🔄 Step 6: Automation Workflow

### Complete Trading Flow:
1. **TradingView Alert** → Triggers when conditions are met
2. **Webhook** → Sends alert to your dashboard
3. **Validation** → Dashboard verifies secret and data
4. **Trade Execution** → Dashboard places order via Dhan API
5. **Confirmation** → Order result logged in dashboard
6. **Monitoring** → Track position and P&L in real-time

## 📊 Monitoring & Management

### Dashboard Features:
- **Real-time Alerts**: See all incoming TradingView alerts
- **Trade Status**: Track order execution and results
- **Error Logs**: Debug any webhook or trading issues
- **Portfolio View**: Monitor overall positions and P&L

### Best Practices:
- 🧪 **Test First**: Use paper trading or small amounts initially
- 📝 **Log Everything**: Keep detailed records of all alerts and trades
- 🔍 **Monitor Regularly**: Check dashboard for errors or issues
- 🔒 **Secure Secrets**: Never expose webhook secrets publicly

## 🎉 Success!

Once everything is working:
- ✅ TradingView alerts will automatically trigger trades
- ✅ Your dashboard will show real-time trading activity
- ✅ You can monitor and manage positions remotely
- ✅ Automated trading is now live! 🚀

---

**Need Help?** Check the error logs in your dashboard or create an issue in the GitHub repository.
