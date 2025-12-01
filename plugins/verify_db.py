from pyrogram import Client, filters
from info import DATABASE_URI, SECONDDB_URI, ADMINS
from motor.motor_asyncio import AsyncIOMotorClient

DB_NAME_PRIMARY = "Emmastonev2"
DB_NAME_SECONDARY = "Emmastonev2"

COLLECTIONS = ["CONNECTION", "Telegram_files", "groups", "users"]


def is_admin(user_id):
    return user_id in ADMINS


@Client.on_message(filters.command("verify") & filters.private)
async def verify_db(bot, message):
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ You are not authorised.")

    primary = AsyncIOMotorClient(DATABASE_URI)[DB_NAME_PRIMARY]
    secondary = AsyncIOMotorClient(SECONDDB_URI)[DB_NAME_SECONDARY]

    text = "📊 **Database Verification Report**\n\n"

    for col in COLLECTIONS:
        p = await primary[col].count_documents({})
        s = await secondary[col].count_documents({})

        status = "✅ SAME" if p == s else "❌ MISMATCH"

        text += f"**{col}** → Primary: `{p}` | Secondary: `{s}` → {status}\n"

    await message.reply(text)
