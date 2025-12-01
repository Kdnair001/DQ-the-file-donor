import asyncio
from pyrogram import Client, filters
from info import ADMINS, LOG_CHANNEL
from motor.motor_asyncio import AsyncIOMotorClient

PRIMARY_DB = "Emmastonev2"
SECONDARY_DB = "Emmastonev2_backup"

COLLECTIONS = ["Telegram_files", "users", "groups", "connections"]


@Client.on_message(filters.command("verify") & filters.user(ADMINS))
async def verify_migration(bot, message):

    status = await message.reply_text("🔍 **Starting verification...**")

    # Database connections
    primary_client = AsyncIOMotorClient(bot.config["DATABASE_URI"])
    secondary_client = AsyncIOMotorClient(bot.config["SECONDDB_URI"])

    primary = primary_client[PRIMARY_DB]
    secondary = secondary_client[SECONDARY_DB]

    results_text = "📊 **Migration Verification Report**\n\n"
    all_good = True

    for col in COLLECTIONS:
        p_col = primary[col]
        s_col = secondary[col]

        # Count documents
        p_count = await p_col.count_documents({})
        s_count = await s_col.count_documents({})

        # Compare
        if p_count == s_count:
            results_text += f"✅ `{col}` — OK ( {p_count} == {s_count} )\n"
        else:
            results_text += f"❌ `{col}` — MISMATCH (Primary: {p_count}, Secondary: {s_count})\n"
            all_good = False

    if all_good:
        results_text += "\n🎉 **All collections match perfectly!**\n"
        results_text += "You may proceed with wiping the primary DB (only when you say so)."
    else:
        results_text += "\n⚠️ **Mismatch found! Do NOT wipe the primary DB.**"

    # Update the status message
    await status.edit(results_text)

    # Also send to logs
    await bot.send_message(LOG_CHANNEL, results_text)
