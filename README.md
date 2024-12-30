# Recipe Bot


This Telegram bot processes YouTube cooking videos and generates recipes by using the YouTube Transcript API and OpenAI's GPT-based completion models. The bot extracts the transcript from the video, processes it, and outputs a structured recipe.


## Features

- **YouTube URL Parsing**: Automatically extracts the video ID from a YouTube URL.
- **Transcript Retrieval**: Fetches the video transcript using the YouTube Transcript API.
- **Recipe Generation**: Uses OpenAI to generate a recipe based on the video transcript.
- **File Output**: Saves the generated recipe to a `.txt` file and sends it back via Telegram.
- **Error Handling**: Provides user-friendly error messages for invalid URLs, missing transcripts, and non-cooking videos.


## Prerequisites

- Python 3.8 or later
- [Telegram Bot API Token](https://core.telegram.org/bots#botfather)
- [OpenAI API Key](https://platform.openai.com/signup/)
- YouTube videos must have subtitles enabled for the bot to process them.


## Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository_url>
   cd <repository_name>
2. **Install required packages**:
    ```bash
    pip install requirements.txt
3. **Create a .env file in the project root with the following variables**:
    ```bash
    TELEGRAM_TOKEN=<Your Telegram Bot Token>
    OPENAI_TOKEN=<Your OpenAI API Key>
    TELEGRAM_ID=<Your Telegram User ID>

## Usage

1. Start the bot by running:
    ```bash
    python <filename>.py

2. Interact via Telegram:
   - Send the /start command to the bot.
   - Provide a YouTube cooking video link.
   - The bot will process the video and send you a .txt file with the recipe.


## Development Notes

- Logging: Logs are written to the console with INFO and ERROR levels for debugging.
- Error Handling: The bot ensures:
    - Only authorized users can interact with it.
    - Invalid or non-cooking videos result in helpful feedback messages.
- OpenAI Usage: The gpt-4o-mini model is used for recipe generation, and its prompts are specifically tailored to generate structured recipes.


## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.


## License

This project is licensed under the MIT License. See the LICENSE file for details.