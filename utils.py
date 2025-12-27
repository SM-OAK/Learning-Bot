import logging
import asyncio
import pytz, re, os 
from datetime import datetime
from typing import Any
from pyrogram import enums
from pyrogram.types import Message
from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid
from imdb import Cinemagoer
from shortzy import Shortzy
from info import AUTH_CHANNEL, LONG_IMDB_DESCRIPTION, IS_VERIFY, SETTINGS, START_IMG

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BANNED = {}
imdb = Cinemagoer() 

# FIXED: Moved utility functions to the top to prevent ImportError during circular imports
async def get_seconds(time_string):
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
    periods = [(' days', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name} '
    return result.strip()

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
    file_name = ' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file_name.split()))
    return file_name

# FIXED: Moved 'db' import inside functions to break circular dependency
async def is_req_subscribed(bot, query):
    from database.users_chats_db import db
    if await db.find_join_req(query.from_user.id):
        return True
    try:
        user = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
    except UserNotParticipant:
        pass
    except Exception as e:
        logger.exception(e)
    else:
        if user.status != enums.ChatMemberStatus.BANNED:
            return True
    return False

async def get_poster(query, bulk=False, id=False, file=None):
    if not id:
        query = (query.strip()).lower()
        title = query
        year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
        if year:
            year = year[0]
            title = (query.replace(year, "")).strip()
        elif file is not None:
            year = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
            if year:
                year = year[0]
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
    
    date = movie.get("original air date") or movie.get("year") or "N/A"
    
    if not LONG_IMDB_DESCRIPTION:
        plot = movie.get('plot')
        plot = plot[0] if plot else ""
    else:
        plot = movie.get('plot outline')
    
    if plot and len(plot) > 800:
        plot = plot[0:800] + "..."

    return {
        'title': movie.get('title'),
        'votes': movie.get('votes'),
        'release_date': date,
        'year': movie.get('year'),
        'genres': ', '.join(movie.get("genres", [])),
        'poster': movie.get('full-size cover url', START_IMG),
        'plot': plot,
        'rating': str(movie.get("rating", "N/A")),
        'url': f'https://www.imdb.com/title/tt{movieid}'
    }

async def users_broadcast(user_id, message, is_pin):
    from database.users_chats_db import db
    try:
        m = await message.copy(chat_id=user_id)
        if is_pin:
            await m.pin(both_sides=True)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await users_broadcast(user_id, message, is_pin)
    except (InputUserDeactivated, UserIsBlocked, PeerIdInvalid):
        await db.delete_user(int(user_id))
        return False, "Error"
    except Exception:
        return False, "Error"

async def groups_broadcast(chat_id, message, is_pin):
    from database.users_chats_db import db
    try:
        m = await message.copy(chat_id=chat_id)
        if is_pin:
            try:
                await m.pin()
            except:
                pass
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await groups_broadcast(chat_id, message, is_pin)
    except Exception:
        await db.delete_chat(chat_id)
        return "Error"

async def get_settings(group_id, pm_mode=False):
    from database.users_chats_db import db
    if pm_mode:
        return SETTINGS.copy()
    return await db.get_settings(group_id)
    
async def save_group_settings(group_id, key, value):
    from database.users_chats_db import db
    current = await get_settings(group_id)
    current.update({key: value})
    temp.SETTINGS.update({group_id: current})
    await db.update_settings(group_id, current)

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units) - 1:
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def get_status():
    tz = pytz.timezone('Asia/Colombo')
    hour = datetime.now(tz).time().hour
    if 5 <= hour < 12:
        return "𝐺𝑜𝑜𝑑 𝑀𝑜𝑟𝑛𝑖𝑛𝑔"
    elif 12 <= hour < 18:
        return "𝐺𝑜𝑜𝑑 𝐴𝑓𝑡𝑒𝑟𝑛𝑜𝑜𝑛"
    return "𝐺𝑜𝑜𝑑 𝐸𝑣𝑒𝑛𝑖𝑛𝑔"

async def is_check_admin(bot, chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except:
        return False

async def get_shortlink(link, grp_id, is_second_shortener=False, is_third_shortener=False, pm_mode=False):
    settings = SETTINGS if pm_mode else await get_settings(grp_id)
    if IS_VERIFY:
        if is_third_shortener:             
            api, site = settings.get('api_three'), settings.get('shortner_three')
        elif is_second_shortener:
            api, site = settings.get('api_two'), settings.get('shortner_two')
        else:
            api, site = settings.get('api'), settings.get('shortner')
        
        if not api or not site:
            return link
            
        shortzy = Shortzy(api, site)
        try:
            return await shortzy.convert(link)
        except:
            return await shortzy.get_quick_link(link)
    return link
                                
