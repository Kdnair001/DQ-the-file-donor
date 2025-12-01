from pyrogram import Client, filters, enums
from pyrogram.errors import ChatWriteForbidden, ChatAdminRequired


@Client.on_message(filters.group)
async def leave_if_not_admin(client, message):
    chat_id = message.chat.id

    # Get bot info
    try:
        me = await client.get_me()
        bot_id = me.id
    except Exception:
        return

    # Check bot role in group
    try:
        member = await client.get_chat_member(chat_id, bot_id)
        bot_status = member.status
    except ChatAdminRequired:
        # Bot can't check admin list → means bot has NO admin privilege at all
        try:
            await client.send_message(
                chat_id,
                "⚠️ **I am leaving this group because I don’t have admin rights.**\n"
                "Please promote me to admin to use my features.",
            )
        except:
            pass
        
        try:
            await client.leave_chat(chat_id)
        except:
            pass
        return
    except Exception:
        return

    # If bot is admin → do nothing
    if bot_status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
        return

    # Bot is NOT admin → warn & leave
    try:
        await client.send_message(
            chat_id,
            "⚠️ **I am leaving this group because I am not an admin.**\n"
            "Promote me to admin if you wish to use my features.",
        )
    except ChatWriteForbidden:
        # Bot cannot even send message
        pass
    except:
        pass

    # Leave safely
    try:
        await client.leave_chat(chat_id)
    except:
        pass
