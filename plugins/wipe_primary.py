import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import ADMINS, LOG_CHANNEL
from motor.motor_asyncio import AsyncIOMotorClient


PRIMARY_DB = "Emmastonev2"
COLLECTIONS = ["Telegram_files", "users", "groups", "connections"]


@Client.on_message(filters.command("wipe_primary") & filters.user(ADMINS))
async def wipe_primary_init(bot, message):

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚠️ YES — WIPE PRIMARY DB", callback_data="confirm_wipe")],
            [InlineKeyboardButton("❌ CANCEL", callback_data="cancel_wipe")]
        ]
    )

    await message.reply(
        "⚠️ **WARNING — DESTRUCTIVE ACTION**\n\n"
        "**This will remove ALL DATA from the PRIMARY database (`Emmastonev2`).**\n"
        "Your secondary DB (`Emmastonev2_backup`) is NOT touched.\n\n"
        "Proceed only if `/verify` shows everything is already migrated.\n\n"
        "**Are you absolutely sure you want to wipe the primary DB?**",
        reply_markup=keyboard,
    )


@Client.on_callback_query(filters.regex("cancel_wipe"))
async def cancel_wipe(client, callback):
    await callback.message.edit("❌ **Wipe cancelled.** Nothing was deleted.")
    await callback.answer("Cancelled.", show_alert=False)


@Client.on_callback_query(filters.regex("confirm_wipe"))
async def confirm_wipe(client, callback):
    await callback.answer("Starting wipe…")

    msg = await callback.message.edit(
        "🔄 **Final verification before wipe...**"
    )

    # DB connections
    primary_client = AsyncIOMotorClient(client.config["DATABASE_URI"])
    secondary_client = AsyncIOMotorClient(client.config["SECONDDB_URI"])

    primary = primary_client[PRIMARY_DB]
    secondary = secondary_client["Emmastonev2_backup"]

    # Verify counts still match
    mismatch = False
    verify_text = "📊 **Final Pre-Wipe Verification**\n\n"

    for col in COLLECTIONS:
        p_count = await primary[col].count_documents({})
        s_count = await secondary[col].count_documents({})

        if p_count == s_count:
            verify_text += f"✅ `{col}` OK ({p_count})\n"
        else:
            verify_text += f"❌ `{col}` MISMATCH — STOP (Primary {p_count}, Secondary {s_count})\n"
            mismatch = True

    if mismatch:
        await msg.edit(
            verify_text
            + "\n⚠️ **Mismatch detected. Wipe aborted to prevent data loss.**"
        )
        return

    await msg.edit(verify_text + "\n🚀 **Verification OK. Starting wipe…**")

    # -----------------------------------------
    # SAFE BATCH DELETION (5000 documents/batch)
    # -----------------------------------------
    BATCH_SIZE = 5000

    for col in COLLECTIONS:
        collection = primary[col]
        col_count = await collection.count_documents({})
        deleted_total = 0

        progress = await callback.message.reply(
            f"🗑 **Wiping `{col}`** — {col_count} documents..."
        )

        while True:
            batch = await collection.find({}).limit(BATCH_SIZE).to_list(length=BATCH_SIZE)
            if not batch:
                break

            ids = [doc["_id"] for doc in batch]

            result = await collection.delete_many({"_id": {"$in": ids}})
            deleted_total += result.deleted_count

            await progress.edit(
                f"🗑 **Wiping `{col}`**\n"
                f"Deleted: {deleted_total}/{col_count}"
            )

        await progress.edit(f"✅ `{col}` wiped successfully.")

    # Final message
    final_report = (
        "🎉 **Primary database wipe completed successfully.**\n"
        "You may now safely switch your DB URIs:\n\n"
        "➡️ Set `SECONDDB_URI` as PRIMARY\n"
        "➡️ Set old PRIMARY as SECONDARY (if needed)\n"
        "➡️ Restart bot\n\n"
        "✔️ Secondary DB is now your full, clean, optimized DB."
    )

    await callback.message.reply(final_report)
    await client.send_message(LOG_CHANNEL, final_report)
