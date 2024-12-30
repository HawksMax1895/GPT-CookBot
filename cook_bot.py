import os
from dotenv import load_dotenv
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import openai
from youtube_transcript_api import YouTubeTranscriptApi

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram and OpenAI tokens
load_dotenv()
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENAI_TOKEN = os.environ.get('OPENAI_TOKEN')
AUTHORIZED_USER_ID = int(os.environ.get('TELEGRAM_ID'))

# Initialize OpenAI
openai.api_key = OPENAI_TOKEN


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # Get the user ID of the message sender
    if user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return
    await update.message.reply_text('Hello! Send me a YouTube cooking video link, and I\'ll create a recipe from it.')


def extract_video_id(url):
    """Extract YouTube video ID from URL."""
    if 'youtu.be' in url:
        return url.split('/')[-1]
    elif 'youtube.com/shorts/' in url:
        return url.split('/shorts/')[1].split('?')[0]
    elif 'youtube.com' in url:
        return url.split('v=')[1].split('&')[0]
    return None


def get_transcript(video_id):
    """Get video transcript using YouTube Transcript API."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([entry['text'] for entry in transcript])
    except Exception as e:
        logger.error(f"Error getting transcript: {e}")
        return None


def generate_recipe(transcript):
    """Generate recipe using OpenAI API."""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "You are an expert chef who creates clear, structured recipes. Create a recipe based on the video transcript provided, including a single list of ingredients and step-by-step instructions. If an ingredient appears multiple times in the recipe, combine the quantities (e.g., if 20g pepper is used for the meat and 50g for the sauce, the total should be 70g of pepper). All ingredients should be listed together, not categorized. Please provide all measurements in units of g, ml, tablespoon, teaspoon, or pieces. The preparation steps should be short and understandable, with 6-8 steps for each recipe. If the video is not a cooking video presenting a recipe, the answer text should be: ### Recipe: NotARecipe."},
                {"role": "user", "content": f"Please create a recipe based on this transcript: {transcript}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating recipe: {e}")
        return None


def save_recipe(recipe, video_id):
    """Save recipe to text file."""
    # Extract the recipe name from the first line (assuming it starts with '### Recipe: ')
    recipe_name = recipe.split('\n')[0].replace('### Recipe: ', '').strip()

    # Sanitize the recipe name to be used as a valid filename (removing unwanted characters)
    sanitized_name = ''.join(c for c in recipe_name if c.isalnum() or c == '_')

    # Use the sanitized recipe name as the filename
    filename = f'{sanitized_name}.txt'

    if filename != "NotARecipe":
        # Create the file and write the full recipe content
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(recipe)  # Write the entire recipe content to the file

    return filename


async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # Get the user ID of the message sender
    logger.info(f"User_ID: {user_id}")
    if user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return
    
    """Process incoming messages."""
    url = update.message.text

    # Check if message is a YouTube URL
    if 'youtube.com' in url or 'youtu.be' in url:
        await update.message.reply_text('Thank you for sending a video, I am processing the video and generating a recipe.')

        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            await update.message.reply_text('Invalid YouTube URL. Please try again.')
            return

        # Get transcript
        transcript = get_transcript(video_id)
        if not transcript:
            await update.message.reply_text(
                'Could not get video transcript. Make sure the video has subtitles enabled.')
            return

        # Generate recipe
        recipe = generate_recipe(transcript)
        if not recipe:
            await update.message.reply_text('Error generating recipe. Please try again.')
            return

        # Check if the recipe indicates it's not a cooking video
        if recipe.startswith('### Recipe: NotARecipe'):
            await update.message.reply_text('This is not a cooking video. Please send a cooking video.')
        else:
            # Save and send recipe if it's a cooking video
            filename = save_recipe(recipe, video_id)
            try:
                with open(filename, 'rb') as f:
                    await update.message.reply_document(f)
                os.remove(filename)  # Clean up file after sending
            except Exception as e:
                logger.error(f"Error sending file: {e}")
                await update.message.reply_text('Error sending recipe file. Please try again.')
    else:
        await update.message.reply_text('Please send a valid YouTube video URL.')


def main():
    """Start the bot."""
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
