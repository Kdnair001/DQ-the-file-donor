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
    ChatRestricted,        # ✅ ADDED
    RPCError,
    FloodWait,
)
from info import ADMINS, LOG_CHANNEL
from database.users_chats_db import db


CLEANUP_TEST_MESSAGE = "🧹 **System Permission Check...**"


# ----------------------------------------------------------
# CHECK WHETHER CHAT EXISTS BEFORE SENDING ANYTHING
# ----------------------------------------------------------
async def chat_exists(bot, chat_id):
    try:
        await bot.get_chat(chat_id)
        return True
    except (PeerIdInvalid, ChannelInvalid, ChatIdInvalid):
        return False
    except RPCError:
        return True  # Chat exists but may have other restrictions


# ----------------------------------------------------------
# SMART LEAVE + DB DISABLE + LOGGING
# ----------------------------------------------------------
async def leave_and_log(bot, chat_id, reason):

    # Disable chat in DB
    try:
        await db.disable_chat(chat_id, reason)
    except Exception as e:
        try:
            await bot.send_message(
                LOG_CHANNEL,
                f"⚠️ Failed to disable `{chat_id}` in DB:\n`{e}`"
            )
        except:
            pass

    # Try leaving the group
    try:
        await bot.leave_chat(chat_id)
    except:
        pass

    # Log to log channel
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
    except Exception:
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
        chat_id = int(chat["id"])

        # --------------------------------------------------
        # 1. CHECK CHAT EXISTS
        # --------------------------------------------------
        if not await chat_exists(bot, chat_id):
            removed += 1
            await leave_and_log(bot, chat_id, "Invalid chat: Deleted / inaccessible")
            continue

        # --------------------------------------------------
        # 2. TRY SENDING TEST MESSAGE
        # --------------------------------------------------
        try:
            await bot.send_message(chat_id, CLEANUP_TEST_MESSAGE)
            ok += 1

        except FloodWait as e:
            await asyncio.sleep(e.value)
            continue

        except ChatWriteForbidden:
            removed += 1
            await leave_and_log(bot, chat_id, "ChatWriteForbidden: Bot cannot send messages")

        except ChatAdminRequired:
            removed += 1
            await leave_and_log(bot, chat_id, "ChatAdminRequired: Missing admin rights")

        except ChatRestricted:
            removed += 1
            await leave_and_log(bot, chat_id, "ChatRestricted: Group is restricted / read-only")

        except UserBannedInChannel:
            removed += 1
            await leave_and_log(bot, chat_id, "UserBannedInChannel: Bot banned")

        except ChatIdInvalid:
            removed += 1
            await leave_and_log(bot, chat_id, "ChatIdInvalid: Unknown or invalid chat")

        except (PeerIdInvalid, ChannelInvalid):
            removed += 1
            await leave_and_log(bot, chat_id, "PeerIdInvalid/ChannelInvalid: Deleted or inaccessible")

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

        # --------------------------------------------------
        # 3. PROGRESS UPDATE
        # --------------------------------------------------
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

    # ----------------------------------------------------------
    # FINAL REPORT
    # ----------------------------------------------------------
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))

    await sts.edit(
        f"✅ **Cleanup Completed**\n"
        f"Time Taken: `{time_taken}`\n\n"
        f"Total Groups: `{total_chats}`\n"
        f"Working: `{ok}`\n"
        f"Removed: `{removed}`\n"
        f"Errors: `{failed}`"
    )
