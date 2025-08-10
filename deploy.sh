#!/bin/bash

echo "🚀 Dhan Automation Dashboard - Render Deployment Script"
echo "========================================================"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

# Check if repository is a git repo
if [ ! -d ".git" ]; then
    echo "❌ This directory is not a git repository."
    echo "Please run: git init && git add . && git commit -m 'Initial commit'"
    exit 1
fi

echo "✅ Git repository found"

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found. Please create it first."
    exit 1
fi

echo "✅ requirements.txt found"

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "❌ app.py not found. Please create it first."
    exit 1
fi

echo "✅ app.py found"

# Check if render.yaml exists
if [ ! -f "render.yaml" ]; then
    echo "❌ render.yaml not found. Please create it first."
    exit 1
fi

echo "✅ render.yaml found"

echo ""
echo "🎯 Deployment Checklist:"
echo "========================"
echo "1. ✅ Repository is ready"
echo "2. ✅ Dependencies defined"
echo "3. ✅ Render config ready"
echo ""
echo "📋 Next Steps:"
echo "=============="
echo "1. Push your code to GitHub:"
echo "   git add ."
echo "   git commit -m 'Ready for Render deployment'"
echo "   git push origin main"
echo ""
echo "2. Go to [render.com](https://render.com) and:"
echo "   - Sign up with GitHub"
echo "   - Click 'New Web Service'"
echo "   - Select this repository"
echo "   - Use these settings:"
echo "     • Build Command: pip install -r requirements.txt"
echo "     • Start Command: gunicorn app:app --bind 0.0.0.0:\$PORT --workers 1 --timeout 120"
echo ""
echo "3. Set environment variables:"
echo "   • DHAN_CLIENT_ID"
echo "   • DHAN_ACCESS_TOKEN"
echo "   • WEBHOOK_SECRET"
echo "   • API_SECRET"
echo "   • FLASK_ENV=production"
echo ""
echo "4. Deploy and get your public URL!"
echo ""
echo "🔗 Your webhook URL will be: https://your-app-name.onrender.com/webhook/tradingview"
echo ""
echo "🎉 Happy Trading!"
