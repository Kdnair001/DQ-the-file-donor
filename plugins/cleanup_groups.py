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
    except (PeerIdInvalid, ChannelInvalid, ChatIdInvalid, ValueError):
        # Invalid, deleted, or unknown chat
        return False
    except RPCError:
        # Chat exists but other RPC errors happened
        return True


# ----------------------------------------------------------
# SMART LEAVE + DB DELETE + LOGGING
# ----------------------------------------------------------
async def leave_and_log(bot, chat_id, reason):
    # Remove from DB entirely
    try:
        await db.delete_chat(chat_id)
    except Exception as e:
        try:
            await bot.send_message(
                LOG_CHANNEL,
                f"⚠️ Failed to delete `{chat_id}` from DB:\n`{e}`",
            )
        except Exception:
            pass

    # Attempt leaving chat
    try:
        await bot.leave_chat(chat_id)
    except Exception:
        pass

    # Log to LOG_CHANNEL
    text = (
        "🚫 **Left / Removed Group**\n"
        f"Group ID: `{chat_id}`\n"
        f"Reason: `{reason}`"
    )

    try:
        await bot.send_message(LOG_CHANNEL, text)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await bot.send_message(LOG_CHANNEL, text)
    except Exception:
        # Ignore logging failures
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

        # 1. CHECK CHAT EXISTS (avoid Peer id invalid crash)
        try:
            exists = await chat_exists(bot, chat_id)
        except Exception:
            exists = False

        if not exists:
            removed += 1
            await leave_and_log(bot, chat_id, "Invalid chat: Deleted / inaccessible")
            continue

        # 2. TRY SENDING TEST MESSAGE
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

        except UserBannedInChannel:
            removed += 1
            await leave_and_log(bot, chat_id, "UserBannedInChannel: Bot banned")

        except (PeerIdInvalid, ChannelInvalid, ChatIdInvalid, ValueError):
            removed += 1
            await leave_and_log(bot, chat_id, "Peer/Channel invalid: Deleted or inaccessible")

        except RPCError as e:
            err_str = str(e)

            # Treat restricted / private chats as dead too
            if "CHAT_RESTRICTED" in err_str:
                removed += 1
                await leave_and_log(bot, chat_id, "ChatRestricted: The chat is restricted")
            elif "CHANNEL_PRIVATE" in err_str:
                removed += 1
                await leave_and_log(bot, chat_id, "ChannelPrivate: Not accessible / private")
            else:
                failed += 1
                try:
                    await bot.send_message(
                        LOG_CHANNEL,
                        f"⚠️ Unexpected error in `{chat_id}`:\n`{e}`",
                    )
                except Exception:
                    pass
            continue

        # 3. Progress Update
        done += 1
        await asyncio.sleep(1.0)

        if not done % 20:
            try:
                await sts.edit(
                    f"🧹 **Cleanup in progress...**\n\n"
                    f"Total Groups: `{total_chats}`\n"
                    f"Checked: `{done}` / `{total_chats}`\n"
                    f"Working: `{ok}`\n"
                    f"Removed: `{removed}`\n"
                    f"Errors: `{failed}`"
                )
            except Exception:
                pass

    # DONE
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))

    try:
        await sts.edit(
            f"✅ **Cleanup Completed**\n"
            f"Time Taken: `{time_taken}`\n\n"
            f"Total Groups: `{total_chats}`\n"
            f"Working: `{ok}`\n"
            f"Removed: `{removed}`\n"
            f"Errors: `{failed}`"
        )
    except Exception:
        pass
