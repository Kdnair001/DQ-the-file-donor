import asyncio
from pyrogram import Client, filters
from info import ADMINS, LOG_CHANNEL
from database.ia_filterdb import Media, Media2
from motor.motor_asyncio import AsyncIOMotorClient
from info import DATABASE_URI, DATABASE_NAME, SECONDDB_URI

BATCH_SIZE = 500   # safe batch size for MongoDB


@Client.on_message(filters.command("migrate_to_secondary") & filters.user(ADMINS))
async def migrate_to_secondary(bot, message):

    await message.reply_text("🔄 **Migration started…**\nCopying Primary → Secondary DB")

    primary = AsyncIOMotorClient(DATABASE_URI)[DATABASE_NAME][Media.Meta.collection_name]
    secondary = AsyncIOMotorClient(SECONDDB_URI)[DATABASE_NAME][Media2.Meta.collection_name]

    total = await primary.count_documents({})
    copied = 0

    # Cursor for batch reading
    cursor = primary.find({}, no_cursor_timeout=True)

    async for doc in cursor:
        try:
            await secondary.insert_one(doc)
        except Exception:
            pass  # Ignore duplicate errors

        copied += 1

        # Progress update
        if copied % BATCH_SIZE == 0:
            await bot.send_message(
                LOG_CHANNEL,
                f"📦 Migrated: `{copied}` / `{total}`"
            )

        await asyncio.sleep(0.01)  # prevent overload

    await bot.send_message(
        LOG_CHANNEL,
        f"✅ **Migration Completed**\n"
        f"Total Files Migrated: `{copied}`\n\n"
        f"⚠️ **Waiting for your verification**.\n"
        f"No data has been deleted."
    )
