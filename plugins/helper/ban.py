from pyrogram import Client, filters
from pyrogram.errors import PeerIdInvalid
from database.users_chats_db import db  
from utils import temp 
from info import *

@Client.on_message(filters.command('ban') & filters.user(ADMINS))
async def ban_a_user(bot, message):
    if len(message.command) == 1:
        return await message.reply('**Usage: /ban 12345678 Reason**')
    
    user_id = message.command[1]
    reason = " ".join(message.command[2:]) if len(message.command) > 2 else "No Reason Provided"
    
    try:
        await db.ban_user(int(user_id), reason)
        await message.reply(f'**Successfully Banned User: `{user_id}`**')
    except Exception as e:
        await message.reply(f'**Error:** `{e}`')
   
@Client.on_message(filters.command('unban') & filters.user(ADMINS))
async def unban_a_user(bot, message):
    if len(message.command) == 1:
        return await message.reply('Give me a user id / username')
    r = message.text.split(None)
    if len(r) > 2:
        reason = message.text.split(None, 2)[2]
        chat = message.text.split(None, 2)[1]
    else:
        chat = message.command[1]
        reason = "No reason Provided"
    try:
        chat = int(chat)
    except:
        pass
    try:
        k = await bot.get_users(chat)
    except PeerIdInvalid:
        return await message.reply("This is an invalid user, make sure ia have met him before.")
    except IndexError:
        return await message.reply("Thismight be a channel, make sure its a user.")
    except Exception as e:
        return await message.reply(f'Error - {e}')
    else:
        jar = await db.get_ban_status(k.id)
        if not jar['is_banned']:
            return await message.reply(f"{k.mention} is not yet banned.")
        await db.remove_ban(k.id)
        temp.BANNED_USERS.remove(k.id)
        await message.reply(f"Successfully unbanned {k.mention}")
      
