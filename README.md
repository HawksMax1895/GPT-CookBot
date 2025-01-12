# Recipe Bot

This Telegram bot processes YouTube cooking videos and generates recipes by leveraging the YouTube Transcript API, OpenAI's GPT-based models, and Notion API. The bot extracts the transcript from the video, processes it, and saves a structured recipe to a connected Notion database.

## Features

- **YouTube URL Parsing**: Automatically extracts the video ID from a YouTube URL.
- **Transcript Retrieval**: Fetches the video transcript using the YouTube Transcript API.
- **Recipe Generation**: Uses OpenAI's GPT model to generate a recipe based on the video transcript.
- **Structured JSON Recipes**: Outputs recipes as JSON objects, including metadata, ingredients, and instructions.
- **Notion Integration**: Saves recipes directly to a Notion database with detailed properties and a formatted structure.
- **Error Handling**: Provides user-friendly error messages for invalid URLs, missing transcripts, and non-cooking videos.
- **Logging**: Comprehensive logging for debugging and monitoring.

## Prerequisites

- Python 3.8 or later
- [Telegram Bot API Token](https://core.telegram.org/bots#botfather)
- [OpenAI API Key](https://platform.openai.com/signup/)
- [Notion API Token and Database ID](https://developers.notion.com/)
- YouTube videos must have subtitles enabled for the bot to process them.

## Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository_url>
   cd <repository_name>
   ```

2. **Install required packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a .env file in the project root with the following variables**:
   ```env
   TELEGRAM_TOKEN=<Your Telegram Bot Token>
   OPENAI_TOKEN=<Your OpenAI API Key>
   TELEGRAM_ID=<Your Telegram User ID>
   NOTION_TOKEN=<Your Notion API Key>
   NOTION_DATABASE_ID=<Your Notion Database ID>
   ```

## Usage

1. Start the bot by running:
   ```bash
   python cook_bot.py
   ```

2. Interact via Telegram:
   - Send the `/start` command to the bot.
   - Provide a YouTube cooking video link.
   - The bot will process the video, generate a recipe, and save it to your Notion database.

## Recipe Output Structure

Recipes are generated as JSON objects with the following format:
```json
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
    "price_per_serving": "€X.XX"
  },
  "ingredients": ["ingredient 1 with quantity", "ingredient 2 with quantity", ...],
  "instructions": ["step 1", "step 2", ...]
}
```

## Development Notes

- **Logging**: Logs are written to the console with INFO and ERROR levels.
- **Authentication**: Only authorized Telegram users can interact with the bot.
- **Error Handling**:
  - Invalid or non-cooking videos result in helpful feedback messages.
  - Detailed error logging is available for debugging.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
