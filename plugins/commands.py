import os, requests, logging, random, asyncio, string, pytz, traceback
from datetime import timedelta, datetime as dt
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup , ForceReply, ReplyKeyboardMarkup
from database.ia_filterdb import Media, get_file_details, get_bad_files, unpack_new_file_id
from database.users_chats_db import db
from database.config_db import mdb
from database.topdb import JsTopDB
from database.jsreferdb import referdb
from utils import formate_file_name, get_settings, save_group_settings, is_req_subscribed, get_size, get_shortlink, is_check_admin, temp, get_readable_time
from info import *

logger = logging.getLogger(__name__)
verification_ids = {}

@Client.on_message(filters.command("settings"))
async def settings(client, message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply("<b>You are an anonymous admin.</b>")
    
    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("Use this command in a group.")

    # Fix: Correctly identify if user is admin before showing settings
    if not await is_check_admin(client, message.chat.id, user_id):
        return await message.reply_text('<b>You are not an admin in this group.</b>')

    settings = await get_settings(message.chat.id)
    if settings:
        buttons = [[
            InlineKeyboardButton('ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{message.chat.id}'),
            InlineKeyboardButton('ᴏɴ ✓' if settings["auto_filter"] else 'ᴏғғ ✗', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{message.chat.id}')
        ],[
            InlineKeyboardButton('ᴠᴇʀɪғʏ', callback_data='verifyon'),
            InlineKeyboardButton('ᴏɴ ✓' if settings["is_verify"] else 'ᴏғғ ✗', callback_data='verifyon')
        ],[
            InlineKeyboardButton('❌ ᴄʟsᴇ ❌', callback_data='close_data')
        ]]
        await message.reply_text(
            text=f"Change settings for <b>'{message.chat.title}'</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

@Client.on_message(filters.command("verifyoff"))
async def verifyoff(bot, message):
    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("This works in groups only.")
    
    if not await is_check_admin(bot, message.chat.id, message.from_user.id):
        return await message.reply_text('<b>Admin access denied.</b>')
    
    try:
        input_id = message.command[1]
        # Fix: Ensure verification session is tracked by Group ID
        if message.chat.id in verification_ids and verification_ids[message.chat.id] == input_id:
            await save_group_settings(message.chat.id, 'is_verify', False)
            del verification_ids[message.chat.id]
            return await message.reply_text("✅ Verification disabled.")
        else:
            return await message.reply_text("❌ Invalid ID.")
    except IndexError:
        return await message.reply_text("Usage: `/verifyoff {id}`")

@Client.on_message(filters.command("verifyon"))
async def verifyon(bot, message):
    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("Groups only!")
    
    if not await is_check_admin(bot, message.chat.id, message.from_user.id):
        return await message.reply_text('<b>Admin access denied.</b>')
    
    await save_group_settings(message.chat.id, 'is_verify', True)
    return await message.reply_text("✅ Verification enabled.")

