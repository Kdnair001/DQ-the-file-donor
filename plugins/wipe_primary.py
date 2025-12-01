from pyrogram import Client, filters
from info import DATABASE_URI, ADMINS
from motor.motor_asyncio import AsyncIOMotorClient

DB_NAME_PRIMARY = "Emmastonev2"
COLLECTIONS = ["CONNECTION", "Telegram_files", "groups", "users"]


def is_admin(user_id):
    return user_id in ADMINS


@Client.on_message(filters.command("wipe") & filters.private)
async def wipe_primary(bot, message):
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ You are not authorised.")

    if message.text.strip() != "/wipe yes":
        return await message.reply(
            "⚠️ **This will delete ALL DATA in the PRIMARY DATABASE.**\n\n"
            "To confirm deletion, send:\n`/wipe yes`"
        )

    primary = AsyncIOMotorClient(DATABASE_URI)[DB_NAME_PRIMARY]

    for col in COLLECTIONS:
        await primary[col].delete_many({})

    await message.reply("🧹 **Primary Database wiped completely.**")
