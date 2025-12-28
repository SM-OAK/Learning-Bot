import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from utils import is_check_admin
from Script import script
from info import ADMINS


@Client.on_message(filters.command('grp_cmds'))
async def grp_cmds(client, message):
    """Show group admin commands"""
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply("<b>💔 ʏᴏᴜ ᴀʀᴇ ᴀɴᴏɴʏᴍᴏᴜꜱ ᴀᴅᴍɪɴ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ...</b>")
    
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<code>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ.</code>")
    
    grp_id = message.chat.id
    
    # FIX: Unpack tuple from is_check_admin
    is_admin, error_msg = await is_check_admin(client, grp_id, message.from_user.id)
    if not is_admin:
        return await message.reply_text(f'<b>❌ {error_msg}</b>')
    
    buttons = [[
        InlineKeyboardButton('❌ ᴄʟᴏsᴇ ❌', callback_data='close_data')
    ]]        
    
    await message.reply_text(
        text=script.GROUP_C_TEXT,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )
    

@Client.on_message(filters.command("admin_cmds") & filters.user(ADMINS))
async def admin_cmds(client, message):
    """Show admin commands with auto-delete"""
    buttons = [
        [KeyboardButton("/add_premium"), KeyboardButton("/premium_users")],
        [KeyboardButton("/remove_premium"), KeyboardButton("/add_redeem")],
        [KeyboardButton("/refresh"), KeyboardButton("/set_muc")],
        [KeyboardButton("/pm_search_on"), KeyboardButton("/pm_search_off")],
        [KeyboardButton("/set_ads"), KeyboardButton("/del_ads")],
        [KeyboardButton("/setlist"), KeyboardButton("/clearlist")],
        [KeyboardButton("/verify_id"), KeyboardButton("/index")],
        [KeyboardButton("/send"), KeyboardButton("/leave")],
        [KeyboardButton("/ban"), KeyboardButton("/unban")],
        [KeyboardButton("/broadcast"), KeyboardButton("/grp_broadcast")],
        [KeyboardButton("/delreq"), KeyboardButton("/channel")],
        [KeyboardButton("/del_file"), KeyboardButton("/delete")],
        [KeyboardButton("/deletefiles"), KeyboardButton("/deleteall")],
        [KeyboardButton("All These Commands Can Be Used Only By Admins.")],
        [KeyboardButton("⚡")]
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
   
    sent_message = await message.reply(
        "<b>Admin All Commands [auto delete 2 min] 👇</b>",
        reply_markup=reply_markup,
    ) 
    
    # Auto-delete after 2 minutes (120 seconds)
    await asyncio.sleep(120)
    try:
        await sent_message.delete()
        await message.delete()
    except Exception as e:
        # Message might already be deleted
        pass


@Client.on_message(filters.command("commands") & filters.user(ADMINS))
async def set_commands(client, message):
    """Set bot commands in Telegram UI"""
    commands = [
        BotCommand("start", "Start The Bot"),
        BotCommand("most", "Get Most Searches Button List"),
        BotCommand("trend", "Get Top Trending Button List"),
        BotCommand("mostlist", "Show Most Searches List"),
        BotCommand("trendlist", "Get Top Trending Button List"),
        BotCommand("plan", "Check Available Premium Membership Plans"),
        BotCommand("myplan", "Check Your Current Plan"),
        BotCommand("refer", "To Refer Your Friend And Get Premium"),
        BotCommand("stats", "Check My Database"),
        BotCommand("id", "Get Telegram Id"),
        BotCommand("font", "To Generate Cool Fonts"),
        BotCommand("details", "Check Group Details"),
        BotCommand("settings", "Change Bot Setting"),
        BotCommand("grp_cmds", "Check Group Commands"),
        BotCommand("admin_cmds", "Bot Admin Commands")
    ]
    
    try:
        await client.set_bot_commands(commands)
        await message.reply("✅ Bot commands set successfully!")
    except Exception as e:
        await message.reply(f"❌ Failed to set commands: {str(e)}")
