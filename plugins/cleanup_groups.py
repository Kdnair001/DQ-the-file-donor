import asyncio
import time
import datetime
from pyrogram import Client, filters
from pyrogram.errors import (
    ChatWriteForbidden,
    ChatAdminRequired,
    UserBannedInChannel,
    PeerIdInvalid,
    RPCError,
    FloodWait
)
from info import ADMINS, LOG_CHANNEL
from database.users_chats_db import db


CLEANUP_TEST_MESSAGE = "🧹 **System Permission Check...**"


@Client.on_message(filters.command("cleanup_groups") & filters.user(ADMINS))
async def cleanup_groups(bot, message):

    chats = await db.get_all_chats()

    sts = await message.reply_text("🧹 **Cleanup started...**")
    start_time = time.time()
    total_chats = await db.total_chat_count()

    done = 0
    removed = 0
    ok = 0
    failed = 0

    for chat in chats:
        chat_id = int(chat["id"])

        try:
            await bot.send_message(chat_id, CLEANUP_TEST_MESSAGE)
            ok += 1

        except FloodWait as e:
            await asyncio.sleep(e.value)
            continue

        except ChatWriteForbidden:
            removed += 1
            await leave_and_log(bot, chat_id, "ChatWriteForbidden: Cannot send messages")

        except ChatAdminRequired:
            removed += 1
            await leave_and_log(bot, chat_id, "ChatAdminRequired: Missing admin rights")

        except UserBannedInChannel:
            removed += 1
            await leave_and_log(bot, chat_id, "UserBannedInChannel: Bot banned")

        except PeerIdInvalid:
            removed += 1
            await leave_and_log(bot, chat_id, "PeerIdInvalid: Group invalid or removed")

        except RPCError as e:
            failed += 1
            await bot.send_message(
                LOG_CHANNEL,
                f"⚠️ Unexpected error in `{chat_id}`:\n`{e}`"
            )
            continue

        done += 1
        await asyncio.sleep(1.0)

        if not done % 20:
            await sts.edit(
                f"🧹 **Cleanup in progress...**\n\n"
                f"Total Groups: `{total_chats}`\n"
                f"Checked: `{done}` / `{total_chats}`\n"
                f"Working: `{ok}`\n"
                f"Removed: `{removed}`\n"
                f"Errors: `{failed}`"
            )

    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))

    await sts.edit(
        f"✅ **Cleanup Completed**\n"
        f"Time Taken: `{time_taken}`\n\n"
        f"Total Groups: `{total_chats}`\n"
        f"Working: `{ok}`\n"
        f"Removed: `{removed}`\n"
        f"Errors: `{failed}`"
    )


async def leave_and_log(bot, chat_id, reason):
    try:
        await bot.leave_chat(chat_id)
    except:
        pass

    try:
        await bot.send_message(
            LOG_CHANNEL,
            f"🚫 **Left Group**\n"
            f"Group ID: `{chat_id}`\n"
            f"Reason: `{reason}`"
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await bot.send_message(
            LOG_CHANNEL,
            f"🚫 **Left Group**\n"
            f"Group ID: `{chat_id}`\n"
            f"Reason: `{reason}`"
        )
