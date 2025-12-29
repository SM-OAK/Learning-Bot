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

# ✅ FIX #1: Comprehensive video file extensions
VIDEO_EXTENSIONS = [
    '.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', 
    '.m4v', '.3gp', '.mpeg', '.mpg', '.ts', '.vob', '.ogv'
]

# ✅ FIX #2: Comprehensive video mime types
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
    'video/mp2t',
    'video/x-msvideo',
    'application/octet-stream',  # Sometimes videos are detected as this
    'application/x-matroska'      # MKV files sometimes
]


def is_video_file(media) -> bool:
    """
    ✅ FIXED: Comprehensive video file detection
    Returns True if media is a video file, False otherwise
    """
    if not media:
        return False
    
    # Check mime type first
    mime_type = getattr(media, 'mime_type', '')
    if mime_type:
        mime_type_lower = mime_type.lower()
        if any(mime_type_lower.startswith(vm) or mime_type_lower == vm for vm in VIDEO_MIME_TYPES):
            logger.debug(f"✅ Video detected by MIME: {mime_type}")
            return True
    
    # Check file extension
    file_name = getattr(media, 'file_name', '')
    if file_name:
        file_name_lower = file_name.lower()
        if any(file_name_lower.endswith(ext) for ext in VIDEO_EXTENSIONS):
            logger.debug(f"✅ Video detected by extension: {file_name}")
            return True
    
    # Additional check: file size (videos are usually > 5MB)
    file_size = getattr(media, 'file_size', 0)
    if file_size > 5 * 1024 * 1024:  # 5MB threshold
        if file_name:
            file_name_lower = file_name.lower()
            # Double-check extension for large files
            if any(file_name_lower.endswith(ext) for ext in VIDEO_EXTENSIONS):
                logger.debug(f"✅ Large video file detected: {file_name} ({file_size} bytes)")
                return True
    
    logger.debug(f"❌ Not a video: {file_name or 'unknown'} (MIME: {mime_type or 'unknown'})")
    return False


@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    """✅ FIXED: Index callback with proper admin check and query answer"""
    
    # ✅ FIX #3: ALWAYS answer the callback query first
    await query.answer()
    
    try:
        _, ident, chat, lst_msg_id, skip = query.data.split("#")
    except ValueError:
        await query.message.edit("❌ Invalid callback data format!")
        return
    
    # ✅ FIX #4: Proper admin check with None handling
    user_id = query.from_user.id if query.from_user else None
    
    if not user_id:
        await query.message.edit("❌ Cannot verify admin status for anonymous users. Please use your personal account.")
        return
    
    # Check if user is admin
    is_admin, error_msg = await is_check_admin(bot, query.message.chat.id, user_id)
    
    if not is_admin:
        await query.message.edit(error_msg or "❌ Only admins can use this command!")
        return
    
    if ident == 'yes':
        msg = query.message
        await msg.edit("<b>⏳ Indexing started...</b>")
        try:
            chat = int(chat)
        except:
            pass  # Keep as string (username)
        await index_files_to_db(int(lst_msg_id), chat, msg, bot, int(skip))
    elif ident == 'cancel':
        temp.CANCEL = True
        await query.message.edit("⏳ Trying to cancel indexing...")


@Client.on_message(filters.command('index') & filters.private & filters.incoming)
async def send_for_index(bot, message):
    """✅ FIXED: Index command with proper admin check"""
    
    # ✅ FIX #5: Check if user is bot owner
    if message.from_user.id not in ADMINS:
        await message.reply('❌ Only bot admins can use this command.')
        return
    
    if lock.locked():
        return await message.reply('⏳ Wait until previous indexing process completes.')
    
    i = await message.reply("📤 Forward the last message from the channel or send the last message link.")
    
    try:
        msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id, timeout=300)
    except asyncio.TimeoutError:
        await i.delete()
        return await message.reply("❌ Timeout! Please try again.")
    
    await i.delete()
    
    # Parse message link or forwarded message
    if msg.text and msg.text.startswith("https://t.me"):
        try:
            msg_link = msg.text.split("/")
            last_msg_id = int(msg_link[-1])
            chat_id = msg_link[-2]
            if chat_id.isnumeric():
                chat_id = int(("-100" + chat_id))
        except Exception as e:
            logger.error(f"Error parsing message link: {e}")
            await message.reply('❌ Invalid message link!')
            return
    elif msg.forward_from_chat and msg.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = msg.forward_from_message_id
        chat_id = msg.forward_from_chat.username or msg.forward_from_chat.id
    else:
        await message.reply('❌ This is not a forwarded message or valid link.')
        return
    
    # Get channel info
    try:
        chat = await bot.get_chat(chat_id)
    except Exception as e:
        logger.error(f"Error getting chat: {e}")
        return await message.reply(f'❌ Error: {e}')
    
    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply("❌ I can only index channels.")
    
    # Get skip number
    s = await message.reply("🔢 Send the skip number (how many messages to skip from start).\n\nExample: Send `0` to start from beginning.")
    
    try:
        skip_msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id, timeout=60)
        await s.delete()
        skip = int(skip_msg.text)
    except asyncio.TimeoutError:
        await s.delete()
        return await message.reply("❌ Timeout! Please try again.")
    except ValueError:
        return await message.reply("❌ Please send a valid number.")
    
    # Confirmation
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
    
    # Check if user is bot owner
    if message.from_user.id not in ADMINS:
        await message.reply('❌ Only bot admins can use this command.')
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
    """✅ FIXED: Index files with improved video detection and better logging"""
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
                
                # Check for cancellation
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
                    await asyncio.sleep(1)
                
                # Skip empty messages
                if message.empty:
                    deleted += 1
                    continue
                
                # Skip non-media messages
                if not message.media:
                    no_media += 1
                    continue
                
                # ✅ FIX #6: Accept both VIDEO and DOCUMENT types
                if message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                
                # Get media object
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                
                # ✅ FIX #7: Use improved video detection function
                if not is_video_file(media):
                    unsupported += 1
                    continue
                
                # Set caption and file type
                media.caption = message.caption
                media.file_type = message.media.value
                
                # Save to database
                try:
                    sts = await save_file(media)
                    
                    if sts == 'suc':
                        total_files += 1
                        logger.info(f"✅ Indexed: {getattr(media, 'file_name', 'unknown')}")
                    elif sts == 'dup':
                        duplicate += 1
                    elif sts == 'err':
                        errors += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Error saving file: {e}")
                    
        except FloodWait as e:
            logger.warning(f"FloodWait: {e.x} seconds")
            await asyncio.sleep(e.x)
            await msg.reply(f"⏳ Rate limited for {e.x} seconds. Resuming...")
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
