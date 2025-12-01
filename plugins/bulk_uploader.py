import asyncio
import time
import datetime
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, MessageIdInvalid, ChannelInvalid, ChatWriteForbidden
from database.ia_filterdb import Media, Media2
from info import ADMINS

UPLOAD_CHANNEL = -1001582951437    # your fixed channel


# --------------------------------------------------------
# helper: send update message
# --------------------------------------------------------
async def update_progress(msg, current, total, last_update_time):
    now = time.time()
    if now - last_update_time >= 3:   # update every 3 seconds
        try:
            await msg.edit(
                f"📤 Uploading files...\n\n"
                f"Uploaded: `{current}` / `{total}`"
            )
        except:
            pass

        return now

    return last_update_time


# --------------------------------------------------------
# upload routine
# --------------------------------------------------------
async def upload_file(client, target, file_obj):
    try:
        await client.send_cached_media(
            chat_id=target,
            file_id=file_obj.file_id,
            caption=file_obj.caption or file_obj.file_name
        )
        return True

    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await upload_file(client, target, file_obj)

    except (MessageIdInvalid, ChannelInvalid, ChatWriteForbidden):
        return False

    except Exception:
        return False


# --------------------------------------------------------
# /upload command
# --------------------------------------------------------
@Client.on_message(filters.command("upload") & filters.user(ADMINS))
async def upload_database_files(client, message):

    # prevent multiple uploads
    async with client.upload_lock:

        status = await message.reply("📤 **Preparing upload...**")

        # get all files from both DBs
        files_db1 = await Media.find({}).to_list(length=None)
        files_db2 = await Media2.find({}).to_list(length=None)

        all_files = files_db1 + files_db2
        total = len(all_files)

        if total == 0:
            return await status.edit("❌ No files in database.")

        await status.edit(f"📤 **Starting upload of {total} files...**")

        uploaded = 0
        failed = 0
        last_update = 0

        # resume support
        resume_from = 0
        try:
            text = message.text.split()
            if len(text) >= 2:
                resume_from = int(text[1])
        except:
            resume_from = 0

        # actual upload loop
        for i in range(resume_from, total):

            file_obj = all_files[i]

            ok = await upload_file(client, UPLOAD_CHANNEL, file_obj)

            if ok:
                uploaded += 1
            else:
                failed += 1

            last_update = await update_progress(
                status, uploaded, total, last_update
            )

            await asyncio.sleep(0.5)   # soft rate control

        # completed
        await status.edit(
            f"✅ **Upload Completed**\n\n"
            f"Total: `{total}`\n"
            f"Uploaded: `{uploaded}`\n"
            f"Failed: `{failed}`"
        )
