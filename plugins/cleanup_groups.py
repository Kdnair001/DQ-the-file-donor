import asyncio
import time
import datetime
from pyrogram import Client, filters
from pyrogram.errors import (
    ChatWriteForbidden,
    ChatAdminRequired,
    UserBannedInChannel,
    PeerIdInvalid,
    ChannelInvalid,
    ChatIdInvalid,
    ChannelPrivate,
    RPCError,
    FloodWait,
)
from info import ADMINS, LOG_CHANNEL
from database.users_chats_db import db


CLEANUP_TEST_MESSAGE = "🧹 **System Permission Check...**"


# ----------------------------------------------------------
# CHECK WHETHER CHAT EXISTS (CATCHES *ALL* INVALID IDs)
# ----------------------------------------------------------
async def chat_exists(bot, chat_id):
    try:
        # chat_id must be int, else Pyrogram explodes
        chat_id = int(chat_id)

    except Exception:
        return False

    try:
        await bot.get_chat(chat_id)
        return True

    except ValueError:
        # The error YOU are getting: “Peer id invalid: -4040550112”
        return False

    except (PeerIdInvalid, ChannelInvalid, ChatIdInvalid, ChannelPrivate):
        return False

    except RPCError:
        return True  # Exists but access is restricted


# ----------------------------------------------------------
# SMART LEAVE + DB DISABLE + LOG
# ----------------------------------------------------------
async def leave_and_log(bot, chat_id, reason):

    try:
        await db.disable_chat(chat_id, reason)
    except Exception as e:
        try:
            await bot.send_message(
                LOG_CHANNEL,
                f"⚠️ Failed to disable `{chat_id}`:\n`{e}`"
            )
        except:
            pass

    try:
        await bot.leave_chat(chat_id)
    except:
        pass

    try:
        await bot.send_message(
            LOG_CHANNEL,
            f"🚫 **Left / Removed Group**\n"
            f"Group ID: `{chat_id}`\n"
            f"Reason: `{reason}`"
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await bot.send_message(
            LOG_CHANNEL,
            f"🚫 **Left / Removed Group**\n"
            f"Group ID: `{chat_id}`\n"
            f"Reason: `{reason}`"
        )
    except:
        pass


# ----------------------------------------------------------
# CLEANUP COMMAND
# ----------------------------------------------------------
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
        chat_id = chat["id"]

        # STEP 1: check
        exists = await chat_exists(bot, chat_id)
        if not exists:
            removed += 1
            await leave_and_log(bot, chat_id, "Invalid / Corrupted / Deleted chat ID")
            continue

        # STEP 2: try sending
        try:
            await bot.send_message(chat_id, CLEANUP_TEST_MESSAGE)
            ok += 1

        except FloodWait as e:
            await asyncio.sleep(e.value)
            continue

        except ChatWriteForbidden:
            removed += 1
            await leave_and_log(bot, chat_id, "Cannot send messages")

        except ChatAdminRequired:
            removed += 1
            await leave_and_log(bot, chat_id, "Admin rights missing")

        except UserBannedInChannel:
            removed += 1
            await leave_and_log(bot, chat_id, "Bot banned")

        except ChannelPrivate:
            removed += 1
            await leave_and_log(bot, chat_id, "ChannelPrivate")

        except ChatIdInvalid:
            removed += 1
            await leave_and_log(bot, chat_id, "ChatIdInvalid")

        except (PeerIdInvalid, ChannelInvalid):
            removed += 1
            await leave_and_log(bot, chat_id, "Peer/Channel invalid")

        except RPCError as e:
            failed += 1
            try:
                await bot.send_message(
                    LOG_CHANNEL,
                    f"⚠️ Unexpected error in `{chat_id}`:\n`{e}`"
                )
            except:
                pass
            continue

        # STEP 3: Progress
        done += 1
        await asyncio.sleep(1)

        if done % 20 == 0:
            await sts.edit(
                f"🧹 **Cleanup in progress…**\n\n"
                f"Total Groups: `{total_chats}`\n"
                f"Checked: `{done}`\n"
                f"Working: `{ok}`\n"
                f"Removed: `{removed}`\n"
                f"Errors: `{failed}`"
            )

    # DONE
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))

    await sts.edit(
        f"✅ **Cleanup Completed**\n"
        f"Time Taken: `{time_taken}`\n\n"
        f"Total Groups: `{total_chats}`\n"
        f"Working: `{ok}`\n"
        f"Removed: `{removed}`\n"
        f"Errors: `{failed}`"
    )
