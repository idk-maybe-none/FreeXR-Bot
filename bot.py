from discord.ext import commands
from config import intents, BOT_VERSION, DISABLED_IN_BETA


class FreeXRBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=".",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        await self.load_extension("cogs.admin")
        await self.load_extension("cogs.moderation")
        await self.load_extension("cogs.devices")
        await self.load_extension("cogs.counting")
        await self.load_extension("cogs.utility")
        await self.load_extension("cogs.maintenance")
        await self.load_extension("cogs.events")

        if "b" in BOT_VERSION.lower():
            for name in DISABLED_IN_BETA:
                if name in self.all_commands:
                    self.remove_command(name)


bot = FreeXRBot()