#!/bin/bash
# Quick Start Guide for Race Wrangler POC

set -e

echo "🏁 Race Wrangler POC - Quick Start Setup"
echo "========================================"
echo ""

# Check for required tools
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker is not installed - you can still run locally"
fi

echo "✓ Prerequisites found:"
echo "  - Python $(python3 --version)"
echo "  - Node $(node --version)"
echo ""

# Backend setup
echo "📦 Setting up Backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Backend dependencies installed"
deactivate
cd ..

# Frontend setup  
echo "📦 Setting up Frontend..."
cd frontend
npm install > /dev/null 2>&1
echo "✓ Frontend dependencies installed"
npm run build > /dev/null 2>&1
echo "✓ Frontend built successfully"
cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the POC:"
echo "  Option 1 (Local Development):"
echo "    Terminal 1: cd backend && source venv/bin/activate && python app.py"
echo "    Terminal 2: cd frontend && npm run dev"
echo ""
echo "  Option 2 (Docker):"
echo "    docker-compose up"
echo ""
echo "Then open: http://localhost:3000"
