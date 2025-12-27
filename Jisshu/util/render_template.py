import jinja2
from info import URL, LOG_CHANNEL
from Jisshu.bot import JisshuBot
from Jisshu.util.human_readable import humanbytes
from Jisshu.util.file_properties import get_file_ids
from Jisshu.server.exceptions import InvalidHash
import urllib.parse
import logging

async def render_page(id, secure_hash, src=None):
    """
    Renders the streaming/download page for a requested file.
    Removed redundant network calls for improved performance.
    """
    # Fetch file data using the provided ID
    file_data = await get_file_ids(JisshuBot, int(LOG_CHANNEL), int(id))
    
    # Security check: Verify the link hash matches the file's unique ID
    if file_data.unique_id[:6] != secure_hash:
        logging.debug(f"link hash: {secure_hash} - {file_data.unique_id[:6]}")
        logging.debug(f"Invalid hash for message with - ID {id}")
        raise InvalidHash

    # Construct the source URL for the stream/download
    src = urllib.parse.urljoin(
        URL,
        f"{id}/{urllib.parse.quote_plus(file_data.file_name)}?hash={secure_hash}",
    )

    # Determine the file type tag and convert size to human-readable format
    tag = file_data.mime_type.split("/")[0].strip()
    file_size = humanbytes(file_data.file_size) # Size already retrieved from Telegram
    
    if tag in ["video", "audio"]:
        template_file = "Jisshu/template/req.html"
    else:
        # FIXED: Removed the redundant aiohttp ClientSession that was fetching Content-Length
        # from the URL. Using the existing file_data.file_size is faster and more reliable.
        template_file = "Jisshu/template/dl.html"

    # Open the appropriate HTML template and render it with context
    with open(template_file) as f:
        template = jinja2.Template(f.read())

    # Format file name for display (replacing underscores with spaces)
    display_name = file_data.file_name.replace("_", " ")

    return template.render(
        file_name=display_name,
        file_url=src,
        file_size=file_size,
        file_unique_id=file_data.unique_id,
    )
    
