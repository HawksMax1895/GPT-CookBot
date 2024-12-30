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
   git clone <repository_url>
   cd <repository_name>