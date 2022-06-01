import os
import time
from subprocess import run
from bot import DOWNLOAD_DIR, GLOBAL_RC_INST
from bot.core.get_vars import get_val
from bot.downloaders.aria.aria_download import AriaDownloader
from bot.downloaders.mega.mega_download import MegaDownloader
from bot.uploaders.rclone.rclone_mirror import RcloneMirror
from bot.utils.bot_utils import is_mega_link
from bot.utils.get_rclone_conf import get_config
from bot.downloaders.progress_for_pyrogram import progress_for_pyrogram
from bot import LOGGER
from bot.utils.misc_utils import clean_filepath
from bot.utils.zip_utils import extract_archive

async def handle_mirror_download(client, message, file, link, tag, pswd, isZip=False, extract=False, new_name=None, is_rename= False):
    mess_age = await message.reply_text("Preparing for download...", quote=True)
    LOGGER.info("Preparing for download...")

    conf_path = await get_config()
    if conf_path is None:
        await mess_age.edit("Rclone config file not found.")
        return

    if get_val("DEF_RCLONE_DRIVE") == "":
        await mess_age.edit("Select a cloud first please")
        return      

    if link is not None:
        if is_mega_link(link):
            mega_dl= MegaDownloader(link, mess_age)   
            state, message, file_path= await mega_dl.execute()
            if not state:
                await mess_age.edit(message)
            else:
                await rclone_mirror(file_path, mess_age, new_name, tag, is_rename)     
        else:
            aria2= AriaDownloader(link, mess_age)   
            state, message, file_path= await aria2.execute()
            if not state:
                await mess_age.edit(message)
            else:
                await mess_age.edit(message)
                await rclone_mirror(file_path, mess_age, new_name, tag, is_rename) 
    else:
        c_time = time.time()
        media_path = await client.download_media(
            message=file,
            file_name= DOWNLOAD_DIR,
            progress=progress_for_pyrogram,
            progress_args=(
            "**Name**: `{}`".format(file.file_name),
            "**Status:** Downloading...",
            mess_age, 
            c_time))
            
        if isZip:
            m_path = media_path
            LOGGER.info("Compressing...")
            await mess_age.edit("Compressing...")
            base = os.path.basename(m_path)
            file_name = base.rsplit('.', maxsplit=1)[0]
            path = os.path.join(os.getcwd(), "Downloads", file_name + ".zip")
            LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}')
            size = os.path.getsize(m_path)
            TG_SPLIT_SIZE= get_val("TG_SPLIT_SIZE")
            if pswd is not None:
                LOGGER.info("Password: {}".format(pswd))     
                if int(size) > TG_SPLIT_SIZE:
                    run(["7z", f"-v{TG_SPLIT_SIZE}b", "a", "-mx=0", f"-p{pswd}", path, m_path])     
                else:
                    run(["7z", "a", "-mx=0", f"-p{pswd}", path, m_path])
            elif int(size) > TG_SPLIT_SIZE:
                run(["7z", f"-v{TG_SPLIT_SIZE}b", "a", "-mx=0", path, m_path])
            else:
                run(["7z", "a", "-mx=0", path, m_path])
            clean_filepath(m_path)
            await rclone_mirror(path, mess_age, new_name, tag, is_rename)
        elif extract:
            m_path = media_path
            LOGGER.info("Extracting...")
            await mess_age.edit("Extracting...")
            extracted_path= await extract_archive(m_path, pswd)
            clean_filepath(m_path)
            if extracted_path is not False:
                await rclone_mirror(extracted_path, mess_age, new_name, tag, is_rename)
            else:
                LOGGER.error('Unable to extract archive!')
        else:
            await rclone_mirror(media_path, mess_age, new_name, tag, is_rename)

async def rclone_mirror(path, mess_age, new_name, tag, is_rename):
    rclone_mirror= RcloneMirror(path, mess_age, new_name, tag, is_rename)
    GLOBAL_RC_INST.append(rclone_mirror)
    await rclone_mirror.mirror()
    GLOBAL_RC_INST.remove(rclone_mirror)

class NotSupportedExtractionArchive(Exception):
    """The archive format use is trying to extract is not supported"""
    pass