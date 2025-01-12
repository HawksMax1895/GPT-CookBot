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
from urllib.parse import urlparse, parse_qs

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
    """Extract YouTube video ID from a URL."""
    try:
        parsed_url = urlparse(url)
        if parsed_url.netloc in ["www.youtube.com", "youtube.com"]:
            # Extract 'v' parameter for regular YouTube links
            query_params = parse_qs(parsed_url.query)
            if 'v' in query_params:
                return query_params['v'][0]
        elif parsed_url.netloc == "youtu.be":
            # For shortened YouTube URLs
            return parsed_url.path.lstrip('/')
        elif 'youtube.com/shorts/' in url:
            # For YouTube Shorts
            return url.split('/shorts/')[1].split('?')[0]
    except Exception as e:
        logger.error(f"Error extracting video ID from URL {url}: {e}")
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
        You are an expert chef who creates clear, structured recipes. Create a recipe based on the video transcript provided, including a single list of ingredients and step-by-step instructions. 
        If an ingredient appears multiple times in the recipe, combine the quantities (e.g., if 20g pepper is used for the meat and 50g for the sauce, the total should be 70g of pepper). All ingredients should be listed together, not categorized. Please provide all measurements in units of g, ml, tablespoon, teaspoon, or pieces. 
        The preparation steps should be understandable, with about 6-8 steps for each recipe. 
        The Recipe Text should be formatted in a clearly arranged structure with markdown formatting. The ingredients should be formatted in a table and the preparation steps in a numbered list. 
        
        Format the response as a JSON object with the following structure:
        {
            "title": "Recipe Name",
            "metadata": {
                "prep_time": "XX minutes",
                "cook_time": "XX minutes",
                "total_time": "XX minutes",
                "servings": "X servings",
                "calories_per_serving": XXX,
                "protein_per_serving": "XX g",
                "carbs_per_serving": "XX g",
                "fat_per_serving": "XX g",
                "price_per_serving": "€X.XX",
            },
            "ingredients": ["ingredient 1 with quantity", "ingredient 2 with quantity", ...],
            "instructions": ["step 1", "step 2", ...]
        }

        Add reasonable metadata values based on your culinary expertise and knowledge of similar recipes.
        
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


def split_ingredient(ingredient):
    """Split ingredient string into name and quantity."""
    # Handle special cases first (optional ingredients, garnishes)
    if '(optional)' in ingredient:
        base = ingredient.replace('(optional)', '').strip()
        is_optional = True
    else:
        base = ingredient
        is_optional = False

    if '(for garnish)' in base:
        return base.replace('(for garnish)', '').strip(), 'for garnish'

    # Handle "salt to taste" type cases
    if 'to taste' in base:
        return base.replace('to taste', '').strip(), 'to taste'

    # Regular ingredient parsing
    parts = base.split(' ')

    # Find where the ingredient name starts
    quantity_parts = []
    name_parts = []
    measurement_found = False

    for part in parts:
        # If we haven't found a measurement unit yet, this must be part of the quantity
        if not measurement_found:
            if part in ['g', 'ml', 'tbsp', 'tsp', 'cups', 'cup']:
                quantity_parts.append(part)
                measurement_found = True
            else:
                try:
                    # Check if it's a number (including decimals)
                    float(part.replace(',', '.'))
                    quantity_parts.append(part)
                except ValueError:
                    # If it's not a number and not a unit, it's part of the name
                    measurement_found = True
                    name_parts.append(part)
        else:
            name_parts.append(part)

    quantity = ' '.join(quantity_parts)
    name = ' '.join(name_parts)

    if is_optional:
        name += ' (optional)'

    return name, quantity


def get_youtube_thumbnail(video_id):
    """Get the highest quality thumbnail URL for a YouTube video."""
    if not video_id:
        logger.error("Invalid video ID provided for thumbnail.")
        return None

    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"


def save_to_notion(recipe_data, video_url):
    """Save recipe to Notion database with metadata as properties."""
    try:
        # Parse the recipe_data
        logger.info(f"Attempting to parse recipe data: {recipe_data}")
        recipe = json.loads(recipe_data)

        if recipe.get('title') == 'NotARecipe':
            logger.info("Recipe marked as NotARecipe")
            return False

        # Get video thumbnail
        video_id = extract_video_id(video_url)
        thumbnail_url = get_youtube_thumbnail(video_id)

        logger.info(f"Creating Notion page for recipe: {recipe['title']}")

        # Create properties with metadata
        properties = {
            "Name": {
                "title": [{"text": {"content": recipe['title']}}]
            },
            "Preparation Time": {
                "rich_text": [{"text": {"content": recipe['metadata']['prep_time']}}]
            },
            "Cooking Time": {
                "rich_text": [{"text": {"content": recipe['metadata']['cook_time']}}]
            },
            "Total Time": {
                "rich_text": [{"text": {"content": recipe['metadata']['total_time']}}]
            },
            "Servings": {
                "number": int(recipe['metadata']['servings'].split()[0])
            },
            "Calories per Serving": {
                "number": recipe['metadata']['calories_per_serving']
            },
            "Protein (g)": {
                "number": float(recipe['metadata']['protein_per_serving'].split()[0])
            },
            "Carbs (g)": {
                "number": float(recipe['metadata']['carbs_per_serving'].split()[0])
            },
            "Fat (g)": {
                "number": float(recipe['metadata']['fat_per_serving'].split()[0])
            },
            "Price per Serving": {
                "rich_text": [{"text": {"content": recipe['metadata']['price_per_serving']}}]
            },
            "Source": {
                "url": video_url
            }
        }

        # Create ingredients table
        ingredients_table = {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": 2,
                "has_column_header": True,
                "has_row_header": False,
                "children": [
                    {
                        "type": "table_row",
                        "table_row": {
                            "cells": [
                                [{"type": "text", "text": {"content": "Ingredient"}}],
                                [{"type": "text", "text": {"content": "Quantity"}}]
                            ]
                        }
                    }
                ]
            }
        }

        # Add ingredients to table
        for ingredient in recipe['ingredients']:
            name, quantity = split_ingredient(ingredient)
            ingredients_table["table"]["children"].append({
                "type": "table_row",
                "table_row": {
                    "cells": [
                        [{"type": "text", "text": {"content": name}}],
                        [{"type": "text", "text": {"content": quantity}}]
                    ]
                }
            })

        # Combine all blocks with headers and dividers
        all_blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Ingredients"}}]
                }
            },
            ingredients_table,
            {
                "object": "block",
                "type": "divider",
                "divider": {}
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Instructions"}}]
                }
            }
        ]

        # Add instructions
        for instruction in recipe['instructions']:
            all_blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": instruction}}]
                }
            })

        # Create the page in Notion with properties, blocks, and cover image
        page = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties,
            children=all_blocks,
            cover={
                "type": "external",
                "external": {
                    "url": thumbnail_url
                }
            }
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

        # Save to Notion with URL
        if save_to_notion(recipe, url):
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