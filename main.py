from datetime import time as dt_time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)

from config import logger, TELEGRAM_TOKEN

from utilities import (
    get_quiz_from_ai,
    send_poll_to_user_and_channel,
    read_puzzles_from_file,
    DatabaseManager
)

try:
    db_manager = DatabaseManager()
except Exception as e:
    logger.critical(f"Failed to initialize DatabaseManager: {e}. Bot cannot start properly.", exc_info=True)
    exit()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message and ask for language level."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    logger.info(f"Start command received from user {user.id} ({user.username or 'N/A'}) in chat {chat_id}.")

    db_manager.add_or_update_user(user_id=user.id, username=user.username or user.first_name)

    welcome_text = (
        "🎉 Welcome to the Quiz Bot! 🎉\n"
        "I'm here to turn your notes into fun quizzes! 📚\n\n"
        "First, please select your English language level:"
    )

    keyboard = [
        [InlineKeyboardButton("A1", callback_data='level_A1'), InlineKeyboardButton("A2", callback_data='level_A2')],
        [InlineKeyboardButton("B1", callback_data='level_B1'), InlineKeyboardButton("B2", callback_data='level_B2')],
        [InlineKeyboardButton("C1", callback_data='level_C1'), InlineKeyboardButton("C2", callback_data='level_C2')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message_to_reply = update.message or (update.callback_query and update.callback_query.message)
    if message_to_reply:
        await message_to_reply.reply_text(welcome_text, reply_markup=reply_markup)
    else:
        logger.warning(f"Could not find a message to reply to for user {user.id}")

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display and edit user's settings"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    logger.info(f"Settings command received from user {user.id} ({user.username or 'N/A'}) in chat {chat_id}.")

    user_data = db_manager.get_user(user.id)
    if user_data['daily_puzzle'] == True:
        daily_puzzle = '✅'
    else:
        daily_puzzle = '❌'
    user_status = f"🌎 English Level: {user_data['level']}\n🧩 Sending Daily Puzzle: {daily_puzzle}"

    settings_text = (
        "⚙️ Bot Settings ⚙️\n\n"
        "📝 Currently Status:\n" + user_status
    )

    keyboard = [
        [InlineKeyboardButton("English Level", callback_data='settings_english_level')],
        [InlineKeyboardButton("Daily Puzzle", callback_data='settings_daily_puzzle')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message_to_reply = update.message or (update.callback_query and update.callback_query.message)
    if message_to_reply:
        await message_to_reply.reply_text(settings_text, reply_markup=reply_markup)
    else:
        logger.warning(f"Could not find a message to reply to for user {user.id}")


async def settings_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings."""

    # callback handeler
    if update.callback_query:
        user = update.effective_user
        chat_id = update.effective_chat.id
        logger.info(f"Settings, CallBackQuery command received from user {user.id} ({user.username or 'N/A'}) in chat {chat_id}.")

        query = update.callback_query
        data = query.data
        await query.answer()

        if data == "settings_english_level":
            keyboard = [
                [InlineKeyboardButton("A1", callback_data='level_A1'), InlineKeyboardButton("A2", callback_data='level_A2')],
                [InlineKeyboardButton("B1", callback_data='level_B1'), InlineKeyboardButton("B2", callback_data='level_B2')],
                [InlineKeyboardButton("C1", callback_data='level_C1'), InlineKeyboardButton("C2", callback_data='level_C2')]
            ]
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
            return

        elif data == "settings_daily_puzzle":
            keyboard = [
                [InlineKeyboardButton("✅ Active", callback_data='settingsـdaily_active')],
                [InlineKeyboardButton("❌ Deactive", callback_data='settingsـdaily_deactive')],
            ]
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
            return
        elif data in ["settingsـdaily_active", "settingsـdaily_deactive"]:
            logger.debug(f"User choice daily settings")

            if data == "settingsـdaily_deactive":
                db_manager.add_or_update_user(chat_id, daily_puzzle=False)
                daily_puzzle_text = (
                    "Your daily puzzle has been successfully deactivated. ✅\n\n"
                    "But daily quiz puzzle is so helpful and fun, don't you wanna activate it again😢?\n"
                    "Although I still here to turn your notes to fun quiz😉. Just send me!"
                )
                message_to_reply = update.message or (update.callback_query and update.callback_query.message)
                await message_to_reply.reply_text(daily_puzzle_text)

            elif data == "settingsـdaily_active":
                db_manager.add_or_update_user(chat_id, daily_puzzle=True)
                daily_puzzle_text = (
                    "Your daily puzzle has been successfully activated. ✅\n\n"
                    "Daily quiz puzzle is so fun and can improve your English significantly\n"
                    "As a strong start, in addition to the daily quiz, send notes to be turned into quizzes😉"
                )
                message_to_reply = update.message or (update.callback_query and update.callback_query.message)
                await message_to_reply.reply_text(daily_puzzle_text)


async def level_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user's language level selection."""
    query = update.callback_query
    await query.answer() # Acknowledge callback
    user = update.effective_user
    chosen_level = query.data.split('_')[1] # Extracts "A1" from "level_A1"
    logger.info(f"User {user.id} ({user.username or 'N/A'}) chose level: {chosen_level}")

    success = db_manager.add_or_update_user(user_id=user.id, username=user.username or user.first_name, level=chosen_level)

    if success:
        # await query.edit_message_text(text=f"Great! Your level is set to {chosen_level}. ✨\nNow, send me your notes, and I'll create a quiz for you!")
        await query.edit_message_text(text=f"Great! Your level is set to {chosen_level}. ✨\n💬 Write a sentence/word/phrase/.. in English.\nI'll catch your grammar mistakes and quiz you on it! 🔥(No idea? send me an color/object/..)")
    else:
        await query.edit_message_text(text="Sorry, there was an issue saving your level. Please try /start again. 😥")


async def quiz_maker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process user's notes and send a quiz."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_notes = update.message.text

    logger.info(f"Quiz maker triggered by user {user.id} in chat {chat_id} with notes: '{user_notes[:50]}...'")
    db_manager.add_or_update_user(user.id)
    await update.message.reply_text("🔍 Got your notes! Generating a fun quiz for you... This might take a moment. 😊")

    user_level = db_manager.get_user(user.id)['level']
    if not user_level:
        logger.warning(f"User {user.id} tried to generate quiz without setting a level. Prompting to /start.")
        await update.message.reply_text("Please set your English level first using the /start command. Then send your notes!")
        return

    quiz_response = get_quiz_from_ai(user_notes, user_level=user_level)

    if not quiz_response or not quiz_response.get('quiz'):
        logger.error(f"Failed to get valid quiz structure from AI for user {user.id}.")
        error_message = quiz_response.get('notes', {}).get('message', "😓 Oops, something went wrong while creating your quiz. Please try again or send different notes.")
        await update.message.reply_text(error_message)
        return

    logger.info(f"AI response for user {user.id}: {str(quiz_response)[:200]}...")

    for item in quiz_response['quiz']:
        try:
            await send_poll_to_user_and_channel(
                context,
                chat_id,
                item['question'],
                item['options'],
                item['answer_index'],
                explanation=item['explanation'] if item.get('explanation') else "Great job! Keep practicing to master this topic! 🌟" # Default explanation
            )
        except Exception as e:
            logger.error(f"Error sending poll item for user {user.id}: {e}", exc_info=True)
            await update.message.reply_text("😓 Oops, there was an issue sending one of the quiz questions. Let's try the rest or you can send new notes.")
            break # Stop if one poll fails, or continue carefully

    # Handle AI notes
    ai_notes = quiz_response.get('notes', {})
    if ai_notes:
        note_text_parts = []
        if 'message' in ai_notes and ai_notes['message']:
             note_text_parts.append(ai_notes['message']) 
        if 'skipped_phrases' in ai_notes and ai_notes['skipped_phrases']:
            note_text_parts.append(f"⚠️ I skipped some parts that weren't clear: {', '.join(ai_notes['skipped_phrases'])}.")
        if 'corrections' in ai_notes and ai_notes['corrections']:
            note_text_parts.append(f"✅ I made these corrections: {', '.join(ai_notes['corrections'])}.")

        if note_text_parts:
            final_note_text = "📝 **A quick note:**\n" + "\n".join(note_text_parts)
            final_note_text += "\n\nThe world of knowledge is endless! Don't you want to learn more? I'm here and all ears! 👂"
            await update.message.reply_text(final_note_text, parse_mode='Markdown')
        elif not quiz_response['quiz']: # No quiz and no specific notes, but AI might have a general message
             await update.message.reply_text(ai_notes.get('message', "All done for now! 😄"))
        else: # Quiz sent, no specific notes
            await update.message.reply_text("🎯 Your quiz is ready! Answer the questions above and let's see how you do! 😄")


async def daily_quiz_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job to send a daily quiz puzzle."""
    logger.info("Executing daily quiz job...")
    puzzle_data = read_puzzles_from_file() # Using the file-based puzzle reader

    if not puzzle_data:
        logger.warning("Daily quiz job: No puzzle data found to send.")
        return

    all_user_ids = db_manager.get_users_with_daily_puzzle_enabled()
    if not all_user_ids:
        logger.info("Daily quiz job: No users found in the database to send puzzles to.")
        return

    for user in all_user_ids:
        user_id = user['user_id']
        try:
            await context.bot.send_message(chat_id=user_id, text="It's time for your daily English puzzle! 🧩🏫")
            for data in puzzle_data:
                await send_poll_to_user_and_channel(
                    context,
                    user_id,
                    data['question'],
                    data['options'],
                    data['answer_index'],
                    explanation=data['explanation'] if data.get('explanation') else "This was your daily challenge! Keep it up! 💪"
                )
            logger.info(f"Sent daily puzzle to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send daily puzzle to user {user_id}: {e}", exc_info=True)
            # Consider how to handle users who have blocked the bot or other errors

async def error_handler_telegram(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates and send a user-friendly message."""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "😥 Oh no, something went a bit sideways on my end! "
                "I've noted it down. Please try again in a moment or use /start to reset. Let's keep the fun going! 🎈"
            )
        except Exception as e:
            logger.error(f"Error sending error message to user: {e}")


def main() -> None:
    """Start the bot."""
    logger.info("Starting bot...")

    if not TELEGRAM_TOKEN:
        logger.critical("TELEGRAM_TOKEN is not set. Bot cannot start.")
        return

    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build() # removed persistence for now .persistence(persistence)

        # Register handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("settings", settings_command))
        application.add_handler(CallbackQueryHandler(level_choice_callback, pattern='level_*')) # Pattern for level callbacks
        application.add_handler(CallbackQueryHandler(settings_choice_callback, pattern='settings_*')) # Pattern for level callbacks
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_maker_handler))

        application.add_error_handler(error_handler_telegram)

        # Schedule daily message
        job_queue = application.job_queue
        if job_queue: 
            job_queue.run_daily(
                daily_quiz_job,
                time=dt_time(hour=7, minute=30, second=00), # Specify timezone if needed: tzinfo=pytz.timezone('Your/Timezone')
                name="daily_quiz_puzzle"
            )
            logger.info("Daily quiz job scheduled for 07:30 server time.")
        else:
            logger.warning("JobQueue not available. Daily quiz job not scheduled.")


        logger.info("Bot is polling...")
        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.critical(f"Critical error during bot setup or runtime: {e}", exc_info=True)
    finally:
        if 'db_manager' in globals() and db_manager:
            db_manager.close_connection()
            logger.info("Database connection closed on shutdown.")
        logger.info("Bot shutdown.")

if __name__ == '__main__':
    main()