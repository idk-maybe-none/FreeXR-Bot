import asyncio


class DiscordConsoleLogger:
    def __init__(self, bot, channel_id):
        self.bot = bot
        self.channel_id = channel_id
        self.buffer = ""
        self.lock = asyncio.Lock()

    def write(self, message):
        self.buffer += message
        if '\n' in self.buffer:
            lines = self.buffer.split('\n')
            self.buffer = lines[-1]
            for line in lines[:-1]:
                if line.strip():
                    asyncio.ensure_future(self.send_to_discord(line.strip()))

    def flush(self):
        if self.buffer.strip():
            asyncio.ensure_future(self.send_to_discord(self.buffer.strip()))
            self.buffer = ""

    async def send_to_discord(self, message):
        async with self.lock:
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                try:
                    await channel.send(f"```\n{message[:1900].replace('```', '')}\n```")
                except Exception:  # Too broad exception clause
                    pass