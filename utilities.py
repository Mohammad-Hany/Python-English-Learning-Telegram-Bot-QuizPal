import sqlite3
import json
import datetime
from typing import List, Optional, Dict, Any

from google import genai
from telegram import Poll

from config import logger, GOOGLE_AI_TOKEN, CHANNEL_ID, DATABASE_NAME
from prompt import get_ai_prompt

try:
    ai_model = genai.Client(api_key=GOOGLE_AI_TOKEN)
    logger.info("Google AI Client configured successfully.")
except Exception as e:
    logger.error(f"Failed to configure Google AI Client: {e}")
    ai_model = None


class DatabaseManager:
    def __init__(self, db_name: str = DATABASE_NAME):
        self.db_name = db_name
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            logger.info(f"Successfully connected to database: {self.db_name}")
            self._create_tables()
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database {self.db_name}: {e}")
            raise

    def _create_tables(self):
        if not self.conn:
            logger.error("Cannot create tables: Database connection not established.")
            return
        try:
            cursor = self.conn.cursor()
            # 0 for False, 1 for True
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                level TEXT CHECK(level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
                daily_puzzle INTEGER DEFAULT 1,
                timestamp DATETIME NOT NULL
            )
            ''')
            self.conn.commit()
            logger.info("Table 'users' checked/created successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error creating table 'users': {e}")

    def add_or_update_user(self,
                           user_id: int,
                           username: Optional[str] = None,
                           level: Optional[str] = None,
                           daily_puzzle: Optional[bool] = None
                           ) -> bool:
        if not self.conn:
            logger.error("Cannot add/update user: Database connection not established.")
            return False

        current_timestamp = datetime.datetime.now()
        cursor = self.conn.cursor()

        try:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
            existing_user_row = cursor.fetchone()

            if existing_user_row:  # User exists, update them
                update_parts = []
                params = []

                if username is not None:
                    update_parts.append("username = ?")
                    params.append(username)
                if level is not None:
                    update_parts.append("level = ?")
                    params.append(level)
                if daily_puzzle is not None: # If a preference for daily_puzzle is explicitly passed
                    update_parts.append("daily_puzzle = ?")
                    params.append(1 if daily_puzzle else 0) # Convert boolean to 0 or 1
                if not update_parts:
                    cursor.execute("UPDATE users SET timestamp = ? WHERE user_id = ?",
                                    (current_timestamp, user_id))
                    logger.info(f"User {user_id} timestamp updated (no other fields provided for update).")
                else:
                    update_parts.append("timestamp = ?")
                    params.append(current_timestamp)

                    set_clause = ", ".join(update_parts)
                    params.append(user_id)  # For the WHERE clause

                    sql_update_query = f"UPDATE users SET {set_clause} WHERE user_id = ?"
                    cursor.execute(sql_update_query, tuple(params))
                    updated_fields_log = [part.split(' ')[0] for part in update_parts] # e.g., ['username', 'level', 'timestamp']
                    logger.info(f"User {user_id} updated. Fields: {updated_fields_log}.")

            else:  # New user, insert them
                username_to_save = username

                # 1 = True/ 0 = False
                daily_puzzle_value_to_insert = 1 # Default to True for new users if not specified
                if daily_puzzle is not None:
                    daily_puzzle_value_to_insert = 1 if daily_puzzle else 0

                # Note: The users table in _create_tables has daily_puzzle INTEGER DEFAULT 1
                # So, if daily_puzzle_value_to_insert is not included in the INSERT statement and
                # the daily_puzzle parameter was None, it would default to 1.
                # To be explicit:
                cursor.execute('''
                    INSERT INTO users (user_id, username, level, timestamp, daily_puzzle)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, username_to_save, level, current_timestamp, daily_puzzle_value_to_insert))
                logger.info(f"User {username_to_save} (ID: {user_id}) added with level {level}, daily_puzzle set to {bool(daily_puzzle_value_to_insert)}.")

            self.conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error for user {user_id} (Username: {username}): {e}. User might already exist or other constraint violation.")
            return False
        except sqlite3.Error as e:
            logger.error(f"Database error for user {user_id} (Username: {username}): {e}")
            return False

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves all data for a user by their user_id."""
        cursor = self.conn.cursor()
        try:
            # Ensure you select all columns you need, including the new one
            cursor.execute("SELECT id, user_id, username, level, timestamp, daily_puzzle FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                # Get column names from cursor.description
                columns = [description[0] for description in cursor.description]
                user_data = dict(zip(columns, row))

                # Convert daily_puzzle from 0/1 to True/False for easier use in Python
                if 'daily_puzzle' in user_data and user_data['daily_puzzle'] is not None:
                    user_data['daily_puzzle'] = bool(user_data['daily_puzzle'])
                else: # Handle case where it might be NULL if not properly defaulted or if schema was manually altered
                    user_data['daily_puzzle'] = True # Default to True if NULL for some reason

                logger.debug(f"User data found for user_id {user_id}: {user_data}")
                return user_data
            else:
                logger.info(f"No user found with user_id {user_id}.")
                return None
        except sqlite3.Error as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    def get_users_with_daily_puzzle_enabled(self) -> List[Dict[str, Any]]:
        """Retrieves all users who have the daily_puzzle preference set to True (1)."""
        if not self.conn:
            logger.error("Cannot get users with daily puzzle enabled: Database connection not established.")
            return []

        users_list = []
        cursor = self.conn.cursor()
        try:
            # Select all columns for users where daily_puzzle is 1 (True)
            cursor.execute("""
                SELECT id, user_id, username, level, timestamp, daily_puzzle
                FROM users
                WHERE daily_puzzle = 1
            """)
            rows = cursor.fetchall()

            if rows:
                # Get column names from cursor.description
                columns = [description[0] for description in cursor.description]
                for row in rows:
                    user_data = dict(zip(columns, row))

                    # Convert daily_puzzle from 0/1 to True/False for easier use in Python
                    if 'daily_puzzle' in user_data and user_data['daily_puzzle'] is not None:
                        user_data['daily_puzzle'] = bool(user_data['daily_puzzle'])
                    else:
                        # This case should ideally not happen if the column has a DEFAULT
                        # and is consistently set. Defaulting to True if somehow NULL.
                        user_data['daily_puzzle'] = True

                    users_list.append(user_data)
                logger.debug(f"Found {len(users_list)} users with daily puzzle enabled.")
            else:
                logger.debug("No users found with daily puzzle enabled.")

            return users_list
        except sqlite3.Error as e:
            logger.error(f"Error fetching users with daily puzzle enabled: {e}")
            return [] # Return an empty list in case of an error

    def get_all_user_ids(self) -> List[int]:
        """Retrieves all user_ids from the database."""
        if not self.conn:
            logger.error("Cannot get all user IDs: Database connection not established.")
            return []
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT user_id FROM users")
            user_ids = [row[0] for row in cursor.fetchall()]
            logger.debug(f"Retrieved {len(user_ids)} user IDs.")
            return user_ids
        except sqlite3.Error as e:
            logger.error(f"Error fetching all user IDs: {e}")
            return []

    def close_connection(self):
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed.")
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection: {e}")
        else:
            logger.info("No active database connection to close.")

def read_puzzles_from_file(file_path='puzzles.json') -> Optional[Dict[str, Any]]:
    """Reads one puzzle from puzzles.json and updates the file."""
    try:
        with open(file_path, 'r+', encoding='utf-8') as file:
            content = file.read()
            if not content:
                logger.warning(f"Puzzle file {file_path} is empty.")
                return None
            quiz_data = json.loads(content)

            if not quiz_data.get('quiz'):
                logger.warning(f"No 'quiz' array found in {file_path} or it's empty.")
                return None

            puzzle = quiz_data['quiz'].pop(0) # Get and remove the first puzzle

            file.seek(0) # Go to the beginning of the file
            json.dump(quiz_data, file, indent=4) # Write the updated data back
            file.truncate() # Remove any leftover old content
            logger.debug(f"Read and removed one puzzle from {file_path}.")
            return puzzle
    except FileNotFoundError:
        logger.error(f"Puzzle file {file_path} not found.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading puzzles from {file_path}: {e}")
        return None

async def send_poll_to_user_and_channel(context, user_chat_id, question, options, correct_option_id, explanation):
    """Sends a poll to a user and optionally to a channel."""
    try:
        await context.bot.send_poll(
            chat_id=user_chat_id,
            question=question,
            options=options,
            type=Poll.QUIZ,
            correct_option_id=correct_option_id,
            is_anonymous=False, # User polls are not anonymous to track progress (if needed)
            explanation=explanation
        )
        logger.info(f"Sent poll to user {user_chat_id}.")

        if CHANNEL_ID: # Only send to channel if CHANNEL_ID is set
            await context.bot.send_poll(
                chat_id=str(CHANNEL_ID),
                question=question,
                options=options,
                type=Poll.QUIZ,
                correct_option_id=correct_option_id,
                is_anonymous=True, # Channel polls are anonymous
                explanation=explanation
            )
            logger.info(f"Sent poll to channel {CHANNEL_ID}.")
        else:
            logger.debug("CHANNEL_ID not set, skipping poll to channel.")

    except Exception as e:
        logger.error(f"Error sending poll: {e}", exc_info=True)


def get_quiz_from_ai(input_phrases: str, user_level: Optional[str] = "B1-B2") -> Optional[Dict[str, Any]]:
    """
    Generates a quiz using Google AI based on input phrases and user level.
    """
    if not ai_model:
        logger.error("AI model not initialized. Cannot generate quiz.")
        return {"quiz": [], "notes": {"message": "AI service is currently unavailable. 😥"}}

    prompt = get_ai_prompt(user_level, input_phrases)
    
    try:
        logger.debug(f"Sending prompt to AI for phrases: {input_phrases}")
        # The new API uses generate_content
        response = ai_model.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            logger.error(f"AI content generation blocked. Reason: {response.prompt_feedback.block_reason_message}")
            return {"quiz": [], "notes": {"message": "Sorry, I couldn't process that request due to content restrictions. 😔"}}

        if not response.text:
            logger.error("AI response structure not recognized or empty.")
            return {"quiz": [], "notes": {"message": "Received an unexpected response from the AI. 😕"}}
        response_text = response.text


        logger.debug(f"Raw AI response text: {response_text[:100]}...") # Log beginning of response
        quiz_data = json.loads(response_text)
        logger.info("Successfully generated and parsed quiz from AI.")
        return quiz_data
    except json.JSONDecodeError as e:
        logger.error(f"AI JSON decoding error: {e}. Raw response: {response_text[:1000]}", exc_info=True)
        return {"quiz": [], "notes": {"message": "I had a little trouble understanding the AI's reply. Please try again! 🛠️"}}
    except Exception as e:
        logger.error(f"Error getting quiz from AI: {e}", exc_info=True)
        return {"quiz": [], "notes": {"message": "Something went wrong while talking to the AI. Please try again later. 🤖"}}