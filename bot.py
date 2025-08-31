from keep_alive import keep_alive
import logging
import json
import os
import time
from datetime import datetime, timedelta, time as dt_time
from random import uniform, choice
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand, BotCommandScopeChat
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest, Forbidden
import asyncio
from typing import Dict, Any

# --- CONFIGURATION ---
BOT_TOKEN = "8310636090:AAFcFbpeCH-fqm0pNzAi7Ng1hWDw7wF72Xs"  # Replace with your bot token
ADMIN_ID = 7258860451  # Change this to your Telegram User ID
MIN_WITHDRAWAL = 500.0
MIN_REWARD = 0.1
MAX_REWARD = 2.0
REFERRAL_BONUS = 1.0
USERS_FILE = 'users.json'
WITHDRAWALS_FILE = 'withdrawals.json'
TASKS_FILE = 'tasks.json'
BACKUP_INTERVAL = 3600  # Backup every hour

# --- UI & ANIMATION SETTINGS ---
EMOJIS = {
    'money': '💰', 'gift': '🎁', 'rocket': '🚀', 'star': '⭐', 'fire': '🔥',
    'diamond': '💎', 'crown': '👑', 'trophy': '🏆', 'party': '🎉', 'cash': '💵',
    'bank': '🏦', 'coin': '🪙', 'gem': '💠', 'magic': '✨', 'lightning': '⚡',
    'clock': '⏰', 'success': '✅', 'error': '❌', 'notify': '🔔'
}

TYPING_DELAY = 0.5    # Seconds to show typing indicator
LOADING_DURATION = 1.8 # How long the loading animation should run before resolving

# Titles for the new stylish loading animation
LOADING_TITLES = {
    'start': '✦ ACCOUNT SETUP ✦',
    'claim': '✦ DAILY GIFT SCANNER ✦',
    'wallet': '✦ VAULT ACCESS ✦',
    'withdraw': '✦ WITHDRAWAL PROCESSOR ✦',
    'stats': '✦ STATS ANALYZER ✦',
    'upi': '✦ UPI VALIDATOR ✦',
    'refer': '✦ LINK GENERATOR ✦',
    'help': '✦ GUIDE COMPILER ✦',
    'tasks': '✦ TASK FETCHER ✦',
    'verify': '✦ MEMBERSHIP VERIFIER ✦',
    'admin': '✦ ADMIN DASHBOARD ✦',
    'admin_stats': '✦ STATS COMPILER ✦',
    'admin_tools': '✦ SYSTEM TOOLS ✦',
    'admin_users': '✦ USER DATABASE ✦',
    'admin_withdrawals': '✦ PAYMENT LEDGER ✦',
    'admin_broadcast': '✦ BROADCAST PREPARATION ✦',
    'admin_task_create': '✦ TASK VERIFICATION ✦',
    'admin_task_clean': '✦ DATABASE CLEANUP ✦',
    'admin_task_remove': '✦ TASK DATABASE ✦',
    'admin_backup': '✦ SECURE BACKUP ✦',
    'admin_export': '✦ DATA EXPORT ✦',
    'admin_health': '✦ SYSTEM DIAGNOSTICS ✦'
}


# --- MOTIVATIONAL QUOTES ---
QUOTES = [
    "💎 Every small step leads to big rewards!",
    "🚀 Your earning journey starts with a single tap!",
    "⭐ Success is the sum of small efforts repeated daily!",
    "🔥 Fortune favors the persistent!",
    "✨ Great things never come from comfort zones!",
    "💰 The secret of getting ahead is getting started!",
    "🏆 Champions keep playing until they get it right!",
    "⚡ Your potential is endless!"
]

# --- STREAK BONUSES ---
# These are extra amounts added to the daily bonus
STREAK_REWARDS = {
    3: 1.0,
    7: 2.0,
    30: 5.0,
    100: 10.0
}

# --- LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# --- COOL & ATTRACTIVE ANIMATION FUNCTIONS ---

async def show_typing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows typing indicator for a more interactive experience."""
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING
        )
        await asyncio.sleep(TYPING_DELAY)
    except Exception as e:
        logger.debug(f"Typing indicator error: {e}")

async def show_stylish_loading_animation(update: Update, context: ContextTypes.DEFAULT_TYPE, title: str = "✦ PROCESSING ✦"):
    """Shows a stylish loading animation with a progress bar and more emojis."""
    try:
        chat_id = update.effective_chat.id
        
        initial_text = f"╭─✨ P L E A S E  W A I T ✨─╮\n│\n  {title}\n│\n  ⏳ Loading...\n│  [░░░░░░░░░░] 0%\n│\n╰─✨──────────────────✨─╯"
        sent_message = await context.bot.send_message(chat_id, initial_text)
        
        start_time = time.time()
        last_text = initial_text
        
        while time.time() - start_time < LOADING_DURATION:
            progress_fraction = (time.time() - start_time) / LOADING_DURATION
            progress_percent = min(100, int(progress_fraction * 100))
            
            filled_blocks = int(progress_fraction * 10)
            empty_blocks = 10 - filled_blocks
            progress_bar = '▓' * filled_blocks + '░' * empty_blocks
            
            # Dynamic emoji and status message
            if progress_percent < 33:
                progress_emoji = "⏳"
                status_message = "Initializing..."
            elif progress_percent < 66:
                progress_emoji = "⚙️"
                status_message = "Working on it..."
            else:
                progress_emoji = "🚀"
                status_message = "Almost there..."


            animation_text = (
                f"╭─✨ P L E A S E  W A I T ✨─╮\n"
                f"│\n"
                f"  {title}\n"
                f"│\n"
                f"  {progress_emoji} {status_message}\n"
                f"│  [{progress_bar}] {progress_percent}%\n"
                f"│\n"
                f"╰─✨──────────────────✨─╯"
            )

            if animation_text != last_text:
                try:
                    await context.bot.edit_message_text(
                        animation_text,
                        chat_id=chat_id,
                        message_id=sent_message.message_id
                    )
                    last_text = animation_text
                except BadRequest as e:
                    if 'message is not modified' not in str(e).lower():
                        logger.warning(f"Error editing stylish loading animation: {e}")
                    pass
            
            await asyncio.sleep(0.15)

        # Final state
        final_text = (
            f"╭──🎉 C O M P L E T E 🎉──╮\n"
            f"│\n"
            f"  {title}\n"
            f"│\n"
            f"  ✅ Ready to proceed!\n"
            f"│  [▓▓▓▓▓▓▓▓▓▓] 100%\n"
            f"│\n"
            f"╰──🎉─────────────🎉──╯"
        )
        await context.bot.edit_message_text(
            final_text,
            chat_id=chat_id,
            message_id=sent_message.message_id
        )
        await asyncio.sleep(0.3) # Short pause on complete
        
        return sent_message
    except Exception as e:
        logger.debug(f"Stylish loading animation error: {e}")
        return await context.bot.send_message(chat_id, f"Processing: {title}...")


async def show_success_animation(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, original_message_id: int = None):
    """Shows an attractive success animation with a burst effect."""
    try:
        chat_id = update.effective_chat.id
        
        if original_message_id:
            animation_steps = ["✨", "💫", "🌟", f"🎉 *Success!* 🎉"]
            for step in animation_steps:
                try:
                    await context.bot.edit_message_text(step, chat_id=chat_id, message_id=original_message_id, parse_mode=ParseMode.MARKDOWN)
                except BadRequest: pass
                await asyncio.sleep(0.25)
            
            await context.bot.edit_message_text(
                f"{EMOJIS['success']} *Success!*\n\n{message}",
                chat_id=chat_id,
                message_id=original_message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(chat_id, f"{EMOJIS['success']} *Success!*\n\n{message}", parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        logger.debug(f"Success animation error: {e}")
        await safe_send_message(update, context, f"{EMOJIS['success']} {message}", parse_mode=ParseMode.MARKDOWN)

async def show_error_animation(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, original_message_id: int = None):
    """Shows an attractive error animation."""
    try:
        chat_id = update.effective_chat.id
        
        if original_message_id:
            animation_steps = ["🤔", "😥", "⚠️", f"❌ *Error!* ❌"]
            for step in animation_steps:
                try:
                    await context.bot.edit_message_text(step, chat_id=chat_id, message_id=original_message_id, parse_mode=ParseMode.MARKDOWN)
                except BadRequest: pass
                await asyncio.sleep(0.25)

            await context.bot.edit_message_text(
                f"{EMOJIS['error']} *Error!*\n\n{message}",
                chat_id=chat_id,
                message_id=original_message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(chat_id, f"{EMOJIS['error']} *Error!*\n\n{message}", parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.debug(f"Error animation error: {e}")
        await safe_send_message(update, context, f"{EMOJIS['error']} {message}", parse_mode=ParseMode.MARKDOWN)

# --- ENHANCED DATA HANDLING ---
def load_data(filepath: str) -> Dict[str, Any]:
    """Safely loads data from a JSON file with backup recovery."""
    if not os.path.exists(filepath):
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
        logger.error(f"Error loading {filepath}: {e}")
        backup_file = f"{filepath}.backup"
        if os.path.exists(backup_file):
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    logger.info(f"Loading backup for {filepath}")
                    return json.load(f)
            except Exception as backup_e:
                logger.error(f"Backup also failed for {filepath}: {backup_e}")
        return {}

def save_data(data: Dict[str, Any], filepath: str) -> bool:
    """Safely saves data with backup creation and validation."""
    try:
        if os.path.exists(filepath):
            backup_file = f"{filepath}.backup"
            try:
                with open(filepath, 'r', encoding='utf-8') as src, open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            except Exception as e:
                logger.warning(f"Failed to create backup for {filepath}: {e}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        
        return True
    except Exception as e:
        logger.error(f"Critical error saving {filepath}: {e}")
        return False

# --- CONVERSATION STATES ---
LINK_UPI, BROADCAST_MESSAGE, ASK_CHANNEL, ASK_REWARD, ASK_EXPIRY, BROADCAST_PHOTO = range(6)

# --- UTILITY FUNCTIONS ---
def get_user_id(update: Update) -> str:
    """Safely extracts user ID from update."""
    try:
        return str(update.effective_user.id)
    except AttributeError:
        logger.error("Failed to get user ID from update")
        return "unknown"

def escape_markdown(text: str) -> str:
    """Enhanced markdown escaping for Telegram."""
    if not text or not isinstance(text, str):
        return "N/A"
    escape_chars = ['_', '*', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_number(number: float, decimals: int = 2) -> str:
    """Formats numbers with proper decimal places."""
    return f"{number:.{decimals}f}"

def get_level_info(balance: float) -> Dict[str, Any]:
    """Returns user level information based on balance."""
    levels = [
        {"name": "Starter", "min": 0, "emoji": "🌱"},
        {"name": "Bronze", "min": 100, "emoji": "🥉"},
        {"name": "Silver", "min": 500, "emoji": "🥈"},
        {"name": "Gold", "min": 1000, "emoji": "🥇"},
        {"name": "Platinum", "min": 2500, "emoji": "💎"},
        {"name": "Diamond", "min": 5000, "emoji": "👑"}
    ]
    current_level = levels[0]
    for level in levels:
        if balance >= level["min"]:
            current_level = level
        else:
            break
    return current_level

async def safe_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            text: str, fallback_text: str = "Service error",
                            force_new: bool = False,
                            **kwargs) -> bool:
    """Safely sends messages with comprehensive error handling."""
    chat_id = update.effective_chat.id
    try:
        await show_typing(update, context)
        if update.callback_query and not force_new:
            await update.callback_query.edit_message_text(text, **kwargs)
        elif chat_id:
            await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        else:
            logger.warning("Could not determine chat_id to send message.")
            return False
        return True
    except Forbidden:
        logger.warning(f"User {get_user_id(update)} blocked the bot")
        return False
    except BadRequest as e:
        if 'message is not modified' in str(e).lower():
            return True
        logger.warning(f"Bad request for user {get_user_id(update)}: {e}")
        try:
            if chat_id:
                await context.bot.send_message(chat_id=chat_id, text=fallback_text)
        except Exception as fallback_e:
            logger.error(f"Failed to send fallback message: {fallback_e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in safe_send_message: {e}")
        return False

# --- ENHANCED USER COMMANDS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced start command with better UI and error handling."""
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['start'])
        
        user = update.effective_user
        if not user:
            await show_error_animation(update, context, "Unable to identify user. Please try again.", loading_msg.message_id if loading_msg else None)
            return
            
        user_id = str(user.id)
        users_data = load_data(USERS_FILE)
        is_new_user = user_id not in users_data

        if is_new_user:
            users_data[user_id] = {
                'balance': 0.0,
                'coin_balance': 0,
                'last_claim': None,
                'upi': None,
                'username': user.username or "User",
                'first_name': user.first_name or "Friend",
                'referrals': 0,
                'completed_tasks': [],
                'join_date': datetime.now().isoformat(),
                'streak_count': 0,
                'total_earned': 0.0,
                'notifications_enabled': True,
                'level': "Starter"
            }
            
            if context.args:
                referrer_id = context.args[0]
                if referrer_id in users_data and referrer_id != user_id:
                    users_data[user_id]['balance'] += REFERRAL_BONUS
                    users_data[user_id]['total_earned'] += REFERRAL_BONUS
                    
                    users_data[referrer_id]['balance'] += REFERRAL_BONUS
                    users_data[referrer_id]['total_earned'] += REFERRAL_BONUS
                    users_data[referrer_id]['referrals'] += 1
                    
                    welcome_msg = (
                        f"🎊 *WELCOME ABOARD!* 🎊\n\n"
                        f"🎁 You've joined through a friend's link!\n"
                        f"💰 Starting bonus: *₹{REFERRAL_BONUS:.2f}*\n"
                        f"🚀 Ready to start earning more?"
                    )
                    
                    if loading_msg:
                        await show_success_animation(update, context, welcome_msg, loading_msg.message_id)
                    else:
                        await safe_send_message(update, context, welcome_msg, parse_mode=ParseMode.MARKDOWN)
                    
                    try:
                        referrer_name = escape_markdown(user.first_name or "Someone")
                        referrer_msg = (
                            f"🤝 *REFERRAL SUCCESS!* 🤝\n\n"
                            f"👤 {referrer_name} joined using your link!\n"
                            f"💰 You both earned *₹{REFERRAL_BONUS:.2f}*!\n"
                            f"📈 Total referrals: *{users_data[referrer_id]['referrals']}*"
                        )
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=referrer_msg,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.warning(f"Failed to notify referrer {referrer_id}: {e}")
            
            save_data(users_data, USERS_FILE)

        user_data = users_data.get(user_id, {})
        level_info = get_level_info(user_data.get('balance', 0))
        
        first_name = user.first_name or "Friend"
        if is_new_user and not context.args:
             welcome_text = (
                f"🌟 *Welcome to EarnBot, {first_name}!* 🌟\n\n"
                f"🎯 Your earning adventure begins now!\n"
                f"🏅 Current Level: {level_info['emoji']} *{level_info['name']}*\n\n"
                f"💡 *Quick Start:*\n"
                f"• 🎁 Claim your daily bonus\n"
                f"• ✨ Complete simple tasks\n"
                f"• 💌 Invite friends for bigger rewards\n\n"
                f"*{choice(QUOTES)}*"
            )
             if loading_msg:
                 await show_success_animation(update, context, welcome_text, loading_msg.message_id)
             else:
                 await safe_send_message(update, context, welcome_text, parse_mode=ParseMode.MARKDOWN)
        elif not is_new_user:
            welcome_text = (
                f"👋 *Welcome back, {first_name}!*\n\n"
                f"🏅 Level: {level_info['emoji']} *{level_info['name']}*\n"
                f"💰 Balance: *₹{user_data.get('balance', 0):.2f}*\n"
                f"🪙 Coins: *{user_data.get('coin_balance', 0)}*\n\n"
                f"*{choice(QUOTES)}*"
            )
            if loading_msg:
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
                except Exception:
                    pass
            await safe_send_message(update, context, welcome_text, parse_mode=ParseMode.MARKDOWN)

        keyboard = [
            [f"{EMOJIS['gift']} Daily Bonus", f"{EMOJIS['magic']} Tasks"],
            [f"{EMOJIS['bank']} My Vault", f"{EMOJIS['cash']} Withdraw"],
            [f"{EMOJIS['rocket']} Invite Friends", f"{EMOJIS['diamond']} Set UPI"],
            ["📊 My Stats", f"{EMOJIS['notify']} Notifications"],
            ["❓ Help & Guide"]
        ]
        
        if user_id == str(ADMIN_ID):
            keyboard.append([f"{EMOJIS['crown']} Admin Panel"])

        reply_markup = ReplyKeyboardMarkup(
            keyboard, 
            resize_keyboard=True, 
            input_field_placeholder="Choose your action..."
        )
        
        await safe_send_message(
            update, context,
            f"{EMOJIS['lightning']} *MAIN MENU* {EMOJIS['lightning']}", 
            reply_markup=reply_markup, 
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await show_error_animation(
            update, context, 
            "Something went wrong! Please try /start again.", 
            None
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced message handler with better error handling."""
    try:
        text = update.message.text
        user_id = get_user_id(update)

        action_map = {
            f"{EMOJIS['gift']} Daily Bonus": claim_reward,
            f"{EMOJIS['magic']} Tasks": show_tasks,
            f"{EMOJIS['bank']} My Vault": my_wallet,
            f"{EMOJIS['cash']} Withdraw": withdraw,
            f"{EMOJIS['rocket']} Invite Friends": refer_command,
            f"{EMOJIS['diamond']} Set UPI": link_upi_start,
            "📊 My Stats": show_user_stats,
            f"{EMOJIS['notify']} Notifications": notifications_menu,
            "❓ Help & Guide": help_command
        }

        if text in action_map:
            await show_typing(update, context)
            await action_map[text](update, context)
        elif text == f"{EMOJIS['crown']} Admin Panel" and user_id == str(ADMIN_ID):
            await show_typing(update, context)
            await admin_command(update, context)
        else:
            await safe_send_message(
                update, context,
                "🤔 I don't recognize that option. Please use the menu buttons below! 👇",
                "Please use the menu options."
            )

    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await show_error_animation(
            update, context,
            "Something went wrong! Please try again.",
            None
        )

async def notifications_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows notification settings menu."""
    user_id = get_user_id(update)
    users_data = load_data(USERS_FILE)
    user_data = users_data.get(user_id)

    if not user_data:
        await start_command(update, context)
        return

    is_enabled = user_data.get('notifications_enabled', True)

    if is_enabled:
        status_emoji = "✅"
        status_text = "Enabled"
        button_emoji = "🔕"
        button_text = "Disable Notifications"
        explanation = "You will receive daily reminders to claim your bonus."
    else:
        status_emoji = "❌"
        status_text = "Disabled"
        button_emoji = "🔔"
        button_text = "Enable Notifications"
        explanation = "You will not receive any daily reminders."

    menu_text = (
        f"🔔 *Notification Settings*\n\n"
        f"Current Status: *{status_text} {status_emoji}*\n\n"
        f"_{explanation}_"
    )

    keyboard = [
        [InlineKeyboardButton(f"{button_emoji} {button_text}", callback_data="toggle_notifications")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text=menu_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        except BadRequest as e:
            if 'message is not modified' not in str(e).lower():
                logger.warning(f"Error editing notifications menu: {e}")
    else:
        await safe_send_message(
            update, context,
            text=menu_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

async def toggle_notifications_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggles the user's notification setting."""
    query = update.callback_query
    await query.answer()

    user_id = get_user_id(update)
    users_data = load_data(USERS_FILE)
    
    if user_id in users_data:
        current_status = users_data[user_id].get('notifications_enabled', True)
        users_data[user_id]['notifications_enabled'] = not current_status
        save_data(users_data, USERS_FILE)
        await notifications_menu(update, context)
    else:
        await query.edit_message_text("Could not find your data. Please use /start again.")

async def claim_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced daily reward system with updated streaks and bonuses."""
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['claim'])
        
        user_id = get_user_id(update)
        users_data = load_data(USERS_FILE)
        user = users_data.get(user_id)

        if not user:
            if loading_msg:
                await show_error_animation(update, context, "User data not found. Starting setup...", loading_msg.message_id)
            await start_command(update, context)
            return

        now = datetime.now()
        last_claim_str = user.get('last_claim')

        if last_claim_str:
            last_claim_time = datetime.fromisoformat(last_claim_str)
            time_since_last_claim = now - last_claim_time
            
            if time_since_last_claim < timedelta(hours=24):
                time_left = timedelta(hours=24) - time_since_last_claim
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                next_claim_msg = f"⏳ Next bonus is ready in *{hours}h {minutes}m*."
                if loading_msg:
                    await show_error_animation(update, context, next_claim_msg, loading_msg.message_id)
                return
            
            if time_since_last_claim <= timedelta(hours=48):
                user['streak_count'] = user.get('streak_count', 0) + 1
            else:
                user['streak_count'] = 1
        else:
            user['streak_count'] = 1

        base_reward = round(uniform(MIN_REWARD, MAX_REWARD), 2)
        streak_bonus = 0.0
        streak_count = user.get('streak_count', 1)
        
        sorted_streaks = sorted(STREAK_REWARDS.keys())
        for days in sorted_streaks:
            if streak_count >= days:
                streak_bonus = STREAK_REWARDS[days]

        total_reward = base_reward + streak_bonus
        
        user['balance'] += total_reward
        user['total_earned'] = user.get('total_earned', 0) + total_reward
        user['last_claim'] = now.isoformat()
        save_data(users_data, USERS_FILE)

        level_info = get_level_info(user['balance'])
        reward_msg = f"💰 Base Reward: *₹{format_number(base_reward)}*\n"
        
        if streak_bonus > 0:
            reward_msg += f"🔥 Streak Bonus: *+₹{format_number(streak_bonus)}* extra!\n"
        
        reward_msg += (
            f"💎 Total Earned: *₹{format_number(total_reward)}*\n"
            f"📊 New Balance: *₹{format_number(user['balance'])}*\n"
            f"⚡ Current Streak: *{streak_count} days*\n"
            f"🏅 Level: {level_info['emoji']} *{level_info['name']}*"
        )
        
        next_milestone_day = None
        for days in sorted_streaks:
            if streak_count < days:
                next_milestone_day = days
                break
        
        if next_milestone_day:
            days_to_go = next_milestone_day - streak_count
            next_bonus = STREAK_REWARDS[next_milestone_day]
            reward_msg += f"\n\n🎯 *Next streak bonus in {days_to_go} day(s): ₹{format_number(next_bonus)} extra!*"

        if loading_msg:
            await show_success_animation(update, context, reward_msg, loading_msg.message_id)

    except Exception as e:
        logger.error(f"Error in claim_reward: {e}")
        await show_error_animation(update, context, "Unable to process your bonus right now.", None)

async def my_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['wallet'])
        
        user_id = get_user_id(update)
        users_data = load_data(USERS_FILE)
        user = users_data.get(user_id)

        if not user:
            if loading_msg:
                await show_error_animation(update, context, "User data not found. Starting setup...", loading_msg.message_id)
            await start_command(update, context)
            return

        balance = user.get('balance', 0.0)
        coin_balance = user.get('coin_balance', 0)
        upi = user.get('upi', "Not Set")
        total_earned = user.get('total_earned', 0.0)
        referrals = user.get('referrals', 0)
        streak = user.get('streak_count', 0)
        
        level_info = get_level_info(balance)
        
        levels = [0, 100, 500, 1000, 2500, 5000]
        current_level_min = level_info['min']
        next_level_target = None
        for level_min in levels:
            if level_min > current_level_min:
                next_level_target = level_min
                break
        
        progress_bar = ""
        if next_level_target:
            progress = min(100, int((balance / next_level_target) * 100))
            filled = progress // 10
            empty = 10 - filled
            progress_bar = f"{'█' * filled}{'░' * empty} {progress}%"
        
        wallet_msg = (
            f"🏦 *YOUR DIGITAL VAULT* 🏦\n\n"
            f"💰 *Cash Balance:* ₹{format_number(balance)}\n"
            f"🪙 *Coin Balance:* {coin_balance:,}\n"
            f"📊 *Total Earned:* ₹{format_number(total_earned)}\n"
            f"🔥 *Current Streak:* {streak} days\n"
            f"👥 *Referrals:* {referrals}\n\n"
            f"🏅 *Current Level:* {level_info['emoji']} {level_info['name']}\n"
        )
        
        if progress_bar:
            wallet_msg += f"📈 *Next Level Progress:*\n`{progress_bar}`\n\n"
        
        wallet_msg += f"💳 *UPI ID:* `{upi}`"
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJIS['gift']} Claim Daily", callback_data="quick_claim")],
            [InlineKeyboardButton(f"{EMOJIS['cash']} Withdraw", callback_data="quick_withdraw")]
        ]
        
        if balance < MIN_WITHDRAWAL:
            needed = MIN_WITHDRAWAL - balance
            wallet_msg += f"\n\n💡 *Need ₹{format_number(needed)} more to withdraw!*"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if loading_msg:
            try:
                await context.bot.edit_message_text(
                    wallet_msg,
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await safe_send_message(
                    update, context, wallet_msg, 
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await safe_send_message(
                update, context, wallet_msg, 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error in my_wallet: {e}")
        await show_error_animation(
            update, context,
            "Unable to load wallet. Please try again!",
            None
        )

async def show_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['stats'])
        
        user_id = get_user_id(update)
        users_data = load_data(USERS_FILE)
        user = users_data.get(user_id)

        if not user:
            if loading_msg:
                await show_error_animation(update, context, "User data not found. Starting setup...", loading_msg.message_id)
            await start_command(update, context)
            return

        join_date = user.get('join_date')
        days_active = 0
        if join_date:
            join_datetime = datetime.fromisoformat(join_date)
            days_active = (datetime.now() - join_datetime).days + 1

        completed_tasks = len(user.get('completed_tasks', []))
        total_earned = user.get('total_earned', 0.0)
        referrals = user.get('referrals', 0)
        level_info = get_level_info(user.get('balance', 0))
        
        stats_msg = (
            f"📊 *YOUR EARNING STATS* 📊\n\n"
            f"📅 *Days Active:* {days_active}\n"
            f"💰 *Total Earned:* ₹{format_number(total_earned)}\n"
            f"✅ *Tasks Completed:* {completed_tasks}\n"
            f"👥 *Friends Referred:* {referrals}\n"
            f"🔥 *Best Streak:* {user.get('streak_count', 0)} days\n"
            f"🏅 *Current Level:* {level_info['emoji']} {level_info['name']}\n\n"
            f"📈 *Earnings Breakdown:*\n"
            f"• Daily bonuses & streaks\n"
            f"• Task completions\n"
            f"• Referral bonuses\n\n"
            f"🎯 *Keep earning to unlock higher levels!*"
        )
        
        if loading_msg:
            await show_success_animation(update, context, stats_msg, loading_msg.message_id)
        else:
            await safe_send_message(update, context, stats_msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in show_user_stats: {e}")
        await show_error_animation(
            update, context,
            "Unable to load stats. Please try again!",
            None
        )

async def link_upi_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = get_user_id(update)
        users_data = load_data(USERS_FILE)
        user = users_data.get(user_id)
        
        current_upi = user.get('upi', 'None') if user else 'None'
        
        upi_msg = (
            f"💳 *UPI SETUP* 💳\n\n"
            f"Current UPI: `{current_upi}`\n\n"
            f"📝 Send your UPI ID to link it:\n"
            f"💡 *Examples:*\n"
            f"• `username@oksbi`\n"
            f"• `9876543210@paytm`\n"
            f"• `user@phonepe`\n\n"
            f"❗ *Important:* Make sure it's correct!\n"
            f"Type /cancel to abort."
        )
        
        await safe_send_message(
            update, context, upi_msg,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
            force_new=True 
        )
        return LINK_UPI

    except Exception as e:
        logger.error(f"Error in link_upi_start: {e}")
        await show_error_animation(update, context, "UPI setup failed. Please try again!")
        return ConversationHandler.END

async def link_upi_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['upi'])
        
        user_id = get_user_id(update)
        upi_address = update.message.text.strip()

        if '@' not in upi_address or len(upi_address.split('@')) != 2:
            error_msg = (
                f"❌ *Invalid UPI Format!*\n\n"
                f"✅ Correct format: `username@bank`\n"
                f"💡 Examples:\n"
                f"• `yourname@oksbi`\n"
                f"• `9876543210@paytm`\n\n"
                f"Please try again:"
            )
            
            if loading_msg:
                await show_error_animation(update, context, error_msg, loading_msg.message_id)
            else:
                await safe_send_message(update, context, error_msg, parse_mode=ParseMode.MARKDOWN)
            return LINK_UPI

        users_data = load_data(USERS_FILE)
        if user_id in users_data:
            old_upi = users_data[user_id].get('upi', 'None')
            users_data[user_id]['upi'] = upi_address
            
            if save_data(users_data, USERS_FILE):
                success_msg = (
                    f"✅ *UPI Successfully Updated!* ✅\n\n"
                    f"Previous: `{old_upi}`\n"
                    f"New UPI: `{upi_address}`\n\n"
                    f"🎉 You can now withdraw funds when you reach ₹{MIN_WITHDRAWAL:.0f}!"
                )
                
                if loading_msg:
                    await show_success_animation(update, context, success_msg, loading_msg.message_id)
                else:
                    await safe_send_message(update, context, success_msg, parse_mode=ParseMode.MARKDOWN)
            else:
                await show_error_animation(update, context, "Failed to save UPI. Please try again!", loading_msg.message_id if loading_msg else None)
        else:
            await show_error_animation(update, context, "User data not found. Please use /start first!", loading_msg.message_id if loading_msg else None)

        await start_command(update, context)
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in link_upi_receive: {e}")
        await show_error_animation(update, context, "UPI setup failed. Please try again!")
        await start_command(update, context)
        return ConversationHandler.END

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['withdraw'])
        
        user_id = get_user_id(update)
        users_data = load_data(USERS_FILE)
        user = users_data.get(user_id)

        if not user:
            if loading_msg:
                await show_error_animation(update, context, "User data not found. Starting setup...", loading_msg.message_id)
            await start_command(update, context)
            return

        balance = user.get('balance', 0.0)
        upi = user.get('upi')

        if not upi or upi == "Not Set":
            no_upi_msg = (
                f"⚠️ *UPI Required!*\n\n"
                f"💳 Link your UPI ID first to withdraw funds.\n"
                f"Use '{EMOJIS['diamond']} Set UPI' button in the main menu."
            )
            
            keyboard = [[InlineKeyboardButton(f"{EMOJIS['diamond']} Set UPI Now", callback_data="setup_upi")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if loading_msg:
                try:
                    await context.bot.edit_message_text(
                        no_upi_msg,
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    await safe_send_message(
                        update, context, no_upi_msg, 
                        reply_markup=reply_markup, 
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await safe_send_message(
                    update, context, no_upi_msg, 
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.MARKDOWN
                )
            return

        if balance < MIN_WITHDRAWAL:
            shortage = MIN_WITHDRAWAL - balance
            progress = int((balance / MIN_WITHDRAWAL) * 100)
            
            progress_bar = "█" * (progress // 10) + "░" * (10 - (progress // 10))
            
            insufficient_msg = (
                f"💡 *Almost There!*\n\n"
                f"💰 Current Balance: ₹{format_number(balance)}\n"
                f"🎯 Minimum Required: ₹{MIN_WITHDRAWAL:.0f}\n"
                f"📉 Still Need: ₹{format_number(shortage)}\n\n"
                f"📊 Progress:\n`{progress_bar}` {progress}%\n\n"
                f"💡 *Quick Earning Tips:*\n"
                f"• {EMOJIS['gift']} Claim daily bonuses\n"
                f"• {EMOJIS['magic']} Complete tasks\n"
                f"• {EMOJIS['rocket']} Invite friends (₹{REFERRAL_BONUS:.0f} each!)"
            )
            
            keyboard = [
                [InlineKeyboardButton(f"{EMOJIS['rocket']} Invite Friends", callback_data="quick_refer")],
                [InlineKeyboardButton(f"{EMOJIS['magic']} View Tasks", callback_data="quick_tasks")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if loading_msg:
                try:
                    await context.bot.edit_message_text(
                        insufficient_msg,
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    await safe_send_message(
                        update, context, insufficient_msg, 
                        reply_markup=reply_markup, 
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await safe_send_message(
                    update, context, insufficient_msg, 
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.MARKDOWN
                )
            return

        withdrawals_data = load_data(WITHDRAWALS_FILE)
        request_id = f"req_{int(datetime.now().timestamp())}_{user_id}"
        
        withdrawal_request = {
            'user_id': user_id,
            'username': user.get('username', 'N/A'),
            'first_name': user.get('first_name', 'User'),
            'amount': balance,
            'upi': upi,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        withdrawals_data[request_id] = withdrawal_request
        
        if save_data(withdrawals_data, WITHDRAWALS_FILE):
            user['balance'] = 0.0
            save_data(users_data, USERS_FILE)
            
            success_msg = (
                f"✅ *WITHDRAWAL SUBMITTED!* ✅\n\n"
                f"💰 Amount: ₹{format_number(balance)}\n"
                f"💳 UPI: `{upi}`\n"
                f"🆔 Request ID: `{request_id}`\n\n"
                f"⏳ *Processing Time:* 24-48 hours\n"
                f"📱 You'll receive a confirmation soon!\n\n"
                f"🎉 Keep earning while you wait!"
            )
            
            if loading_msg:
                await show_success_animation(update, context, success_msg, loading_msg.message_id)
            else:
                await safe_send_message(update, context, success_msg, parse_mode=ParseMode.MARKDOWN, force_new=True)
            
            username_safe = escape_markdown(user.get('username', 'N/A'))
            first_name_safe = escape_markdown(user.get('first_name', 'User'))
            admin_msg = (
                f"💸 *NEW WITHDRAWAL REQUEST* 💸\n\n"
                f"👤 User: {first_name_safe} (@{username_safe})\n"
                f"🆔 ID: `{user_id}`\n"
                f"💰 Amount: ₹{format_number(balance)}\n"
                f"💳 UPI: `{upi}`\n"
                f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"🔢 Request ID: `{request_id}`"
            )
            
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=admin_msg,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to notify admin about withdrawal: {e}")
        else:
            await show_error_animation(
                update, context,
                "Withdrawal failed to process. Please try again!",
                loading_msg.message_id if loading_msg else None
            )

    except Exception as e:
        logger.error(f"Error in withdraw: {e}")
        await show_error_animation(
            update, context,
            "Withdrawal service error. Please try again later!",
            None
        )

async def refer_command(update: Update, context: ContextTypes.DEFAULT_TYPE, force_new: bool = False) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['refer'])
        
        user_id = get_user_id(update)
        bot_username = (await context.bot.get_me()).username
        users_data = load_data(USERS_FILE)
        user_data = users_data.get(user_id, {})
        referral_count = user_data.get('referrals', 0)
        
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        potential_earnings = referral_count * REFERRAL_BONUS * 2
        next_milestone = ((referral_count // 5) + 1) * 5
        
        refer_msg = (
            f"🚀 *INVITE & EARN PROGRAM* 🚀\n\n"
            f"💎 *Your Unique Link:*\n`{referral_link}`\n\n"
            f"🎁 *How It Works:*\n"
            f"• Share your link with friends\n"
            f"• They get ₹{REFERRAL_BONUS:.0f} signup bonus\n"
            f"• You get ₹{REFERRAL_BONUS:.0f} referral bonus\n"
            f"• Win-win for everyone! 🎉\n\n"
            f"📊 *Your Stats:*\n"
            f"👥 Friends Invited: *{referral_count}*\n"
            f"💰 Earnings from Referrals: *₹{format_number(potential_earnings)}*\n"
            f"🎯 Next Milestone: *{next_milestone} referrals*\n\n"
            f"💡 *Pro Tips:*\n"
            f"• Share in groups and social media\n"
            f"• Tell friends about daily bonuses\n"
            f"• Mention the easy tasks available!"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_link:{referral_link}")],
            [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={referral_link}&text=💰 Join me on this amazing earning bot! Get ₹{REFERRAL_BONUS:.0f} signup bonus! 🎁")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if loading_msg:
            try:
                await context.bot.edit_message_text(
                    refer_msg,
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            except:
                await safe_send_message(
                    update, context, refer_msg, 
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                    force_new=force_new
                )
        else:
            await safe_send_message(
                update, context, refer_msg, 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                force_new=force_new
            )

    except Exception as e:
        logger.error(f"Error in refer_command: {e}")
        await show_error_animation(
            update, context,
            "Unable to generate referral link. Please try again!",
            None
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced help system with updated streak info."""
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['help'])
        
        help_msg = (
            f"❓ *COMPLETE USER GUIDE* ❓\n\n"
            f"🎯 *Main Features:*\n\n"
            f"{EMOJIS['gift']} *Daily Bonus System*\n"
            f"• Claim a random bonus every 24 hours.\n"
            f"• Build streaks for extra rewards on top of your bonus!\n"
            f"  - 3-Day Streak: *+₹{STREAK_REWARDS[3]:.2f} extra*\n"
            f"  - 7-Day Streak: *+₹{STREAK_REWARDS[7]:.2f} extra*\n"
            f"  - 30-Day Streak: *+₹{STREAK_REWARDS[30]:.2f} extra*\n"
            f"  - 100-Day Streak: *+₹{STREAK_REWARDS[100]:.2f} extra*\n\n"
            f"{EMOJIS['magic']} *Task System*\n"
            f"• Complete simple tasks like joining channels to earn coins 🪙.\n\n"
            f"{EMOJIS['rocket']} *Referral Program*\n"
            f"• Invite friends and you both get *₹{REFERRAL_BONUS:.2f}* when they start!\n\n"
            f"{EMOJIS['cash']} *Withdrawal System*\n"
            f"• Minimum withdrawal: *₹{MIN_WITHDRAWAL:.0f}*\n"
            f"• Payments via UPI within 24-48 hours.\n\n"
            f"🏅 *Level System*\n"
            f"• Earn more to level up from Starter 🌱 to Diamond 👑!\n\n"
            f"💡 *Pro Tips for Fast Earning:*\n"
            f"• Never miss a daily bonus to keep your streak alive.\n"
            f"• Invite as many friends as possible for the best rewards.\n\n"
            f"📞 *Need Help?* Contact the admin for any issues."
        )
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJIS['gift']} Claim Daily Bonus", callback_data="quick_claim")],
            [InlineKeyboardButton(f"{EMOJIS['rocket']} Start Referring", callback_data="quick_refer")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if loading_msg:
            try:
                await context.bot.edit_message_text(
                    help_msg,
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await safe_send_message(update, context, help_msg, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            await safe_send_message(update, context, help_msg, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        await show_error_animation(update, context, "Help system unavailable. Please try again!", None)

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE, force_new: bool = False) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['tasks'])
        
        user_id = get_user_id(update)
        tasks_data = load_data(TASKS_FILE)
        users_data = load_data(USERS_FILE)
        user = users_data.get(user_id)
        
        if not user:
            if loading_msg:
                await show_error_animation(update, context, "User data not found. Starting setup...", loading_msg.message_id)
            await start_command(update, context)
            return
        
        now = datetime.now()
        
        active_tasks = {}
        for tid, task in tasks_data.items():
            if task.get('status') != 'active':
                continue
            
            expiry_str = task.get('expiry_date')
            if expiry_str:
                try:
                    expiry_date = datetime.fromisoformat(expiry_str)
                    if expiry_date <= now:
                        continue
                except ValueError:
                    continue
            
            active_tasks[tid] = task

        if not active_tasks:
            no_tasks_msg = (
                f"🎉 *ALL TASKS COMPLETED!* 🎉\n\n"
                f"👏 Amazing work! You've cleared all available tasks.\n\n"
                f"💡 *While you wait for new tasks:*\n"
                f"• {EMOJIS['gift']} Claim daily bonuses\n"
                f"• {EMOJIS['rocket']} Invite friends (₹{REFERRAL_BONUS:.0f} each)\n"
                f"• 📊 Check your earning stats\n\n"
                f"🔔 New tasks will be announced automatically!"
            )
            
            keyboard = [
                [InlineKeyboardButton(f"{EMOJIS['rocket']} Invite Friends", callback_data="quick_refer")],
                [InlineKeyboardButton(f"{EMOJIS['gift']} Daily Bonus", callback_data="quick_claim")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if loading_msg:
                try:
                    await context.bot.edit_message_text(
                        no_tasks_msg,
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    await safe_send_message(
                        update, context, no_tasks_msg, 
                        reply_markup=reply_markup, 
                        parse_mode=ParseMode.MARKDOWN,
                        force_new=force_new
                    )
            else:
                await safe_send_message(
                    update, context, no_tasks_msg, 
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.MARKDOWN,
                    force_new=force_new
                )
            return

        completed_tasks = set(user.get('completed_tasks', []))
        available_count = 0
        
        if loading_msg:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id
                )
            except:
                pass
        
        for task_id, task in active_tasks.items():
            if task_id in completed_tasks:
                continue
            
            available_count += 1
            channel_username = task['channel_username']
            reward = task['reward']
            
            expiry_str = task.get('expiry_date')
            time_left_str = ""
            if expiry_str:
                try:
                    expiry_date = datetime.fromisoformat(expiry_str)
                    time_left = expiry_date - now
                    if time_left.days > 0:
                        time_left_str = f"⏰ {time_left.days} days left"
                    else:
                        hours_left = time_left.seconds // 3600
                        time_left_str = f"⏰ {hours_left} hours left"
                except ValueError:
                    time_left_str = ""
            
            task_msg = (
                f"✨ *NEW TASK AVAILABLE* ✨\n\n"
                f"📺 Channel: `{channel_username}`\n"
                f"🪙 Reward: *{reward} Coins*\n"
                f"{time_left_str}\n\n"
                f"📝 *Instructions:*\n"
                f"1️⃣ Click 'Join Channel' button\n"
                f"2️⃣ Join the channel\n"
                f"3️⃣ Click 'Verify' to claim reward\n\n"
                f"💡 *Note:* You must stay in the channel until verification!"
            )
            
            callback_data = f"verify:{task_id}:{channel_username}"
            
            keyboard = [
                [InlineKeyboardButton("1️⃣ Join Channel 🔗", url=f"https://t.me/{channel_username.replace('@','')}")],
                [InlineKeyboardButton("2️⃣ Verify Membership ✅", callback_data=callback_data)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_send_message(
                update, context, task_msg, 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.MARKDOWN,
                force_new=True 
            )

        if available_count == 0:
            completed_msg = (
                f"🏆 *ALL TASKS COMPLETED!* 🏆\n\n"
                f"🎉 You've completed all {len(active_tasks)} available tasks!\n"
                f"💰 Keep earning through:\n"
                f"• {EMOJIS['gift']} Daily bonuses\n"
                f"• {EMOJIS['rocket']} Friend referrals\n\n"
                f"🔔 We'll notify you when new tasks arrive!"
            )
            
            if loading_msg:
                await show_success_animation(update, context, completed_msg, loading_msg.message_id)
            else:
                await safe_send_message(update, context, completed_msg, parse_mode=ParseMode.MARKDOWN, force_new=force_new)

    except Exception as e:
        logger.error(f"Error in show_tasks: {e}")
        await show_error_animation(
            update, context,
            "Unable to load tasks. Please try again!",
            None
        )

async def verify_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer("🔍 Verifying membership...")

        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['verify'])

        user_id = str(query.from_user.id)
        callback_parts = query.data.split(':', 2)
        
        if len(callback_parts) != 3:
            await show_error_animation(update, context, "Invalid task data. Please try again.", loading_msg.message_id if loading_msg else None)
            return
        
        _, task_id, channel_username = callback_parts

        users_data = load_data(USERS_FILE)
        tasks_data = load_data(TASKS_FILE)
        
        if user_id not in users_data:
            await show_error_animation(update, context, "User data not found. Please use /start first.", loading_msg.message_id if loading_msg else None)
            return
        
        user = users_data[user_id]
        task = tasks_data.get(task_id)

        if not task or task.get('status') != 'active':
            await show_error_animation(
                update, context,
                "This task is no longer available.",
                loading_msg.message_id if loading_msg else None
            )
            return

        if task_id in user.get('completed_tasks', []):
            await show_error_animation(
                update, context,
                "You've already claimed this task reward!",
                loading_msg.message_id if loading_msg else None
            )
            return

        try:
            member = await context.bot.get_chat_member(chat_id=channel_username, user_id=user_id)
            
            if member.status in ['member', 'administrator', 'creator']:
                reward = task['reward']
                user['coin_balance'] = user.get('coin_balance', 0) + reward
                user.setdefault('completed_tasks', []).append(task_id)
                
                if save_data(users_data, USERS_FILE):
                    success_msg = (
                        f"✅ Membership verified!\n"
                        f"🪙 Earned: *{reward} Coins*\n"
                        f"💰 New Coin Balance: *{user['coin_balance']} Coins*\n\n"
                        f"🚀 Keep completing tasks to earn more!"
                    )
                    
                    if loading_msg:
                        await show_success_animation(update, context, success_msg, loading_msg.message_id)
                    else:
                        await safe_send_message(update, context, success_msg, parse_mode=ParseMode.MARKDOWN)
                    
                    remaining_tasks = len([t for t_id, t in tasks_data.items()
                                           if t.get('status') == 'active' and 
                                           t_id != task_id and 
                                           t_id not in user.get('completed_tasks', [])])
                    
                    if remaining_tasks > 0:
                        await asyncio.sleep(2)
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"💡 *{remaining_tasks} more tasks available!*\nUse '{EMOJIS['magic']} Tasks' to continue earning!",
                            parse_mode=ParseMode.MARKDOWN
                        )
                else:
                    await show_error_animation(update, context, "Failed to save progress. Please try again!", loading_msg.message_id if loading_msg else None)
            else:
                not_member_msg = (
                    f"❌ *Membership Not Found!*\n\n"
                    f"Please make sure you:\n"
                    f"1️⃣ Clicked 'Join Channel'\n"
                    f"2️⃣ Actually joined the channel\n"
                    f"3️⃣ Didn't immediately leave\n\n"
                    f"💡 Try joining again, then click verify!"
                )
                
                if loading_msg:
                    await show_error_animation(update, context, not_member_msg, loading_msg.message_id)
                else:
                    await safe_send_message(update, context, not_member_msg, parse_mode=ParseMode.MARKDOWN)

        except BadRequest as e:
            error_msg = e.message.lower()
            if any(phrase in error_msg for phrase in ["user not found", "member not found", "user_not_participant"]):
                error_text = (
                    f"❌ *Verification Failed!*\n\n"
                    f"You haven't joined `{channel_username}` yet.\n"
                    f"Please join the channel first, then click verify!"
                )
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
            elif "chat not found" in error_msg:
                error_text = "This channel may no longer exist or be private."
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
                
                try:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"⚠️ *Broken Task Alert*\n\nChannel `{channel_username}` not found!\nTask ID: `{task_id}`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception:
                    pass
            else:
                logger.error(f"Verification error for {channel_username}: {e}")
                error_text = "Cannot check this task right now. Admin has been notified."
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
                
                try:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"🔴 *Task Verification Error*\n\nChannel: `{channel_username}`\nError: `{e.message}`\n\n*Action:* Check bot permissions in channel.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception:
                    pass

        except Forbidden:
            error_text = "Bot doesn't have permission to check this channel."
            await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
        except Exception as e:
            logger.error(f"Unexpected verification error: {e}")
            error_text = "Something went wrong. Please try again later!"
            await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)

    except Exception as e:
        logger.error(f"Critical error in verify_membership_callback: {e}")
        try:
            await show_error_animation(
                update, context,
                "Critical error occurred. Please contact admin!",
                None
            )
        except Exception:
            pass

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        data = query.data

        if data == "quick_claim":
            await query.answer("Claiming...")
            await claim_reward(update, context)
        
        elif data == "quick_withdraw":
            await query.answer("Checking...")
            await withdraw(update, context)

        elif data == "quick_refer":
            await query.answer()
            await refer_command(update, context, force_new=True)
        
        elif data == "quick_tasks":
            await query.answer()
            await show_tasks(update, context, force_new=True)
        
        elif data.startswith("copy_link:"):
            await query.answer("Link copied to clipboard!", show_alert=True)
            link = data.split(":", 1)[1]
            await query.edit_message_text(
                f"📋 *Link Copied!*\n\n`{link}`\n\nShare this link to start earning!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=query.message.reply_markup
            )
        
        elif data == "setup_upi":
            await query.answer()
            await query.edit_message_text(
                "To set your UPI, please use the main menu button or type /linkupi",
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error in handle_callback_query: {e}")

# --- SCHEDULED JOBS ---
async def send_daily_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a daily reminder to users who haven't claimed their bonus."""
    logger.info("Running daily reminder job...")
    users_data = load_data(USERS_FILE)
    now = datetime.now()
    reminded_count = 0

    for user_id, user_data in users_data.items():
        if not user_data.get('notifications_enabled', True):
            continue

        should_remind = True
        last_claim_str = user_data.get('last_claim')

        if last_claim_str:
            try:
                last_claim_time = datetime.fromisoformat(last_claim_str)
                if now - last_claim_time < timedelta(hours=24):
                    should_remind = False
            except ValueError:
                logger.warning(f"Invalid last_claim format for user {user_id}")
        
        if should_remind:
            try:
                reminder_message = (
                    f"👋 Hey {user_data.get('first_name', 'there')}!\n\n"
                    f"🎁 Your daily bonus is ready to be claimed! Don't miss out on your reward and break your streak! 🔥"
                )
                keyboard = [[InlineKeyboardButton(f"{EMOJIS['gift']} Claim Now!", callback_data="quick_claim")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_message(
                    chat_id=user_id, 
                    text=reminder_message,
                    reply_markup=reply_markup
                )
                reminded_count += 1
                await asyncio.sleep(0.1)
            except Forbidden:
                logger.warning(f"User {user_id} has blocked the bot. Disabling notifications for them.")
                users_data[user_id]['notifications_enabled'] = False
            except Exception as e:
                logger.error(f"Failed to send reminder to {user_id}: {e}")
    
    save_data(users_data, USERS_FILE)
    logger.info(f"Daily reminder job finished. Sent reminders to {reminded_count} users.")


# --- ADMIN FUNCTIONS ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if get_user_id(update) != str(ADMIN_ID):
            return

        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin'])
        
        users_data = load_data(USERS_FILE)
        tasks_data = load_data(TASKS_FILE)
        withdrawals_data = load_data(WITHDRAWALS_FILE)
        
        total_users = len(users_data)
        active_tasks = len([t for t in tasks_data.values() if t.get('status') == 'active'])
        pending_withdrawals = len([w for w in withdrawals_data.values() if w.get('status') == 'pending'])
        total_balance = sum(user.get('balance', 0) for user in users_data.values())
        
        admin_msg = (
            f"👑 *ADMIN DASHBOARD* 👑\n\n"
            f"📊 *Quick Stats:*\n"
            f"👥 Total Users: {total_users}\n"
            f"✨ Active Tasks: {active_tasks}\n"
            f"💸 Pending Withdrawals: {pending_withdrawals}\n"
            f"💰 Total User Balance: ₹{format_number(total_balance)}\n\n"
            f"⚡ Select an action below:"
        )
        
        keyboard = [
            ["📤 Broadcast Text", "🖼️ Broadcast Image"],
            ["➕ Create Task", "🗑️ Remove Task"],
            ["📊 Detailed Stats", "👥 User List"],
            ["💸 Withdrawal Requests", "🔧 System Tools"],
            ["🧹 Clean Expired Tasks", "⬅️ Back to Main"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if loading_msg:
            try:
                await context.bot.edit_message_text(
                    admin_msg,
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await safe_send_message(
                    update, context, admin_msg, 
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await safe_send_message(
                update, context, admin_msg, 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error in admin_command: {e}")
        await show_error_animation(update, context, "Admin panel error!")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        text = update.message.text
        if get_user_id(update) != str(ADMIN_ID):
            return

        action_map = {
            "📤 Broadcast Text": broadcast_start,
            "🖼️ Broadcast Image": broadcast_photo_start,
            "📊 Detailed Stats": detailed_stats,
            "👥 User List": view_users,
            "💸 Withdrawal Requests": view_withdrawals,
            "🔧 System Tools": system_tools,
            "➕ Create Task": create_task_start,
            "🗑️ Remove Task": remove_task_start,
            "🧹 Clean Expired Tasks": clean_expired_tasks,
            "⬅️ Back to Main": start_command
        }
        
        if text in action_map:
            await show_typing(update, context)
            await action_map[text](update, context)
        else:
            await handle_message(update, context)

    except Exception as e:
        logger.error(f"Error in handle_admin_message: {e}")
        await show_error_animation(update, context, "Admin action failed!")

async def detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_stats'])
        
        users_data = load_data(USERS_FILE)
        tasks_data = load_data(TASKS_FILE)
        withdrawals_data = load_data(WITHDRAWALS_FILE)
        
        total_users = len(users_data)
        total_balance = sum(user.get('balance', 0) for user in users_data.values())
        total_coins = sum(user.get('coin_balance', 0) for user in users_data.values())
        total_earned = sum(user.get('total_earned', 0) for user in users_data.values())
        total_referrals = sum(user.get('referrals', 0) for user in users_data.values())
        
        active_tasks = len([t for t in tasks_data.values() if t.get('status') == 'active'])
        total_tasks = len(tasks_data)
        
        pending_withdrawals = [w for w in withdrawals_data.values() if w.get('status') == 'pending']
        completed_withdrawals = [w for w in withdrawals_data.values() if w.get('status') == 'completed']
        pending_amount = sum(w.get('amount', 0) for w in pending_withdrawals)
        completed_amount = sum(w.get('amount', 0) for w in completed_withdrawals)
        
        level_counts = {}
        for user in users_data.values():
            level = get_level_info(user.get('balance', 0))['name']
            level_counts[level] = level_counts.get(level, 0) + 1
        
        week_ago = datetime.now() - timedelta(days=7)
        recent_users = 0
        recent_claims = 0
        
        for user in users_data.values():
            join_date_str = user.get('join_date')
            if join_date_str:
                try:
                    join_date = datetime.fromisoformat(join_date_str)
                    if join_date >= week_ago:
                        recent_users += 1
                except ValueError:
                    pass
            
            last_claim_str = user.get('last_claim')
            if last_claim_str:
                try:
                    last_claim = datetime.fromisoformat(last_claim_str)
                    if last_claim >= week_ago:
                        recent_claims += 1
                except ValueError:
                    pass
        
        stats_msg = (
            f"📊 *DETAILED STATISTICS* 📊\n\n"
            f"👥 *User Statistics:*\n"
            f"• Total Users: {total_users}\n"
            f"• New Users (7d): {recent_users}\n"
            f"• Active Users (7d): {recent_claims}\n\n"
            f"💰 *Financial Overview:*\n"
            f"• Total User Balance: ₹{format_number(total_balance)}\n"
            f"• Total Earned by Users: ₹{format_number(total_earned)}\n"
            f"• Total Coins: {total_coins:,}\n"
            f"• Total Referrals: {total_referrals}\n\n"
            f"✨ *Task Statistics:*\n"
            f"• Active Tasks: {active_tasks}\n"
            f"• Total Tasks Created: {total_tasks}\n\n"
            f"💸 *Withdrawal Statistics:*\n"
            f"• Pending: {len(pending_withdrawals)} (₹{format_number(pending_amount)})\n"
            f"• Completed: {len(completed_withdrawals)} (₹{format_number(completed_amount)})\n\n"
            f"🏅 *User Level Distribution:*\n"
        )
        
        for level, count in level_counts.items():
            percentage = (count / total_users * 100) if total_users > 0 else 0
            stats_msg += f"• {level}: {count} ({percentage:.1f}%)\n"
        
        if loading_msg:
            await show_success_animation(update, context, stats_msg, loading_msg.message_id)
        else:
            await safe_send_message(update, context, stats_msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in detailed_stats: {e}")
        await show_error_animation(update, context, "Failed to generate detailed stats!")

async def system_tools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_tools'])
        
        tools_msg = (
            f"🔧 *SYSTEM TOOLS* 🔧\n\n"
            f"⚠️ *Warning:* These are maintenance tools.\n"
            f"Use with caution!\n\n"
            f"Select a tool to use:"
        )
        
        keyboard = [
            [InlineKeyboardButton("💾 Backup Data", callback_data="tool_backup")],
            [InlineKeyboardButton("🧹 Clean Expired", callback_data="tool_clean")],
            [InlineKeyboardButton("📤 Export Users", callback_data="tool_export")],
            [InlineKeyboardButton("🩺 Health Check", callback_data="tool_health")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if loading_msg:
            try:
                await context.bot.edit_message_text(
                    tools_msg,
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await safe_send_message(
                    update, context, tools_msg, 
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await safe_send_message(
                update, context, tools_msg, 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error in system_tools: {e}")
        await show_error_animation(update, context, "System tools unavailable!")

async def view_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_users'])
        
        users_data = load_data(USERS_FILE)
        if not users_data:
            await show_error_animation(update, context, "No users have joined yet.", loading_msg.message_id if loading_msg else None)
            return

        sorted_users = sorted(
            users_data.items(), 
            key=lambda x: x[1].get('balance', 0), 
            reverse=True
        )
        
        message_parts = ["👥 *USER LIST* (Top 20 by Balance)\n\n"]
        
        for i, (user_id, data) in enumerate(sorted_users[:20], 1):
            username = escape_markdown(data.get('username', 'N/A'))
            first_name = escape_markdown(data.get('first_name', 'User'))
            balance = data.get('balance', 0.0)
            coins = data.get('coin_balance', 0)
            referrals = data.get('referrals', 0)
            level = get_level_info(balance)['name']
            
            user_info = (
                f"{i}. {first_name} (@{username})\n"
                f"    💰 ₹{format_number(balance)} | 🪙 {coins} | 👥 {referrals}\n"
                f"    🏅 {level} | ID: `{user_id}`\n"
                f"    ─────────────────────\n"
            )
            
            if len(''.join(message_parts) + user_info) > 4000:
                break
            
            message_parts.append(user_info)
        
        total_message = ''.join(message_parts)
        
        if len(sorted_users) > 20:
            total_message += f"\n... and {len(sorted_users) - 20} more users"
        
        if len(total_message) > 4096:
            filename = f"user_list_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("USER LIST - FULL EXPORT\n")
                f.write("=" * 50 + "\n\n")
                
                for user_id, data in sorted_users:
                    username = data.get('username', 'N/A')
                    first_name = data.get('first_name', 'User')
                    balance = data.get('balance', 0.0)
                    coins = data.get('coin_balance', 0)
                    referrals = data.get('referrals', 0)
                    total_earned = data.get('total_earned', 0.0)
                    join_date = data.get('join_date', 'Unknown')
                    
                    f.write(f"User: {first_name} (@{username})\n")
                    f.write(f"ID: {user_id}\n")
                    f.write(f"Balance: ₹{balance:.2f}\n")
                    f.write(f"Coins: {coins}\n")
                    f.write(f"Total Earned: ₹{total_earned:.2f}\n")
                    f.write(f"Referrals: {referrals}\n")
                    f.write(f"Join Date: {join_date}\n")
                    f.write("-" * 30 + "\n")
            
            if loading_msg:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id
                    )
                except:
                    pass
            
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(filename, 'rb'),
                caption=f"📊 Complete user list ({len(users_data)} users)"
            )
            os.remove(filename)
        else:
            if loading_msg:
                await show_success_animation(update, context, total_message, loading_msg.message_id)
            else:
                await safe_send_message(update, context, total_message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in view_users: {e}")
        await show_error_animation(update, context, "Failed to load user list!")

async def view_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_withdrawals'])
        
        withdrawals_data = load_data(WITHDRAWALS_FILE)
        pending_requests = [(req_id, req) for req_id, req in withdrawals_data.items() 
                            if req.get('status') == 'pending']
        
        if not pending_requests:
            await show_error_animation(update, context, "No pending withdrawal requests!", loading_msg.message_id if loading_msg else None)
            return

        withdrawal_msg = f"💸 *PENDING WITHDRAWALS* ({len(pending_requests)})\n\n"
        total_pending = 0
        
        for i, (req_id, req) in enumerate(pending_requests[:10], 1):
            username = escape_markdown(req.get('username', 'N/A'))
            first_name = escape_markdown(req.get('first_name', 'User'))
            amount = req['amount']
            upi = req['upi']
            timestamp = req.get('timestamp', '')
            
            try:
                req_time = datetime.fromisoformat(timestamp)
                time_str = req_time.strftime('%d/%m %H:%M')
            except:
                time_str = 'Unknown'
            
            total_pending += amount
            
            withdrawal_msg += (
                f"{i}. {first_name} (@{username})\n"
                f"    💰 Amount: ₹{format_number(amount)}\n"
                f"    💳 UPI: `{upi}`\n"
                f"    📅 Time: {time_str}\n"
                f"    🆔 ID: `{req_id}`\n"
                f"    ─────────────────\n"
            )
        
        if len(pending_requests) > 10:
            withdrawal_msg += f"\n... and {len(pending_requests) - 10} more requests"
        
        withdrawal_msg += f"\n💰 *Total Pending: ₹{format_number(total_pending)}*"
        
        keyboard = [
            [InlineKeyboardButton("✅ Mark as Paid", callback_data="mark_paid")],
            [InlineKeyboardButton("📤 Export List", callback_data="export_withdrawals")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if loading_msg:
            try:
                await context.bot.edit_message_text(
                    withdrawal_msg,
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await safe_send_message(
                    update, context, withdrawal_msg, 
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await safe_send_message(
                update, context, withdrawal_msg, 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error in view_withdrawals: {e}")
        await show_error_animation(update, context, "Failed to load withdrawal requests!")

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        broadcast_msg = (
            f"📤 *TEXT BROADCAST SETUP*\n\n"
            f"📝 Send the message you want to broadcast to all users.\n\n"
            f"💡 *Tips:*\n"
            f"• Use *bold* and _italic_ for emphasis\n"
            f"• Keep it engaging and valuable\n"
            f"• Test with yourself first\n\n"
            f"Type /cancel to abort."
        )
        
        await safe_send_message(
            update, context, broadcast_msg, 
            reply_markup=ReplyKeyboardRemove(), 
            parse_mode=ParseMode.MARKDOWN
        )
        return BROADCAST_MESSAGE

    except Exception as e:
        logger.error(f"Error in broadcast_start: {e}")
        await show_error_animation(update, context, "Broadcast setup failed!")
        return ConversationHandler.END

async def broadcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_broadcast'])
        
        message_to_broadcast = f"📢 *Message from Admin:*\n\n{update.message.text}"
        users_data = load_data(USERS_FILE)
        total_users = len(users_data)
        
        if total_users == 0:
            await show_error_animation(update, context, "No users to broadcast to!", loading_msg.message_id if loading_msg else None)
            await admin_command(update, context)
            return ConversationHandler.END
        
        confirm_msg = (
            f"🚀 *BROADCAST STARTING*\n\n"
            f"👥 Target: {total_users} users\n"
            f"📝 Message ready!\n\n"
            f"⏳ This may take a few minutes..."
        )
        
        if loading_msg:
            try:
                await context.bot.edit_message_text(
                    confirm_msg,
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await safe_send_message(update, context, confirm_msg, parse_mode=ParseMode.MARKDOWN)
        
        sent_count = 0
        failed_count = 0
        blocked_count = 0
        
        for i, user_id in enumerate(users_data.keys(), 1):
            try:
                await context.bot.send_message(
                    chat_id=user_id, 
                    text=message_to_broadcast, 
                    parse_mode=ParseMode.MARKDOWN
                )
                sent_count += 1
                
                if i % 50 == 0 and loading_msg:
                    progress = int((i / total_users) * 100)
                    try:
                        progress_text = (
                            f"📡 *Broadcasting... {progress}%*\n\n"
                            f"✅ Sent: {sent_count}\n"
                            f"❌ Failed: {failed_count}"
                        )
                        await context.bot.edit_message_text(
                            progress_text,
                            chat_id=update.effective_chat.id,
                            message_id=loading_msg.message_id,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.warning(f"Could not edit broadcast status message: {e}")
                
                if i % 30 == 0:
                    await asyncio.sleep(1)
                    
            except Forbidden:
                blocked_count += 1
                failed_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to {user_id}: {e}")
                failed_count += 1
        
        final_msg = (
            f"✅ *BROADCAST COMPLETE!*\n\n"
            f"📊 *Results:*\n"
            f"✅ Successfully sent: {sent_count}\n"
            f"🚫 Blocked bot: {blocked_count}\n"
            f"❌ Other failures: {failed_count - blocked_count}\n"
            f"📈 Success rate: {(sent_count/total_users*100):.1f}%"
        )
        
        if loading_msg:
            try:
                await context.bot.edit_message_text(
                    final_msg,
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await safe_send_message(update, context, final_msg, parse_mode=ParseMode.MARKDOWN)
        await admin_command(update, context)
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in broadcast_receive: {e}")
        await show_error_animation(update, context, "Broadcast failed!")
        await admin_command(update, context)
        return ConversationHandler.END

async def broadcast_photo_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        photo_msg = (
            f"🖼️ *IMAGE BROADCAST SETUP*\n\n"
            f"📸 Send an image with optional caption.\n\n"
            f"💡 *Tips:*\n"
            f"• Use high-quality images\n"
            f"• Keep captions short and engaging\n"
            f"• Test the image quality first\n\n"
            f"Type /cancel to abort."
        )
        
        await safe_send_message(
            update, context, photo_msg, 
            reply_markup=ReplyKeyboardRemove(), 
            parse_mode=ParseMode.MARKDOWN
        )
        return BROADCAST_PHOTO

    except Exception as e:
        logger.error(f"Error in broadcast_photo_start: {e}")
        await show_error_animation(update, context, "Photo broadcast setup failed!")
        return ConversationHandler.END

async def broadcast_photo_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_broadcast'])
        
        if not update.message.photo:
            await show_error_animation(update, context, "Please send a photo! Use /cancel to abort.", loading_msg.message_id if loading_msg else None)
            return BROADCAST_PHOTO
        
        photo_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        
        if caption:
            caption = f"📢 *Message from Admin:*\n\n{caption}"
        
        users_data = load_data(USERS_FILE)
        total_users = len(users_data)
        
        if total_users == 0:
            await show_error_animation(update, context, "No users to broadcast to!", loading_msg.message_id if loading_msg else None)
            await admin_command(update, context)
            return ConversationHandler.END
        
        confirm_msg = (
            f"🚀 *PHOTO BROADCAST STARTING*\n\n"
            f"👥 Target: {total_users} users\n"
            f"🖼️ Photo ready!\n\n"
            f"⏳ This may take a few minutes..."
        )
        
        if loading_msg:
            try:
                await context.bot.edit_message_text(
                    confirm_msg,
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await safe_send_message(update, context, confirm_msg, parse_mode=ParseMode.MARKDOWN)
        
        sent_count = 0
        failed_count = 0
        blocked_count = 0

        for i, user_id in enumerate(users_data.keys(), 1):
            try:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=photo_id,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN if caption else None
                )
                sent_count += 1
                
                if i % 30 == 0 and loading_msg:
                    progress = int((i / total_users) * 100)
                    try:
                        progress_text = (
                            f"📡 *Broadcasting... {progress}%*\n\n"
                            f"✅ Sent: {sent_count}\n"
                            f"❌ Failed: {failed_count}"
                        )
                        await context.bot.edit_message_text(
                            progress_text,
                            chat_id=update.effective_chat.id,
                            message_id=loading_msg.message_id,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.warning(f"Could not edit broadcast status message: {e}")
                
                if i % 30 == 0:
                    await asyncio.sleep(1)
                    
            except Forbidden:
                blocked_count += 1
                failed_count += 1
            except Exception as e:
                logger.error(f"Failed to send photo broadcast to {user_id}: {e}")
                failed_count += 1
        
        final_msg = (
            f"✅ *PHOTO BROADCAST COMPLETE!*\n\n"
            f"📊 *Results:*\n"
            f"✅ Successfully sent: {sent_count}\n"
            f"🚫 Blocked bot: {blocked_count}\n"
            f"❌ Other failures: {failed_count - blocked_count}\n"
            f"📈 Success rate: {(sent_count/total_users*100):.1f}%"
        )
        
        if loading_msg:
            try:
                await context.bot.edit_message_text(
                    final_msg,
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await safe_send_message(update, context, final_msg, parse_mode=ParseMode.MARKDOWN)
        await admin_command(update, context)
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in broadcast_photo_receive: {e}")
        await show_error_animation(update, context, "Photo broadcast failed!")
        await admin_command(update, context)
        return ConversationHandler.END

async def create_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        task_msg = (
            f"➕ *NEW TASK CREATION*\n\n"
            f"📝 *Step 1: Channel Username*\n\n"
            f"Send the channel username (with @)\n"
            f"Example: `@telegram`\n\n"
            f"⚠️ *Important Requirements:*\n"
            f"• Bot must be admin in the channel\n"
            f"• Channel must be public or accessible\n"
            f"• Use exact username format\n\n"
            f"Type /cancel to abort."
        )
        
        await safe_send_message(
            update, context, task_msg, 
            reply_markup=ReplyKeyboardRemove(), 
            parse_mode=ParseMode.MARKDOWN
        )
        return ASK_CHANNEL

    except Exception as e:
        logger.error(f"Error in create_task_start: {e}")
        await show_error_animation(update, context, "Task creation setup failed!")
        return ConversationHandler.END

async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_task_create'])
        
        channel = update.message.text.strip()
        
        if not channel.startswith('@'):
            await show_error_animation(
                update, context,
                "Channel username must start with '@'\n\nExample: `@telegram`\n\nPlease try again:",
                loading_msg.message_id if loading_msg else None
            )
            return ASK_CHANNEL
        
        try:
            chat_info = await context.bot.get_chat(channel)
            bot_member = await context.bot.get_chat_member(channel, context.bot.id)
            
            if bot_member.status not in ['administrator']:
                error_text = (
                    f"Bot is not an admin in `{channel}`\n\nPlease:\n1. Add bot to the channel\n2. Make it an admin\n3. Try again\n\nOr send a different channel:"
                )
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
                return ASK_CHANNEL
            
            context.user_data['task_channel'] = channel
            context.user_data['channel_title'] = chat_info.title
            
            reward_msg = (
                f"✅ *Channel Verified!*\n\n"
                f"📺 Channel: `{channel}`\n"
                f"📝 Title: {escape_markdown(chat_info.title)}\n\n"
                f"*Step 2: Reward Amount*\n\n"
                f"How many coins should users earn?\n"
                f"Range: 10-500 coins\n"
                f"Recommended: 50-100 coins"
            )
            
            if loading_msg:
                await show_success_animation(update, context, reward_msg, loading_msg.message_id)
            else:
                await safe_send_message(update, context, reward_msg, parse_mode=ParseMode.MARKDOWN)
            return ASK_REWARD
            
        except Exception as e:
            error_text = (
                f"Cannot access `{channel}`\n\nPossible issues:\n• Channel doesn't exist\n• Channel is private\n• Bot not added to channel\n• Incorrect username\n\nPlease check and try again:"
            )
            await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
            return ASK_CHANNEL

    except Exception as e:
        logger.error(f"Error in receive_channel: {e}")
        await show_error_animation(update, context, "Channel validation failed!")
        return ASK_CHANNEL

async def receive_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, "Setting reward amount")
        
        try:
            reward = int(update.message.text.strip())
            if not (10 <= reward <= 500):
                error_text = (
                    f"Reward must be between 10-500 coins\n\nRecommended ranges:\n• Easy tasks: 10-50\n• Medium tasks: 50-100\n• Premium tasks: 100-500\n\nPlease enter a valid amount:"
                )
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
                return ASK_REWARD
        except ValueError:
            error_text = "Please enter a number only\n\nExample: `75`"
            await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
            return ASK_REWARD

        context.user_data['task_reward'] = reward
        
        expiry_msg = (
            f"✅ *Reward Set: {reward} Coins*\n\n"
            f"*Step 3: Task Duration*\n\n"
            f"How many days should this task be active?\n\n"
            f"Recommended durations:\n"
            f"• 1-3 days: Short-term campaigns\n"
            f"• 7 days: Standard duration\n"
            f"• 14-30 days: Long-term tasks\n\n"
            f"Enter number of days:"
        )
        
        if loading_msg:
            await show_success_animation(update, context, expiry_msg, loading_msg.message_id)
        else:
            await safe_send_message(update, context, expiry_msg, parse_mode=ParseMode.MARKDOWN)
        return ASK_EXPIRY

    except Exception as e:
        logger.error(f"Error in receive_reward: {e}")
        await show_error_animation(update, context, "Reward validation failed!")
        return ASK_REWARD

async def receive_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, "Creating your task")
        
        try:
            days = int(update.message.text.strip())
            if not (1 <= days <= 90):
                error_text = "Duration must be 1-90 days\n\nPlease enter a valid number:"
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
                return ASK_EXPIRY
        except ValueError:
            error_text = "Please enter a number only\n\nExample: `7`"
            await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
            return ASK_EXPIRY

        expiry_date = datetime.now() + timedelta(days=days)
        tasks_data = load_data(TASKS_FILE)
        task_id = f"task_{int(datetime.now().timestamp())}"
        
        channel = context.user_data['task_channel']
        channel_title = context.user_data.get('channel_title', 'Unknown')
        reward = context.user_data['task_reward']
        
        new_task = {
            'channel_username': channel,
            'channel_title': channel_title,
            'reward': reward,
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'expiry_date': expiry_date.isoformat(),
            'created_by': str(ADMIN_ID),
            'total_completions': 0
        }
        
        tasks_data[task_id] = new_task
        
        if save_data(tasks_data, TASKS_FILE):
            del context.user_data['task_channel']
            del context.user_data['task_reward']
            if 'channel_title' in context.user_data:
                del context.user_data['channel_title']
            
            success_msg = (
                f"✅ *TASK CREATED SUCCESSFULLY!* ✅\n\n"
                f"📺 Channel: `{channel}`\n"
                f"🏷️ Title: {escape_markdown(channel_title)}\n"
                f"🪙 Reward: {reward} Coins\n"
                f"⏰ Duration: {days} day(s)\n"
                f"📅 Expires: {expiry_date.strftime('%d/%m/%Y %H:%M')}\n"
                f"🆔 Task ID: `{task_id}`\n\n"
                f"🚀 Broadcasting to all users..."
            )
            
            if loading_msg:
                await show_success_animation(update, context, success_msg, loading_msg.message_id)
            else:
                await safe_send_message(update, context, success_msg, parse_mode=ParseMode.MARKDOWN)
            
            users_data = load_data(USERS_FILE)
            broadcast_msg = (
                f"🎉 *NEW TASK ALERT!* 🎉\n\n"
                f"📺 Join: `{channel}`\n"
                f"🪙 Earn: *{reward} Coins*\n"
                f"⏰ Available for {days} day(s)\n\n"
                f"💡 Go to '{EMOJIS['magic']} Tasks' to complete it now!"
            )
            
            sent_count = 0
            for user_id in users_data.keys():
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=broadcast_msg,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    sent_count += 1
                    
                    if sent_count % 30 == 0:
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Failed to send task alert to {user_id}: {e}")
            
            await safe_send_message(
                update, context, 
                f"📢 *Task alert sent to {sent_count} users!*", 
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await show_error_animation(update, context, "Failed to save task! Please try again.", loading_msg.message_id if loading_msg else None)
        
        await admin_command(update, context)
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in receive_expiry: {e}")
        await show_error_animation(update, context, "Task creation failed!")
        await admin_command(update, context)
        return ConversationHandler.END

async def clean_expired_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_task_clean'])
        
        tasks_data = load_data(TASKS_FILE)
        now = datetime.now()
        
        expired_tasks = []
        active_tasks = {}
        
        for task_id, task in tasks_data.items():
            expiry_str = task.get('expiry_date')
            if expiry_str:
                try:
                    expiry_date = datetime.fromisoformat(expiry_str)
                    if expiry_date < now:
                        expired_tasks.append((task_id, task))
                    else:
                        active_tasks[task_id] = task
                except ValueError:
                    expired_tasks.append((task_id, task)) # Treat invalid format as expired
            else:
                active_tasks[task_id] = task
        
        if not expired_tasks:
            await show_error_animation(update, context, "All tasks are up to date!", loading_msg.message_id if loading_msg else None)
            return
        
        cleanup_msg = f"🗑️ *CLEANING EXPIRED TASKS* 🗑️\n\n"
        
        for i, (task_id, task) in enumerate(expired_tasks[:10], 1):
            channel = task.get('channel_username', 'Unknown')
            reward = task.get('reward', 0)
            completions = task.get('total_completions', 0)
            
            cleanup_msg += f"{i}. `{channel}` ({reward} 🪙, {completions} completions)\n"
        
        if len(expired_tasks) > 10:
            cleanup_msg += f"... and {len(expired_tasks) - 10} more\n"
        
        cleanup_msg += f"\n📊 *Summary:*\n"
        cleanup_msg += f"🗑️ Expired: {len(expired_tasks)}\n"
        cleanup_msg += f"✅ Active: {len(active_tasks)}\n"
        
        if save_data(active_tasks, TASKS_FILE):
            cleanup_msg += f"\n✅ *Cleanup completed successfully!*"
        else:
            cleanup_msg += f"\n❌ *Cleanup failed - data not saved*"
        
        if loading_msg:
            await show_success_animation(update, context, cleanup_msg, loading_msg.message_id)
        else:
            await safe_send_message(update, context, cleanup_msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in clean_expired_tasks: {e}")
        await show_error_animation(update, context, "Task cleanup failed!")

async def remove_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_task_remove'])
        
        tasks_data = load_data(TASKS_FILE)
        now = datetime.now()
        
        active_tasks = {}
        for tid, task in tasks_data.items():
            if task.get('status') != 'active':
                continue
            
            expiry_str = task.get('expiry_date')
            if expiry_str:
                try:
                    expiry_date = datetime.fromisoformat(expiry_str)
                    if expiry_date <= now:
                        continue
                except ValueError:
                    continue
            
            active_tasks[tid] = task

        if not active_tasks:
            await show_error_animation(update, context, "There are no tasks to remove!", loading_msg.message_id if loading_msg else None)
            return

        removal_msg = f"🗑️ *TASK REMOVAL* 🗑️\n\nSelect a task to remove permanently:\n\n"
        
        keyboard = []
        for i, (task_id, task) in enumerate(list(active_tasks.items())[:15], 1):
            channel = task['channel_username']
            reward = task['reward']
            
            expiry_str = task.get('expiry_date')
            time_info = ""
            if expiry_str:
                try:
                    expiry_date = datetime.fromisoformat(expiry_str)
                    time_left = expiry_date - now
                    if time_left.days > 0:
                        time_info = f" ({time_left.days}d left)"
                    else:
                        hours = time_left.seconds // 3600
                        time_info = f" ({hours}h left)"
                except ValueError:
                    pass
            
            button_text = f"❌ {channel} - {reward}🪙{time_info}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"remove:{task_id}")])

        if len(active_tasks) > 15:
            removal_msg += f"Showing first 15 of {len(active_tasks)} tasks.\n\n"

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if loading_msg:
            try:
                await context.bot.edit_message_text(
                    removal_msg,
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await safe_send_message(
                    update, context, removal_msg, 
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await safe_send_message(
                update, context, removal_msg, 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error in remove_task_start: {e}")
        await show_error_animation(update, context, "Failed to load tasks for removal!")

async def remove_task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer("Removing task...")

        loading_msg = await show_stylish_loading_animation(update, context, "Removing task")

        _, task_id_to_remove = query.data.split(':', 1)

        tasks_data = load_data(TASKS_FILE)
        
        if task_id_to_remove not in tasks_data:
            await show_error_animation(update, context, "This task may have already been removed.", loading_msg.message_id if loading_msg else None)
            return
        
        task = tasks_data[task_id_to_remove]
        channel = task['channel_username']
        reward = task['reward']
        completions = task.get('total_completions', 0)
        
        del tasks_data[task_id_to_remove]
        
        if save_data(tasks_data, TASKS_FILE):
            success_msg = (
                f"✅ *TASK REMOVED* ✅\n\n"
                f"📺 Channel: `{channel}`\n"
                f"🪙 Reward: {reward} Coins\n"
                f"👥 Completions: {completions}\n"
                f"🆔 Task ID: `{task_id_to_remove}`\n\n"
                f"🗑️ Task has been permanently deleted."
            )
        else:
            success_msg = "❌ *Removal Failed*\n\nCould not save changes. Please try again."
        
        if loading_msg:
            await show_success_animation(update, context, success_msg, loading_msg.message_id)
        else:
            await safe_send_message(update, context, success_msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in remove_task_callback: {e}")
        try:
            await show_error_animation(
                update, context,
                "Failed to remove task. Please try again!",
                None
            )
        except:
            pass

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await show_success_animation(update, context, "Action cancelled.")
    await start_command(update, context)
    return ConversationHandler.END

# --- ADMIN TOOL CALLBACKS (NEWLY ADDED) ---
async def tool_backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the 'Backup Data' button callback."""
    query = update.callback_query
    await query.answer("💾 Creating backup...")
    loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_backup'])
    
    success = await create_backup()
    
    if success:
        await show_success_animation(update, context, "All data files have been successfully backed up.", loading_msg.message_id)
    else:
        await show_error_animation(update, context, "The backup process failed. Please check the logs.", loading_msg.message_id)

async def tool_clean_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the 'Clean Expired' button callback."""
    query = update.callback_query
    await query.answer("🧹 Cleaning tasks...")
    # The clean_expired_tasks function already handles animations and user feedback.
    await clean_expired_tasks(update, context)

async def tool_export_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the 'Export Users' button callback."""
    query = update.callback_query
    await query.answer("📤 Exporting user data...")
    loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_export'])
    
    try:
        users_data = load_data(USERS_FILE)
        if not users_data:
            await show_error_animation(update, context, "No user data to export.", loading_msg.message_id)
            return

        filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        save_data(users_data, filename)
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(filename, 'rb'),
            caption=f"📊 Full user data export containing {len(users_data)} users."
        )
        os.remove(filename)

        if loading_msg:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)

    except Exception as e:
        logger.error(f"Error during user export: {e}")
        await show_error_animation(update, context, "Failed to export user data.", loading_msg.message_id if loading_msg else None)

async def tool_health_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the 'Health Check' button callback."""
    query = update.callback_query
    await query.answer("🩺 Performing health check...")
    loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_health'])

    try:
        health_report = ["🩺 *System Health Report* 🩺\n"]
        
        # 1. Bot API Connectivity
        try:
            bot_info = await context.bot.get_me()
            health_report.append(f"✅ Bot API: Connected as @{bot_info.username}")
        except Exception as e:
            health_report.append(f"❌ Bot API: Connection FAILED! Error: {e}")

        # 2. Data File Accessibility
        for file in [USERS_FILE, TASKS_FILE, WITHDRAWALS_FILE]:
            if os.path.exists(file):
                try:
                    load_data(file)
                    health_report.append(f"✅ Data File: `{file}` is accessible and valid.")
                except Exception:
                       health_report.append(f"❌ Data File: `{file}` is corrupted or unreadable.")
            else:
                health_report.append(f"⚠️ Data File: `{file}` does not exist (will be created).")

        # 3. Job Queue Check
        jobs = context.job_queue.get_jobs_by_name("daily_reminder_job")
        if jobs:
            health_report.append(f"✅ Job Queue: Daily reminder job is scheduled.")
        else:
            health_report.append(f"❌ Job Queue: Daily reminder job is NOT scheduled!")

        report_str = "\n".join(health_report)
        await show_success_animation(update, context, report_str, loading_msg.message_id)

    except Exception as e:
        logger.error(f"Error during health check: {e}")
        await show_error_animation(update, context, "Health check failed to complete.", loading_msg.message_id if loading_msg else None)

async def handle_admin_tool_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles callbacks from the admin system tools menu."""
    query = update.callback_query
    data = query.data

    if data == "tool_backup":
        await tool_backup_callback(update, context)
    elif data == "tool_clean":
        await tool_clean_callback(update, context)
    elif data == "tool_export":
        await tool_export_users_callback(update, context)
    elif data == "tool_health":
        await tool_health_check_callback(update, context)
    else:
        await query.answer("Unknown tool command.")

async def post_init(application: Application) -> None:
    """Enhanced bot initialization with comprehensive command setup."""
    try:
        # Create initial backup when bot starts
        await create_backup()

        # User commands
        user_commands = [
            BotCommand("start", "🚀 Start/Restart Bot"),
            BotCommand("help", "❓ Complete Guide & Help"),
            BotCommand("claim", f"{EMOJIS['gift']} Claim Daily Bonus"),
            BotCommand("wallet", f"{EMOJIS['bank']} View My Vault"),
            BotCommand("withdraw", f"{EMOJIS['cash']} Withdraw Funds"),
            BotCommand("linkupi", f"{EMOJIS['diamond']} Set/Update UPI"),
            BotCommand("refer", f"{EMOJIS['rocket']} Invite Friends"),
            BotCommand("tasks", f"{EMOJIS['magic']} View Available Tasks"),
            BotCommand("stats", "📊 My Earning Statistics"),
        ]
        await application.bot.set_my_commands(user_commands)

        admin_commands = user_commands + [
            BotCommand("admin", f"{EMOJIS['crown']} Admin Dashboard"),
            BotCommand("broadcast", "📤 Send Broadcast Message"),
            BotCommand("users", "👥 View All Users"),
            BotCommand("withdrawals", "💸 Manage Withdrawals"),
            BotCommand("createtask", "➕ Create New Task"),
            BotCommand("cleantasks", "🧹 Clean Expired Tasks"),
        ]
        await application.bot.set_my_commands(
            admin_commands, 
            scope=BotCommandScopeChat(chat_id=ADMIN_ID)
        )

        await application.bot.set_my_description(
            f"💰 Earn money daily! Get ₹{MIN_REWARD}-{MAX_REWARD} daily bonuses, "
            f"complete tasks, invite friends, and withdraw at ₹{MIN_WITHDRAWAL}!"
        )
        
        await application.bot.set_my_short_description(
            f"💰 Daily earning bot with tasks & referrals!"
        )

        logger.info("✅ Bot initialization completed successfully!")
        
        try:
            startup_msg = (
                f"🤖 *BOT STARTED SUCCESSFULLY* 🤖\n\n"
                f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🆔 Bot ID: @{(await application.bot.get_me()).username}\n"
                f"👑 Admin ID: {ADMIN_ID}\n\n"
                f"📊 *Configuration:*\n"
                f"• Daily reward: ₹{MIN_REWARD}-{MAX_REWARD}\n"
                f"• Min withdrawal: ₹{MIN_WITHDRAWAL}\n"
                f"• Referral bonus: ₹{REFERRAL_BONUS}\n\n"
                f"✅ Bot is ready for users!"
            )
            
            await application.bot.send_message(
                chat_id=ADMIN_ID,
                text=startup_msg,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.warning(f"Could not send startup notification to admin: {e}")

    except Exception as e:
        logger.error(f"Error in post_init: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.error(f"Exception while handling an update: {context.error}")
        
        user_id = "Unknown"
        if isinstance(update, Update) and update.effective_user:
            user_id = update.effective_user.id
        
        logger.error(f"Error occurred for user {user_id}: {context.error}")
        
        if not hasattr(context.bot_data, 'last_error_notification'):
            context.bot_data['last_error_notification'] = 0
        
        now = time.time()
        if now - context.bot_data['last_error_notification'] > 300:  # 5 minutes
            try:
                error_msg = (
                    f"🔴 *BOT ERROR ALERT* 🔴\n\n"
                    f"👤 User: {user_id}\n"
                    f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}\n"
                    f"❌ Error: `{str(context.error)[:100]}...`\n\n"
                    f"Check logs for details."
                )
                
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=error_msg,
                    parse_mode=ParseMode.MARKDOWN
                )
                context.bot_data['last_error_notification'] = now
            except Exception:
                pass
        
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ Something went wrong! Please try again or contact admin if the problem persists.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Error in error handler: {e}")
        
async def create_backup() -> bool:
    """Creates backup of all data files."""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        
        files_to_backup = [USERS_FILE, TASKS_FILE, WITHDRAWALS_FILE]
        
        for file in files_to_backup:
            if os.path.exists(file):
                backup_file = os.path.join(backup_dir, file)
                with open(file, 'r', encoding='utf-8') as src:
                    with open(backup_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
        
        logger.info(f"✅ Backup created: {backup_dir}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        return False

def main() -> None:
    """Enhanced main function with comprehensive setup."""
    if BOT_TOKEN in ["YOUR_TELEGRAM_BOT_TOKEN", ""]:
        print("🚨 ERROR: Please set your BOT_TOKEN!")
        return
    
    if ADMIN_ID in [123456789, 0]:
        print("🚨 ERROR: Please set your ADMIN_ID!")
        return

    try:
        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .post_init(post_init)
            .concurrent_updates(True)
            .build()
        )
        
        admin_filter = filters.User(user_id=ADMIN_ID)

        task_conv_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^➕ Create Task$') & admin_filter, create_task_start)],
            states={
                ASK_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel)],
                ASK_REWARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reward)],
                ASK_EXPIRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_expiry)],
            },
            fallbacks=[
                CommandHandler('cancel', cancel_conversation),
                MessageHandler(filters.COMMAND, cancel_conversation)
            ],
            per_user=True,
            per_chat=True
        )

        main_conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f'^{EMOJIS["diamond"]} Set UPI$'), link_upi_start),
                CommandHandler('linkupi', link_upi_start),
                CallbackQueryHandler(link_upi_start, pattern='^setup_upi$'),
                MessageHandler(filters.Regex('^📤 Broadcast Text$') & admin_filter, broadcast_start),
                MessageHandler(filters.Regex('^🖼️ Broadcast Image$') & admin_filter, broadcast_photo_start),
            ],
            states={
                LINK_UPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, link_upi_receive)],
                BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_receive)],
                BROADCAST_PHOTO: [MessageHandler(filters.PHOTO & ~filters.COMMAND, broadcast_photo_receive)],
            },
            fallbacks=[
                CommandHandler('cancel', cancel_conversation),
                MessageHandler(filters.COMMAND, cancel_conversation)
            ],
            per_user=True,
            per_chat=True
        )

        handlers = [
            task_conv_handler,
            main_conv_handler,
            
            CommandHandler("start", start_command),
            CommandHandler("help", help_command),
            CommandHandler("admin", admin_command),
            CommandHandler("claim", claim_reward),
            CommandHandler("wallet", my_wallet),
            CommandHandler("withdraw", withdraw),
            CommandHandler("refer", refer_command),
            CommandHandler("stats", show_user_stats),
            CommandHandler("tasks", show_tasks),
            CommandHandler("linkupi", link_upi_start),
            
            CommandHandler("broadcast", broadcast_start, filters=admin_filter),
            CommandHandler("users", view_users, filters=admin_filter),
            CommandHandler("withdrawals", view_withdrawals, filters=admin_filter),
            CommandHandler("createtask", create_task_start, filters=admin_filter),
            CommandHandler("cleantasks", clean_expired_tasks, filters=admin_filter),
            
            CallbackQueryHandler(toggle_notifications_callback, pattern='^toggle_notifications$'),
            CallbackQueryHandler(verify_membership_callback, pattern='^verify:'),
            CallbackQueryHandler(remove_task_callback, pattern='^remove:'),
            CallbackQueryHandler(handle_admin_tool_callback, pattern='^tool_'),
            CallbackQueryHandler(handle_callback_query),
            
            MessageHandler(
                filters.Regex(f'^({EMOJIS["notify"]} Notifications)$'), 
                notifications_menu
            ),
            MessageHandler(
                filters.Regex('^(📤 Broadcast Text|🖼️ Broadcast Image|📊 Detailed Stats|👥 User List|💸 Withdrawal Requests|🔧 System Tools|➕ Create Task|🗑️ Remove Task|🧹 Clean Expired Tasks|⬅️ Back to Main)$') & admin_filter, 
                handle_admin_message
            ),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        ]

        application.add_handlers(handlers)
        
        application.add_error_handler(error_handler)

        job_queue = application.job_queue
        ist = ZoneInfo("Asia/Kolkata")
        job_queue.run_daily(send_daily_reminders, time=dt_time(hour=10, minute=0, tzinfo=ist), name="daily_reminder_job")


        print("=" * 60)
        print("🤖 TELEGRAM EARNING BOT")
        print("=" * 60)
        print(f"🚀 Bot is starting...")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print(f"💰 Minimum withdrawal: ₹{MIN_WITHDRAWAL}")
        print(f"🎁 Daily reward range: ₹{MIN_REWARD} - ₹{MAX_REWARD}")
        print(f"🤝 Referral bonus: ₹{REFERRAL_BONUS}")
        print(f"🔥 Streak rewards: 3d→₹{STREAK_REWARDS[3]}, 7d→₹{STREAK_REWARDS[7]}, 30d→₹{STREAK_REWARDS[30]}, 100d→₹{STREAK_REWARDS[100]}")
        print("=" * 60)
        print("✅ Bot is running successfully!")
        print("💡 Press Ctrl+C to stop the bot")
        print("=" * 60)
        
        # The initial backup is now handled by post_init
        
        # Run the bot
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )

    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.critical(f"Critical error starting bot: {e}")
        print(f"❌ Failed to start bot: {e}")
        print("🔧 Check your BOT_TOKEN and network connection")

if __name__ == '__main__':
    keep_alive()
    main()

