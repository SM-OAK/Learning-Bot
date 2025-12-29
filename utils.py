import logging
from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid, ChatAdminRequired
from info import AUTH_CHANNEL, LONG_IMDB_DESCRIPTION, IS_VERIFY, SETTINGS, START_IMG
from imdb import Cinemagoer
import asyncio
from pyrogram.types import Message
from pyrogram import enums
import pytz
import re
import os
from shortzy import Shortzy
from datetime import datetime
from typing import Any, Tuple
from database.users_chats_db import db

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BANNED = {}
imdb = Cinemagoer()

class temp(object):
    ME = None
    CURRENT = int(os.environ.get("SKIP", 2))
    CANCEL = False
    U_NAME = None
    B_NAME = None
    B_LINK = None
    SETTINGS = {}
    FILES_ID = {}
    USERS_CANCEL = False
    GROUPS_CANCEL = False
    CHAT = {}
    BANNED_USERS = []
    BANNED_CHATS = []

def formate_file_name(file_name):
    """Remove unwanted prefixes from file names"""
    file_name = ' '.join(filter(
        lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'),
        file_name.split()
    ))
    return file_name

async def is_req_subscribed(bot, query):
    """Check if user has subscribed to required channel"""
    if await db.find_join_req(query.from_user.id):
        return True
    try:
        user = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
    except UserNotParticipant:
        return False
    except Exception as e:
        logger.exception(f"Error checking subscription: {e}")
        return False
    else:
        if user.status != enums.ChatMemberStatus.BANNED:
            return True
    return False

async def get_poster(query, bulk=False, id=False, file=None):
    """Fetch movie poster and details from IMDb"""
    if not id:
        query = (query.strip()).lower()
        title = query
        year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
        if year:
            year = list_to_str(year[:1])
            title = (query.replace(year, "")).strip()
        elif file is not None:
            year = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
            if year:
                year = list_to_str(year[:1])
        else:
            year = None

        movieid = imdb.search_movie(title.lower(), results=10)
        if not movieid:
            return None

        if year:
            filtered = list(filter(lambda k: str(k.get('year')) == str(year), movieid))
            if not filtered:
                filtered = movieid
        else:
            filtered = movieid

        movieid = list(filter(lambda k: k.get('kind') in ['movie', 'tv series'], filtered))
        if not movieid:
            movieid = filtered

        if bulk:
            return movieid

        movieid = movieid[0].movieID
    else:
        movieid = query

    movie = imdb.get_movie(movieid)
    if movie.get("original air date"):
        date = movie["original air date"]
    elif movie.get("year"):
        date = movie.get("year")
    else:
        date = "N/A"

    plot = ""
    if not LONG_IMDB_DESCRIPTION:
        plot = movie.get('plot')
        if plot and len(plot) > 0:
            plot = plot[0]
    else:
        plot = movie.get('plot outline')

    if plot and len(plot) > 800:
        plot = plot[0:800] + "..."

    return {
        'title': movie.get('title'),
        'votes': movie.get('votes'),
        "aka": list_to_str(movie.get("akas")),
        "seasons": movie.get("number of seasons"),
        "box_office": movie.get('box office'),
        'localized_title': movie.get('localized title'),
        'kind': movie.get("kind"),
        "imdb_id": f"tt{movie.get('imdbID')}",
        "cast": list_to_str(movie.get("cast")),
        "runtime": list_to_str(movie.get("runtimes")),
        "countries": list_to_str(movie.get("countries")),
        "certificates": list_to_str(movie.get("certificates")),
        "languages": list_to_str(movie.get("languages")),
        "director": list_to_str(movie.get("director")),
        "writer": list_to_str(movie.get("writer")),
        "producer": list_to_str(movie.get("producer")),
        "composer": list_to_str(movie.get("composer")),
        "cinematographer": list_to_str(movie.get("cinematographer")),
        "music_team": list_to_str(movie.get("music department")),
        "distributors": list_to_str(movie.get("distributors")),
        'release_date': date,
        'year': movie.get('year'),
        'genres': list_to_str(movie.get("genres")),
        'poster': movie.get('full-size cover url', START_IMG),
        'plot': plot,
        'rating': str(movie.get("rating")),
        'url': f'https://www.imdb.com/title/tt{movieid}'
    }

async def users_broadcast(user_id, message, is_pin):
    """Broadcast message to a user"""
    try:
        m = await message.copy(chat_id=user_id)
        if is_pin:
            await m.pin(both_sides=True)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await users_broadcast(user_id, message, is_pin)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        logging.info(f"{user_id} - Blocked the bot.")
        await db.delete_user(user_id)
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        logging.error(f"Error broadcasting to {user_id}: {e}")
        return False, "Error"

async def groups_broadcast(chat_id, message, is_pin):
    """Broadcast message to a group"""
    try:
        m = await message.copy(chat_id=chat_id)
        if is_pin:
            try:
                await m.pin()
            except Exception as e:
                logging.error(f"Error pinning message in {chat_id}: {e}")
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await groups_broadcast(chat_id, message, is_pin)
    except Exception as e:
        logging.error(f"Error broadcasting to {chat_id}: {e}")
        await db.delete_chat(chat_id)
        return "Error"

async def get_settings(group_id, pm_mode=False):
    """Get settings for a group or PM"""
    if pm_mode:
        return SETTINGS.copy()
    else:
        settings = await db.get_settings(group_id)
    return settings

async def save_group_settings(group_id, key, value):
    """Save group settings to database"""
    current = await get_settings(group_id)
    current.update({key: value})
    temp.SETTINGS.update({group_id: current})
    await db.update_settings(group_id, current)

def get_size(size):
    """Convert bytes to human readable format"""
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def get_name(name):
    """Remove @ mentions from names"""
    regex = re.sub(r'@\w+', '', name)
    return regex

def list_to_str(k):
    """Convert list to comma-separated string"""
    if not k:
        return "N/A"
    elif len(k) == 1:
        return str(k[0])
    else:
        return ', '.join(str(item) for item in k)

async def get_shortlink(link, grp_id, is_second_shortener=False, is_third_shortener=False, pm_mode=False):
    """Generate short link using configured shortener"""
    if not pm_mode:
        settings = await get_settings(grp_id)
    else:
        settings = SETTINGS

    if IS_VERIFY:
        if is_third_shortener:
            api, site = settings['api_three'], settings['shortner_three']
        else:
            if is_second_shortener:
                api, site = settings['api_two'], settings['shortner_two']
            else:
                api, site = settings['api'], settings['shortner']

        shortzy = Shortzy(api, site)
        try:
            link = await shortzy.convert(link)
        except Exception as e:
            logger.error(f"Error creating shortlink: {e}")
            try:
                link = await shortzy.get_quick_link(link)
            except Exception as e:
                logger.error(f"Error creating quick link: {e}")
    return link

def get_file_id(message: "Message") -> Any:
    """Extract file ID from message"""
    media_types = (
        "audio",
        "document",
        "photo",
        "sticker",
        "animation",
        "video",
        "voice",
        "video_note",
    )
    if message.media:
        for attr in media_types:
            media = getattr(message, attr, None)
            if media:
                setattr(media, "message_type", attr)
                return media

def get_status():
    """Get greeting based on time of day"""
    tz = pytz.timezone('Asia/Kolkata')
    hour = datetime.now(tz).time().hour
    if 5 <= hour < 12:
        sts = "𝐺𝑜𝑜𝑑 𝑀𝑜𝑟𝑛𝑖𝑛𝑔"
    elif 12 <= hour < 18:
        sts = "𝐺𝑜𝑜𝑑 𝐴𝑓𝑡𝑒𝑟𝑛𝑜𝑜𝑛"
    else:
        sts = "𝐺𝑜𝑜𝑑 𝐸𝑣𝑒𝑛𝑖𝑛𝑔"
    return sts

async def is_check_admin(bot, chat_id, user_id) -> Tuple[bool, str]:
    """
    Check if user is admin in chat.
    
    Args:
        bot: Pyrogram client
        chat_id: Chat ID to check
        user_id: User ID to check
        
    Returns:
        Tuple of (is_admin: bool, error_message: str or None)
    """
    # CRITICAL FIX: Handle None user_id (anonymous admins)
    if not user_id:
        logger.warning(f"Cannot verify admin status: user_id is None (anonymous admin)")
        return False, "Cannot verify anonymous admins. Please send command with your personal account."
    
    try:
        # Get member info
        member = await bot.get_chat_member(chat_id, user_id)
        
        # Check if user is admin or owner
        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            logger.info(f"User {user_id} is admin in {chat_id}")
            return True, None
        else:
            logger.warning(f"User {user_id} is not admin in {chat_id} (status: {member.status})")
            return False, "You are not an admin in this group."
            
    except UserNotParticipant:
        logger.warning(f"User {user_id} not in chat {chat_id}")
        return False, "You are not a member of this group."
        
    except ChatAdminRequired:
        logger.error(f"Bot lacks admin rights in {chat_id}")
        return False, "Bot is not an admin. Please make bot admin to use this command."
        
    except PeerIdInvalid:
        logger.error(f"Invalid peer ID: user={user_id}, chat={chat_id}")
        return False, "Invalid user or chat ID."
        
    except Exception as e:
        logger.error(f"Unexpected error checking admin status for {user_id} in {chat_id}: {e}", exc_info=True)
        return False, f"Error checking admin status: {str(e)}"

async def get_seconds(time_string):
    """Convert time string to seconds"""
    def extract_value_and_unit(ts):
        value = ""
        unit = ""
        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1
        unit = ts[index:].lstrip()
        if value:
            value = int(value)
        return value, unit

    value, unit = extract_value_and_unit(time_string)
    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hour':
        return value * 3600
    elif unit == 'day':
        return value * 86400
    elif unit == 'month':
        return value * 86400 * 30
    elif unit == 'year':
        return value * 86400 * 365
    else:
        return 0

def get_readable_time(seconds):
    """Convert seconds to readable time format"""
    periods = [('days', 86400), ('hour', 3600), ('min', 60), ('sec', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    return result if result else '0sec'
