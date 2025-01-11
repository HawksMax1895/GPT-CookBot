import os
from dotenv import load_dotenv
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import openai
from youtube_transcript_api import YouTubeTranscriptApi
from notion_client import Client
import json
import sys

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def validate_environment():
    """Validate all required environment variables are set and valid."""
    load_dotenv()

    required_vars = {
        'TELEGRAM_TOKEN': os.environ.get('TELEGRAM_TOKEN'),
        'OPENAI_TOKEN': os.environ.get('OPENAI_TOKEN'),
        'TELEGRAM_ID': os.environ.get('TELEGRAM_ID'),
        'NOTION_TOKEN': os.environ.get('NOTION_TOKEN'),
        'NOTION_DATABASE_ID': os.environ.get('NOTION_DATABASE_ID')
    }

    missing_vars = [var for var, value in required_vars.items() if not value]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file contains all required variables")
        sys.exit(1)

    logger.info("Environment variables validated successfully")
    logger.info(f"Using Notion Database ID: {required_vars['NOTION_DATABASE_ID']}")


    return required_vars


# Validate environment variables
env_vars = validate_environment()

# Initialize clients with validated environment variables
TELEGRAM_TOKEN = env_vars['TELEGRAM_TOKEN']
OPENAI_TOKEN = env_vars['OPENAI_TOKEN']
AUTHORIZED_USER_ID = int(env_vars['TELEGRAM_ID'])
NOTION_TOKEN = env_vars['NOTION_TOKEN']
NOTION_DATABASE_ID = env_vars['NOTION_DATABASE_ID']

openai.api_key = OPENAI_TOKEN
notion = Client(auth=NOTION_TOKEN)


def verify_notion_access():
    """Verify access to Notion database."""
    try:
        # Try to query the database to verify access
        notion.databases.retrieve(NOTION_DATABASE_ID)
        logger.info("Notion database access verified successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to access Notion database: {e}")
        return False


# Verify Notion access on startup
if not verify_notion_access():
    logger.error("Could not access Notion database. Please check your NOTION_TOKEN and NOTION_DATABASE_ID")
    sys.exit(1)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return
    await update.message.reply_text(
        'Hello! Send me a YouTube cooking video link, and I\'ll create a recipe and save it to Notion.')


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
                 "content": """
        You are an expert chef who creates clear, structured recipes. Create a recipe based on the video transcript provided.
        The recipe should include:
        1. A clear title
        2. A list of ingredients with quantities
        3. Step-by-step instructions

        Format the response as a JSON object with the following structure:
        {
            "title": "Recipe Name",
            "ingredients": ["ingredient 1 with quantity", "ingredient 2 with quantity", ...],
            "instructions": ["step 1", "step 2", ...]
        }

        If the video is not a cooking video, return: {"title": "NotARecipe"}

        Make sure to return ONLY the JSON object, no additional text or formatting.
        """
                 },
                {"role": "user", "content": f"Please create a recipe based on this transcript: {transcript}"}
            ]
        )

        recipe_text = response.choices[0].message.content
        logger.info(f"Generated recipe text: {recipe_text}")

        # Try to parse the JSON to validate it
        recipe_json = json.loads(recipe_text)
        return recipe_text

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing recipe JSON: {e}")
        logger.error(f"Raw recipe text: {recipe_text}")
        return None
    except Exception as e:
        logger.error(f"Error generating recipe: {e}")
        return None


def save_to_notion(recipe_data):
    """Save recipe to Notion database."""
    try:
        # Parse the recipe_data
        logger.info(f"Attempting to parse recipe data: {recipe_data}")
        recipe = json.loads(recipe_data)

        if recipe.get('title') == 'NotARecipe':
            logger.info("Recipe marked as NotARecipe")
            return False

        logger.info(f"Creating Notion page for recipe: {recipe['title']}")

        # Create individual blocks for each ingredient
        ingredient_blocks = []
        for ingredient in recipe['ingredients']:
            ingredient_blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": ingredient}}]
                }
            })

        # Create individual blocks for each instruction
        instruction_blocks = []
        for instruction in recipe['instructions']:
            instruction_blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": instruction}}]
                }
            })

        # Combine all blocks
        all_blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Ingredients"}}]
                }
            }
        ]
        all_blocks.extend(ingredient_blocks)
        all_blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Instructions"}}]
            }
        })
        all_blocks.extend(instruction_blocks)

        # Create the page in Notion
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": recipe['title']
                            }
                        }
                    ]
                }
            },
            children=all_blocks
        )

        logger.info("Successfully created Notion page")
        return True

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing recipe JSON in save_to_notion: {e}")
        logger.error(f"Raw recipe data: {recipe_data}")
        return False
    except Exception as e:
        logger.error(f"Error saving to Notion: {e}")
        return False


async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User_ID: {user_id}")
    if user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    url = update.message.text

    if 'youtube.com' in url or 'youtu.be' in url:
        await update.message.reply_text('Processing video and generating recipe...')

        video_id = extract_video_id(url)
        if not video_id:
            await update.message.reply_text('Invalid YouTube URL. Please try again.')
            return

        transcript = get_transcript(video_id)
        if not transcript:
            await update.message.reply_text(
                'Could not get video transcript. Make sure the video has subtitles enabled.')
            return

        recipe = generate_recipe(transcript)
        if not recipe:
            await update.message.reply_text('Error generating recipe. Please try again.')
            return

        # Save to Notion
        if save_to_notion(recipe):
            await update.message.reply_text('Recipe has been successfully saved to Notion!')
        else:
            error_msg = "There was an error saving to Notion. Please check the logs for details."
            await update.message.reply_text(error_msg)
    else:
        await update.message.reply_text('Please send a valid YouTube video URL.')


def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")