
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import telegram
import sys
import json
import asyncio
import random
import datetime # Added this line

# --- Constants ---
GOOGLE_SHEET_NAME = 'english vocab'  # Name of your Google Sheet
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_IDS = os.environ.get('TELEGRAM_CHAT_IDS', '').split(',')
SENT_WORDS_TRACKER_FILE = 'sent_words_tracker.txt'
GOOGLE_CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS_JSON')

# --- Google Sheets Connection ---
def get_google_sheet():
    """Connects to the Google Sheet and returns the worksheet."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        
        if not GOOGLE_CREDENTIALS_JSON:
            raise ValueError("GOOGLE_CREDENTIALS_JSON environment variable not set.")
            
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON) # Changed eval() to json.loads()
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
        return sheet
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        sys.exit(1)

# --- Telegram Bot ---
async def send_telegram_message(bot, chat_id, message):
    """Sends a message to a Telegram chat."""
    try:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode=telegram.constants.ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")

# --- Core Logic ---
async def send_daily_words():
    """Fetches and sends 3 new words to the Telegram chats."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("Telegram token or chat IDs are not set.")
        return

    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    sheet = get_google_sheet()
    words = sheet.get_all_records()

    try:
        with open(SENT_WORDS_TRACKER_FILE, 'r') as f:
            last_sent_index = int(f.read().strip())
    except FileNotFoundError:
        last_sent_index = 0

    new_words = words[last_sent_index : last_sent_index + 3]

    if not new_words:
        message = "No new words to send today!"
    else:
        message_parts = []
        for i, word in enumerate(new_words):
            word_entry = (
                f"*Word:* {word['Word']}\n"
                f"*Meaning:* {word['Meaning']}\n"
                f"*Synonyms:* {word['Synonyms']}\n"
                f"*Antonyms:* {word['Antonyms']}\n"
                f"*Example:* {word['Example Sentence']}"
            )
            message_parts.append(f"*{last_sent_index + i + 1}.* {word_entry}")
        message = "\n\n---\n\n".join(message_parts)

    for chat_id in TELEGRAM_CHAT_IDS:
        if chat_id:
            await send_telegram_message(bot, chat_id, message)

    # Update the tracker
    with open(SENT_WORDS_TRACKER_FILE, 'w') as f:
        f.write(str(last_sent_index + len(new_words)))

async def send_weekly_summary():
    """Fetches and sends a summary of the last 21 words learned."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("Telegram token or chat IDs are not set.")
        return

    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    sheet = get_google_sheet()
    words = sheet.get_all_records()

    try:
        with open(SENT_WORDS_TRACKER_FILE, 'r') as f:
            last_sent_index = int(f.read().strip())
    except FileNotFoundError:
        last_sent_index = 0

    # Calculate the range for the last 21 words (3 words/day * 7 days)
    start_index = max(0, last_sent_index - 21)
    summary_words = words[start_index:last_sent_index]

    if not summary_words:
        message = "No words learned this week yet for a summary."
    else:
        message_parts = ["*Weekly Vocabulary Summary:*"]
        for i, word in enumerate(summary_words):
            word_entry = (
                f"*Word:* {word['Word']}\n"
                f"*Meaning:* {word['Meaning']}\n"
                f"*Synonyms:* {word['Synonyms']}\n"
                f"*Antonyms:* {word['Antonyms']}\n"
                f"*Example:* {word['Example Sentence']}"
            )
            message_parts.append(f"\n---\n\n*{i+1}.* {word_entry}")
        message = "\n".join(message_parts)

    for chat_id in TELEGRAM_CHAT_IDS:
        if chat_id:
            await send_telegram_message(bot, chat_id, message)

# --- Quiz Functions ---
def shuffle_word(word):
    """Shuffles the letters of a word."""
    word_list = list(word)
    random.shuffle(word_list)
    return "".join(word_list)

def generate_quiz(words_for_quiz):
    """Generates a quiz with 20-25 questions from the given words."""
    quiz_questions = []
    quiz_answers = []
    num_questions = random.randint(20, 25)

    if len(words_for_quiz) < 5: # Need at least a few words to make a decent quiz
        return [], []

    for q_num in range(1, num_questions + 1):
        word_data = random.choice(words_for_quiz)
        word = word_data['Word']
        meaning = word_data['Meaning']
        synonyms = word_data['Synonyms'].split(', ') if word_data['Synonyms'] else []
        antonyms = word_data['Antonyms'].split(', ') if word_data['Antonyms'] else []
        example = word_data['Example Sentence']

        q_type = random.choice(['meaning', 'synonym', 'antonym', 'fill_blank', 'unscramble'])

        if q_type == 'meaning':
            question = f"Q{q_num}: What is the meaning of \"{word}\"?"
            correct_answer = meaning
            options = [meaning]
            # Add 2-3 random incorrect meanings from other words
            other_meanings = [w['Meaning'] for w in words_for_quiz if w['Word'] != word]
            options.extend(random.sample(other_meanings, min(len(other_meanings), 2)))
            random.shuffle(options)
            quiz_questions.append(f"{question}\n{chr(65)}. {options[0]}\n{chr(66)}. {options[1]}\n{chr(67)}. {options[2]}")
            quiz_answers.append(f"A{q_num}: {correct_answer}")

        elif q_type == 'synonym' and synonyms:
            question = f"Q{q_num}: What are the synonyms of \"{word}\"?"
            correct_answer = ', '.join(synonyms)
            options = [correct_answer]
            other_synonyms = [s for w in words_for_quiz if w['Word'] != word for s in (w['Synonyms'].split(', ') if w['Synonyms'] else [])]
            options.extend(random.sample(other_synonyms, min(len(other_synonyms), 2)))
            random.shuffle(options)
            quiz_questions.append(f"{question}\n{chr(65)}. {options[0]}\n{chr(66)}. {options[1]}\n{chr(67)}. {options[2]}")
            quiz_answers.append(f"A{q_num}: {correct_answer}")

        elif q_type == 'antonym' and antonyms:
            question = f"Q{q_num}: What are the antonyms of \"{word}\"?"
            correct_answer = ', '.join(antonyms)
            options = [correct_answer]
            other_antonyms = [a for w in words_for_quiz if w['Word'] != word for a in (w['Antonyms'].split(', ') if w['Antonyms'] else [])]
            options.extend(random.sample(other_antonyms, min(len(other_antonyms), 2)))
            random.shuffle(options)
            quiz_questions.append(f"{question}\n{chr(65)}. {options[0]}\n{chr(66)}. {options[1]}\n{chr(67)}. {options[2]}")
            quiz_answers.append(f"A{q_num}: {correct_answer}")

        elif q_type == 'fill_blank' and example:
            # Replace the word in the example sentence with a blank
            blanked_example = example.replace(word, "______", 1)
            question = f"Q{q_num}: Fill in the blank: \"{blanked_example}\""
            quiz_questions.append(question)
            quiz_answers.append(f"A{q_num}: {word}")

        elif q_type == 'unscramble':
            shuffled = shuffle_word(word)
            question = f"Q{q_num}: Unscramble the letters to find the correct spelling: \"{shuffled}\""
            quiz_questions.append(question)
            quiz_answers.append(f"A{q_num}: {word}")
        else:
            # Fallback if a specific type can't be generated (e.g., no synonyms)
            # This might lead to fewer than 20-25 questions if words_for_quiz is small
            pass

    return quiz_questions, quiz_answers

async def send_quiz(force_run=False):
    """Generates and sends a quiz based on recently learned words."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("Telegram token or chat IDs are not set.")
        return

    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    sheet = get_google_sheet()
    all_words = sheet.get_all_records()

    try:
        with open(SENT_WORDS_TRACKER_FILE, 'r') as f:
            last_sent_index = int(f.read().strip())
    except FileNotFoundError:
        last_sent_index = 0

    # Determine words for quiz based on day of week
    # This is an approximation based on last_sent_index
    today = datetime.datetime.now().weekday() # Monday is 0, Sunday is 6
    words_for_quiz = []

    if not force_run:
        if today == 0: # Monday quiz: Sat, Sun, Mon (3 days * 3 words/day = 9 words)
            start_quiz_index = max(0, last_sent_index - 9)
            words_for_quiz = all_words[start_quiz_index:last_sent_index]
        elif today == 2: # Wednesday quiz: Tue, Wed (2 days * 3 words/day = 6 words)
            start_quiz_index = max(0, last_sent_index - 6)
            words_for_quiz = all_words[start_quiz_index:last_sent_index]
        elif today == 4: # Friday quiz: Thu, Fri (2 days * 3 words/day = 6 words)
            start_quiz_index = max(0, last_sent_index - 6)
            words_for_quiz = all_words[start_quiz_index:last_sent_index]
        else:
            print("Not a quiz day.")
            return
    else: # force_run is True, so get words for quiz regardless of day
        # For forced runs, let's just take the last 9 words for a decent quiz size
        start_quiz_index = max(0, last_sent_index - 9)
        words_for_quiz = all_words[start_quiz_index:last_sent_index]

    if not words_for_quiz:
        print("Not enough words to generate a quiz.")
        return

    quiz_questions, quiz_answers = generate_quiz(words_for_quiz)

    if not quiz_questions:
        print("Quiz generation failed or no questions generated.")
        return

    quiz_message = "Here is your quiz!\n\n" + "\n\n".join(quiz_questions)

    for chat_id in TELEGRAM_CHAT_IDS:
        if chat_id:
            await send_telegram_message(bot, chat_id, quiz_message)

    # Save quiz answers for later
    quiz_data = {
        "questions": quiz_questions,
        "answers": quiz_answers
    }
    with open('quiz_data.json', 'w') as f:
        json.dump(quiz_data, f)

async def send_quiz_answers():
    """Sends the answers to the last generated quiz."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("Telegram token or chat IDs are not set.")
        return

    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        with open('quiz_data.json', 'r') as f:
            quiz_data = json.load(f)
        answers_message = "Here are the answers!\n\n" + "\n".join(quiz_data['answers'])

        for chat_id in TELEGRAM_CHAT_IDS:
            if chat_id:
                await send_telegram_message(bot, chat_id, answers_message)

        # Clean up quiz_data.json after sending answers
        os.remove('quiz_data.json')

    except FileNotFoundError:
        print("No quiz data found to send answers.")
    except Exception as e:
        print(f"Error sending quiz answers: {e}")

if __name__ == "__main__":
    # This allows us to run different functions based on arguments
    # We will use this in our GitHub Actions workflow
    if len(sys.argv) > 1:
        if sys.argv[1] == 'daily_words':
            asyncio.run(send_daily_words())
        elif sys.argv[1] == 'weekly_summary':
            asyncio.run(send_weekly_summary())
        elif sys.argv[1] == 'quiz':
            asyncio.run(send_quiz(force_run=True))
        elif sys.argv[1] == 'quiz_answers':
            asyncio.run(send_quiz_answers())
    else:
        print("No task specified.")
