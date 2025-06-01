# config.py
import logging
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in environment variables or .env file")

CHANNEL_ID = os.getenv("CHANNEL_ID")
if not CHANNEL_ID:
    print("Warning: CHANNEL_ID not found in environment variables or .env file. Some features might not work.")

GOOGLE_AI_TOKEN = os.getenv("GOOGLE_AI_TOKEN")
if not GOOGLE_AI_TOKEN:
    raise ValueError("GOOGLE_AI_TOKEN not found in environment variables or .env file")

DATABASE_NAME = os.getenv("DATABASE_NAME", "quizpal_default.db")

# --- Logger Setup ---
LOG_LEVEL_STR = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.getenv('LOG_FILE', 'app.log') # Default log file name if not in .env
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Convert string log level to logging constant
log_level = getattr(logging, LOG_LEVEL_STR, logging.INFO)

# Create logger
logger = logging.getLogger("QuizPalBot") # Application-specific logger name
logger.setLevel(log_level)

# Create handlers if they don't already exist to prevent duplication during reloads
if not logger.handlers:
    # File Handler
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(log_level)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)

    # Create formatter and attach to handlers
    formatter = logging.Formatter(LOG_FORMAT)
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(fh)
    logger.addHandler(ch)

logger.info("Configuration loaded and logger initialized.")