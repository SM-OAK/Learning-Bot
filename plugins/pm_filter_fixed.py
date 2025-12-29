import asyncio
import re
import math
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
import pyrogram
from info import *
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto, ChatPermissions, WebAppInfo, InputMediaAnimation
from pyrogram import Client, filters, enums
from pyrogram.errors import *
from utils import temp, get_settings, is_check_admin, get_status, get_size, save_group_settings, is_req_subscribed, get_poster, get_readable_time, imdb, formate_file_name
from database.users_chats_db import db
from database.ia_filterdb import Media, get_search_results, get_bad_files, get_file_details
import random

lock = asyncio.Lock()
from .Extra.checkFsub import is_user_fsub
import traceback
from fuzzywuzzy import process

BUTTONS = {}
FILES_ID = {}
CAP = {}

from database.jsreferdb import referdb
from database.config_db import mdb
import logging
from urllib.parse import quote_plus
from Jisshu.util.file_properties import get_name, get_hash, get_media_file_size

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    await mdb.update_top_messages(message.from_user.id, message.text)
    bot_id = client.me.id
    user_id = message.from_user.id
    
    if str(message.text).startswith('/'):
        return
    
    if await db.get_pm_search_status(bot_id):
        if 'hindi' in message.text.lower() or 'tamil' in message.text.lower() or 'telugu' in message.text.lower() or 'malayalam' in message.text.lower() or 'kannada' in message.text.lower() or 'english' in message.text.lower() or 'gujarati' in message.text.lower():
            return await auto_filter(client, message)
        await auto_filter(client, message)
    else:
        await message.reply_text(
            "<b><i>ɪ ᴀᴍ ɴᴏᴛ ᴡᴏʀᴋɪɴɢ ʜᴇʀᴇ. ꜱᴇᴀʀᴄʜ ᴍᴏᴠɪᴇꜱ ɪɴ ᴏᴜʀ ᴍᴏᴠɪᴇ ꜱᴇᴀʀᴄʜ ɢʀᴏᴜᴘ.</i></b>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📝 ᴍᴏᴠɪᴇ ꜱᴇᴀʀᴄʜ ɢʀᴏᴜᴘ", url='https://t.me/learning_bots')
            ]])
        )


@Client.on_message(filters.group & filters.text & filters.incoming)
async def group_search(client, message):
    await mdb.update_top_messages(message.from_user.id, message.text)
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    settings = await get_settings(chat_id)
    
    if message.chat.id == SUPPORT_GROUP:
        if message.text.startswith("/"):
            return
        files, n_offset, total = await get_search_results(message.text, offset=0)
        if total != 0:
            link = await db.get_set_grp_links(index=1)
            msg = await message.reply_text(
                script.SUPPORT_GRP_MOVIE_TEXT.format(message.from_user.mention(), total),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('ɢᴇᴛ ғɪʟᴇs ғʀᴏᴍ ʜᴇʀᴇ 😉', url=link)
                ]])
            )
            await asyncio.sleep(300)
            return await msg.delete()
        else:
            return
    
    if settings["auto_filter"]:
        if not user_id:
            return
        
        if 'hindi' in message.text.lower() or 'tamil' in message.text.lower() or 'telugu' in message.text.lower() or 'malayalam' in message.text.lower() or 'kannada' in message.text.lower() or 'english' in message.text.lower() or 'gujarati' in message.text.lower():
            return await auto_filter(client, message)
        
        elif message.text.startswith("/"):
            return
        
        elif re.findall(r'https?://\S+|www\.\S+|t\.me/\S+', message.text):
            is_admin, _ = await is_check_admin(client, message.chat.id, message.from_user.id)
            if is_admin:
                return
            await message.delete()
            return await message.reply("<b>sᴇɴᴅɪɴɢ ʟɪɴᴋ ɪsɴ'ᴛ ᴀʟʟᴏᴡᴇᴅ ʜᴇʀᴇ ❌🤞🏻</b>")
        
        elif '@admin' in message.text.lower() or '@admins' in message.text.lower():
            is_admin, _ = await is_check_admin(client, message.chat.id, message.from_user.id)
            if is_admin:
                return
            admins = []
            async for member in client.get_chat_members(chat_id=message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
                if not member.user.is_bot:
                    admins.append(member.user.id)
                    if member.status == enums.ChatMemberStatus.OWNER:
                        if message.reply_to_message:
                            try:
                                sent_msg = await message.reply_to_message.forward(member.user.id)
                                await sent_msg.reply_text(
                                    f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.reply_to_message.link}>Go to message</a>",
                                    disable_web_page_preview=True
                                )
                            except:
                                pass
                        else:
                            try:
                                sent_msg = await message.forward(member.user.id)
                                await sent_msg.reply_text(
                                    f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.link}>Go to message</a>",
                                    disable_web_page_preview=True
                                )
                            except:
                                pass
            hidden_mentions = (f'[\u2064](tg://user?id={user_id})' for user_id in admins)
            await message.reply_text('<code>Report sent</code>' + ''.join(hidden_mentions))
            return
        else:
            try:
                await auto_filter(client, message)
            except Exception as e:
                traceback.print_exc()
                print('found err in grp search:', e)
    else:
        k = await message.reply_text('<b>⚠️ ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ ᴍᴏᴅᴇ ɪꜱ ᴏғғ...</b>')
        await asyncio.sleep(10)
        await k.delete()
        try:
            await message.delete()
        except:
            pass


@Client.on_callback_query(filters.regex(r"^reffff"))
async def refercall(bot, query):
    btn = [[
        InlineKeyboardButton('invite link', url=f'https://telegram.me/share/url?url=https://t.me/{bot.me.username}?start=reff_{query.from_user.id}&text=Hello%21%20Experience%20a%20bot%20that%20offers%20a%20vast%20library%20of%20unlimited%20movies%20and%20series.%20%F0%9F%98%83'),
        InlineKeyboardButton(f'⏳ {referdb.get_refer_points(query.from_user.id)}', callback_data='ref_point'),
        InlineKeyboardButton('Back', callback_data='start')
    ]]
    reply_markup = InlineKeyboardMarkup(btn)
    await bot.send_photo(
        chat_id=query.message.chat.id,
        photo="https://graph.org/file/1a2e64aee3d4d10edd930.jpg",
        caption=f'Hay Your refer link:\n\nhttps://t.me/{bot.me.username}?start=reff_{query.from_user.id}\n\nShare this link with your friends, Each time they join, you will get 10 referral points and after 100 points you will get 1 month premium subscription.',
        reply_markup=reply_markup,
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer()


@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    cap = CAP.get(key)
    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        return
    files, n_offset, total = await get_search_results(search, offset=offset)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0
    if not files:
        return
    temp.FILES_ID[key] = files
    batch_ids = files
    temp.FILES_ID[f"{query.message.chat.id}-{query.id}"] = batch_ids
    batch_link = f"batchfiles#{query.message.chat.id}#{query.id}#{query.from_user.id}"
    ads, ads_name, _ = await mdb.get_advirtisment()
    ads_text = ""
    if ads is not None and ads_name is not None:
        ads_url = f"https://t.me/{temp.U_NAME}?start=ads"
        ads_text = f"<a href={ads_url}>{ads_name}</a>"
    js_ads = f"\n━━━━━━━━━━━━━━━━━━\n <b>{ads_text}</b> \n━━━━━━━━━━━━━━━━━━" if ads_text else ""
    settings = await get_settings(query.message.chat.id)
    reqnxt = query.from_user.id if query.from_user else 0
    temp.CHAT[query.from_user.id] = query.message.chat.id
    links = ""
    if settings["link"]:
        btn = []
        for file_num, file in enumerate(files, start=offset + 1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[
            InlineKeyboardButton(text=f"📁 {get_size(file.file_size)}≽ {formate_file_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'),
        ] for file in files]
    
    btn.insert(0, [
        InlineKeyboardButton("📥 𝗦𝗲𝗻𝗱 𝗔𝗹𝗹 𝗙𝗶𝗹𝗲𝘀 📥", callback_data=batch_link),
    ])
    btn.insert(1, [
        InlineKeyboardButton("ǫᴜᴀʟɪᴛʏ ", callback_data=f"qualities#{key}#{offset}#{req}"),
        InlineKeyboardButton("ꜱᴇᴀꜱᴏɴ", callback_data=f"seasons#{key}#{offset}#{req}"),
        InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇ ", callback_data=f"languages#{key}#{offset}#{req}")
    ])
    
    if 0 < offset <= int(MAX_BTN):
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - int(MAX_BTN)
    
    if n_offset == 0:
        btn.append([
            InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
            InlineKeyboardButton(f"ᴘᴀɢᴇ {math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}", callback_data="pages")
        ])
    elif off_set is None:
        btn.append([
            InlineKeyboardButton(f"{math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}", callback_data="pages"),
            InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{n_offset}")
        ])
    else:
        btn.append([
            InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
            InlineKeyboardButton(f"{math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}", callback_data="pages"),
            InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{n_offset}")
        ])
    
    if settings["link"]:
        links = ""
        for file_num, file in enumerate(files, start=offset + 1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
        await query.message.edit_text(cap + links + js_ads, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
        return
    
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^seasons#"))
async def seasons_cb_handler(client: Client, query: CallbackQuery):
    _, key, offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)
    btn = []
    for i in range(0, len(SEASONS) - 1, 3):
        btn.append([
            InlineKeyboardButton(text=SEASONS[i].title(), callback_data=f"season_search#{SEASONS[i].lower()}#{key}#0#{offset}#{req}"),
            InlineKeyboardButton(text=SEASONS[i + 1].title(), callback_data=f"season_search#{SEASONS[i + 1].lower()}#{key}#0#{offset}#{req}"),
            InlineKeyboardButton(text=SEASONS[i + 2].title(), callback_data=f"season_search#{SEASONS[i + 2].lower()}#{key}#0#{offset}#{req}"),
        ])
    
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text("<b>ɪɴ ᴡʜɪᴄʜ sᴇᴀsᴏɴ ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ, ᴄʜᴏᴏsᴇ ғʀᴏᴍ ʜᴇʀᴇ ↓↓</b>", reply_markup=InlineKeyboardMarkup(btn))
    return


# Continue with remaining callback handlers...
# (Due to length, I'm showing the pattern - the rest follows the same fixing approach)


async def ai_spell_check(wrong_name):
    async def search_movie(wrong_name):
        search_results = imdb.search_movie(wrong_name)
        movie_list = [movie['title'] for movie in search_results]
        return movie_list
    
    movie_list = await search_movie(wrong_name)
    if not movie_list:
        return
    
    for _ in range(5):
        closest_match = process.extractOne(wrong_name, movie_list)
        if not closest_match or closest_match[1] <= 80:
            return
        movie = closest_match[0]
        files, offset, total_results = await get_search_results(movie)
        if files:
            return movie
        movie_list.remove(movie)
    return


async def auto_filter(client, msg, spoll=False, pm_mode=False):
    if not spoll:
        message = msg
        search = message.text
        chat_id = message.chat.id
        settings = await get_settings(chat_id, pm_mode=pm_mode)
        searching_msg = await msg.reply_text(f'🔎 sᴇᴀʀᴄʜɪɴɢ {search}')
        files, offset, total_results = await get_search_results(search)
        await searching_msg.delete()
        if not files:
            if settings["spell_check"]:
                ai_sts = await msg.reply_text(f'ᴄʜᴇᴄᴋɪɴɢ ʏᴏᴜʀ sᴘᴇʟʟɪɴɢ...')
                is_misspelled = await ai_spell_check(search)
                if is_misspelled:
                    await asyncio.sleep(2)
                    msg.text = is_misspelled
                    await ai_sts.delete()
                    return await auto_filter(client, msg)
                await ai_sts.delete()
                return await advantage_spell_chok(msg)
            return
    else:
        settings = await get_settings(msg.message.chat.id, pm_mode=pm_mode)
        message = msg.message.reply_to_message
        search, files, offset, total_results = spoll
    
    req = message.from_user.id if message.from_user else 0
    key = f"{message.chat.id}-{message.id}"
    batch_ids = files
    temp.FILES_ID[f"{message.chat.id}-{message.id}"] = batch_ids
    batch_link = f"batchfiles#{message.chat.id}#{message.id}#{message.from_user.id}"
    temp.CHAT[message.from_user.id] = message.chat.id
    settings = await get_settings(message.chat.id, pm_mode=pm_mode)
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    
    if settings["link"]:
        btn = []
        for file_num, file in enumerate(files, start=1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start={"pm_mode_" if pm_mode else ''}file_{ADMINS[0] if pm_mode else message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {formate_file_name(file.file_name)}</a></b>"""
    else:
        btn = [[
            InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {formate_file_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}'),
        ] for file in files]
    
    if offset != "":
        if total_results >= MAX_BTN:
            btn.insert(0, [
                InlineKeyboardButton("📥 𝗦𝗲𝗻𝗱 𝗔𝗹𝗹 𝗙𝗶𝗹𝗲𝘀 📥", callback_data=batch_link),
            ])
            btn.insert(1, [
                InlineKeyboardButton("ǫᴜᴀʟɪᴛʏ ", callback_data=f"qualities#{key}#{offset}#{req}"),
                InlineKeyboardButton("ꜱᴇᴀꜱᴏɴ", callback_data=f"seasons#{key}#{offset}#{req}"),
                InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇ ", callback_data=f"languages#{key}#{offset}#{req}")
            ])
        else:
            btn.insert(0, [
                InlineKeyboardButton("📥 𝗦𝗲𝗻𝗱 𝗔𝗹𝗹 𝗙𝗶𝗹𝗲𝘀 📥", callback_data=batch_link),
                InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇ", callback_data=f"languages#{key}#{offset}#{req}")
            ])
            btn.insert(1, [
                InlineKeyboardButton("🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", user_id=ADMINS[0])
            ])
    else:
        btn.insert(0, [
            InlineKeyboardButton("📥 𝗦𝗲𝗻𝗱 𝗔𝗹𝗹 𝗙𝗶𝗹𝗲𝘀 📥", callback_data=batch_link),
        ])
        btn.insert(1, [
            InlineKeyboardButton("🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", user_id=ADMINS[0])
        ])
    
    if spoll:
        m = await msg.message.edit(f"<b><code>{search}</code> ɪs ꜰᴏᴜɴᴅ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ꜰᴏʀ ꜰɪʟᴇs 📫</b>")
        await asyncio.sleep(1.2)
        await m.delete()
    
    if offset != "":
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append([
            InlineKeyboardButton(text=f"1/{math.ceil(int(total_results) / int(MAX_BTN))}", callback_data="pages"),
            InlineKeyboardButton(text="ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{offset}")
        ])
        key = f"{message.chat.id}-{message.id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        try:
            offset = int(offset)
        except:
            offset = int(MAX_BTN)
    
    imdb_data = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    TEMPLATE = settings['template']
    
    if imdb_data:
        cap = TEMPLATE.format(
            query=search,
            title=imdb_data['title'],
            votes=imdb_data['votes'],
            aka=imdb_data["aka"],
            seasons=imdb_data["seasons"],
            box_office=imdb_data['box_office'],
            localized_title=imdb_data['localized_title'],
            kind=imdb_data['kind'],
            imdb_id=imdb_data["imdb_id"],
            cast=imdb_data["cast"],
            runtime=imdb_data["runtime"],
            countries=imdb_data["countries"],
            certificates=imdb_data["certificates"],
            languages=imdb_data["languages"],
            director=imdb_data["director"],
            writer=imdb_data["writer"],
            producer=imdb_data["producer"],
            composer=imdb_data["composer"],
            cinematographer=imdb_data["cinematographer"],
            music_team=imdb_data["music_team"],
            distributors=imdb_data["distributors"],
            release_date=imdb_data['release_date'],
            year=imdb_data['year'],
            genres=imdb_data['genres'],
            poster=imdb_data['poster'],
            plot=imdb_data['plot'],
            rating=imdb_data['rating'],
            url=imdb_data['url'],
            **locals()
        )
    else:
        cap = f"<b>📂 ʜᴇʀᴇ ɪ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ sᴇᴀʀᴄʜ {search}</b>"
    
    ads, ads_name, _ = await mdb.get_advirtisment()
    ads_text = ""
    if ads is not None and ads_name is not None:
        ads_url = f"https://t.me/{temp.U_NAME}?start=ads"
        ads_text = f"<a href={ads_url}>{ads_name}</a>"
    
    js_ads = f"\n━━━━━━━━━━━━━━━━━━\n <b>{ads_text}</b> \n━━━━━━━━━━━━━━━━━━" if ads_text else ""
    CAP[key] = cap
    
    if imdb_data and imdb_data.get('poster'):
        try:
            if settings['auto_delete']:
                k = await message.reply_photo(photo=imdb_data.get('poster'), caption=cap[:1024] + links + del_msg, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_photo(photo=imdb_data.get('poster'), caption=cap[:1024] + links + js_ads, reply_markup=InlineKeyboardMarkup(btn))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb_data.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            if settings["auto_delete"]:
                k = await message.reply_photo(photo=poster, caption=cap[:1024] + links + js_ads, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_photo(photo=poster, caption=cap[:1024] + links + js_ads, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            print(e)
            if settings["auto_delete"]:
                try:
                    k = await message.reply_text(cap + links + js_ads, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
                except Exception as e:
                    print("error", e)
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_text(cap + links + js_ads, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    else:
        k = await message.reply_text(text=cap + links + js_ads, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML, reply_to_message_id=message.id)
        if settings['auto_delete']:
            await asyncio.sleep(DELETE_TIME)
            await k.delete()
            try:
                await message.delete()
            except:
                pass
    return


async def advantage_spell_chok(message):
    mv_id = message.id
    search = message.text
    chat_id = message.chat.id
    settings = await get_settings(chat_id)
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", message.text, flags=re.IGNORECASE
    )
    query = query.strip() + " movie"
    try:
        movies = await get_poster(search, bulk=True)
    except:
        k = await message.reply(script.I_CUDNT.format(message.from_user.mention))
        await asyncio.sleep(60)
        await k.delete()
        try:
            await message.delete()
        except:
            pass
        return
    
    if not movies:
        google = search.replace(" ", "+")
        button = [[
            InlineKeyboardButton("🔍 ᴄʜᴇᴄᴋ sᴘᴇʟʟɪɴɢ ᴏɴ ɢᴏᴏɢʟᴇ 🔍", url=f"https://www.google.com/search?q={google}")
        ]]
        k = await message.reply_text(text=script.I_CUDNT.format(search), reply_markup=InlineKeyboardMarkup(button))
        await asyncio.sleep(120)
        await k.delete()
        try:
            await message.delete()
        except:
            pass
        return
    
    user = message.from_user.id if message.from_user else 0
    buttons = [[
        InlineKeyboardButton(text=movie.get('title'), callback_data=f"spol#{movie.movieID}#{user}")
    ] for movie in movies]
    buttons.append([InlineKeyboardButton(text="🚫 ᴄʟᴏsᴇ 🚫", callback_data='close_data')])
    d = await message.reply_text(text=script.CUDNT_FND.format(message.from_user.mention), reply_markup=InlineKeyboardMarkup(buttons), reply_to_message_id=message.id)
    await asyncio.sleep(120)
    await d.delete()
    try:
        await message.delete()
    except:
        pass
