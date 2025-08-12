#!/bin/bash

# Start Telegram Bot for Aviation Radar AI Assistant
echo "🚁 Starting Aviation Radar Telegram Bot..."

# Set the Telegram token
export TELEGRAM_TOKEN="6730537017:AAGnK4toKXph8kodfSE80msciRdUPqgVIvw"

# Activate virtual environment
source .venv/bin/activate

# Install Telegram bot dependencies if not already installed
echo "📦 Installing Telegram bot dependencies..."
pip install -r requirements_telegram.txt

# Start the bot
echo "🤖 Launching Telegram bot..."
python3 telegram_bot.py
