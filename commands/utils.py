async def handle_pin(bot, message):
    content = (message.content or "").lower().strip()
    if content.startswith("!"):
        content = content[1:]

    if content not in ("pin", "unpin"):
        return False

    if not message.reference:
        return True

    replied = await message.channel.fetch_message(message.reference.message_id)

    if content == "pin":
        await replied.pin(reason=f"Pinned by {message.author}")
        await message.add_reaction("📌", remove_after=5)
    else:
        await replied.unpin(reason=f"Unpinned by {message.author}")
        await message.add_reaction("❌", remove_after=5)

    return True
