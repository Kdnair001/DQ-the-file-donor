from pyrogram import Client, filters
from info import ADMINS, LOG_CHANNEL
from motor.motor_asyncio import AsyncIOMotorClient
from database.ia_filterdb import Media
from info import DATABASE_URI, DATABASE_NAME

@Client.on_message(filters.command("clear_primary_db") & filters.user(ADMINS))
async def clear_primary_db(bot, message):

    await message.reply_text("🗑 **Deleting Primary DB…**")

    primary = AsyncIOMotorClient(DATABASE_URI)[DATABASE_NAME][Media.Meta.collection_name]

    result = await primary.delete_many({})

    await bot.send_message(
        LOG_CHANNEL,
        f"🗑 **Primary DB Cleared Successfully**\n"
        f"Deleted Files: `{result.deleted_count}`"
    )
