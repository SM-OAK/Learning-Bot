from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL
from utils import is_check_admin
import logging

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("fsub"))
async def force_subscribe(client, message):
    """Set force subscribe for a group"""
    m = await message.reply_text("⏳ Wait, I'm checking...")
    
    # Check if used in group
    if not message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.edit("❌ This command is only for groups!")
    
    # FIX: Unpack tuple from is_check_admin
    is_admin, error_msg = await is_check_admin(client, message.chat.id, message.from_user.id)
    if not is_admin:
        return await m.edit(f"❌ {error_msg}")
    
    # Get channel ID from command
    try: 
        toFsub = message.command[1]
    except IndexError:
        return await m.edit(
            "<b>⚠️ Usage Error</b>\n\n"
            "<b>Usage:</b> <code>/fsub CHAT_ID</code>\n\n"
            "<b>Example:</b> <code>/fsub -1001234567890</code>\n\n"
            "<b>How to get Chat ID:</b>\n"
            "1. Forward any message from your channel to @userinfobot\n"
            "2. Copy the channel ID\n"
            "3. Use it with this command"
        )
    
    # Validate and format channel ID
    if not toFsub.startswith("-100"):
        toFsub = '-100' + toFsub
    
    if not toFsub[1:].isdigit() or len(toFsub) != 14:
        return await m.edit(
            "❌ <b>Invalid Chat ID!</b>\n\n"
            "Chat ID must be 14 characters and start with -100\n\n"
            "<b>Example:</b> <code>-1001234567890</code>"
        )
    
    toFsub = int(toFsub)
    
    # Prevent setting fsub to same group
    if toFsub == message.chat.id:
        return await m.edit(
            "❌ <b>Invalid Configuration</b>\n\n"
            "You can't set force subscribe to this same group!\n"
            "Please use a different channel ID."
        )
    
    # Check if bot is admin in target channel
    is_bot_admin, bot_error_msg = await is_check_admin(client, toFsub, client.me.id)
    if not is_bot_admin:
        return await m.edit(
            "❌ <b>Bot Not Admin</b>\n\n"
            f"{bot_error_msg}\n\n"
            "<b>How to fix:</b>\n"
            "1. Add bot to your channel\n"
            "2. Make bot admin with 'Invite Users' permission\n"
            "3. Try this command again"
        )
    
    # Save to database
    try:
        await db.setFsub(grpID=message.chat.id, fsubID=toFsub)
        
        # Try to get channel name
        try:
            channel = await client.get_chat(toFsub)
            channel_name = channel.title
        except:
            channel_name = f"Channel {toFsub}"
        
        return await m.edit(
            f"<b>✅ Force Subscribe Enabled</b>\n\n"
            f"<b>Group:</b> {message.chat.title}\n"
            f"<b>Channel:</b> {channel_name}\n"
            f"<b>Channel ID:</b> <code>{toFsub}</code>\n\n"
            f"Users must now join the channel to access files.\n\n"
            f"<b>Manage:</b>\n"
            f"• View: <code>/show_fsub</code>\n"
            f"• Remove: <code>/del_fsub</code>"
        )
    except Exception as e:
        logger.exception(f"Error setting fsub: {e}")
        return await m.edit(
            f"❌ <b>Database Error</b>\n\n"
            f"Failed to set force subscribe.\n\n"
            f"Error: <code>{str(e)}</code>\n\n"
            f"Please try again or contact support."
        )


@Client.on_message(filters.command("del_fsub"))
async def del_force_subscribe(client, message):
    """Remove force subscribe from group"""
    m = await message.reply_text("⏳ Wait, I'm checking...")
    
    # Check if used in group
    if not message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.edit("❌ This command is only for groups!")
    
    # FIX: Unpack tuple from is_check_admin
    is_admin, error_msg = await is_check_admin(client, message.chat.id, message.from_user.id)
    if not is_admin:
        return await m.edit(f"❌ {error_msg}")
    
    # Delete from database
    try:
        ifDeleted = await db.delFsub(message.chat.id)
        
        if ifDeleted:
            return await m.edit(
                f"<b>✅ Force Subscribe Removed</b>\n\n"
                f"<b>Group:</b> {message.chat.title}\n\n"
                f"Users can now access files without joining any channel.\n\n"
                f"<b>To add again:</b> <code>/fsub YOUR_CHANNEL_ID</code>"
            )
        else:
            return await m.edit(
                f"<b>⚠️ Not Found</b>\n\n"
                f"Force subscribe is not configured for {message.chat.title}\n\n"
                f"<b>To add:</b> <code>/fsub YOUR_CHANNEL_ID</code>"
            )
    except Exception as e:
        logger.exception(f"Error deleting fsub: {e}")
        return await m.edit(
            f"❌ <b>Database Error</b>\n\n"
            f"Failed to remove force subscribe.\n\n"
            f"Error: <code>{str(e)}</code>"
        )


@Client.on_message(filters.command("show_fsub"))
async def show_fsub(client, message):
    """Show current force subscribe configuration"""
    m = await message.reply_text("⏳ Wait, I'm checking...")
    
    # Check if used in group
    if not message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.edit("❌ This command is only for groups!")
    
    # FIX: Unpack tuple from is_check_admin
    is_admin, error_msg = await is_check_admin(client, message.chat.id, message.from_user.id)
    if not is_admin:
        return await m.edit(f"❌ {error_msg}")
    
    # Get fsub configuration
    try:
        fsub = await db.getFsub(message.chat.id)
        
        if fsub:
            # Get channel info
            try:
                channel = await client.get_chat(fsub)
                channel_name = channel.title
                invite_link = await client.export_chat_invite_link(fsub)
                
                await m.edit(
                    f"<b>📋 Force Subscribe Configuration</b>\n\n"
                    f"<b>Group:</b> {message.chat.title}\n"
                    f"<b>Channel:</b> {channel_name}\n"
                    f"<b>Channel ID:</b> <code>{fsub}</code>\n"
                    f"<b>Invite Link:</b> <a href='{invite_link}'>Join Channel</a>\n\n"
                    f"<b>Status:</b> ✅ Active\n\n"
                    f"<b>Manage:</b>\n"
                    f"• Remove: <code>/del_fsub</code>",
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Error getting channel info: {e}")
                await m.edit(
                    f"<b>📋 Force Subscribe Configuration</b>\n\n"
                    f"<b>Group:</b> {message.chat.title}\n"
                    f"<b>Channel ID:</b> <code>{fsub}</code>\n\n"
                    f"<b>Status:</b> ✅ Active\n\n"
                    f"⚠️ Could not fetch channel details.\n"
                    f"Make sure bot is still admin in the channel.\n\n"
                    f"<b>Manage:</b>\n"
                    f"• Remove: <code>/del_fsub</code>"
                )
        else:
            await m.edit(
                f"<b>📋 Force Subscribe Configuration</b>\n\n"
                f"<b>Group:</b> {message.chat.title}\n\n"
                f"<b>Status:</b> ❌ Not Configured\n\n"
                f"Force subscribe is not set for this group.\n\n"
                f"<b>To add:</b> <code>/fsub YOUR_CHANNEL_ID</code>"
            )
    except Exception as e:
        logger.exception(f"Error showing fsub: {e}")
        await m.edit(
            f"❌ <b>Database Error</b>\n\n"
            f"Failed to fetch force subscribe configuration.\n\n"
            f"Error: <code>{str(e)}</code>"
                                      )
