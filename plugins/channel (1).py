from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import CHANNELS, MOVIE_UPDATE_CHANNEL, ADMINS, LOG_CHANNEL
from database.ia_filterdb import save_file, unpack_new_file_id
from utils import get_poster, temp
import re
from Script import script
from database.users_chats_db import db
import logging

logger = logging.getLogger(__name__)

# Track processed movies to avoid duplicates
processed_movies = set()

# Media filter for documents and videos
media_filter = filters.document | filters.video


@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    """Handle new media files from channels"""
    media = getattr(message, message.media.value, None)
    
    if not media:
        return
    
    # Accept all video files (don't be too restrictive on mime type)
    media.file_type = message.media.value
    media.caption = message.caption
    
    # Save to database
    success_sts = await save_file(media)
    
    if success_sts == 'suc':
        try:
            file_id, file_ref = unpack_new_file_id(media.file_id)
            await send_movie_updates(bot, file_name=media.file_name, file_id=file_id)
        except Exception as e:
            logger.error(f"Error sending movie update for {media.file_name}: {e}")


def name_format(file_name: str):
    """Format file name for IMDb search"""
    if not file_name:
        return ""
    
    file_name = file_name.lower()
    
    # Remove URLs and mentions
    file_name = re.sub(r'http\S+', '', file_name)
    file_name = re.sub(r'@\w+|#\w+', '', file_name)
    
    # Clean up formatting
    file_name = file_name.replace('_', ' ').replace('[', '').replace(']', '').strip()
    
    # Remove quality markers
    file_name = re.sub(r'\d{3,4}p|hdrip|bluray|web-?dl|x26[45]|hevc|aac', '', file_name, flags=re.IGNORECASE)
    
    # Remove season/episode info
    file_name = re.split(r's\d+|season\s*\d+|chapter\s*\d+', file_name, flags=re.IGNORECASE)[0]
    file_name = file_name.strip()
    
    # Remove year if present to get clean title
    file_name = re.sub(r'\(?\d{4}\)?', '', file_name).strip()
    
    # Take first 4 words only
    words = file_name.split()[:4]
    imdb_file_name = ' '.join(words)
    
    return imdb_file_name


async def get_imdb(file_name):
    """
    ✅ FIXED: Fetch IMDb information for a movie
    Returns: (title, poster_url, caption) or (None, None, None)
    """
    if not file_name:
        logger.warning("Empty file name provided to get_imdb")
        return None, None, None
    
    try:
        # Format the file name for IMDb search
        imdb_file_name = name_format(file_name)
        
        if not imdb_file_name:
            logger.warning(f"Could not format file name: {file_name}")
            return None, None, None
        
        logger.info(f"Searching IMDb for: {imdb_file_name}")
        
        # Fetch IMDb data
        imdb = await get_poster(imdb_file_name)
        
        if not imdb:
            logger.info(f"No IMDb data found for: {imdb_file_name}")
            return None, None, None
        
        # ✅ FIX: Validate required fields
        title = imdb.get('title')
        poster = imdb.get('poster')
        rating = imdb.get('rating', 'N/A')
        genres = imdb.get('genres', 'N/A')
        year = imdb.get('year', 'N/A')
        
        # Check if we have minimum required data
        if not title:
            logger.warning(f"No title in IMDb data for: {file_name}")
            return None, None, None
            
        if not poster or poster == 'N/A':
            logger.warning(f"No poster in IMDb data for: {file_name}")
            return None, None, None
        
        # Build caption
        caption = script.MOVIES_UPDATE_TXT.format(
            title=title,
            rating=rating,
            genres=genres,
            year=year
        )
        
        logger.info(f"✅ IMDb data fetched successfully for: {title}")
        return title, poster, caption
            
    except Exception as e:
        logger.error(f"Error fetching IMDb for {file_name}: {e}", exc_info=True)
        return None, None, None


async def send_movie_updates(bot, file_name, file_id):
    """
    ✅ FIXED: Send movie update to channel
    Key fix: Check IMDb data BEFORE checking processed_movies
    """
    try:
        logger.info(f"Processing movie update for: {file_name}")
        
        # ✅ FIX #1: Get IMDb information FIRST
        imdb_title, poster_url, caption = await get_imdb(file_name)
        
        # ✅ FIX #2: Check if we got valid data BEFORE checking processed_movies
        if not imdb_title or not poster_url or not caption:
            logger.info(f"Skipping movie update for {file_name} - incomplete IMDb data")
            return
        
        # ✅ FIX #3: NOW check if already processed (after we know it's valid)
        if imdb_title in processed_movies:
            logger.info(f"Movie already processed: {imdb_title}")
            return
        
        # Mark as processed
        processed_movies.add(imdb_title)
        logger.info(f"Added to processed list: {imdb_title}")
        
        # Create button
        btn = [
            [InlineKeyboardButton(
                '🎬 Get File', 
                url=f'https://t.me/{temp.U_NAME}?start=pm_mode_file_{ADMINS[0]}_{file_id}'
            )]
        ]
        reply_markup = InlineKeyboardMarkup(btn)
        
        # Get movie update channel
        movie_update_channel = await db.movies_update_channel_id()
        target_channel = movie_update_channel if movie_update_channel else MOVIE_UPDATE_CHANNEL
        
        # Validate target channel
        if not target_channel or target_channel == 0:
            logger.error("❌ Movie update channel not configured!")
            
            # Try to notify in log channel
            try:
                await bot.send_message(
                    LOG_CHANNEL,
                    f"<b>⚠️ Configuration Error</b>\n\n"
                    f"<b>Movie:</b> {imdb_title}\n"
                    f"<b>Issue:</b> MOVIE_UPDATE_CHANNEL is not set!\n\n"
                    f"<b>Fix:</b> Set MOVIE_UPDATE_CHANNEL in config"
                )
            except:
                pass
            return
        
        # Send update
        try:
            await bot.send_photo(
                chat_id=target_channel,
                photo=poster_url,
                caption=caption,
                reply_markup=reply_markup
            )
            logger.info(f"✅ Movie update sent successfully for: {imdb_title}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send movie update for {imdb_title}: {e}")
            
            # Remove from processed list so it can be retried
            if imdb_title in processed_movies:
                processed_movies.remove(imdb_title)
            
            # Notify in log channel
            try:
                await bot.send_message(
                    LOG_CHANNEL,
                    f"<b>❌ Failed to send movie update</b>\n\n"
                    f"<b>Movie:</b> {imdb_title}\n"
                    f"<b>File:</b> {file_name}\n"
                    f"<b>Error:</b> <code>{str(e)}</code>\n\n"
                    f"<b>Possible reasons:</b>\n"
                    f"• Bot not admin in update channel\n"
                    f"• Update channel ID incorrect: <code>{target_channel}</code>\n"
                    f"• Network error\n"
                    f"• Invalid poster URL\n\n"
                    f"<b>What to check:</b>\n"
                    f"1. Make bot admin in channel <code>{target_channel}</code>\n"
                    f"2. Verify MOVIE_UPDATE_CHANNEL ID is correct\n"
                    f"3. Check bot has 'Post Messages' permission"
                )
            except:
                pass
            
    except Exception as e:
        logger.exception(f"❌ Unexpected error in send_movie_updates: {e}")


# Optional: Clear processed movies cache periodically (prevents memory issues)
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    
    scheduler = AsyncIOScheduler()
    
    def clear_processed_cache():
        """Clear processed movies cache to prevent memory issues"""
        global processed_movies
        old_size = len(processed_movies)
        processed_movies.clear()
        logger.info(f"🧹 Cleared processed movies cache ({old_size} entries)")
    
    # Clear cache every 24 hours
    scheduler.add_job(clear_processed_cache, 'interval', hours=24)
    scheduler.start()
    logger.info("✅ Scheduled cache clearing every 24 hours")
    
except ImportError:
    logger.warning("⚠️ apscheduler not installed. Processed movies cache won't be auto-cleared.")
    logger.warning("Install with: pip install apscheduler")
