import logging
import os
from datetime import datetime, timezone
import pytz
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from telegram.constants import ParseMode
from database import Database

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Bot token from environment variable
TOKEN = os.getenv("BOT_TOKEN", "7660169417:AAFBkJ5gFLIcXc1jxW0HyBfDGjYaDb0gaWw")

# Initialize database
db = Database()

# Conversation states
TITLE, CONTENT, TAGS = range(3)
REMINDER_TIME = range(1)

# Store admin user IDs (you can add admin IDs here)
ADMIN_IDS = []

# Basic Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    welcome_message = (
        f"👋 Hi {user.mention_html()}!\n\n"
        "I'm your multipurpose Telegram bot. Here's what I can do:\n\n"
        "🔹 Store notes and reminders\n"
        "🔹 Manage groups\n"
        "🔹 Customize your preferences\n"
        "🔹 And much more!\n\n"
        "Use /help to see all available commands."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📝 Notes", callback_data="help_notes"),
            InlineKeyboardButton("⏰ Reminders", callback_data="help_reminders")
        ],
        [
            InlineKeyboardButton("⚙️ Preferences", callback_data="help_preferences"),
            InlineKeyboardButton("ℹ️ About", callback_data="about")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(welcome_message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
*Available Commands:*

*Notes Management:*
/newnote - Create a new note
/notes - List all your notes
/note <id> - View a specific note
/searchnotes <query> - Search your notes
/deletenote <id> - Delete a note

*Reminders:*
/remind <time> <message> - Set a reminder
/reminders - List all your reminders
/deletereminder <id> - Delete a reminder

*Preferences:*
/theme - Set your theme preference
/timezone - Set your timezone
/language - Set your language
/notifications - Configure notifications

*Group Management:*
/welcome - Set welcome message
/rules - Set/view group rules
/warn - Warn a user
/unwarn - Remove warning from a user
/ban - Ban a user
/unban - Unban a user
/mute - Mute a user
/unmute - Unmute a user
/pin - Pin a message
/unpin - Unpin a message

*Utility Commands:*
/info - Get user info
/id - Get chat ID
/stats - Get chat statistics
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# Notes Management
async def new_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the conversation to create a new note."""
    await update.message.reply_text(
        "Let's create a new note! First, send me the title of your note."
    )
    return TITLE

async def get_note_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the title of the note and ask for content."""
    context.user_data['note_title'] = update.message.text
    await update.message.reply_text(
        "Great! Now send me the content of your note."
    )
    return CONTENT

async def get_note_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the content of the note and ask for tags."""
    context.user_data['note_content'] = update.message.text
    await update.message.reply_text(
        "Optional: Send me tags for your note (space-separated) or send /skip to skip."
    )
    return TAGS

async def get_note_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the note with tags."""
    if update.message.text != '/skip':
        tags = update.message.text.split()
    else:
        tags = []

    note_id = db.save_note(
        update.effective_user.id,
        update.effective_chat.id,
        context.user_data['note_title'],
        context.user_data['note_content'],
        tags
    )

    await update.message.reply_text(
        f"✅ Note saved successfully!\nYou can view it with /note {note_id}"
    )
    return ConversationHandler.END

async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all notes for the user."""
    notes = db.get_notes(update.effective_user.id)
    
    if not notes:
        await update.message.reply_text("You don't have any notes yet. Use /newnote to create one!")
        return

    response = "*Your Notes:*\n\n"
    for note in notes:
        tags = ' '.join([f'#{tag}' for tag in note['tags']]) if note['tags'] else ''
        response += f"📝 *{note['title']}* (ID: `{note['note_id']}`)\n"
        response += f"Tags: {tags}\n\n"

    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get a specific note by ID."""
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /note <note_id>")
        return

    try:
        note_id = int(context.args[0])
        notes = db.get_notes(update.effective_user.id)
        note = next((n for n in notes if n['note_id'] == note_id), None)

        if note:
            tags = ' '.join([f'#{tag}' for tag in note['tags']]) if note['tags'] else ''
            response = f"📝 *{note['title']}*\n\n{note['content']}\n\n"
            if tags:
                response += f"Tags: {tags}\n"
            response += f"Created: {note['created_at']}"
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("Note not found!")
    except ValueError:
        await update.message.reply_text("Please provide a valid note ID!")

async def search_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search notes by query."""
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /searchnotes <query>")
        return

    query = " ".join(context.args)
    notes = db.search_notes(update.effective_user.id, query)

    if not notes:
        await update.message.reply_text("No notes found matching your query!")
        return

    response = f"*Search Results for '{query}':*\n\n"
    for note in notes:
        tags = ' '.join([f'#{tag}' for tag in note['tags']]) if note['tags'] else ''
        response += f"📝 *{note['title']}* (ID: `{note['note_id']}`)\n"
        if tags:
            response += f"Tags: {tags}\n"
        response += "\n"

    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

# Reminders
async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set a reminder."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /remind <time> <message>\n"
            "Example: /remind 2h30m Buy groceries"
        )
        return

    time_str = context.args[0]
    message = " ".join(context.args[1:])
    
    try:
        # Parse time string (implement your own time parsing logic)
        remind_at = datetime.now(timezone.utc) # Add parsed time
        
        reminder_id = db.set_reminder(
            update.effective_user.id,
            update.effective_chat.id,
            message,
            remind_at.isoformat()
        )
        
        await update.message.reply_text(
            f"✅ Reminder set!\nI'll remind you about: {message}\n"
            f"At: {remind_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
    except ValueError as e:
        await update.message.reply_text(f"Error setting reminder: {str(e)}")

# User Preferences
async def set_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user theme preference."""
    keyboard = [
        [
            InlineKeyboardButton("🌞 Light", callback_data="theme_light"),
            InlineKeyboardButton("🌚 Dark", callback_data="theme_dark")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Choose your preferred theme:",
        reply_markup=reply_markup
    )

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user timezone."""
    if len(context.args) != 1:
        # Show common timezones
        common_timezones = [
            "UTC", "US/Eastern", "US/Pacific", "Europe/London",
            "Asia/Tokyo", "Australia/Sydney"
        ]
        timezone_list = "\n".join(common_timezones)
        await update.message.reply_text(
            f"Usage: /timezone <timezone>\n\nCommon timezones:\n{timezone_list}"
        )
        return

    timezone_str = context.args[0]
    try:
        # Validate timezone
        pytz.timezone(timezone_str)
        
        # Get current preferences and update timezone
        prefs = db.get_user_preference(update.effective_user.id)
        prefs['timezone'] = timezone_str
        db.set_user_preference(update.effective_user.id, prefs)
        
        await update.message.reply_text(f"✅ Timezone set to: {timezone_str}")
    except pytz.exceptions.UnknownTimeZoneError:
        await update.message.reply_text("❌ Invalid timezone! Please use a valid timezone identifier.")

# Callback Query Handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("theme_"):
        theme = query.data.split("_")[1]
        prefs = db.get_user_preference(query.from_user.id)
        prefs['theme'] = theme
        db.set_user_preference(query.from_user.id, prefs)
        await query.edit_message_text(f"✅ Theme set to: {theme}")
    elif query.data == "help_notes":
        text = """
*📝 Notes Help:*
/newnote - Create a new note
/notes - List all notes
/note <id> - View a note
/searchnotes <query> - Search notes
/deletenote <id> - Delete a note
"""
    elif query.data == "help_reminders":
        text = """
*⏰ Reminders Help:*
/remind <time> <message> - Set a reminder
/reminders - List all reminders
/deletereminder <id> - Delete a reminder
"""
    elif query.data == "help_preferences":
        text = """
*⚙️ Preferences Help:*
/theme - Set theme
/timezone - Set timezone
/language - Set language
/notifications - Configure notifications
"""
    else:
        text = "Invalid callback"
    
    if not query.data.startswith("theme_"):
        await query.edit_message_text(text=text, parse_mode=ParseMode.MARKDOWN)

# Group Management Commands
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set welcome message for the group."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ This command is only for admins!")
        return
    
    if len(context.args) == 0:
        current_msg = db.get_welcome_message(update.effective_chat.id)
        if current_msg:
            await update.message.reply_text(f"Current welcome message:\n\n{current_msg}\n\nUse /welcome <message> to change it.")
        else:
            await update.message.reply_text("No welcome message set. Use /welcome <message> to set one.")
        return
        
    welcome_msg = " ".join(context.args)
    db.set_welcome_message(update.effective_chat.id, welcome_msg)
    await update.message.reply_text(f"✅ Welcome message has been set to:\n\n{welcome_msg}")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set or view group rules."""
    if len(context.args) == 0:
        rules_text = db.get_rules(update.effective_chat.id) or "No rules set for this group yet."
        await update.message.reply_text(rules_text)
    else:
        if not await is_admin(update, context):
            await update.message.reply_text("❌ Only admins can set rules!")
            return
        rules_text = " ".join(context.args)
        db.set_rules(update.effective_chat.id, rules_text)
        await update.message.reply_text(f"✅ Rules have been updated to:\n\n{rules_text}")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn a user."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can warn users!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a message to warn the user!")
        return

    user = update.message.reply_to_message.from_user
    warnings = db.add_warning(user.id)
    
    warn_text = f"⚠️ {user.mention_html()} has been warned.\nTotal warnings: {warnings}/3"
    if warnings >= 3:
        # Ban user after 3 warnings
        await ban_user(update, context, user.id)
        warn_text += "\n\n❌ User has been banned due to exceeding warning limit!"
    
    await update.message.reply_html(warn_text)

async def unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a warning from a user."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can remove warnings!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a message to remove warning from the user!")
        return

    user = update.message.reply_to_message.from_user
    warnings = db.remove_warning(user.id)
    await update.message.reply_html(
        f"✅ Removed a warning from {user.mention_html()}\nCurrent warnings: {warnings}/3"
    )

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    """Ban a user from the group."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can ban users!")
        return

    if user_id is None:
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Reply to a message to ban the user!")
            return
        user_id = update.message.reply_to_message.from_user.id

    try:
        db.set_ban_status(user_id, True)
        await context.bot.ban_chat_member(update.effective_chat.id, user_id)
        user = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        await update.message.reply_html(f"🚫 {user.user.mention_html()} has been banned!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to ban user: {str(e)}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user from the group."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can unban users!")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Please provide the user ID to unban!")
        return

    try:
        user_id = int(context.args[0])
        db.set_ban_status(user_id, False)
        await context.bot.unban_chat_member(update.effective_chat.id, user_id)
        await update.message.reply_text(f"✅ User {user_id} has been unbanned!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to unban user: {str(e)}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a user in the group."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can mute users!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a message to mute the user!")
        return

    user = update.message.reply_to_message.from_user
    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False
    )

    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions)
        await update.message.reply_html(f"🤐 {user.mention_html()} has been muted!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to mute user: {str(e)}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unmute a user in the group."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can unmute users!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a message to unmute the user!")
        return

    user = update.message.reply_to_message.from_user
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )

    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions)
        await update.message.reply_html(f"🔊 {user.mention_html()} has been unmuted!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to unmute user: {str(e)}")

async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pin a message in the group."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can pin messages!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a message to pin it!")
        return

    try:
        await context.bot.pin_chat_message(
            update.effective_chat.id,
            update.message.reply_to_message.message_id
        )
        await update.message.reply_text("📌 Message pinned successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to pin message: {str(e)}")

async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unpin a message in the group."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can unpin messages!")
        return

    try:
        await context.bot.unpin_chat_message(update.effective_chat.id)
        await update.message.reply_text("📌 Message unpinned successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to unpin message: {str(e)}")

async def get_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get information about a user."""
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    stats = db.get_user_stats(user.id)
    
    info_text = f"""
*User Information:*
🆔 ID: `{user.id}`
👤 Name: {user.full_name}
🔰 Username: @{user.username if user.username else 'None'}
⚠️ Warnings: {stats['warnings']}/3
🚫 Banned: {'Yes' if stats['is_banned'] else 'No'}
📅 Join Date: {stats['join_date'] if stats['join_date'] else 'Unknown'}
"""
    await update.message.reply_text(info_text, parse_mode=ParseMode.MARKDOWN)

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome new members to the group."""
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.message.reply_text("👋 Thanks for adding me to the group! Use /help to see available commands.")
            continue
            
        welcome_msg = db.get_welcome_message(update.effective_chat.id)
        if welcome_msg:
            await update.message.reply_text(
                welcome_msg.format(
                    user=member.mention_html(),
                    group=update.effective_chat.title
                ),
                parse_mode=ParseMode.HTML
            )

# Admin Utilities
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the user is an admin."""
    user_id = update.effective_user.id
    if user_id in ADMIN_IDS:
        return True
    
    chat_id = update.effective_chat.id
    user = await context.bot.get_chat_member(chat_id, user_id)
    return user.status in ["creator", "administrator"]

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add conversation handlers
    note_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("newnote", new_note)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_note_title)],
            CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_note_content)],
            TAGS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_note_tags),
                CommandHandler("skip", get_note_tags)
            ],
        },
        fallbacks=[],
    )
    application.add_handler(note_conv_handler)

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("notes", list_notes))
    application.add_handler(CommandHandler("note", get_note))
    application.add_handler(CommandHandler("searchnotes", search_notes))
    application.add_handler(CommandHandler("remind", set_reminder))
    application.add_handler(CommandHandler("theme", set_theme))
    application.add_handler(CommandHandler("timezone", set_timezone))
    
    # Add existing handlers
    application.add_handler(CommandHandler("welcome", welcome))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("warn", warn_user))
    application.add_handler(CommandHandler("unwarn", unwarn_user))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("mute", mute_user))
    application.add_handler(CommandHandler("unmute", unmute_user))
    application.add_handler(CommandHandler("pin", pin_message))
    application.add_handler(CommandHandler("unpin", unpin_message))
    application.add_handler(CommandHandler("info", get_user_info))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start the bot
    print("✨ Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 