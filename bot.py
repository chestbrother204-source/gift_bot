from keep_alive import keep_alive
import logging
import json
import os
import time
import re
from datetime import datetime, timedelta, time as dt_time
from random import uniform, choice, randint
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand, BotCommandScopeChat
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest, Forbidden
import asyncio
from typing import Dict, Any, Tuple

# --- CONFIGURATION ---
# IMPORTANT: Replace these with your actual bot token and admin ID
BOT_TOKEN = "8310636090:AAFcFbpeCH-fqm0pNzAi7Ng1hWDw7wF72Xs"
ADMIN_ID = 7258860451
MIN_WITHDRAWAL = 1000.0
MIN_REWARD = 0.1
MAX_REWARD = 2.0
REFERRAL_BONUS = 1.0
COIN_CONVERSION_RATE = 5 # 5 coins = 1 Rupee
USERS_FILE = 'users.json'
WITHDRAWALS_FILE = 'withdrawals.json'
TASKS_FILE = 'tasks.json'
SETTINGS_FILE = 'settings.json' # New settings file
BACKUP_INTERVAL = 3600 # Backup every hour

# --- ANTI-SPAM & RATE LIMITING CONFIG ---
USER_COOLDOWN = {} # Stores user last action timestamp
RATE_LIMIT_SECONDS = 1.0 # Allow one action per second
SPAM_WARN_MESSAGE = "⏳ Please slow down! Try again in a moment."

# --- UI & ANIMATION SETTINGS ---
EMOJIS = {
    'money': '💰', 'gift': '🎁', 'rocket': '🚀', 'star': '⭐', 'fire': '🔥',
    'diamond': '💎', 'crown': '👑', 'trophy': '🏆', 'party': '🎉', 'cash': '💵',
    'bank': '🏦', 'coin': '🪙', 'gem': '💠', 'magic': '✨', 'lightning': '⚡',
    'clock': '⏰', 'success': '✅', 'error': '❌', 'notify': '🔔', 'airdrop': '💧',
    'leaderboard': '🏆', 'shield': '🛡️', 'achievement': '🏅', 'feedback': '📝',
    'quiz': '❓', 'social': '🌐', 'game': '🎮', 'convert': '🔄',
    'settings': '⚙️', 'back': '🔙'
}

TYPING_DELAY = 0.5        # Seconds to show typing indicator
LOADING_DURATION = 1.2 # Slightly faster for a snappier feel

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
    'leaderboard': '✦ RANKING CALCULATOR ✦',
    'achievements': '✦ ACHIEVEMENT HALL ✦',
    'feedback': '✦ MESSAGE TRANSPORTER ✦',
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
    'admin_health': '✦ SYSTEM DIAGNOSTICS ✦',
    'admin_airdrop': '✦ AIRDROP INITIATION ✦',
    'coin_convert': '✦ COIN CONVERTER ✦',
    'adjust_balance': '✦ BALANCE ADJUSTMENT ✦',
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
STREAK_REWARDS = {
    3: 1.0, 7: 2.0, 30: 5.0, 100: 10.0
}

# --- REFERRAL MILESTONE BONUSES ---
REFERRAL_MILESTONES = {
    5: {'cash': 3.0, 'coins': 0}, 10: {'cash': 10.0, 'coins': 20},
    50: {'cash': 75.0, 'coins': 50}, 100: {'cash': 200.0, 'coins': 100},
    1000: {'cash': 2000.0, 'coins': 500},
}

# --- NEW: ACHIEVEMENTS CONFIG ---
ACHIEVEMENTS = {
    # Claim-based
    'claim_1': {'name': 'First Claim', 'emoji': '🥇', 'desc': 'Claim your first daily bonus.', 'type': 'total_claims', 'value': 1},
    'claim_10': {'name': 'Consistent Clicker', 'emoji': '🥈', 'desc': 'Claim the daily bonus 10 times.', 'type': 'total_claims', 'value': 10},
    'claim_50': {'name': 'Habitual Earner', 'emoji': '🥉', 'desc': 'Claim the daily bonus 50 times.', 'type': 'total_claims', 'value': 50},
    'claim_100': {'name': 'Centurion', 'emoji': '💯', 'desc': 'Claim the daily bonus 100 times.', 'type': 'total_claims', 'value': 100},

    # Referral-based
    'refer_1': {'name': 'First Invitation', 'emoji': '🤝', 'desc': 'Successfully refer your first friend.', 'type': 'referrals', 'value': 1},
    'refer_10': {'name': 'Community Builder', 'emoji': '👨‍👩‍👧‍👦', 'desc': 'Successfully refer 10 friends.', 'type': 'referrals', 'value': 10},
    'refer_50': {'name': 'Influencer', 'emoji': '🌟', 'desc': 'Successfully refer 50 friends.', 'type': 'referrals', 'value': 50},

    # Task-based
    'task_1': {'name': 'Task Taker', 'emoji': '📝', 'desc': 'Complete your first task.', 'type': 'tasks', 'value': 1},
    'task_20': {'name': 'Task Master', 'emoji': '🦾', 'desc': 'Complete 20 tasks.', 'type': 'tasks', 'value': 20},
    'task_100': {'name': 'Task Legend', 'emoji': '🏆', 'desc': 'Complete 100 tasks.', 'type': 'tasks', 'value': 100},
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

async def show_success_animation(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, original_message_id: int = None, reply_markup=None):
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
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(chat_id, f"{EMOJIS['success']} *Success!*\n\n{message}", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
    except Exception as e:
        logger.debug(f"Success animation error: {e}")
        await safe_send_message(update, context, f"{EMOJIS['success']} {message}", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def show_error_animation(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, original_message_id: int = None, reply_markup=None):
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
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(chat_id, f"{EMOJIS['error']} *Error!*\n\n{message}", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    except Exception as e:
        logger.debug(f"Error animation error: {e}")
        await safe_send_message(update, context, f"{EMOJIS['error']} {message}", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# --- ENHANCED DATA HANDLING (In-memory cache with periodic saves) ---
def load_data(filepath: str) -> Dict[str, Any]:
    """Safely loads data from a JSON file with backup recovery."""
    if not os.path.exists(filepath):
        if filepath == SETTINGS_FILE:
            default_settings = {"coin_convert_enabled": False}
            save_data(default_settings, SETTINGS_FILE)
            return default_settings
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, dict) or isinstance(data, list) else {} # Added list support for safety
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

def save_data(data: Any, filepath: str) -> bool: # Changed type hint to Any for flexibility
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
        
        # Verify write
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        
        return True
    except Exception as e:
        logger.error(f"Critical error saving {filepath}: {e}")
        return False

async def save_all_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job to save all in-memory data to disk."""
    if not context.bot_data:
        return
    logger.info("Running scheduled data save...")
    
    users_data = context.bot_data.get('users', {})
    tasks_data = context.bot_data.get('tasks', {})
    withdrawals_data = context.bot_data.get('withdrawals', {})
    settings_data = context.bot_data.get('settings', {})
    
    save_data(users_data, USERS_FILE)
    save_data(tasks_data, TASKS_FILE)
    save_data(withdrawals_data, WITHDRAWALS_FILE)
    save_data(settings_data, SETTINGS_FILE)
    logger.info("Data saved successfully.")

# --- CONVERSATION STATES ---
(
    LINK_UPI, BROADCAST_MESSAGE, ASK_CHANNEL, ASK_REWARD, ASK_EXPIRY,
    BROADCAST_PHOTO, AIRDROP_ASK_CASH, AIRDROP_ASK_COINS,
    # New States
    ASK_FEEDBACK,
    ASK_TASK_TYPE, ASK_QUIZ_QUESTION, ASK_QUIZ_ANSWER, ASK_SOCIAL_LINK,
    GAME_GUESS_NUMBER, ASK_COIN_CONVERT, ASK_CHANNEL_TITLE, ASK_CHANNEL_ID,
    ADJUST_BALANCE_ID, ADJUST_BALANCE_CASH, ADJUST_BALANCE_COIN
) = range(20)  # Update the range to include the new states


# --- UTILITY FUNCTIONS ---
def is_rate_limited(user_id: str) -> bool:
    """Checks if a user is sending messages too frequently."""
    now = time.time()
    last_action_time = USER_COOLDOWN.get(user_id, 0)
    
    if now - last_action_time < RATE_LIMIT_SECONDS:
        return True
        
    USER_COOLDOWN[user_id] = now
    return False

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

# --- Gamification - Streak Progress Bar ---
def get_streak_progress_bar(streak_count: int) -> Tuple[str, str]:
    """Generates a visual progress bar for the next streak milestone."""
    sorted_milestones = sorted(STREAK_REWARDS.keys())
    
    next_milestone = None
    for m in sorted_milestones:
        if streak_count < m:
            next_milestone = m
            break
    
    if not next_milestone:
        return "🔥 Max Streak!", ""

    prev_milestone = 0
    for m in sorted(sorted_milestones, reverse=True):
        if streak_count >= m:
            prev_milestone = m
            break

    total_steps = next_milestone - prev_milestone
    current_steps = streak_count - prev_milestone
    
    progress_fraction = current_steps / total_steps
    filled_blocks = int(progress_fraction * 10)
    empty_blocks = 10 - filled_blocks
    
    bar = '▓' * filled_blocks + '░' * empty_blocks
    
    progress_text = f"`{bar}`\n`({streak_count}/{next_milestone} days)`"
    
    days_to_go = next_milestone - streak_count
    next_bonus_amount = STREAK_REWARDS[next_milestone]
    milestone_info = f"🎯 *Next bonus in {days_to_go} day(s): ₹{format_number(next_bonus_amount)} extra!*"
    
    return progress_text, milestone_info


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

# --- NEW: ACHIEVEMENT SYSTEM ---
async def check_and_grant_achievements(user_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Checks user stats against achievement criteria and grants new ones."""
    users_data = context.bot_data.get('users', {})
    user_data = users_data.get(user_id)
    if not user_data:
        return

    unlocked_achievements = user_data.get('achievements', [])
    
    stats = {
        'total_claims': user_data.get('total_claims', 0),
        'referrals': user_data.get('referrals', 0),
        'tasks': len(user_data.get('completed_tasks', []))
    }

    for achievement_id, details in ACHIEVEMENTS.items():
        if achievement_id not in unlocked_achievements:
            stat_type = details['type']
            required_value = details['value']
            
            if stats.get(stat_type, 0) >= required_value:
                # UNLOCK ACHIEVEMENT
                user_data.setdefault('achievements', []).append(achievement_id)
                
                # Notify User
                notification_text = (
                    f"🎉 *ACHIEVEMENT UNLOCKED* 🎉\n\n"
                    f"{details['emoji']} *{details['name']}*\n"
                    f"_{details['desc']}_\n\n"
                    f"Your dedication is paying off! Keep up the great work."
                )
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=notification_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.warning(f"Failed to send achievement notification to {user_id}: {e}")

    # No need to call save_data here, a background job will handle it
    # This function is called after every major action, so a full save is not needed

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
        users_data = context.bot_data.setdefault('users', {})
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
                'level': "Starter",
                'achievements': [],
                'total_claims': 0,
            }
            
            if context.args:
                referrer_id = context.args[0]
                if referrer_id in users_data and referrer_id != user_id:
                    # Standard referral bonus
                    users_data[user_id]['balance'] += REFERRAL_BONUS
                    users_data[user_id]['total_earned'] += REFERRAL_BONUS
                    users_data[referrer_id]['balance'] += REFERRAL_BONUS
                    users_data[referrer_id]['total_earned'] += REFERRAL_BONUS
                    users_data[referrer_id]['referrals'] += 1
                    
                    # Send standard welcome and notification
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
                    
                    # --- Check for Referral Milestones ---
                    new_referral_count = users_data[referrer_id]['referrals']
                    milestone_bonus = REFERRAL_MILESTONES.get(new_referral_count)

                    if milestone_bonus:
                        cash_bonus = milestone_bonus['cash']
                        coin_bonus = milestone_bonus['coins']
                        
                        users_data[referrer_id]['balance'] += cash_bonus
                        users_data[referrer_id]['total_earned'] += cash_bonus
                        users_data[referrer_id]['coin_balance'] = users_data[referrer_id].get('coin_balance', 0) + coin_bonus

                        try:
                            milestone_msg = (
                                f"🎉 *REFERRAL MILESTONE REACHED!* 🎉\n\n"
                                f"🏆 You've invited *{new_referral_count} friends*!\n"
                                f"🎁 As a bonus, you've received:\n"
                                f"  - 💰 *₹{cash_bonus:.2f}* Cash\n"
                                f"  - 🪙 *{coin_bonus}* Coins\n\n"
                                f"🔥 Keep inviting to unlock the next milestone!"
                            )
                            await context.bot.send_message(
                                chat_id=referrer_id,
                                text=milestone_msg,
                                parse_mode=ParseMode.MARKDOWN
                            )
                        except Exception as e:
                            logger.warning(f"Failed to notify referrer {referrer_id} about milestone: {e}")
                    
                    # Check achievements for the referrer
                    await check_and_grant_achievements(referrer_id, context)
        
        user_data = users_data.get(user_id, {})
        level_info = get_level_info(user_data.get('balance', 0))
        
        first_name = user.first_name or "Friend"
        if is_new_user and not context.args:
            welcome_text = f"🌟 *Welcome to EarnBot, {first_name}!* 🌟\n\n🎯 Your earning adventure begins now!\n🏅 Current Level: {level_info['emoji']} *{level_info['name']}*\n\n💡 *Quick Start:*\n• 🎁 Claim your daily bonus\n• ✨ Complete simple tasks\n• 💌 Invite friends for bigger rewards\n\n*{choice(QUOTES)}*"
            if loading_msg:
                await show_success_animation(update, context, welcome_text, loading_msg.message_id)
            else:
                await safe_send_message(update, context, welcome_text, parse_mode=ParseMode.MARKDOWN)
        elif not is_new_user:
            welcome_text = f"👋 *Welcome back, {first_name}!* \n\n🏅 Level: {level_info['emoji']} *{level_info['name']}*\n💰 Balance: *₹{format_number(user_data.get('balance', 0))}*\n🪙 Coins: *{user_data.get('coin_balance', 0)}*\n\n*{choice(QUOTES)}*"
            if loading_msg:
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
                except Exception:
                    pass
            await safe_send_message(update, context, welcome_text, parse_mode=ParseMode.MARKDOWN)
        
        # --- DYNAMIC KEYBOARD ---
        keyboard = [
            [f"{EMOJIS['gift']} Daily Bonus", f"{EMOJIS['magic']} Tasks"],
            [f"{EMOJIS['bank']} My Vault", f"{EMOJIS['cash']} Withdraw"],
            [f"{EMOJIS['rocket']} Invite Friends", f"{EMOJIS['leaderboard']} Leaderboard"],
            ["📊 My Stats", f"{EMOJIS['achievement']} Achievements"],
            [f"{EMOJIS['diamond']} Set UPI", f"{EMOJIS['feedback']} Send Feedback"],
            ["❓ Help & Guide"]
        ]

        # Add Coin Convert button only if enabled by admin
        settings = context.bot_data.get('settings', {})
        if settings.get('coin_convert_enabled', False):
            for row in keyboard:
                if f"{EMOJIS['feedback']} Send Feedback" in row:
                    feedback_index = row.index(f"{EMOJIS['feedback']} Send Feedback")
                    row.insert(feedback_index, f"{EMOJIS['convert']} Coin Convert")
                    break
        
        if user_id == str(ADMIN_ID):
            keyboard.append([f"{EMOJIS['crown']} Admin Panel"])

        reply_markup = ReplyKeyboardMarkup(
            keyboard, 
            resize_keyboard=True, 
            input_field_placeholder="Choose your action..."
        )
        
        main_menu_text = f"{EMOJIS['lightning']} *MAIN MENU* {EMOJIS['lightning']}"
        await safe_send_message(
            update, context,
            main_menu_text, 
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
        user_id = get_user_id(update)
        if is_rate_limited(user_id):
            return

        text = update.message.text

        action_map = {
            f"{EMOJIS['gift']} Daily Bonus": claim_reward,
            f"{EMOJIS['magic']} Tasks": show_tasks,
            f"{EMOJIS['bank']} My Vault": my_wallet,
            f"{EMOJIS['cash']} Withdraw": withdraw,
            f"{EMOJIS['rocket']} Invite Friends": refer_command,
            f"{EMOJIS['leaderboard']} Leaderboard": leaderboard_command,
            f"{EMOJIS['achievement']} Achievements": show_achievements,
            f"{EMOJIS['feedback']} Send Feedback": feedback_start,
            f"{EMOJIS['diamond']} Set UPI": link_upi_start,
            "📊 My Stats": show_user_stats,
            f"{EMOJIS['convert']} Coin Convert": coin_convert_start,
            "❓ Help & Guide": help_command,
            f"{EMOJIS['crown']} Admin Panel": admin_command,
            "⬅️ Back to Main": start_command
        }
        
        # Admin message handling
        admin_map = {
            "📤 Broadcast Text": broadcast_start,
            "🖼️ Broadcast Image": broadcast_photo_start,
            f"{EMOJIS['money']} Adjust User Balance": adjust_balance_start,
            "📊 Detailed Stats": detailed_stats,
            "👥 User List": view_users,
            "💸 Withdrawal Requests": view_withdrawals,
            "🔧 System Tools": system_tools,
            f"{EMOJIS['airdrop']} Airdrop": airdrop_start,
            "➕ Create Task": create_task_start,
            "🗑️ Remove Task": remove_task_start,
            "🧹 Clean Expired Tasks": clean_expired_tasks,
        }

        if user_id == str(ADMIN_ID) and text in admin_map:
            await show_typing(update, context)
            await admin_map[text](update, context)
        elif text.startswith(f"{EMOJIS['settings']} Coin Convert") and user_id == str(ADMIN_ID):
            await show_typing(update, context)
            await toggle_coin_convert(update, context)
        elif text in action_map:
            await show_typing(update, context)
            await action_map[text](update, context)
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
    users_data = context.bot_data.get('users', {})
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
        explanation = "You will receive reminders 24 hours after your last claim."
    else:
        status_emoji = "❌"
        status_text = "Disabled"
        button_emoji = "🔔"
        button_text = "Enable Notifications"
        explanation = "You will not receive any claim reminders."

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
    users_data = context.bot_data.get('users', {})
    
    if user_id in users_data:
        current_status = users_data[user_id].get('notifications_enabled', True)
        users_data[user_id]['notifications_enabled'] = not current_status
        await notifications_menu(update, context)
    else:
        await query.edit_message_text("Could not find your data. Please use /start again.")

async def claim_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced daily reward system with updated streaks and bonuses."""
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['claim'])
        
        user_id = get_user_id(update)
        users_data = context.bot_data.get('users', {})
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
                user['streak_count'] = 1 # Streak broken
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
        user['total_claims'] = user.get('total_claims', 0) + 1 # Increment total claims
        
        # Check for achievements after saving
        await check_and_grant_achievements(user_id, context)


        # Schedule the next reminder
        job_name = f'reminder_{user_id}'
        # Remove any existing reminder job for this user to avoid duplicates
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()
            logger.info(f"Removed existing reminder job for user {user_id}")

        # Schedule a new reminder for 24 hours from now
        context.job_queue.run_once(
            send_single_reminder,
            when=timedelta(hours=24),
            name=job_name,
            data={'user_id': user_id, 'first_name': user.get('first_name', 'there')}
        )
        logger.info(f"Scheduled next reminder for user {user_id} in 24 hours.")

        level_info = get_level_info(user['balance'])
        
        reward_msg = f"💰 Base Reward: *₹{format_number(base_reward)}*\n🔥 Streak Bonus: *+₹{format_number(streak_bonus)}* extra!\n💎 Total Earned: *₹{format_number(total_reward)}*\n📊 New Balance: *₹{format_number(user['balance'])}*\n⚡ Current Streak: *{streak_count} days*\n🏅 Level: {level_info['emoji']} *{level_info['name']}*"
        
        # New Streak Progress Bar
        progress_bar, milestone_info = get_streak_progress_bar(streak_count)
        if milestone_info:
            reward_msg += f"\n\n*Streak Progress:*\n{progress_bar}\n{milestone_info}"

        if loading_msg:
            await show_success_animation(update, context, reward_msg, loading_msg.message_id)

    except Exception as e:
        logger.error(f"Error in claim_reward: {e}")
        await show_error_animation(update, context, "Unable to process your bonus right now.", None)

async def my_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['wallet'])
        
        user_id = get_user_id(update)
        users_data = context.bot_data.get('users', {})
        user = users_data.get(user_id)

        if not user:
            if loading_msg:
                await show_error_animation(update, context, "User data not found. Starting setup...", loading_msg.message_id)
            await start_command(update, context)
            return

        balance = user.get('balance', 0.0)
        coin_balance = user.get('coin_balance', 0)
        upi = user.get('upi')
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
        
        wallet_msg = "🏦 *YOUR DIGITAL VAULT* 🏦" + "\n\n"
        wallet_msg += f"💰 *Cash Balance:* `₹{format_number(balance)}`\n🪙 *Coin Balance:* `{coin_balance}`\n📊 *Total Earned:* `₹{format_number(total_earned)}`\n🔥 *Current Streak:* `{streak} days`\n👥 *Referrals:* `{referrals}`\n\n🏅 *Current Level:* {level_info['emoji']} *{level_info['name']}*"
        
        if progress_bar:
            wallet_msg += f"\n📈 *Next Level Progress:*\n`{progress_bar}`" + "\n\n"

        # New Streak Progress Bar
        streak_progress_bar, _ = get_streak_progress_bar(streak)
        wallet_msg += f"*Streak Progress:*\n{streak_progress_bar}" + "\n\n"

        wallet_msg += f"💳 *UPI ID:* `{upi}`" if upi else f"💳 *UPI ID:* `Not Set`"
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJIS['gift']} Claim Daily", callback_data="quick_claim")],
            [InlineKeyboardButton(f"{EMOJIS['cash']} Withdraw", callback_data="quick_withdraw")]
        ]
        
        if balance < MIN_WITHDRAWAL:
            needed = MIN_WITHDRAWAL - balance
            wallet_msg += f"\n\n💡 _You're just *₹{format_number(needed)}* away from your first withdrawal!_"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await show_success_animation(update, context, wallet_msg, loading_msg.message_id, reply_markup=reply_markup)

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
        users_data = context.bot_data.get('users', {})
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
            f"📊 *YOUR EARNING PROFILE* 📊\n\n"
            f"📅 *Days Active:* {days_active}\n"
            f"💰 *Total Earned:* ₹{format_number(total_earned)}\n"
            f"✅ *Tasks Completed:* {completed_tasks}\n"
            f"👥 *Friends Referred:* {referrals}\n"
            f"🔥 *Current Streak:* {user.get('streak_count', 0)} days\n"
            f"🏅 *Current Level:* {level_info['emoji']} {level_info['name']}\n\n"
            f"📈 *Your Earnings Come From:*\n"
            f"  `• Daily bonuses & streaks`\n"
            f"  `• Task completions`\n"
            f"  `• Referral bonuses`\n\n"
            f"🎯 _Keep up the great work to climb the ranks!_"
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
        users_data = context.bot_data.get('users', {})
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

        users_data = context.bot_data.get('users', {})
        if user_id in users_data:
            old_upi = users_data[user_id].get('upi', 'None')
            users_data[user_id]['upi'] = upi_address
            
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
        users_data = context.bot_data.get('users', {})
        user = users_data.get(user_id)

        if not user:
            if loading_msg:
                await show_error_animation(update, context, "User data not found. Starting setup...", loading_msg.message_id)
            await start_command(update, context)
            return

        balance = user.get('balance', 0.0)
        upi = user.get('upi')

        if not upi:
            no_upi_msg = (
                f"⚠️ *UPI Required!*\n\n"
                f"💳 Link your UPI ID first to withdraw funds.\n"
                f"Use '{EMOJIS['diamond']} Set UPI' button in the main menu."
            )
            
            keyboard = [[InlineKeyboardButton(f"{EMOJIS['diamond']} Set UPI Now", callback_data="setup_upi")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await show_error_animation(update, context, no_upi_msg, loading_msg.message_id, reply_markup=reply_markup)
            return

        if balance < MIN_WITHDRAWAL:
            shortage = MIN_WITHDRAWAL - balance
            progress = int((balance / MIN_WITHDRAWAL) * 100)
            
            progress_bar = "█" * (progress // 10) + "░" * (10 - (progress // 10))
            
            insufficient_msg = (
                f"💡 *Keep Going!*\n\n"
                f"💰 Current Balance: *₹{format_number(balance)}*\n"
                f"🎯 Minimum Required: *₹{MIN_WITHDRAWAL:.0f}*\n"
                f"📉 _You're just *₹{format_number(shortage)}* away from your first withdrawal._\n\n"
                f"📊 *Withdrawal Progress:*\n`{progress_bar}` {progress}%\n\n"
                f"🚀 *Fastest Ways to Earn:*\n"
                f"  `•` {EMOJIS['rocket']} Invite friends (₹{REFERRAL_BONUS:.0f} each!)\n"
                f"  `•` {EMOJIS['magic']} Complete all available tasks"
            )
            
            keyboard = [
                [InlineKeyboardButton(f"{EMOJIS['rocket']} Invite Friends", callback_data="quick_refer")],
                [InlineKeyboardButton(f"{EMOJIS['magic']} View Tasks", callback_data="quick_tasks")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await show_error_animation(update, context, insufficient_msg, loading_msg.message_id, reply_markup=reply_markup)
            return

        withdrawals_data = context.bot_data.setdefault('withdrawals', {})
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
        
        user['balance'] = 0.0
        
        success_msg = (
            f"✅ *WITHDRAWAL SUBMITTED!* ✅\n\n"
            f"💰 Amount: *₹{format_number(balance)}*\n"
            f"💳 UPI: `{upi}`\n"
            f"🆔 Request ID: `{request_id}`\n\n"
            f"⏳ _Processing Time: 24-48 hours_\n"
            f"📱 _You'll receive a confirmation soon!_\n\n"
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
            f"💰 Amount: *₹{format_number(balance)}*\n"
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
        users_data = context.bot_data.get('users', {})
        user_data = users_data.get(user_id, {})
        referral_count = user_data.get('referrals', 0)
        
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        # Calculate next milestone
        next_milestone_val = 0
        sorted_milestones = sorted(REFERRAL_MILESTONES.keys())
        for m in sorted_milestones:
            if referral_count < m:
                next_milestone_val = m
                break
        
        refer_msg = (
            f"🚀 *INVITE & EARN PROGRAM* 🚀\n\n"
            f"💎 *Your Unique Link:*\n`{referral_link}`\n\n"
            f"🎁 *How It Works:*\n"
            f"  `•` Share your link with friends\n"
            f"  `•` They get *₹{REFERRAL_BONUS:.2f}* signup bonus\n"
            f"  `•` You get *₹{REFERRAL_BONUS:.2f}* referral bonus\n"
            f"  `•` _It's a win-win for everyone!_ 🎉\n\n"
            f"📊 *Your Stats:*\n"
            f"  `•` Friends Invited: *{referral_count}*\n"
        )

        if next_milestone_val:
            needed = next_milestone_val - referral_count
            refer_msg += f"  `•` Next Milestone: *{needed} more invites to reach {next_milestone_val}!* 🎯\n\n"
        else:
            refer_msg += "  `•` 🏆 _You've unlocked all referral milestones!_\n\n"

        refer_msg += (
            f"💡 *Pro Tips:*\n"
            f"  `•` Share in groups and social media\n"
            f"  `•` Tell friends about daily bonuses\n"
            f"  `•` Mention the easy tasks available!"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_link:{referral_link}")],
            [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={referral_link}&text=💰 Join me on this amazing earning bot! Get ₹{REFERRAL_BONUS:.0f} signup bonus! 🎁")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await show_success_animation(update, context, refer_msg, loading_msg.message_id, reply_markup=reply_markup)


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
            f"*{EMOJIS['gift']} Daily Bonus System*\n"
            f"  `•` Claim a random bonus every 24 hours.\n"
            f"  `•` Build streaks for *extra rewards* on top of your bonus!\n"
            f"  `  -` 3-Day Streak: *+₹{STREAK_REWARDS[3]:.2f} extra*\n"
            f"  `  -` 7-Day Streak: *+₹{STREAK_REWARDS[7]:.2f} extra*\n"
            f"  `  -` 30-Day Streak: *+₹{STREAK_REWARDS[30]:.2f} extra*\n"
            f"  `  -` 100-Day Streak: *+₹{STREAK_REWARDS[100]:.2f} extra*\n\n"
            f"*{EMOJIS['magic']} Task System*\n"
            f"  `•` Complete simple tasks like joining channels, answering quizzes, or playing mini-games to earn coins 🪙.\n\n"
            f"*{EMOJIS['rocket']} Referral Program*\n"
            f"  `•` Invite friends and you both get *₹{REFERRAL_BONUS:.2f}* when they start!\n"
            f"  `•` Reach milestones for huge extra bonuses!\n\n"
            f"*{EMOJIS['achievement']} Achievements*\n"
            f"  `•` Unlock badges for reaching milestones like inviting 10 friends or completing 20 tasks!\n\n"
            f"*{EMOJIS['cash']} Withdrawal System*\n"
            f"  `•` Minimum withdrawal: *₹{MIN_WITHDRAWAL:.0f}*\n"
            f"  `•` Payments via UPI within 24-48 hours.\n\n"
            f"*{EMOJIS['leaderboard']} Level System*\n"
            f"  `•` Earn more to level up from Starter 🌱 to Diamond 👑!\n\n"
            f"📞 *Need Help?* Use the '{EMOJIS['feedback']} Send Feedback' button to contact the admin."
        )
        
        keyboard = [
            [InlineKeyboardButton(f"{EMOJIS['gift']} Claim Daily Bonus", callback_data="quick_claim")],
            [InlineKeyboardButton(f"{EMOJIS['rocket']} Start Referring", callback_data="quick_refer")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await show_success_animation(update, context, help_msg, loading_msg.message_id, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        await show_error_animation(update, context, "Help system unavailable. Please try again!", None)

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE, force_new: bool = False) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['tasks'])
        
        user_id = get_user_id(update)
        tasks_data = context.bot_data.get('tasks', {})
        users_data = context.bot_data.get('users', {})
        user = users_data.get(user_id)
        
        if not user:
            if loading_msg:
                await show_error_animation(update, context, "User data not found. Starting setup...", loading_msg.message_id)
            await start_command(update, context)
            return
        
        now = datetime.now()
        
        available_tasks = []
        for tid, task in tasks_data.items():
            try:
                if task.get('status') != 'active':
                    continue
                
                expiry_str = task.get('expiry_date')
                if expiry_str:
                    expiry_date = datetime.fromisoformat(expiry_str)
                    if expiry_date <= now:
                        continue
                
                # Check if user has already completed the task
                if tid in user.get('completed_tasks', []):
                    continue

                available_tasks.append((tid, task))
            except KeyError as e:
                logger.error(f"Skipping malformed task with ID {tid}: Missing key {e}")
                continue
            except ValueError:
                logger.error(f"Skipping task with ID {tid}: Invalid expiry date format")
                continue

        if not available_tasks:
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
            
            await show_success_animation(update, context, no_tasks_msg, loading_msg.message_id, reply_markup=reply_markup)
            return

        if loading_msg:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=loading_msg.message_id
                )
            except:
                pass
        
        for task_id, task in available_tasks:
            reward = task.get('reward', 0)
            task_type = task.get('type', 'join')
            
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

            # --- DYNAMIC TASK DISPLAY ---
            if task_type == 'join':
                channel_identifier = task.get('channel_username', '')
                channel_title = task.get('channel_title', 'Unknown Channel')
                
                if task.get('is_private', False):
                    join_url = channel_identifier
                    verify_data = f"verify:{task_id}:{task.get('channel_hash', '')}"
                else:
                    if isinstance(channel_identifier, str) and channel_identifier.startswith("https://t.me/+"):
                        join_url = channel_identifier
                        verify_data = f"verify:{task_id}:{channel_identifier}"
                    elif isinstance(channel_identifier, str):
                        join_url = f"https://t.me/{channel_identifier.replace('@','')}"
                        verify_data = f"verify:{task_id}:{channel_identifier}"
                    else: # Handle cases where channel_identifier is an int (from old tasks)
                        join_url = f"https://t.me/c/{str(channel_identifier).lstrip('-100')}"
                        verify_data = f"verify:{task_id}:{channel_identifier}"
                        logger.warning(f"Found non-string channel_identifier in task {task_id}. Assuming it's an old chat ID.")

                task_msg = (
                    f"{EMOJIS['magic']} *NEW JOIN TASK AVAILABLE* ✨\n\n"
                    f"📺 Channel: `{channel_title}`\n"
                    f"🪙 Reward: *{reward} Coins*\n"
                    f"{time_left_str}\n\n"
                    f"📝 *Instructions:*\n"
                    f"1️⃣ Click 'Join Channel' button\n"
                    f"2️⃣ Join the channel\n"
                    f"3️⃣ Click 'Verify' to claim reward\n\n"
                )
                keyboard = [
                    [InlineKeyboardButton("1️⃣ Join Channel 🔗", url=join_url)],
                    [InlineKeyboardButton("2️⃣ Verify Membership ✅", callback_data=verify_data)]
                ]
            
            elif task_type == 'quiz':
                question = task.get('question', 'No question provided.')
                task_msg = (
                    f"{EMOJIS['quiz']} *NEW QUIZ TASK AVAILABLE* ❓\n\n"
                    f"🤔 *Question:* {question}\n"
                    f"🪙 Reward: *{reward} Coins*\n"
                    f"{time_left_str}\n\n"
                    f"📝 *Instructions:*\n"
                    f"1️⃣ Click 'Answer Quiz' button\n"
                    f"2️⃣ Send your answer in the chat\n"
                )
                keyboard = [
                    [InlineKeyboardButton("✍️ Answer Quiz", callback_data=f"start_quiz:{task_id}")]
                ]

            elif task_type == 'social':
                link = task.get('link', 'https://telegram.org')
                task_msg = (
                    f"{EMOJIS['social']} *NEW SOCIAL TASK AVAILABLE* 🌐\n\n"
                    f"🔗 *Link:* [Click Here to View]({link})\n"
                    f"🪙 Reward: *{reward} Coins*\n"
                    f"{time_left_str}\n\n"
                    f"📝 *Instructions:*\n"
                    f"1️⃣ Visit the link above.\n"
                    f"2️⃣ Complete the required action (e.g., follow, like).\n"
                    f"3️⃣ Click 'I've Completed It' below to claim your reward.\n"
                )
                keyboard = [
                    [InlineKeyboardButton("✅ I've Completed It!", callback_data=f"claim_social:{task_id}")]
                ]

            elif task_type == 'game':
                task_msg = (
                    f"{EMOJIS['game']} *NEW GAME TASK AVAILABLE* 🎮\n\n"
                    f"🎲 *Game:* Guess the Number!\n"
                    f"🪙 Reward: *{reward} Coins*\n"
                    f"{time_left_str}\n\n"
                    f"📝 *Instructions:*\n"
                    f"1️⃣ Click 'Play Game' to start.\n"
                    f"2️⃣ Guess the secret number between 1 and 20.\n"
                    f"3️⃣ You have 3 attempts!\n"
                )
                keyboard = [
                    [InlineKeyboardButton("▶️ Play Game", callback_data=f"start_game:{task_id}")]
                ]

            else: # Fallback for unknown task types
                continue

            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_send_message(
                update, context, task_msg, 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                force_new=True 
            )

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
        
        _, task_id, channel_identifier = callback_parts

        users_data = context.bot_data.get('users', {})
        tasks_data = context.bot_data.get('tasks', {})
        
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
            if task.get('is_private', False):
                channel_id = task.get('channel_id')
                if not channel_id:
                    error_text = "Cannot verify this private channel. Missing channel ID."
                    await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
                    return
                    
                member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                
                if member.status in ['member', 'administrator', 'creator']:
                    reward = task['reward']
                    user['coin_balance'] = user.get('coin_balance', 0) + reward
                    user.setdefault('completed_tasks', []).append(task_id)
                    
                    success_msg = (
                        f"✅ Membership verified!\n"
                        f"🪙 Earned: *{reward} Coins*\n"
                        f"💰 New Coin Balance: *{user['coin_balance']} Coins*\n\n"
                        f"🚀 Keep completing tasks to earn more!"
                    )
                    
                    await show_success_animation(update, context, success_msg, loading_msg.message_id if loading_msg else None)
                    await check_and_grant_achievements(user_id, context)
                else:
                    not_member_msg = (
                        f"❌ *Membership Not Found!*\n\n"
                        f"Please make sure you:\n"
                        f"1️⃣ Clicked 'Join Channel'\n"
                        f"2️⃣ Actually joined the channel\n"
                        f"3️⃣ Didn't immediately leave\n\n"
                        f"💡 Try joining again, then click verify!"
                    )
                    
                    await show_error_animation(update, context, not_member_msg, loading_msg.message_id if loading_msg else None)
                    
            else:
                member = await context.bot.get_chat_member(chat_id=channel_identifier, user_id=user_id)
                
                if member.status in ['member', 'administrator', 'creator']:
                    reward = task['reward']
                    user['coin_balance'] = user.get('coin_balance', 0) + reward
                    user.setdefault('completed_tasks', []).append(task_id)
                    
                    success_msg = (
                        f"✅ Membership verified!\n"
                        f"🪙 Earned: *{reward} Coins*\n"
                        f"💰 New Coin Balance: *{user['coin_balance']} Coins*\n\n"
                        f"🚀 Keep completing tasks to earn more!"
                    )
                    
                    await show_success_animation(update, context, success_msg, loading_msg.message_id if loading_msg else None)
                    await check_and_grant_achievements(user_id, context)
                else:
                    not_member_msg = (
                        f"❌ *Membership Not Found!*\n\n"
                        f"Please make sure you:\n"
                        f"1️⃣ Clicked 'Join Channel'\n"
                        f"2️⃣ Actually joined the channel\n"
                        f"3️⃣ Didn't immediately leave\n\n"
                        f"💡 Try joining again, then click verify!"
                    )
                    
                    await show_error_animation(update, context, not_member_msg, loading_msg.message_id if loading_msg else None)

        except BadRequest as e:
            error_msg = e.message.lower()
            if any(phrase in error_msg for phrase in ["user not found", "member not found", "user_not_participant"]):
                error_text = (
                    f"❌ *Verification Failed!*\n\n"
                    f"You haven't joined yet.\n"
                    f"Please join the channel first, then click verify!"
                )
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
            elif "chat not found" in error_msg:
                error_text = "This channel may no longer exist or be private."
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
            else:
                logger.error(f"Verification error for {channel_identifier}: {e}")
                error_text = "Cannot check this task right now. Admin has been notified."
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)

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

# --- NEW GAMIFICATION: LEADERBOARD ---
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the main leaderboard menu."""
    loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['leaderboard'])
    
    leaderboard_text = (
        f"{EMOJIS['leaderboard']} *Leaderboard*\n\n"
        "See who's at the top of their game! Select a category to view the rankings."
    )
    
    keyboard = [
        [InlineKeyboardButton("💰 Top by Balance", callback_data="lb_balance")],
        [InlineKeyboardButton("🚀 Top by Referrals", callback_data="lb_referrals")],
        [InlineKeyboardButton("✨ Top by Tasks", callback_data="lb_tasks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await show_success_animation(update, context, leaderboard_text, loading_msg.message_id, reply_markup=reply_markup)

async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles leaderboard category selection and displays rankings."""
    query = update.callback_query
    await query.answer("Calculating ranks...")
    
    if query.data == "lb_back":
        await start_command(update, context)
        await query.delete_message()
        return
        
    leaderboard_type = query.data.split('_', 1)[1]
    
    users_data = context.bot_data.get('users', {})
    
    if not users_data:
        await query.edit_message_text("No users to rank yet!")
        return
        
    if leaderboard_type == "balance":
        sorted_users = sorted(users_data.items(), key=lambda item: item[1].get('balance', 0), reverse=True)
        title = "💰 Top 10 by Balance"
        value_key = 'balance'
        formatter = lambda v: f"₹{format_number(v)}"
    elif leaderboard_type == "referrals":
        sorted_users = sorted(users_data.items(), key=lambda item: item[1].get('referrals', 0), reverse=True)
        title = "🚀 Top 10 by Referrals"
        value_key = 'referrals'
        formatter = lambda v: f"{v} invites"
    elif leaderboard_type == "tasks":
        sorted_users = sorted(users_data.items(), key=lambda item: len(item[1].get('completed_tasks', [])), reverse=True)
        title = "✨ Top 10 by Tasks Completed"
        value_key = 'completed_tasks'
        formatter = lambda v: f"{len(v)} tasks"
    else:
        return

    rank_emojis = ["🥇", "🥈", "🥉", "4.", "5.", "6.", "7.", "8.", "9.", "10."]
    
    leaderboard_text = f"{EMOJIS['leaderboard']} *{title}*\n\n"
    
    leaderboard_has_entries = False
    for i, (user_id, user_data) in enumerate(sorted_users[:10]):
        first_name = escape_markdown(user_data.get('first_name', 'User'))
        value = user_data.get(value_key, 0 if leaderboard_type != 'tasks' else [])
        
        # Don't show users with 0 score
        if (isinstance(value, list) and len(value) == 0) or (isinstance(value, (int, float)) and value == 0):
            continue

        leaderboard_has_entries = True
        leaderboard_text += f"{rank_emojis[i]} *{first_name}* - {formatter(value)}\n"

    if not leaderboard_has_entries:
        leaderboard_text += "_No one has made it to the leaderboard yet!_"

    keyboard = [
        [
            InlineKeyboardButton("💰 Balance", callback_data="lb_balance"),
            InlineKeyboardButton("🚀 Referrals", callback_data="lb_referrals"),
            InlineKeyboardButton("✨ Tasks", callback_data="lb_tasks")
        ],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="lb_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(leaderboard_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# --- NEW: Achievements Command ---
async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the user's unlocked and locked achievements."""
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['achievements'])
        user_id = get_user_id(update)
        users_data = context.bot_data.get('users', {})
        user_data = users_data.get(user_id)

        if not user_data:
            if loading_msg:
                await show_error_animation(update, context, "User data not found. Starting setup...", loading_msg.message_id)
            await start_command(update, context)
            return

        unlocked_ids = set(user_data.get('achievements', []))
        
        unlocked_text = ""
        locked_text = ""
        
        for achievement_id, details in ACHIEVEMENTS.items():
            if achievement_id in unlocked_ids:
                unlocked_text += f"{details['emoji']} *{details['name']}* - _{details['desc']}_\n"
            else:
                locked_text += f"❓ *{details['name']}* - _{details['desc']}_\n"
        
        if not unlocked_text:
            unlocked_text = "_You haven't unlocked any achievements yet. Keep earning!_\n"
            
        achievement_msg = (
            f"🏅 *YOUR ACHIEVEMENTS* 🏅\n\n"
            f"✅ *Unlocked:*\n{unlocked_text}\n"
            f"🔒 *Locked:*\n{locked_text}"
        )
        
        await show_success_animation(update, context, achievement_msg, loading_msg.message_id)

    except Exception as e:
        logger.error(f"Error in show_achievements: {e}")
        await show_error_animation(update, context, "Unable to load achievements. Please try again!")

# --- NEW: User Feedback System ---
async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the feedback conversation."""
    try:
        feedback_msg = (
            f"📝 *SEND FEEDBACK* 📝\n\n"
            f"Have a suggestion, question, or found a bug? We'd love to hear from you!\n\n"
            f"Please type your message below, or send a photo with a caption. It will be sent directly to the admin.\n\n"
            f"Type /cancel to abort."
        )
        await safe_send_message(
            update, context, feedback_msg,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
            force_new=True
        )
        return ASK_FEEDBACK
    except Exception as e:
        logger.error(f"Error in feedback_start: {e}")
        return ConversationHandler.END

async def feedback_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives feedback (text or photo) and forwards it to the admin."""
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['feedback'])
        user = update.effective_user

        admin_caption = (
            f"📝 *New Feedback Received*\n\n"
            f"👤 *From:* {escape_markdown(user.first_name or 'N/A')} (@{escape_markdown(user.username or 'N/A')})\n"
            f"🆔 *User ID:* `{user.id}`"
        )
        
        message_sent = False
        if update.message.photo:
            photo_id = update.message.photo[-1].file_id
            user_caption = update.message.caption or ""
            
            # Add user's caption to the admin message if it exists
            if user_caption:
                admin_caption += f"\n\n✉️ *Message:*\n{escape_markdown(user_caption)}"

            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo_id,
                caption=admin_caption,
                parse_mode=ParseMode.MARKDOWN
            )
            message_sent = True
        elif update.message.text:
            user_feedback = update.message.text
            admin_message = admin_caption + f"\n\n✉️ *Message:*\n\n{escape_markdown(user_feedback)}"
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode=ParseMode.MARKDOWN
            )
            message_sent = True
        else:
            await show_error_animation(update, context, "Unsupported feedback format. Please send text or a photo with a caption.", loading_msg.message_id)

        if message_sent:
            # Confirm to user
            confirmation_msg = (
                f"✅ *Feedback Sent!* ✅\n\n"
                f"Thank you for your message! The admin has received it and will review it soon.\n\n"
                f"Your input helps make this bot better for everyone! ✨"
            )
            await show_success_animation(update, context, confirmation_msg, loading_msg.message_id)

    except Exception as e:
        logger.error(f"Error in feedback_receive: {e}")
        await show_error_animation(update, context, "Sorry, there was an issue sending your feedback. Please try again later.")
    
    await start_command(update, context)
    return ConversationHandler.END


# --- SCHEDULED JOBS ---
async def send_single_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a personalized reminder to a single user 24 hours after their last claim."""
    job = context.job
    user_id = job.data['user_id']
    first_name = job.data['first_name']
    logger.info(f"Running single reminder job for user {user_id}")

    users_data = context.bot_data.get('users', {})
    user_data = users_data.get(str(user_id))

    if not user_data or not user_data.get('notifications_enabled', True):
        logger.info(f"User {user_id} has notifications disabled. Skipping reminder.")
        return

    last_claim_str = user_data.get('last_claim')
    if last_claim_str:
        last_claim_time = datetime.fromisoformat(last_claim_str)
        if datetime.now() - last_claim_time < timedelta(hours=24):
            logger.info(f"User {user_id} already claimed. Skipping reminder.")
            return

    try:
        reminder_message = (
            f"👋 Hey {first_name}!\n\n"
            f"🎁 Your daily bonus is ready to be claimed! Don't miss out on your reward and break your streak! 🔥"
        )
        keyboard = [[InlineKeyboardButton(f"{EMOJIS['gift']} Claim Now!", callback_data="quick_claim")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text=reminder_message,
            reply_markup=reply_markup
        )
    except Forbidden:
        logger.warning(f"User {user_id} has blocked the bot. Disabling notifications for them.")
        if user_data:
            users_data[str(user_id)]['notifications_enabled'] = False
            # Data is saved periodically, so no need for an immediate save here
    except Exception as e:
        logger.error(f"Failed to send single reminder to {user_id}: {e}")

async def backup_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodically creates backups and notifies the admin."""
    logger.info("Running scheduled backup job...")
    success = await create_backup()
    try:
        if success:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ *Automated Backup Successful!*\n\nData files were backed up at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"❌ *Automated Backup FAILED!*\n\nPlease check the bot logs for errors.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.error(f"Failed to send backup notification to admin: {e}")

# --- ADMIN FUNCTIONS ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if get_user_id(update) != str(ADMIN_ID):
            return

        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin'])
        
        users_data = context.bot_data.get('users', {})
        tasks_data = context.bot_data.get('tasks', {})
        withdrawals_data = context.bot_data.get('withdrawals', {})
        settings = context.bot_data.get('settings', {})
        
        total_users = len(users_data)
        active_tasks = len([t for t in tasks_data.values() if t.get('status') == 'active'])
        pending_withdrawals = len([w for w in withdrawals_data.values() if w.get('status') == 'pending'])
        total_balance = sum(user.get('balance', 0) for user in users_data.values())
        
        # Coin convert status
        convert_status = "ON" if settings.get('coin_convert_enabled') else "OFF"
        convert_button_text = f"{EMOJIS['settings']} Coin Convert: {convert_status}"

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
            [f"{EMOJIS['airdrop']} Airdrop", "➕ Create Task"],
            ["🗑️ Remove Task", "📊 Detailed Stats"],
            ["👥 User List", "💸 Withdrawal Requests"],
            [convert_button_text, "🔧 System Tools"],
            [f"{EMOJIS['money']} Adjust User Balance", "🧹 Clean Expired Tasks"],
            ["⬅️ Back to Main"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await show_success_animation(update, context, admin_msg, loading_msg.message_id, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in admin_command: {e}")
        await show_error_animation(update, context, "Admin panel error!")

async def detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_stats'])
        
        users_data = context.bot_data.get('users', {})
        tasks_data = context.bot_data.get('tasks', {})
        withdrawals_data = context.bot_data.get('withdrawals', {})
        
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
        
        await show_success_animation(update, context, stats_msg, loading_msg.message_id)

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
        
        await show_success_animation(update, context, tools_msg, loading_msg.message_id, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in system_tools: {e}")
        await show_error_animation(update, context, "System tools unavailable!")

async def view_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_users'])
        
        users_data = context.bot_data.get('users', {})
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
                f"       💰 ₹{format_number(balance)} | 🪙 {coins} | 👥 {referrals}\n"
                f"       🏅 {level} | ID: `{user_id}`\n"
                f"       ─────────────────────\n"
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
                caption=f"📊 Full user data export containing {len(users_data)} users."
            )
            os.remove(filename)
        else:
            await show_success_animation(update, context, total_message, loading_msg.message_id)

    except Exception as e:
        logger.error(f"Error in view_users: {e}")
        await show_error_animation(update, context, "Failed to load user list!")

async def view_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_withdrawals'])
        
        withdrawals_data = context.bot_data.get('withdrawals', {})
        pending_requests = [(req_id, req) for req_id, req in withdrawals_data.items() 
                            if req.get('status') == 'pending']
        
        if not pending_requests:
            await show_error_animation(update, context, "No pending withdrawal requests!", loading_msg.message_id if loading_msg else None)
            return

        withdrawal_msg = f"💸 *PENDING WITHDRAWALS* ({len(pending_requests)})\n\n"
        
        keyboard = []
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
            
            withdrawal_msg += (
                f"{i}. {first_name} (@{username})\n"
                f"       💰 Amount: ₹{format_number(amount)}\n"
                f"       💳 UPI: `{upi}`\n"
                f"       📅 Time: {time_str}\n"
                f"       🆔 ID: `{req_id}`\n"
                f"       ─────────────────\n"
            )

            # Add a "Mark Paid" button for each request
            keyboard.append([InlineKeyboardButton(f"✅ Mark Paid for {first_name}", callback_data=f"mark_paid:{req_id}")])

        if len(pending_requests) > 10:
            withdrawal_msg += f"\n... and {len(pending_requests) - 10} more requests"

        keyboard.append([InlineKeyboardButton("📤 Export List", callback_data="export_withdrawals")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await show_success_animation(update, context, withdrawal_msg, loading_msg.message_id, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in view_withdrawals: {e}")
        await show_error_animation(update, context, "Failed to load withdrawal requests!")

async def mark_as_paid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Marks a specific withdrawal request as paid."""
    query = update.callback_query
    await query.answer("Marking as paid...")
    
    loading_msg = await show_stylish_loading_animation(update, context, "Processing payment...")
    
    try:
        _, request_id = query.data.split(':', 1)
        withdrawals_data = context.bot_data.get('withdrawals', {})
        request = withdrawals_data.get(request_id)

        if not request:
            await show_error_animation(update, context, "❌ Request not found or already processed.", loading_msg.message_id)
            return

        request['status'] = 'completed'
        request['paid_at'] = datetime.now().isoformat()
        
        # Notify the user
        try:
            user_msg = (
                f"✅ *PAYMENT SENT!* ✅\n\n"
                f"💰 Amount: *₹{format_number(request['amount'])}*\n"
                f"💳 UPI: `{request['upi']}`\n"
                f"🎉 The payment for your withdrawal request has been successfully processed.\n\n"
                f"Thank you for using our bot! Keep earning! ✨"
            )
            await context.bot.send_message(request['user_id'], user_msg, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning(f"Failed to notify user {request['user_id']} of paid withdrawal: {e}")

        success_msg = f"✅ Withdrawal request `{request_id}` marked as paid."
        await show_success_animation(update, context, success_msg, loading_msg.message_id)

    except Exception as e:
        logger.error(f"Error marking withdrawal as paid: {e}")
        await show_error_animation(update, context, "Failed to mark withdrawal as paid.", loading_msg.message_id)
    
    await view_withdrawals(update, context)

async def export_withdrawals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exports all pending withdrawal requests to a JSON file."""
    query = update.callback_query
    await query.answer("📤 Exporting pending withdrawals...")
    
    loading_msg = await show_stylish_loading_animation(update, context, "Exporting data")

    try:
        withdrawals_data = context.bot_data.get('withdrawals', {})
        pending_requests = {req_id: req for req_id, req in withdrawals_data.items() if req.get('status') == 'pending'}

        if not pending_requests:
            await show_error_animation(update, context, "No pending withdrawal requests to export.", loading_msg.message_id)
            return

        filename = f"pending_withdrawals_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        if save_data(pending_requests, filename):
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(filename, 'rb'),
                caption=f"📋 Exported {len(pending_requests)} pending withdrawal requests."
            )
            os.remove(filename)
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
        else:
            await show_error_animation(update, context, "Failed to create export file.", loading_msg.message_id)
    
    except Exception as e:
        logger.error(f"Error exporting withdrawals: {e}")
        await show_error_animation(update, context, "Failed to export list.", loading_msg.message_id)

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
        users_data = context.bot_data.get('users', {})
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
                
            except Forbidden:
                blocked_count += 1
                failed_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to {user_id}: {e}")
                failed_count += 1
            
            if i % 30 == 0:
                await asyncio.sleep(1)
        
        final_msg = (
            f"✅ *BROADCAST COMPLETE!*\n\n"
            f"📊 *Results:*\n"
            f"✅ Successfully sent: {sent_count}\n"
            f"🚫 Blocked bot: {blocked_count}\n"
            f"❌ Other failures: {failed_count - blocked_count}\n"
            f"📈 Success rate: {(sent_count/total_users*100):.1f}%"
        )
        
        await show_success_animation(update, context, final_msg, loading_msg.message_id)
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
        
        users_data = context.bot_data.get('users', {})
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
                
            except Forbidden:
                blocked_count += 1
                failed_count += 1
            except Exception as e:
                logger.error(f"Failed to send photo broadcast to {user_id}: {e}")
                failed_count += 1
            
            if i % 30 == 0:
                await asyncio.sleep(1)
        
        final_msg = (
            f"✅ *PHOTO BROADCAST COMPLETE!*\n\n"
            f"📊 *Results:*\n"
            f"✅ Successfully sent: {sent_count}\n"
            f"🚫 Blocked bot: {blocked_count}\n"
            f"❌ Other failures: {failed_count - blocked_count}\n"
            f"📈 Success rate: {(sent_count/total_users*100):.1f}%"
        )
        
        await show_success_animation(update, context, final_msg, loading_msg.message_id)
        await admin_command(update, context)
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in broadcast_photo_receive: {e}")
        await show_error_animation(update, context, "Photo broadcast failed!")
        await admin_command(update, context)
        return ConversationHandler.END

async def airdrop_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the airdrop conversation."""
    try:
        airdrop_msg = (
            f"{EMOJIS['airdrop']} *Airdrop Tool*\n\n"
            f"💸 *Step 1: Cash Amount*\n\n"
            f"Enter the amount of cash (e.g., `2.5`) to airdrop to every user.\n\n"
            f"Enter `0` if you don't want to airdrop cash.\n\n"
            f"Type /cancel to abort."
        )
        await safe_send_message(
            update, context, airdrop_msg,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN
        )
        return AIRDROP_ASK_CASH
    except Exception as e:
        logger.error(f"Error in airdrop_start: {e}")
        await show_error_animation(update, context, "Airdrop setup failed!")
        return ConversationHandler.END

async def airdrop_receive_cash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives cash amount and asks for coin amount."""
    try:
        cash_amount_str = update.message.text.strip()
        cash_amount = float(cash_amount_str)
        if cash_amount < 0:
            await update.message.reply_text("Cash amount cannot be negative. Please enter a valid amount (or 0).")
            return AIRDROP_ASK_CASH
        
        context.user_data['airdrop_cash'] = cash_amount
        
        coins_msg = (
            f"✅ Cash amount set to *₹{cash_amount:.2f}*\n\n"
            f"🪙 *Step 2: Coin Amount*\n\n"
            f"Enter the amount of coins (e.g., `100`) to airdrop to every user.\n\n"
            f"Enter `0` if you don't want to airdrop coins.\n\n"
            f"Type /cancel to abort."
        )
        await update.message.reply_text(coins_msg, parse_mode=ParseMode.MARKDOWN)
        return AIRDROP_ASK_COINS

    except ValueError:
        await update.message.reply_text("Invalid number. Please enter a valid cash amount (e.g., `2.5` or `0`).")
        return AIRDROP_ASK_CASH
    except Exception as e:
        logger.error(f"Error in airdrop_receive_cash: {e}")
        await show_error_animation(update, context, "Airdrop process failed!")
        return ConversationHandler.END

async def airdrop_receive_coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives coin amount and executes the airdrop."""
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_airdrop'])

        coin_amount_str = update.message.text.strip()
        coin_amount = int(coin_amount_str)
        cash_amount = context.user_data.get('airdrop_cash', 0.0)

        if coin_amount < 0:
            await show_error_animation(update, context, "Coin amount cannot be negative. Please enter a valid amount (or 0).", loading_msg.message_id)
            return AIRDROP_ASK_COINS

        if cash_amount == 0 and coin_amount == 0:
            await show_error_animation(update, context, "Both amounts cannot be zero. Action cancelled.", loading_msg.message_id)
            await admin_command(update, context)
            return ConversationHandler.END

        users_data = context.bot_data.get('users', {})
        total_users = len(users_data)
        
        if total_users == 0:
            await show_error_animation(update, context, "No users to airdrop to!", loading_msg.message_id)
            await admin_command(update, context)
            return ConversationHandler.END

        sent_count, failed_count = 0, 0
        airdrop_notification = (
            f"🎉 *You've received an Airdrop!* 🎉\n\n"
            f"The admin has sent you a special gift:\n"
            f"💰 *+₹{cash_amount:.2f}* Cash\n"
            f"🪙 *+{coin_amount}* Coins\n\n"
            f"Check your vault to see your new balance!"
        )

        for i, (user_id, user_data) in enumerate(users_data.items(), 1):
            user_data['balance'] = user_data.get('balance', 0.0) + cash_amount
            user_data['coin_balance'] = user_data.get('coin_balance', 0) + coin_amount
            
            try:
                await context.bot.send_message(user_id, airdrop_notification, parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                failed_count += 1
                logger.warning(f"Failed to send airdrop notification to {user_id}: {e}")
            else:
                sent_count += 1
            
            if i % 30 == 0:
                await asyncio.sleep(1)
        
        final_msg = (
            f"✅ *AIRDROP COMPLETE!*\n\n"
            f"💰 Cash per user: *₹{cash_amount:.2f}*\n"
            f"🪙 Coins per user: *{coin_amount}*\n\n"
            f"📊 *Results:*\n"
            f"✅ Sent to: *{sent_count}/{total_users}* users\n"
            f"❌ Failed for: *{failed_count}* users"
        )
        await show_success_animation(update, context, final_msg, loading_msg.message_id)

    except ValueError:
        await show_error_animation(update, context, "Invalid number. Please enter a valid coin amount (e.g., `100` or `0`).")
        return AIRDROP_ASK_COINS
    except Exception as e:
        logger.error(f"Error in airdrop_receive_coins: {e}")
        await show_error_animation(update, context, "Airdrop process failed critically!")
    
    del context.user_data['airdrop_cash']
    await admin_command(update, context)
    return ConversationHandler.END

async def create_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        keyboard = [
            [f"{EMOJIS['magic']} Join Channel", f"{EMOJIS['quiz']} Quiz"],
            [f"{EMOJIS['social']} Social Media", f"{EMOJIS['game']} Mini-Game"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        task_msg = (
            f"➕ *NEW TASK CREATION*\n\n"
            f"📝 *Step 1: Task Type*\n\n"
            f"Select the type of task you want to create.\n\n"
            f"Type /cancel to abort."
        )
        
        await safe_send_message(
            update, context, task_msg, 
            reply_markup=reply_markup, 
            parse_mode=ParseMode.MARKDOWN
        )
        return ASK_TASK_TYPE

    except Exception as e:
        logger.error(f"Error in create_task_start: {e}")
        await show_error_animation(update, context, "Task creation setup failed!")
        return ConversationHandler.END

async def receive_task_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the admin's selection of a task type."""
    task_type_text = update.message.text
    
    if f"{EMOJIS['magic']} Join Channel" in task_type_text:
        context.user_data['task_type'] = 'join'
        await update.message.reply_text(
            "Great! Now, send the channel username (e.g., `@telegram`), a private invite link (e.g., `https://t.me/+...`), or the private invite hash (e.g., `+<invite_hash>`). The bot *must* be an admin in the channel to verify users.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASK_CHANNEL
        
    elif f"{EMOJIS['quiz']} Quiz" in task_type_text:
        context.user_data['task_type'] = 'quiz'
        await update.message.reply_text(
            "Let's create a quiz! First, what is the question?",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASK_QUIZ_QUESTION
        
    elif f"{EMOJIS['social']} Social Media" in task_type_text:
        context.user_data['task_type'] = 'social'
        await update.message.reply_text(
            "Social media task! Please send the full link for the user to visit (e.g., `https://twitter.com/user/status/123`).",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASK_SOCIAL_LINK

    elif f"{EMOJIS['game']} Mini-Game" in task_type_text:
        context.user_data['task_type'] = 'game'
        # For the number guessing game, we can go straight to asking for the reward
        await update.message.reply_text(
            "Game time! The 'Guess the Number' game is ready. How many coins should users earn for winning? (Max 5000 coins)",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASK_REWARD
        
    else:
        await update.message.reply_text("Invalid selection. Please choose a task type from the buttons.")
        return ASK_TASK_TYPE

async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Receives channel information (username or invite link) and validates it.
    """
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_task_create'])
        
        channel_input = update.message.text.strip()
        channel_identifier = None

        if channel_input.startswith('+') or ('t.me/+' in channel_input):
            if channel_input.startswith('+'):
                invite_hash = channel_input
                full_invite_link = f"https://t.me/{invite_hash}"
            else:
                full_invite_link = channel_input
                invite_hash = full_invite_link.split('/')[-1]
            
            context.user_data['task_channel'] = full_invite_link
            context.user_data['channel_hash'] = invite_hash
            context.user_data['is_private_channel'] = True
            
            await show_success_animation(
                update, context, 
                "✅ Private channel detected!\n\nPlease enter the channel's numeric ID (ask the channel owner for this):",
                loading_msg.message_id if loading_msg else None
            )
            return ASK_CHANNEL_ID
            
        else:
            # Handle public channels as before
            private_invite_link_match = re.match(r'https?://t\.me/\+([a-zA-Z0-9_-]+)', channel_input)
            private_invite_hash_match = re.match(r'^\+([a-zA-Z0-9_-]+)$', channel_input)
            
            if private_invite_hash_match:
                channel_identifier = channel_input
            elif private_invite_link_match:
                channel_identifier = channel_input
            elif channel_input.lstrip('-').isdigit():
                channel_identifier = int(channel_input)
            elif channel_input.startswith('@'):
                channel_identifier = channel_input
            else:
                channel_identifier = f"@{channel_input}"
                
            if not channel_identifier:
                error_text = (
                    f"❌ *Invalid Channel Format!*\n\n"
                    f"Please provide a valid channel username, a private invite link, or a private invite hash."
                )
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
                return ASK_CHANNEL

            try:
                chat_info = await context.bot.get_chat(channel_identifier)
            except BadRequest as e:
                logger.error(f"Error accessing channel {channel_input}: {e}")
                error_text = (
                    f"❌ *Error Accessing Channel!*\n\n"
                    f"This channel could not be found or accessed by the bot. Please ensure you have taken these two critical steps:\n\n"
                    f"1. *Add the bot:* Use the invite link or hash to add the bot to the channel.\n"
                    f"2. *Promote to Admin:* In the channel's settings, promote the bot to an administrator with `Invite Users` and `Pin Messages` permissions.\n\n"
                    f"Once you've done this, please send the link or hash again."
                )
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
                return ASK_CHANNEL

            # Verify bot is an admin in the channel
            try:
                bot_member = await context.bot.get_chat_member(chat_id=chat_info.id, user_id=context.bot.id)
                if bot_member.status not in ['administrator', 'creator']:
                    error_text = (
                        f"Bot is not an admin in the channel `{chat_info.title}`\n\nPlease make the bot an administrator and try again."
                    )
                    await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
                    return ASK_CHANNEL
            except Exception as e:
                logger.error(f"Admin check failed for {channel_input}: {e}")
                error_text = "Could not verify admin status. Please ensure the bot is an admin and try again."
                await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
                return ASK_CHANNEL

            # If everything is successful, save the chat ID and title
            context.user_data['task_channel'] = channel_input # Store the original string input
            context.user_data['channel_title'] = chat_info.title
            context.user_data['is_private_channel'] = False
            
            reward_msg = (
                f"✅ *Channel Verified!*\n\n"
                f"📺 Channel: `{chat_info.title}`\n"
                f"🆔 Identifier: `{channel_input}`\n\n"
                f"*Step 2: Reward Amount*\n\n"
                f"How many coins should users earn? (Max 5000 coins)\n"
                f"Recommended: 50-100 coins"
            )
            
            await show_success_animation(update, context, reward_msg, loading_msg.message_id if loading_msg else None)
            return ASK_REWARD

    except Exception as e:
        logger.error(f"Critical error in receive_channel: {e}")
        error_text = "An unexpected error occurred during channel validation. Please try again or contact support."
        await show_error_animation(update, context, error_text, loading_msg.message_id if loading_msg else None)
        return ASK_CHANNEL
    
async def receive_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the channel ID for private channels."""
    try:
        loading_msg = await show_stylish_loading_animation(update, context, "Setting channel ID")
        
        channel_id_str = update.message.text.strip()
        
        # Validate it's a numeric ID
        if not channel_id_str.lstrip('-').isdigit():
            await show_error_animation(update, context, "Invalid channel ID. Please enter a numeric ID.", loading_msg.message_id)
            return ASK_CHANNEL_ID
            
        channel_id = int(channel_id_str)
        context.user_data['channel_id'] = channel_id
        
        # Also ask for a display title for the private channel
        await show_success_animation(
            update, context, 
            "✅ Channel ID set!\n\nPlease enter a display name for this channel:",
            loading_msg.message_id if loading_msg else None
        )
        return ASK_CHANNEL_TITLE
        
    except Exception as e:
        logger.error(f"Error in receive_channel_id: {e}")
        await show_error_animation(update, context, "Failed to set channel ID!")
        return ASK_CHANNEL_ID

async def receive_channel_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the display title for private channels."""
    try:
        loading_msg = await show_stylish_loading_animation(update, context, "Setting channel title")
        
        channel_title = update.message.text.strip()
        context.user_data['channel_title'] = channel_title
        
        reward_msg = (
            f"✅ *Private Channel Setup Complete!*\n\n"
            f"📺 Channel: `{channel_title}`\n"
            f"🔗 Invite Link: `{context.user_data['task_channel']}`\n\n"
            f"*Step 2: Reward Amount*\n\n"
            f"How many coins should users earn? (Max 5000 coins)\n"
            f"Recommended: 50-100 coins"
        )
        
        await show_success_animation(update, context, reward_msg, loading_msg.message_id if loading_msg else None)
        return ASK_REWARD
        
    except Exception as e:
        logger.error(f"Error in receive_channel_title: {e}")
        await show_error_animation(update, context, "Failed to set channel title!")
        return ASK_CHANNEL_TITLE

async def receive_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, "Setting reward amount")
        
        try:
            reward = int(update.message.text.strip())
            if not (10 <= reward <= 5000):
                error_text = (
                    f"Reward must be between 10-5000 coins\n\nRecommended ranges:\n• Easy tasks: 10-50\n• Medium tasks: 50-100\n• Premium tasks: 100-500\n\nPlease enter a valid amount:"
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
        
        await show_success_animation(update, context, expiry_msg, loading_msg.message_id)
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
        tasks_data = context.bot_data.setdefault('tasks', {})
        task_id = f"task_{int(datetime.now().timestamp())}"
        
        new_task = {
            'type': context.user_data.get('task_type'),
            'reward': context.user_data.get('task_reward'),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'expiry_date': expiry_date.isoformat(),
            'created_by': str(ADMIN_ID),
            'total_completions': 0
        }

        # Add type-specific data
        task_type = new_task['type']
        if task_type == 'join':
            if context.user_data.get('is_private_channel', False):
                new_task['channel_username'] = context.user_data['task_channel']
                new_task['channel_hash'] = context.user_data['channel_hash']
                new_task['channel_id'] = context.user_data['channel_id']  # Store the channel ID
                new_task['is_private'] = True
            else:
                new_task['channel_username'] = context.user_data['task_channel']
                new_task['is_private'] = False
            new_task['channel_title'] = context.user_data.get('channel_title', 'Unknown')
        elif task_type == 'quiz':
            new_task['question'] = context.user_data['task_question']
            new_task['answer'] = context.user_data['task_answer']
        elif task_type == 'social':
            new_task['link'] = context.user_data['task_link']
        elif task_type == 'game':
            pass # No specific data needed for this game

        tasks_data[task_id] = new_task
        
        # Clean up context data
        for key in list(context.user_data.keys()):
            if key.startswith('task_'):
                del context.user_data[key]
        
        success_msg = f"✅ *TASK CREATED SUCCESSFULLY!* ✅\n\n"
        if task_type == 'join':
            success_msg += f"📺 Channel: `{new_task['channel_title']}`\n"
            if new_task.get('is_private', False):
                success_msg += f"🔗 Invite Link: `{new_task['channel_username']}`\n"
                success_msg += f"🆔 Channel ID: `{new_task['channel_id']}`\n"
            else:
                success_msg += f"🆔 Identifier: `{new_task['channel_username']}`\n"
        elif task_type == 'quiz':
            success_msg += f"❓ Question: `{new_task['question']}`\n"
        elif task_type == 'social':
            success_msg += f"🌐 Link: `{new_task['link']}`\n"
        elif task_type == 'game':
            success_msg += f"🎮 Game: Guess the Number\n"

        success_msg += (
            f"🪙 Reward: {new_task['reward']} Coins\n"
            f"⏰ Duration: {days} day(s)\n"
            f"📅 Expires: {expiry_date.strftime('%d/%m/%Y %H:%M')}\n"
            f"🆔 Task ID: `{task_id}`\n\n"
            f"🚀 Broadcasting to all users..."
        )
        
        await show_success_animation(update, context, success_msg, loading_msg.message_id if loading_msg else None)
        
        # Broadcast is handled after returning
        context.job_queue.run_once(
            broadcast_new_task, 
            when=1, 
            data={'task': new_task, 'days': days}
        )
        
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
        
        tasks_data = context.bot_data.get('tasks', {})
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
            await show_success_animation(update, context, "All tasks are up to date! No expired tasks found.", loading_msg.message_id if loading_msg else None)
            return
        
        cleanup_msg = f"🗑️ *CLEANING EXPIRED TASKS* 🗑️\n\n"
        
        for i, (task_id, task) in enumerate(expired_tasks[:10], 1):
            channel = task.get('channel_username', 'Misc Task')
            reward = task.get('reward', 0)
            completions = task.get('total_completions', 0)
            
            cleanup_msg += f"{i}. `{channel}` ({reward} 🪙, {completions} completions)\n"
        
        if len(expired_tasks) > 10:
            cleanup_msg += f"... and {len(expired_tasks) - 10} more\n"
        
        cleanup_msg += f"\n📊 *Summary:*\n"
        cleanup_msg += f"🗑️ Expired: {len(expired_tasks)}\n"
        cleanup_msg += f"✅ Active: {len(active_tasks)}\n"
        
        context.bot_data['tasks'] = active_tasks
        cleanup_msg += f"\n✅ *Cleanup completed successfully!*"
        
        await show_success_animation(update, context, cleanup_msg, loading_msg.message_id)

    except Exception as e:
        logger.error(f"Error in clean_expired_tasks: {e}")
        await show_error_animation(update, context, "Task cleanup failed!")

async def remove_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['admin_task_remove'])
        
        tasks_data = context.bot_data.get('tasks', {})
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
            task_type = task.get('type', 'join')
            if task_type == 'join':
                name = task.get('channel_title', 'Unknown')
            elif task_type == 'quiz':
                name = f"Quiz: {task.get('question', '...')[:15]}"
            else:
                name = task_type.capitalize()

            reward = task['reward']
            
            button_text = f"❌ {name} - {reward}🪙"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"remove:{task_id}")])

        if len(active_tasks) > 15:
            removal_msg += f"Showing first 15 of {len(active_tasks)} tasks.\n\n"

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await show_success_animation(update, context, removal_msg, loading_msg.message_id, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in remove_task_start: {e}")
        await show_error_animation(update, context, "Failed to load tasks for removal!")

async def remove_task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer("Removing task...")

        loading_msg = await show_stylish_loading_animation(update, context, "Removing task")

        _, task_id_to_remove = query.data.split(':', 1)

        tasks_data = context.bot_data.get('tasks', {})
        
        if task_id_to_remove not in tasks_data:
            await show_error_animation(update, context, "This task may have already been removed.", loading_msg.message_id if loading_msg else None)
            return
        
        task = tasks_data[task_id_to_remove]
        task_info = f"Task '{task.get('channel_title', 'Misc Task')}' (ID: `{task_id_to_remove}`)"
        
        del tasks_data[task_id_to_remove]
        
        success_msg = f"✅ *TASK REMOVED* ✅\n\n🗑️ {task_info} has been permanently deleted."
        
        await show_success_animation(update, context, success_msg, loading_msg.message_id)

    except Exception as e:
        logger.error(f"Error in remove_task_callback: {e}")
        await show_error_animation(update, context, "Failed to remove task.")

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
        users_data = context.bot_data.get('users', {})
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
        for file in [USERS_FILE, TASKS_FILE, WITHDRAWALS_FILE, SETTINGS_FILE]:
            if os.path.exists(file):
                try:
                    load_data(file)
                    health_report.append(f"✅ Data File: `{file}` is accessible and valid.")
                except Exception:
                        health_report.append(f"❌ Data File: `{file}` is corrupted or unreadable.")
            else:
                health_report.append(f"⚠️ Data File: `{file}` does not exist (will be created).")

        # 3. Job Queue Check
        if context.job_queue:
            health_report.append(f"✅ Job Queue: Service is running with {len(context.job_queue.jobs())} jobs.")
        else:
            health_report.append(f"❌ Job Queue: Service is NOT running!")

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

# --- NEW ADMIN CONVERSATION FOR ADJUSTING USER BALANCE ---
async def adjust_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation for adjusting a user's balance."""
    msg = (
        f"🎁 *ADJUST USER BALANCE*\n\n"
        f"Please send the user's Telegram ID or username to adjust their balance.\n"
        f"Example: `123456789` or `@username`\n\n"
        f"Type /cancel to abort."
    )
    await safe_send_message(update, context, msg, parse_mode=ParseMode.MARKDOWN, force_new=True)
    return ADJUST_BALANCE_ID

async def adjust_balance_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives user ID/username and asks for the cash amount."""
    users_data = context.bot_data.get('users', {})
    
    user_input = update.message.text.strip().replace('@', '')
    target_user_id = None

    # Try to find user by ID first
    if user_input.isdigit() and user_input in users_data:
        target_user_id = user_input
    # Then try to find user by username
    else:
        for user_id, user_data in users_data.items():
            if user_data.get('username', '').lower() == user_input.lower():
                target_user_id = user_id
                break
    
    if not target_user_id or target_user_id not in users_data:
        await update.message.reply_text("❌ User not found. Please enter a valid user ID or username.")
        return ADJUST_BALANCE_ID
    
    context.user_data['target_user_id'] = target_user_id
    user_data = users_data.get(target_user_id)
    
    msg = (
        f"✅ User found: *{escape_markdown(user_data.get('first_name', 'N/A'))} (@{escape_markdown(user_data.get('username', 'N/A'))})*\n"
        f"Current Balance: *₹{format_number(user_data.get('balance', 0))}* | Coins: *{user_data.get('coin_balance', 0)}*\n\n"
        f"Now, enter the amount of cash to add or subtract.\n"
        f"Use a minus sign for subtraction (e.g., `+50` or `-10.5`)\n\n"
        f"Type /cancel to abort."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    return ADJUST_BALANCE_CASH

async def adjust_balance_cash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the cash amount and asks for the coin amount."""
    try:
        cash_change = float(update.message.text.strip())
        context.user_data['cash_change'] = cash_change
    except ValueError:
        await update.message.reply_text("❌ Invalid cash amount. Please enter a number.")
        return ADJUST_BALANCE_CASH
    
    msg = (
        f"✅ Cash change set to *₹{format_number(context.user_data['cash_change'])}*\n\n"
        f"Now, enter the amount of coins to add or subtract.\n"
        f"Use a minus sign for subtraction (e.g., `+100` or `-50`)\n\n"
        f"Type /cancel to abort."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    return ADJUST_BALANCE_COIN

async def adjust_balance_coin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the coin amount, applies the changes, and ends the conversation."""
    loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['adjust_balance'])

    try:
        coin_change = int(update.message.text.strip())
        context.user_data['coin_change'] = coin_change
    except ValueError:
        await show_error_animation(update, context, "❌ Invalid coin amount. Please enter an integer.", loading_msg.message_id if loading_msg else None)
        return ADJUST_BALANCE_COIN
    
    user_id = context.user_data.get('target_user_id')
    cash_change = context.user_data.get('cash_change', 0)
    coin_change = context.user_data.get('coin_change', 0)

    users_data = context.bot_data.get('users', {})
    user_data = users_data.get(user_id)
    
    if user_data:
        old_cash = user_data.get('balance', 0)
        old_coins = user_data.get('coin_balance', 0)
        
        user_data['balance'] += cash_change
        user_data['coin_balance'] += coin_change
        
        if user_data['balance'] < 0: user_data['balance'] = 0
        if user_data['coin_balance'] < 0: user_data['coin_balance'] = 0

        final_msg = (
            f"✅ *BALANCE ADJUSTED!* ✅\n\n"
            f"User: *{escape_markdown(user_data.get('first_name', 'N/A'))} (@{escape_markdown(user_data.get('username', 'N/A'))})*\n"
            f"Cash: *₹{format_number(old_cash)}* -> *₹{format_number(user_data['balance'])}*\n"
            f"Coins: *{old_coins}* -> *{user_data['coin_balance']}*\n\n"
            f"Changes applied successfully!"
        )
        
        await show_success_animation(update, context, final_msg, loading_msg.message_id)

        # Notify the user of the change
        try:
            user_notification = (
                f"🔔 *Your balance has been adjusted by an admin!* 🔔\n"
                f"Cash: *{'+' if cash_change >= 0 else ''}{format_number(cash_change)}* ₹\n"
                f"Coins: *{'+' if coin_change >= 0 else ''}{coin_change}* 🪙\n\n"
                f"Your new balance is:\n"
                f"💰 Cash: *₹{format_number(user_data['balance'])}*\n"
                f"🪙 Coins: *{user_data['coin_balance']}*"
            )
            await context.bot.send_message(user_id, user_notification, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning(f"Failed to notify user {user_id} of balance change: {e}")
    else:
        await show_error_animation(update, context, "❌ User data disappeared unexpectedly.", loading_msg.message_id if loading_msg else None)

    # Clean up and return to admin panel
    context.user_data.clear()
    await admin_command(update, context)
    return ConversationHandler.END


# --- FIX: MISSING FUNCTION IMPLEMENTATIONS ---
async def receive_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the quiz question and asks for the answer."""
    context.user_data['task_question'] = update.message.text
    await update.message.reply_text("Question set! Now, what is the *exact* answer (case-sensitive)?")
    return ASK_QUIZ_ANSWER

async def receive_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the quiz answer and asks for the reward."""
    context.user_data['task_answer'] = update.message.text
    await update.message.reply_text("Answer set! How many coins should users get for a correct answer? (Max 5000 coins)")
    return ASK_REWARD

async def receive_social_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the social media link and asks for the reward."""
    link = update.message.text
    if not (link.startswith("http://") or link.startswith("https://")):
        await update.message.reply_text("Invalid link. Please send a full URL starting with http:// or https://.")
        return ASK_SOCIAL_LINK
    
    context.user_data['task_link'] = link
    await update.message.reply_text("Link saved! How many coins should users get for completing this task? (Max 5000 coins)")
    return ASK_REWARD

async def claim_social_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles a user claiming a social media task."""
    query = update.callback_query
    await query.answer("Claiming reward...")
    
    user_id = get_user_id(update)
    task_id = query.data.split(':', 1)[1]
    
    users_data = context.bot_data.get('users', {})
    tasks_data = context.bot_data.get('tasks', {})
    user_data = users_data.get(user_id)
    task_data = tasks_data.get(task_id)

    if not user_data or not task_data:
        await query.edit_message_text("❌ Error: Task or user not found. Please try /start.")
        return

    if task_id in user_data.get('completed_tasks', []):
        await query.edit_message_text("✅ You have already completed this task!")
        return
        
    reward = task_data['reward']
    user_data['coin_balance'] = user_data.get('coin_balance', 0) + reward
    user_data.setdefault('completed_tasks', []).append(task_id)
    
    success_msg = f"🎉 Task complete! You've earned *{reward}* coins! 🪙"
    await query.edit_message_text(success_msg, parse_mode=ParseMode.MARKDOWN)
    await check_and_grant_achievements(user_id, context)

async def start_quiz_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the quiz for a user."""
    query = update.callback_query
    await query.answer()
    
    task_id = query.data.split(':', 1)[1]
    user_id = get_user_id(update)
    users_data = context.bot_data.get('users', {})
    user_data = users_data.get(user_id, {})
    
    if task_id in user_data.get('completed_tasks', []):
        await query.message.reply_text("❌ You have already completed this quiz task.")
        return ConversationHandler.END

    tasks_data = context.bot_data.get('tasks', {})
    question = tasks_data.get(task_id, {}).get('question', 'No question provided.')
    
    context.user_data['current_quiz_task'] = task_id
    
    await query.message.reply_text(f"❓ *Quiz Question:*\n{question}\n\nPlease type your answer in the chat.\n\nType /cancel to abort.", parse_mode=ParseMode.MARKDOWN)
    return 1 # Next state in quiz_conv_handler

async def process_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes the user's answer for a quiz task."""
    user_answer = update.message.text.strip()
    task_id = context.user_data.get('current_quiz_task')

    if not task_id:
        await update.message.reply_text("Quiz session expired. Please start again.")
    
    tasks_data = context.bot_data.get('tasks', {})
    task_data = tasks_data.get(task_id)
    correct_answer = task_data.get('answer')
    user_id = get_user_id(update)
    users_data = context.bot_data.get('users', {})
    user_data = users_data[user_id]
    
    # Mark as completed regardless of the outcome to prevent multiple attempts
    user_data.setdefault('completed_tasks', []).append(task_id)

    if user_answer.lower() == correct_answer.lower():
        # User is correct
        reward = task_data['reward']
        user_data['coin_balance'] = user_data.get('coin_balance', 0) + reward
        
        success_msg = f"✅ Correct! You've earned *{reward}* coins! 🪙"
        await update.message.reply_text(success_msg, parse_mode=ParseMode.MARKDOWN)
        await check_and_grant_achievements(user_id, context)
    else:
        # User is incorrect
        await update.message.reply_text("❌ Incorrect answer. Better luck next time!")
        
    del context.user_data['current_quiz_task']
    return ConversationHandler.END

async def start_game_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the 'Guess the Number' game for a user."""
    query = update.callback_query
    await query.answer()
    
    task_id = query.data.split(':', 1)[1]
    user_id = get_user_id(update)
    users_data = context.bot_data.get('users', {})
    user_data = users_data.get(user_id, {})
    
    if task_id in user_data.get('completed_tasks', []):
        await query.message.reply_text("❌ You have already completed this game task.")
        return ConversationHandler.END

    secret_number = randint(1, 20)
    
    context.user_data['game_task_id'] = task_id
    context.user_data['game_secret_number'] = secret_number
    context.user_data['game_attempts_left'] = 3
    
    await query.message.reply_text(
        "I'm thinking of a number between 1 and 20. You have 3 guesses!\n\nWhat's your first guess?"
    )
    return GAME_GUESS_NUMBER

async def process_game_guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes a user's guess in the game."""
    try:
        guess = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("That's not a number! Please guess a number between 1 and 20.")
        return GAME_GUESS_NUMBER

    secret_number = context.user_data.get('game_secret_number')
    attempts_left = context.user_data.get('game_attempts_left', 0)
    
    if not secret_number:
        await update.message.reply_text("Game session expired. Please start again.")
        return ConversationHandler.END
        
    attempts_left -= 1
    context.user_data['game_attempts_left'] = attempts_left
    
    users_data = context.bot_data.get('users', {})
    user_id = get_user_id(update)
    user_data = users_data[user_id]
    task_id = context.user_data['game_task_id']


    if guess == secret_number:
        # User wins
        tasks_data = context.bot_data.get('tasks', {})
        task_data = tasks_data[task_id]
        reward = task_data['reward']
        
        user_data['coin_balance'] = user_data.get('coin_balance', 0) + reward
        user_data.setdefault('completed_tasks', []).append(task_id)

        await update.message.reply_text(f"🎉 You got it! The number was {secret_number}. You've earned *{reward}* coins! 🪙", parse_mode=ParseMode.MARKDOWN)
        await check_and_grant_achievements(user_id, context)

        # Clean up context
        del context.user_data['game_task_id']
        del context.user_data['game_secret_number']
        del context.user_data['game_attempts_left']
        return ConversationHandler.END
    
    elif attempts_left > 0:
        hint = "higher" if guess < secret_number else "lower"
        await update.message.reply_text(f"Nope! Try a little {hint}. You have {attempts_left} guess(es) left.")
        return GAME_GUESS_NUMBER
    else:
        # User loses, mark task as complete so they can't try again.
        user_data.setdefault('completed_tasks', []).append(task_id)
        
        await update.message.reply_text(f"😥 Out of guesses! The correct number was {secret_number}. Better luck next time!")
        
        # Clean up context
        del context.user_data['game_task_id']
        del context.user_data['game_secret_number']
        del context.user_data['game_attempts_left']
        return ConversationHandler.END

async def broadcast_new_task(context: ContextTypes.DEFAULT_TYPE):
    """Broadcasts a new task notification to all users."""
    task_info = context.job.data['task']
    days = context.job.data['days']
    
    task_type = task_info['type']
    reward = task_info['reward']
    
    if task_type == 'join':
        description = f"Join the channel `{task_info['channel_title']}`"
    elif task_type == 'quiz':
        description = f"Answer a quiz question: *{task_info['question']}*"
    elif task_type == 'social':
        description = f"Complete a social media action"
    elif task_type == 'game':
        description = f"Play the 'Guess the Number' game"
    else:
        description = "Check out the new task"
        
    broadcast_msg = (
        f"✨ *NEW TASK AVAILABLE!* ✨\n\n"
        f"{description} and earn *{reward} coins*!\n\n"
        f"This task is available for *{days} day(s)*. Go to the '{EMOJIS['magic']} Tasks' section to complete it now!"
    )
    
    users_data = context.bot_data.get('users', {})
    for user_id in users_data.keys():
        try:
            await context.bot.send_message(user_id, broadcast_msg, parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(0.05) # To avoid hitting rate limits
        except Exception:
            pass
            
async def create_backup() -> bool:
    """Creates backup of all data files."""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        
        files_to_backup = [USERS_FILE, TASKS_FILE, WITHDRAWALS_FILE, SETTINGS_FILE]
        
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

# --- NEW: COIN CONVERT FUNCTIONS ---
async def toggle_coin_convert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggles the coin convert feature for all users."""
    if get_user_id(update) != str(ADMIN_ID):
        await update.message.reply_text("You are not authorized to use this command.")
        return
    
    loading_msg = await show_stylish_loading_animation(update, context, "Toggling feature")

    try:
        settings = context.bot_data.setdefault('settings', {})
        current_status = settings.get('coin_convert_enabled', False)
        settings['coin_convert_enabled'] = not current_status
        
        new_status = "ON" if settings['coin_convert_enabled'] else "OFF"
        success_msg = f"✅ *Coin Convert feature is now {new_status}!* ✅"
        logger.info(f"Admin toggled coin convert to {new_status}")
        await show_success_animation(update, context, success_msg, loading_msg.message_id)

    except Exception as e:
        logger.error(f"Error toggling coin convert: {e}")
        await show_error_animation(update, context, "Failed to toggle feature. Please check logs.", loading_msg.message_id)

    await admin_command(update, context)

async def coin_convert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the coin conversion conversation for a user."""
    
    loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['coin_convert'])

    settings = context.bot_data.get('settings', {})
    if not settings.get('coin_convert_enabled', False):
        await show_error_animation(update, context, "❌ The coin conversion feature is currently disabled. Please check back later!", loading_msg.message_id)
        return ConversationHandler.END

    user_id = get_user_id(update)
    users_data = context.bot_data.get('users', {})
    user_data = users_data.get(user_id, {})
    coin_balance = user_data.get('coin_balance', 0)
    
    min_convert = 5000 # Minimum coins to convert

    if coin_balance < min_convert:
        await show_error_animation(update, context, f"You need at least *{min_convert}* coins to convert! Earn some more coins first by completing tasks.", loading_msg.message_id)
        return ConversationHandler.END

    convert_msg = (
        f"🔄 *COIN CONVERTER* 🔄\n\n"
        f"Your current coin balance: *{coin_balance}* 🪙\n"
        f"Conversion rate: *{COIN_CONVERSION_RATE} coins = 1 ₹*\n"
        f"Minimum to convert: *{min_convert}* 🪙\n\n"
        f"Please enter the number of coins you want to convert to cash.\n\n"
        f"Type /cancel to abort."
    )

    await show_success_animation(
        update, context,
        convert_msg,
        loading_msg.message_id,
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ASK_COIN_CONVERT

async def coin_convert_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes the user's coin conversion request."""
    loading_msg = await show_stylish_loading_animation(update, context, LOADING_TITLES['coin_convert'])

    min_convert = 5000
    try:
        coins_to_convert = int(update.message.text.strip())
        
        if coins_to_convert <= 0:
            await show_error_animation(update, context, "Please enter a number greater than 0.", loading_msg.message_id)
            return ASK_COIN_CONVERT
        
        if coins_to_convert < min_convert:
            await show_error_animation(update, context, f"You need to convert a minimum of *{min_convert}* coins.", loading_msg.message_id)
            return ASK_COIN_CONVERT

        user_id = get_user_id(update)
        users_data = context.bot_data.get('users', {})
        user_data = users_data.get(user_id)

        if not user_data:
            await show_error_animation(update, context, "User data not found. Please try /start.", loading_msg.message_id)
            await start_command(update, context)
            return ConversationHandler.END

        if coins_to_convert > user_data.get('coin_balance', 0):
            await show_error_animation(update, context, "You don't have enough coins! Please enter a valid amount.", loading_msg.message_id)
            return ASK_COIN_CONVERT

        # Perform conversion
        cash_earned = coins_to_convert / COIN_CONVERSION_RATE
        user_data['coin_balance'] -= coins_to_convert
        user_data['balance'] = user_data.get('balance', 0.0) + cash_earned

        success_msg = (
            f"✅ *Conversion Successful!* ✅\n\n"
            f"You converted *{coins_to_convert}* coins to *₹{format_number(cash_earned)}* cash.\n"
            f"💰 New Cash Balance: *₹{format_number(user_data['balance'])}*\n"
            f"🪙 New Coin Balance: *{user_data['coin_balance']}*\n\n"
            f"View your wallet with the '{EMOJIS['bank']} My Vault' button."
        )
        await show_success_animation(update, context, success_msg, loading_msg.message_id)

    except ValueError:
        await show_error_animation(update, context, "Invalid input. Please enter a valid number.", loading_msg.message_id)
        return ASK_COIN_CONVERT
    except Exception as e:
        logger.error(f"Error in coin_convert_receive: {e}")
        await show_error_animation(update, context, "An error occurred during conversion. Please try again later.", loading_msg.message_id)
    
    await start_command(update, context)
    return ConversationHandler.END

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


async def post_init(application: Application) -> None:
    """Enhanced bot initialization with comprehensive command setup and data loading."""
    try:
        # Load data into memory at startup
        application.bot_data['users'] = load_data(USERS_FILE)
        application.bot_data['tasks'] = load_data(TASKS_FILE)
        application.bot_data['withdrawals'] = load_data(WITHDRAWALS_FILE)
        application.bot_data['settings'] = load_data(SETTINGS_FILE)
        
        await create_backup()
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
            BotCommand("leaderboard", f"{EMOJIS['leaderboard']} View Leaderboard"),
            BotCommand("achievements", f"{EMOJIS['achievement']} My Achievements"),
            BotCommand("feedback", f"{EMOJIS['feedback']} Send Feedback"),
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
        
        # --- NEW CONVERSATION HANDLERS ---
        feedback_conv = ConversationHandler(
            entry_points=[
                CommandHandler('feedback', feedback_start),
                MessageHandler(filters.Regex(f"^{EMOJIS['feedback']} Send Feedback$"), feedback_start)
            ],
            states={
                ASK_FEEDBACK: [MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, feedback_receive)]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
            per_user=True, per_chat=True
        )

        task_conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex('^➕ Create Task$') & admin_filter, create_task_start),
                CommandHandler('createtask', create_task_start, filters=admin_filter),
            ],
            states={
                ASK_TASK_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_type)],
                ASK_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel)],
                ASK_CHANNEL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel_id)],
                ASK_CHANNEL_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel_title)],
                ASK_REWARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reward)],
                ASK_EXPIRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_expiry)],
                ASK_QUIZ_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quiz_question)],
                ASK_QUIZ_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quiz_answer)],
                ASK_SOCIAL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_social_link)],
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
            per_user=True, per_chat=True
        )
        
        quiz_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(start_quiz_task, pattern='^start_quiz:')],
            states={
                1: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_quiz_answer)]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
            per_user=True, per_chat=True
        )

        game_conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(start_game_task, pattern='^start_game:')],
            states={
                GAME_GUESS_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_game_guess)]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
            per_user=True, per_chat=True
        )
        
        airdrop_conv_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(f'^{EMOJIS["airdrop"]} Airdrop$') & admin_filter, airdrop_start)],
            states={
                AIRDROP_ASK_CASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, airdrop_receive_cash)],
                AIRDROP_ASK_COINS: [MessageHandler(filters.TEXT & ~filters.COMMAND, airdrop_receive_coins)],
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
            per_user=True, per_chat=True
        )
        
        coin_convert_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(f'^{EMOJIS["convert"]} Coin Convert$'), coin_convert_start)],
            states={
                ASK_COIN_CONVERT: [MessageHandler(filters.TEXT & ~filters.COMMAND, coin_convert_receive)]
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
            per_user=True, per_chat=True
        )

        adjust_balance_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(f"^{EMOJIS['money']} Adjust User Balance$") & admin_filter, adjust_balance_start)],
            states={
                ADJUST_BALANCE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, adjust_balance_id)],
                ADJUST_BALANCE_CASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, adjust_balance_cash)],
                ADJUST_BALANCE_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, adjust_balance_coin)],
            },
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
            per_user=True, per_chat=True
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
            fallbacks=[CommandHandler('cancel', cancel_conversation)],
            per_user=True, per_chat=True
        )

        leaderboard_handler = CallbackQueryHandler(leaderboard_callback, pattern='^lb_')

        handlers = [
            task_conv_handler, main_conv_handler, airdrop_conv_handler, 
            feedback_conv, quiz_conv_handler, game_conv_handler, 
            coin_convert_handler, adjust_balance_conv,
            leaderboard_handler,
            
            CommandHandler("start", start_command),
            CommandHandler("help", help_command),
            CommandHandler("admin", admin_command, filters=admin_filter),
            CommandHandler("claim", claim_reward),
            CommandHandler("wallet", my_wallet),
            CommandHandler("withdraw", withdraw),
            CommandHandler("refer", refer_command),
            CommandHandler("tasks", show_tasks),
            CommandHandler("stats", show_user_stats),
            CommandHandler("leaderboard", leaderboard_command),
            CommandHandler("achievements", show_achievements),
            
            CommandHandler("broadcast", broadcast_start, filters=admin_filter),
            CommandHandler("users", view_users, filters=admin_filter),
            CommandHandler("withdrawals", view_withdrawals, filters=admin_filter),
            CommandHandler("createtask", create_task_start, filters=admin_filter),
            CommandHandler("cleantasks", clean_expired_tasks, filters=admin_filter),
            
            CallbackQueryHandler(toggle_notifications_callback, pattern='^toggle_notifications$'),
            CallbackQueryHandler(verify_membership_callback, pattern='^verify:'),
            CallbackQueryHandler(claim_social_task, pattern='^claim_social:'),
            CallbackQueryHandler(remove_task_callback, pattern='^remove:'),
            CallbackQueryHandler(handle_admin_tool_callback, pattern='^tool_'),
            CallbackQueryHandler(mark_as_paid_callback, pattern='^mark_paid:'),
            CallbackQueryHandler(export_withdrawals_callback, pattern='^export_withdrawals$'),
            CallbackQueryHandler(handle_callback_query),
            
            MessageHandler(filters.Regex(f'^{EMOJIS["notify"]} Notifications$'), notifications_menu),
            MessageHandler(
                filters.TEXT & (
                    filters.Regex('^📤 Broadcast Text$') | 
                    filters.Regex('^🖼️ Broadcast Image$') | 
                    filters.Regex('^📊 Detailed Stats$') | 
                    filters.Regex('^👥 User List$') | 
                    filters.Regex('^💸 Withdrawal Requests$') | 
                    filters.Regex('^🔧 System Tools$') | 
                    filters.Regex(f'^{EMOJIS["airdrop"]} Airdrop$') |
                    filters.Regex('^➕ Create Task$') | 
                    filters.Regex('^🗑️ Remove Task$') | 
                    filters.Regex('^🧹 Clean Expired Tasks$') | 
                    filters.Regex('^⬅️ Back to Main$') | 
                    filters.Regex(f'^{EMOJIS["settings"]} Coin Convert.*$') |
                    filters.Regex(f'^{EMOJIS["money"]} Adjust User Balance$')
                ) & admin_filter, 
                handle_message
            ),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        ]

        application.add_handlers(handlers)
        
        application.job_queue.run_repeating(save_all_data, interval=BACKUP_INTERVAL, first=10) # Save every hour
        application.job_queue.run_repeating(backup_job, interval=BACKUP_INTERVAL * 6, first=BACKUP_INTERVAL * 6) # Full backup every 6 hours

        application.add_error_handler(error_handler)

        print("=" * 60)
        print("🤖 TELEGRAM EARNING BOT (UPGRADED)")
        print("=" * 60)
        print(f"🚀 Bot is starting...")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print("✅ New Features: Achievements, More Tasks, Feedback System, Multi-Language, Coin Convert")
        print("=" * 60)
        
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )

    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.critical(f"Critical error starting bot: {e}")
        print(f"❌ Failed to start bot: {e}")

if __name__ == '__main__':
    keep_alive()
    main()
