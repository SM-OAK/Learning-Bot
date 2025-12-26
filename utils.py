import logging
from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid
from info import AUTH_CHANNEL, LONG_IMDB_DESCRIPTION, IS_VERIFY, SETTINGS, START_IMG
from imdb import Cinemagoer
import asyncio
from pyrogram.types import Message
from pyrogram import enums
import pytz, re, os 
from shortzy import Shortzy
from datetime import datetime
from typing import Any
from database.users_chats_db import db

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BANNED = {}
imdb = Cinemagoer() 
 
class temp(object):
    ME = None
    CURRENT=int(os.environ.get("SKIP", 2))
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

async def is_req_subscribed(bot, query):
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

async def get_settings(group_id , pm_mode = False):
    if pm_mode:
        return SETTINGS.copy()
    else:
        settings = await db.get_settings(group_id)
    return settings 

async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current.update({key: value})
    temp.SETTINGS.update({group_id: current})
    await db.update_settings(group_id, current)

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

async def is_check_admin(bot, chat_id, user_id):
    try:
        # Fix: Ensure IDs are integers before calling API
        member = await bot.get_chat_member(int(chat_id), int(user_id))
        return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except Exception as e:
        logger.error(f"Admin Check Failed: {e}")
        return False

def get_readable_time(seconds):
    periods = [('days', 86400), ('hour', 3600), ('min', 60), ('sec', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    return result

async def get_shortlink(link, grp_id, is_second_shortener=False, is_third_shortener=False , pm_mode=False):
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
            link = await shortzy.get_quick_link(link)
    return link
 
