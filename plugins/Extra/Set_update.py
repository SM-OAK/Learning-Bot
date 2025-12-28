from pyrogram import Client, filters, enums
from info import ADMINS
import re
from database.users_chats_db import db
import logging

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("set_muc") & filters.user(ADMINS))
async def set_muc_id(client, message):
    """Set movie update channel ID"""
    
    # Check if channel ID provided
    if len(message.command) < 2:
        return await message.reply(
            "<b>⚠️ Usage Error</b>\n\n"
            "<b>Usage:</b> <code>/set_muc CHANNEL_ID</code>\n\n"
            "<b>Example:</b> <code>/set_muc -1001234567890</code>\n\n"
            "<b>How to get Channel ID:</b>\n"
            "1. Forward any message from channel to @userinfobot\n"
            "2. Copy the channel ID\n"
            "3. Use it with this command"
        )
    
    try:
        channel_id = message.command[1]
        
        # Validate channel ID format
        if not str(channel_id).startswith('-100'):
            return await message.reply(
                "❌ <b>Invalid Channel ID</b>\n\n"
                "Channel ID must start with -100\n\n"
                "<b>Example:</b> <code>-1001234567890</code>"
            )
        
        if len(str(channel_id)) != 14:
            return await message.reply(
                "❌ <b>Invalid Channel ID Length</b>\n\n"
                "Channel ID must be exactly 14 characters\n\n"
                "<b>Example:</b> <code>-1001234567890</code> (14 characters)"
            )
        
        # Convert to integer to validate
        try:
            channel_id_int = int(channel_id)
        except ValueError:
            return await message.reply(
                "❌ <b>Invalid Channel ID Format</b>\n\n"
                "Channel ID must be a valid number\n\n"
                "<b>Example:</b> <code>-1001234567890</code>"
            )
        
        # Verify bot can access the channel
        status_msg = await message.reply("⏳ Verifying channel access...")
        
        try:
            # Try to get channel info
            channel = await client.get_chat(channel_id_int)
            
            # Check if bot is admin
            try:
                bot_member = await client.get_chat_member(channel_id_int, client.me.id)
                
                if bot_member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                    return await status_msg.edit(
                        "❌ <b>Bot Not Admin</b>\n\n"
                        f"<b>Channel:</b> {channel.title}\n"
                        f"<b>ID:</b> <code>{channel_id}</code>\n\n"
                        "Bot must be admin in the channel to send updates.\n\n"
                        "<b>How to fix:</b>\n"
                        "1. Add bot to your channel\n"
                        "2. Promote bot to admin\n"
                        "3. Try this command again"
                    )
                
            except Exception as e:
                logger.error(f"Error checking bot admin status: {e}")
                return await status_msg.edit(
                    "❌ <b>Permission Check Failed</b>\n\n"
                    f"Could not verify bot permissions in channel.\n\n"
                    "Make sure:\n"
                    "• Bot is added to the channel\n"
                    "• Bot is admin in the channel\n\n"
                    f"Error: <code>{str(e)}</code>"
                )
            
            # Save to database
            is_success = await db.movies_update_channel_id(channel_id)
            
            if is_success:
                await status_msg.edit(
                    "<b>✅ Movie Update Channel Set Successfully!</b>\n\n"
                    f"<b>Channel:</b> {channel.title}\n"
                    f"<b>Channel ID:</b> <code>{channel_id}</code>\n"
                    f"<b>Bot Status:</b> Admin ✅\n\n"
                    "New movie updates will be posted to this channel."
                )
                
                # Send test message to confirm
                try:
                    test_msg = await client.send_message(
                        channel_id_int,
                        "<b>🎬 Movie Update Channel Configured</b>\n\n"
                        "This channel is now set as the movie update channel.\n"
                        "New movies will be automatically posted here."
                    )
                    await asyncio.sleep(5)
                    await test_msg.delete()
                except Exception as e:
                    logger.error(f"Failed to send test message: {e}")
            else:
                await status_msg.edit(
                    "❌ <b>Database Error</b>\n\n"
                    f"Failed to save channel ID to database.\n\n"
                    "Please try again or contact support."
                )
                
        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            return await status_msg.edit(
                "❌ <b>Channel Not Found</b>\n\n"
                f"Could not access channel with ID: <code>{channel_id}</code>\n\n"
                "<b>Possible reasons:</b>\n"
                "• Bot is not in the channel\n"
                "• Channel ID is incorrect\n"
                "• Channel is private and bot not added\n\n"
                f"Error: <code>{str(e)}</code>"
            )
            
    except IndexError:
        return await message.reply(
            "❌ <b>Missing Channel ID</b>\n\n"
            "Please provide a channel ID.\n\n"
            "<b>Usage:</b> <code>/set_muc -1001234567890</code>"
        )
    except Exception as e:
        logger.exception(f"Error in set_muc_id: {e}")
        return await message.reply(
            "❌ <b>Unexpected Error</b>\n\n"
            f"Failed to set movie update channel.\n\n"
            f"Error: <code>{str(e)}</code>\n\n"
            "Please try again or contact support."
        )


@Client.on_message(filters.command("show_muc") & filters.user(ADMINS))
async def show_muc_id(client, message):
    """Show current movie update channel"""
    try:
        channel_id = await db.movies_update_channel_id()
        
        if not channel_id or channel_id == 0:
            return await message.reply(
                "<b>📋 Movie Update Channel</b>\n\n"
                "<b>Status:</b> ❌ Not Configured\n\n"
                "No movie update channel is set.\n\n"
                "<b>To set:</b> <code>/set_muc CHANNEL_ID</code>"
            )
        
        # Get channel info
        try:
            channel = await client.get_chat(channel_id)
            
            # Get bot status
            try:
                bot_member = await client.get_chat_member(channel_id, client.me.id)
                bot_status = "✅ Admin" if bot_member.status in [
                    enums.ChatMemberStatus.ADMINISTRATOR,
                    enums.ChatMemberStatus.OWNER
                ] else "❌ Not Admin"
            except:
                bot_status = "❓ Unknown"
            
            await message.reply(
                "<b>📋 Movie Update Channel</b>\n\n"
                f"<b>Channel:</b> {channel.title}\n"
                f"<b>Username:</b> @{channel.username if channel.username else 'Private'}\n"
                f"<b>Channel ID:</b> <code>{channel_id}</code>\n"
                f"<b>Bot Status:</b> {bot_status}\n\n"
                "<b>Manage:</b>\n"
                f"• Change: <code>/set_muc NEW_CHANNEL_ID</code>",
                disable_web_page_preview=True
            )
        except Exception as e:
            await message.reply(
                "<b>📋 Movie Update Channel</b>\n\n"
                f"<b>Channel ID:</b> <code>{channel_id}</code>\n\n"
                "⚠️ Could not fetch channel details.\n"
                "Bot may not have access to this channel.\n\n"
                "<b>Manage:</b>\n"
                f"• Change: <code>/set_muc NEW_CHANNEL_ID</code>"
            )
            
    except Exception as e:
        logger.exception(f"Error in show_muc_id: {e}")
        await message.reply(
            "❌ <b>Error</b>\n\n"
            f"Failed to fetch movie update channel.\n\n"
            f"Error: <code>{str(e)}</code>"
        )
