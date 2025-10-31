import discord
from discord.ext import commands
import platform
import time
import sys

from config import BOT_VERSION, QUARANTINE_ROLE_ID, QUARANTINE_DATA_FILE, BOT_CONSOLE_CHANNEL_ID, WELCOME_CHANNEL_ID, MEMBER_ROLE_ID
from utils.file_handlers import load_json
from utils.logger import DiscordConsoleLogger
from utils.helpers import get_uptime

start_time = time.time()


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync()
        sys.stdout = DiscordConsoleLogger(self.bot, BOT_CONSOLE_CHANNEL_ID)
        sys.stderr = sys.stdout
        print(f"Logged in as {self.bot.user}")

        os_info = platform.system()
        release = platform.release()
        architecture = platform.machine()
        python_version = platform.python_version()
        uptime = get_uptime(start_time)

        env_message = (
            f"✅ Bot is running in **{os_info} {release} ({architecture})** environment "
            f"with **Python {python_version}**\n"
            f"🛠 Version: **{BOT_VERSION}**\n"
            f"⏱ Load time: **{uptime}**"
        )
        if "b" in BOT_VERSION.lower():
            env_message += "\n⚠️ Beta version detected – may be unstable! Potentially destructive commands have been disabled."
        channel = self.bot.get_channel(BOT_CONSOLE_CHANNEL_ID)
        await channel.send(env_message)

        print(env_message)

        active_quarantines = load_json(QUARANTINE_DATA_FILE, {})
        guild = self.bot.guilds[0]
        quarantine_role = guild.get_role(QUARANTINE_ROLE_ID)
        to_remove = []

        for user_id_str, unq_time_str in active_quarantines.items():
            user_id = int(user_id_str)
            member = guild.get_member(user_id)
            from datetime import datetime
            unq_time = datetime.fromisoformat(unq_time_str)
            if member is None:
                to_remove.append(user_id_str)
                continue
            if quarantine_role not in member.roles:
                to_remove.append(user_id_str)

        for user_id_str in to_remove:
            active_quarantines.pop(user_id_str)

        from utils.file_handlers import save_json
        save_json(QUARANTINE_DATA_FILE, active_quarantines)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            await member.add_roles(member.guild.get_role(MEMBER_ROLE_ID))
        except discord.Forbidden:
            print(f"Couldn't add role to {member} (permissions issue)")

        try:
            await member.send(
                "# 👋 Welcome to the server!\n Hello and welcome to FreeXR. We hack headsets to root them and unlock their bootloaders, and we appreciate you for joining. To get started, please read the https://discord.com/channels/1344235945238593547/1364918149404688454.\nWe hope you have a great stay here, and thank you for joining."
            )
        except discord.Forbidden:
            channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
            if channel:
                msg = await channel.send(
                    f"{member.mention} 👋 Welcome to the server! Please read the https://discord.com/channels/1344235945238593547/1364918149404688454, and we hope you have a great stay here!.\n-# Psst! Your DMs are closed, so I couldn't send you a DM."
                )

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            if not self.bot.get_cog('Utility').replies[ctx.message.content]:
                print(f"Ignoring exception: CommandNotFound: '{ctx.message.content}'")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.MissingRole):
            await ctx.send(f"{ctx.author.mention}❌ You are not authorized to use this command.")
        else:
            print(f"Unhandled command error: {error}")


async def setup(bot):
    await bot.add_cog(Events(bot))