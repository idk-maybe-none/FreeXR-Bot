import discord
from discord.ext import commands
import platform
import time

from config import BOT_VERSION
from utils.helpers import get_uptime, load_replies, clean_message_content

start_time = time.time()


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.replies = load_replies()

    @commands.hybrid_command()
    async def status(self, ctx):
        """Displays the bot's status and environment information"""
        os_info = platform.system()
        release = platform.release()
        architecture = platform.machine()
        python_version = platform.python_version()
        uptime = get_uptime(start_time)

        env_message = (
            f"✅ Bot is running in **{os_info} {release} ({architecture})** environment "
            f"with **Python {python_version}**\n"
            f"🛠 Version: **{BOT_VERSION}**\n"
            f"⏱ Uptime: **{uptime}**"
        )
        if "b" in BOT_VERSION.lower():
            env_message += "\n⚠️ Beta version detected – may be unstable!"
        await ctx.send(env_message)

    @commands.hybrid_command()
    async def pin(self, ctx):
        """Pins a message that you reply to"""
        if not ctx.message.reference:
            await ctx.send("Please reply to the message you want to pin.")
            return

        try:
            msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            await msg.pin()
            await ctx.send("📌 Message pinned.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to pin messages in this channel.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to pin message: {e}")

    @commands.hybrid_command(name="replies")
    async def replies_command(self, ctx):
        """Lists all available quick replies"""
        if not self.replies:
            await ctx.send("⚠️ No replies available.")
            return

        response = "\n".join([f"* {key}: {val[0]}" for key, val in self.replies.items()])
        await ctx.send(f"```\n{response}\n```")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle message filtering and report collection."""
        if message.author.bot:
            return

        content = clean_message_content(message.content)
        message.content = content

        if content.startswith("."):
            cmd = content[1:]
            if cmd in self.replies:
                await message.channel.send(self.replies[cmd][1])
                return


async def setup(bot):
    await bot.add_cog(Utility(bot))