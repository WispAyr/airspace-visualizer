#!/usr/bin/env python3
"""
Telegram Bot for Aviation Radar AI Assistant
Provides access to radar data, aircraft tracking, and AI assistance via Telegram
"""

import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')  # Set this in environment
AI_SERVER_URL = 'http://localhost:11435'
RADAR_SERVER_URL = 'http://localhost:8080'

class AviationTelegramBot:
    def __init__(self):
        self.application = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🚁 *TACAMOBOT - Aviation Radar AI Assistant*

Welcome to your personal aviation radar bot! I can help you with:

*Commands:*
/start - Show this help message
/status - Current radar system status
/aircraft - Live aircraft information
/weather <ICAO> - Weather for airport (e.g., /weather EGPK)
/notams - Active NOTAMs
/ai <question> - Ask the AI anything about aviation

*Examples:*
/ai how many aircraft are flying?
/ai what's the weather like?
/ai show me database statistics

*Features:*
• Real-time aircraft tracking
• Live weather data
• NOTAM information
• AI-powered aviation assistance
• Historical data access
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command - show system status"""
        try:
            # Check AI server status
            ai_response = requests.get(f"{AI_SERVER_URL}/chat?q=system status", timeout=5)
            ai_status = "🟢 Online" if ai_response.status_code == 200 else "🔴 Offline"
            
            # Check radar server status
            radar_response = requests.get(f"{RADAR_SERVER_URL}/api/database/stats", timeout=5)
            radar_status = "🟢 Online" if radar_response.status_code == 200 else "🔴 Offline"
            
            # Get database stats if available
            db_stats = ""
            if radar_response.status_code == 200:
                stats = radar_response.json().get('stats', {})
                db_stats = f"""
*Database Stats:*
• Size: {stats.get('database_size', 'Unknown')}
• Total Contacts: {stats.get('total_contacts', 'Unknown')}
• Total Events: {stats.get('total_events', 'Unknown')}
• Last Update: {stats.get('newest_contact', 'Unknown')}
                """
            
            status_message = f"""
📡 *Radar System Status*

*AI Server:* {ai_status}
*Radar Server:* {radar_status}
{db_stats}

*Last Check:* {datetime.now().strftime('%H:%M:%S')}
            """
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error checking status: {str(e)}")
    
    async def aircraft(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /aircraft command - show current aircraft"""
        try:
            # Get aircraft data via AI
            response = requests.get(f"{AI_SERVER_URL}/chat?q=how many aircraft are currently flying", timeout=10)
            if response.status_code == 200:
                data = response.json()
                aircraft_info = data.get('response', 'No aircraft data available')
                await update.message.reply_text(f"✈️ *Current Aircraft:*\n\n{aircraft_info}", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Unable to fetch aircraft data")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching aircraft data: {str(e)}")
    
    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /weather command - get weather for airport"""
        if not context.args:
            await update.message.reply_text("❌ Please specify an airport ICAO code.\nExample: /weather EGPK")
            return
            
        icao = context.args[0].upper()
        try:
            # Get weather via AI with specific weather query
            response = requests.get(f"{AI_SERVER_URL}/chat?q=current METAR weather conditions at {icao} airport", timeout=10)
            if response.status_code == 200:
                data = response.json()
                weather_info = data.get('response', f'No weather data available for {icao}')
                await update.message.reply_text(f"🌤️ *Weather for {icao}:*\n\n{weather_info}", parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ Unable to fetch weather for {icao}")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching weather: {str(e)}")
    
    async def notams(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /notams command - show active NOTAMs"""
        try:
            # Get NOTAMs via AI
            response = requests.get(f"{AI_SERVER_URL}/chat?q=what NOTAMs are currently active", timeout=10)
            if response.status_code == 200:
                data = response.json()
                notam_info = data.get('response', 'No NOTAM data available')
                await update.message.reply_text(f"🚨 *Active NOTAMs:*\n\n{notam_info}", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Unable to fetch NOTAM data")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching NOTAMs: {str(e)}")
    
    async def ai_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ai command - ask AI questions"""
        if not context.args:
            await update.message.reply_text("❌ Please ask a question.\nExample: /ai how many aircraft are flying?")
            return
            
        question = " ".join(context.args)
        try:
            # Send question to AI server
            response = requests.get(f"{AI_SERVER_URL}/chat?q={question}", timeout=15)
            if response.status_code == 200:
                data = response.json()
                ai_response = data.get('response', 'No response from AI')
                await update.message.reply_text(f"🤖 *AI Response:*\n\n{ai_response}", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Unable to get AI response")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting AI response: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages - treat as AI queries"""
        if update.message.text and not update.message.text.startswith('/'):
            try:
                question = update.message.text
                # Send question to AI server
                response = requests.get(f"{AI_SERVER_URL}/chat?q={question}", timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    ai_response = data.get('response', 'No response from AI')
                    await update.message.reply_text(f"🤖 *AI Response:*\n\n{ai_response}", parse_mode='Markdown')
                else:
                    await update.message.reply_text("❌ Unable to get AI response")
                    
            except Exception as e:
                await update.message.reply_text(f"❌ Error getting AI response: {str(e)}")
    
    def run(self):
        """Start the Telegram bot"""
        if not TELEGRAM_TOKEN:
            logger.error("TELEGRAM_TOKEN environment variable not set!")
            return
            
        # Create application
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("aircraft", self.aircraft))
        self.application.add_handler(CommandHandler("weather", self.weather))
        self.application.add_handler(CommandHandler("notams", self.notams))
        self.application.add_handler(CommandHandler("ai", self.ai_query))
        
        # Add message handler for regular text
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start the bot
        logger.info("Starting TACAMOBOT - Aviation Radar Telegram Bot...")
        self.application.run_polling()

def main():
    """Main function"""
    bot = AviationTelegramBot()
    bot.run()

if __name__ == '__main__':
    main()
