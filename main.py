import logging
import os
from telegram import Update, Poll
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from dotenv import load_dotenv

from utilities import get_quiz_of_ai
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in environment variables")

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    
    logger.info(f"Start command received from {update.effective_user.id}")
    message = update.message or update.callback_query.message
    await message.reply_text("Hey my friend!I'm here to make cool quiz with your lessons, Are your ready?Just send everything that you learned(after on of them got new line)")
    
async def ai_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send user's question to ai."""
    logger.info("ai_bot triggered")
    message = update.message.text
    response = get_quiz_of_ai(message)
    print(response)
    for item in response['quiz']:
        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=item['question'],
            options=item['options'],
            type=Poll.QUIZ,
            correct_option_id=item['answer_index'],
            is_anonymous=False
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and notify the user."""
    logger.error(f"Update {update} caused error: {context.error}")
    await update.message.reply_text("I don't know exactly but I think there is an issue on bot, I'm sorry😥")


def main() -> None:
    """Start the bot."""
    logger.info("Starting bot...")
    
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Register handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters=~filters.COMMAND & filters.TEXT, callback=ai_bot))
        
        # Error handler
        application.add_error_handler(error_handler)

        logger.info("Bot is running...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()