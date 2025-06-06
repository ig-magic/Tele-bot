# Telegram Bot

A feature-rich Telegram bot with group management, notes, reminders, and more.

## Features

- Notes Management
- Reminders System
- Group Management
- User Preferences
- And more!

## Deployment on Render

1. Create a free account on [Render](https://render.com)

2. Click on "New +" and select "Web Service"

3. Connect your GitHub repository

4. Fill in the following details:
   - Name: your-bot-name
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`

5. Add Environment Variable:
   - Key: `BOT_TOKEN`
   - Value: Your Telegram Bot Token

6. Click "Create Web Service"

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the bot:
```bash
python bot.py
```

## Environment Variables

Create a `.env` file with:
```
BOT_TOKEN=your_bot_token_here
```

## Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/newnote` - Create a new note
- `/notes` - List all notes
- `/remind` - Set a reminder
- `/theme` - Set theme preference
- `/timezone` - Set timezone 