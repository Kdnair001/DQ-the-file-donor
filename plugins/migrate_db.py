from pyrogram import Client, filters
from info import DATABASE_URI, SECONDDB_URI, ADMINS
from motor.motor_asyncio import AsyncIOMotorClient

DB_NAME_PRIMARY = "Emmastonev2"
DB_NAME_SECONDARY = "Emmastonev2"

COLLECTIONS = ["CONNECTION", "Telegram_files", "groups", "users"]


def is_admin(user_id):
    return user_id in ADMINS


@Client.on_message(filters.command("migrate") & filters.private)
async def migrate_db(bot, message):
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ You are not authorised.")

    msg = await message.reply("🚀 **Migration started...**\n")

    primary = AsyncIOMotorClient(DATABASE_URI)[DB_NAME_PRIMARY]
    secondary = AsyncIOMotorClient(SECONDDB_URI)[DB_NAME_SECONDARY]

    total = 0

    for col_name in COLLECTIONS:
        await msg.edit(f"📁 Migrating **{col_name}**...")

        src = primary[col_name]
        dst = secondary[col_name]

        cursor = src.find({})
        async for doc in cursor:
            try:
                await dst.replace_one({"_id": doc["_id"]}, doc, upsert=True)
                total += 1
            except Exception as e:
                print(f"Error copying {col_name}: {e}")

    await msg.edit(
        "✅ **Migration Completed Successfully!**\n\n"
        f"📦 Total Documents Migrated: **{total}**\n"
        f"📚 Collections: {', '.join(COLLECTIONS)}"
    )
