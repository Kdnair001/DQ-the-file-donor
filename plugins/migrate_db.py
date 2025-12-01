import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from info import ADMINS, LOG_CHANNEL
from motor.motor_asyncio import AsyncIOMotorClient

# ❗ YOUR DATABASE NAMES
PRIMARY_DB = "Emmastonev2"
SECONDARY_DB = "Emmastonev2_backup"

# ❗ COLLECTIONS TO MIGRATE
COLLECTIONS = ["Telegram_files", "users", "groups", "connections"]

# ❗ Batch size
BATCH = 2500


# -------------------------------------------------------
# /migrate command
# -------------------------------------------------------
@Client.on_message(filters.command("migrate") & filters.user(ADMINS))
async def migrate_db(bot, message):

    status = await message.reply_text("⏳ **Preparing database migration...**")

    # Connect to both DBs
    primary_client = AsyncIOMotorClient(bot.config["DATABASE_URI"])
    secondary_client = AsyncIOMotorClient(bot.config["SECONDDB_URI"])

    primary = primary_client[PRIMARY_DB]
    secondary = secondary_client[SECONDARY_DB]

    total_docs = 0
    migrated_docs = 0

    # -------------------------------
    # Count total documents
    # -------------------------------
    for col in COLLECTIONS:
        count = await primary[col].count_documents({})
        total_docs += count

    await status.edit(f"📦 **Migration Started**\n\n"
                      f"🗂 Total documents to migrate: `{total_docs}`\n"
                      f"📁 Collections: `{', '.join(COLLECTIONS)}`\n"
                      f"⚡ Batch size: `{BATCH}`\n\n"
                      f"⏳ Starting now...")

    # -------------------------------
    # Start migration
    # -------------------------------
    for col in COLLECTIONS:
        collection_primary = primary[col]
        collection_secondary = secondary[col]

        count = await collection_primary.count_documents({})
        if count == 0:
            await bot.send_message(LOG_CHANNEL, f"⚠️ `{col}` is empty. Skipping.")
            continue

        await bot.send_message(LOG_CHANNEL,
                               f"📁 **Migrating collection:** `{col}`\n"
                               f"Total: `{count}` documents")

        skip = 0

        while skip < count:
            try:
                cursor = collection_primary.find().skip(skip).limit(BATCH)
                documents = await cursor.to_list(length=BATCH)

                if not documents:
                    break

                # Prevent duplicate _id
                for doc in documents:
                    doc.pop("_id", None)

                if documents:
                    await collection_secondary.insert_many(documents)

                skip += len(documents)
                migrated_docs += len(documents)

                await status.edit(
                    f"⬆️ **Migrating...**\n"
                    f"📁 Current collection: `{col}`\n"
                    f"🟩 Migrated `{migrated_docs}` / `{total_docs}`\n"
                    f"📦 Batch size: `{BATCH}`"
                )

                await asyncio.sleep(0.5)

            except FloodWait as e:
                await asyncio.sleep(e.value)

    # -------------------------------
    # DONE
    # -------------------------------
    await status.edit(
        f"✅ **Migration completed successfully!**\n\n"
        f"📦 Total migrated: `{migrated_docs}`\n"
        f"📁 Collections: `{', '.join(COLLECTIONS)}`\n"
        f"📍 Primary → `{PRIMARY_DB}`\n"
        f"📍 Secondary → `{SECONDARY_DB}`\n\n"
        f"⚠️ No content was deleted.\n"
        f"🟢 Safe to verify now."
    )

    await bot.send_message(
        LOG_CHANNEL,
        f"🎉 **Database Migration Completed**\n\n"
        f"Total Migrated: `{migrated_docs}`\n"
        f"From: `{PRIMARY_DB}` → `{SECONDARY_DB}`"
    )
