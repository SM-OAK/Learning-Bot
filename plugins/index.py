import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from info import ADMINS, LOG_CHANNEL, CHANNELS
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp, get_readable_time, is_check_admin
import time
import logging

logger = logging.getLogger(__name__)

lock = asyncio.Lock()

# ✅ FIX #1: Video file extensions
VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.3gp', '.mpeg', '.mpg']

# ✅ FIX #2: Video mime types
VIDEO_MIME_TYPES = [
    'video/mp4',
    'video/x-matroska',
    'video/avi',
    'video/quicktime',
    'video/x-flv',
    'video/x-ms-wmv',
    'video/webm',
    'video/mpeg',
    'video/3gpp',
    'application/octet-stream'  # Sometimes videos are detected as this
]


def is_video_file(media) -> bool:
    """
    ✅ FIXED: Comprehensive video file detection
    """
    if not media:
        return False
    
    # Check mime type
    mime_type = getattr(media, 'mime_type', '')
    if mime_type and mime_type in VIDEO_MIME_TYPES:
        return True
    
    # Check file extension
    file_name = getattr(media, 'file_name', '')
    if file_name:
        file_name_lower = file_name.lower()
        if any(file_name_lower.endswith(ext) for ext in VIDEO_EXTENSIONS):
            return True
    
    # Check file size (videos are usually > 5MB)
    file_size = getattr(media, 'file_size', 0)
    if file_size > 5 * 1024 * 1024:  # 5MB
        # If it's a large document, it might be a video
        if file_name:
            file_name_lower = file_name.lower()
            if any(file_name_lower.endswith(ext) for ext in VIDEO_EXTENSIONS):
                return True
    
    return False


@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    """✅ FIXED: Index callback with admin check"""
    _, ident, chat, lst_msg_id, skip = query.data.split("#")
    
    # FIX #3: Check if user is admin
    user_id = query.from_user.id if query.from_user else None
    is_admin, error_msg = await is_check_admin(bot, query.message.chat.id, user_id)
    
    if not is_admin:
        await query.answer(error_msg or "❌ Only admins can use this!", show_alert=True)
        return
    
    if ident == 'yes':
        msg = query.message
        await msg.edit("<b>⏳ Indexing started...</b>")
        try:
            chat = int(chat)
        except:
            chat = chat
        await index_files_to_db(int(lst_msg_id), chat, msg, bot, int(skip))
    elif ident == 'cancel':
        temp.CANCEL = True
        await query.message.edit("⏳ Trying to cancel indexing...")


@Client.on_message(filters.command('index') & filters.private & filters.incoming)
async def send_for_index(bot, message):
    """✅ FIXED: Index command with proper admin check"""
    # FIX #4: Check if user is admin
    if message.from_user.id not in ADMINS:
        await message.reply('❌ Only bot owner can use this command.')
        return
    
    if lock.locked():
        return await message.reply('⏳ Wait until previous indexing process completes.')
    
    i = await message.reply("📤 Forward the last message from the channel or send the last message link.")
    msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id)
    await i.delete()
    
    if msg.text and msg.text.startswith("https://t.me"):
        try:
            msg_link = msg.text.split("/")
            last_msg_id = int(msg_link[-1])
            chat_id = msg_link[-2]
            if chat_id.isnumeric():
                chat_id = int(("-100" + chat_id))
        except:
            await message.reply('❌ Invalid message link!')
            return
    elif msg.forward_from_chat and msg.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = msg.forward_from_message_id
        chat_id = msg.forward_from_chat.username or msg.forward_from_chat.id
    else:
        await message.reply('❌ This is not a forwarded message or valid link.')
        return
    
    try:
        chat = await bot.get_chat(chat_id)
    except Exception as e:
        return await message.reply(f'❌ Error: {e}')
    
    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply("❌ I can only index channels.")
    
    s = await message.reply("🔢 Send the skip number (how many messages to skip from start).\n\nExample: Send `0` to start from beginning.")
    msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id)
    await s.delete()
    
    try:
        skip = int(msg.text)
    except:
        return await message.reply("❌ Please send a valid number.")
    
    buttons = [[
        InlineKeyboardButton('✅ YES', callback_data=f'index#yes#{chat_id}#{last_msg_id}#{skip}')
    ],[
        InlineKeyboardButton('❌ CLOSE', callback_data='close_data'),
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply(
        f'<b>📊 Index Confirmation</b>\n\n'
        f'<b>Channel:</b> {chat.title}\n'
        f'<b>Total Messages:</b> <code>{last_msg_id}</code>\n'
        f'<b>Skip Messages:</b> <code>{skip}</code>\n\n'
        f'Do you want to start indexing?',
        reply_markup=reply_markup
    )


@Client.on_message(filters.command('channel') & filters.private)
async def channel_info(bot, message):
    """✅ FIXED: Channel info command with admin check"""
    # FIX #5: Check if user is admin
    if message.from_user.id not in ADMINS:
        await message.reply('❌ Only bot owner can use this command.')
        return
    
    ids = CHANNELS
    if not ids:
        return await message.reply("❌ No channels configured in CHANNELS variable.")
    
    text = '<b>📺 Indexed Channels:</b>\n\n'
    for id in ids:
        try:
            chat = await bot.get_chat(id)
            text += f'• {chat.title} (<code>{id}</code>)\n'
        except Exception as e:
            text += f'• <code>{id}</code> (❌ Error: {str(e)[:30]})\n'
    
    text += f'\n<b>Total:</b> {len(ids)}'
    await message.reply(text)


async def index_files_to_db(lst_msg_id, chat, msg, bot, skip):
    """✅ FIXED: Index files with better video detection"""
    start_time = time.time()
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    current = skip
    
    async with lock:
        try:
            async for message in bot.iter_messages(chat, lst_msg_id, skip):
                time_taken = get_readable_time(time.time()-start_time)
                
                if temp.CANCEL:
                    temp.CANCEL = False
                    await msg.edit(
                        f'<b>⛔ Indexing Cancelled!</b>\n\n'
                        f'<b>Time:</b> {time_taken}\n'
                        f'<b>Saved:</b> <code>{total_files}</code> files\n'
                        f'<b>Duplicates:</b> <code>{duplicate}</code>\n'
                        f'<b>Deleted:</b> <code>{deleted}</code>\n'
                        f'<b>Non-Media:</b> <code>{no_media}</code>\n'
                        f'<b>Unsupported:</b> <code>{unsupported}</code>\n'
                        f'<b>Errors:</b> <code>{errors}</code>'
                    )
                    return
                
                current += 1
                
                # Update progress every 100 messages
                if current % 100 == 0:
                    btn = [[
                        InlineKeyboardButton('⛔ CANCEL', callback_data=f'index#cancel#{chat}#{lst_msg_id}#{skip}')
                    ]]
                    await msg.edit_text(
                        text=f'<b>⏳ Indexing in progress...</b>\n\n'
                        f'<b>Processed:</b> <code>{current}</code>\n'
                        f'<b>Saved:</b> <code>{total_files}</code>\n'
                        f'<b>Duplicates:</b> <code>{duplicate}</code>\n'
                        f'<b>Deleted:</b> <code>{deleted}</code>\n'
                        f'<b>Non-Media:</b> <code>{no_media}</code>\n'
                        f'<b>Unsupported:</b> <code>{unsupported}</code>\n'
                        f'<b>Errors:</b> <code>{errors}</code>\n'
                        f'<b>Time:</b> {time_taken}',
                        reply_markup=InlineKeyboardMarkup(btn)
                    )
                    await asyncio.sleep(2)
                
                # Skip empty messages
                if message.empty:
                    deleted += 1
                    continue
                
                # Skip non-media messages
                if not message.media:
                    no_media += 1
                    continue
                
                # FIX #6: Check if media is video or document
                if message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                
                # Get media
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                
                # FIX #7: Use improved video detection
                if not is_video_file(media):
                    unsupported += 1
                    logger.debug(f"Skipping non-video: {getattr(media, 'file_name', 'unknown')}")
                    continue
                
                # Set caption
                media.caption = message.caption
                
                # Save to database
                sts = await save_file(media)
                
                if sts == 'suc':
                    total_files += 1
                    logger.info(f"✅ Indexed: {getattr(media, 'file_name', 'unknown')}")
                elif sts == 'dup':
                    duplicate += 1
                elif sts == 'err':
                    errors += 1
                    
        except FloodWait as e:
            logger.warning(f"FloodWait: {e.x} seconds")
            await asyncio.sleep(e.x)
        except Exception as e:
            logger.error(f"Index error: {e}", exc_info=True)
            await msg.reply(f'❌ Indexing cancelled due to error: {e}')
        else:
            time_taken = get_readable_time(time.time()-start_time)
            await msg.edit(
                f'<b>✅ Indexing Complete!</b>\n\n'
                f'<b>Time:</b> {time_taken}\n'
                f'<b>Saved:</b> <code>{total_files}</code> files\n'
                f'<b>Duplicates:</b> <code>{duplicate}</code>\n'
                f'<b>Deleted:</b> <code>{deleted}</code>\n'
                f'<b>Non-Media:</b> <code>{no_media}</code>\n'
                f'<b>Unsupported:</b> <code>{unsupported}</code>\n'
                f'<b>Errors:</b> <code>{errors}</code>'
            )
