import discord
from discord.ext import commands
import sys
import os
from git import Repo

from config import ADMIN_ROLE_ID, REPO_DIR, REPO_URL
from utils.helpers import load_replies


class Maintenance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def update(self, ctx):
        """Updates the bot by pulling latest code and restarting"""
        await ctx.send("📥 Downloading latest version...")

        try:
            await ctx.send("📥 Pulling from repository...")
            if os.path.exists(REPO_DIR):
                repo = Repo(REPO_DIR)
                repo.remotes.origin.pull()
            else:
                Repo.clone_from(REPO_URL, REPO_DIR)

            await ctx.send("✅ Update complete. Restarting bot...")
            python = sys.executable
            os.execv(python, [python] + sys.argv)
        except Exception as e:
            await ctx.send(f"❌ Update failed:\n```{e}```")

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def hotupdate(self, ctx):
        """Pulls everything from repository without restarting"""
        try:
            await ctx.send("📥 Pulling everything from the repository...")
            if os.path.exists(REPO_DIR):
                repo = Repo(REPO_DIR)
                repo.remotes.origin.pull()
            else:
                Repo.clone_from(REPO_URL, REPO_DIR)

            self.bot.get_cog('Utility').replies = load_replies()
            await ctx.send("✅ Hot update complete.")
        except Exception as e:
            await ctx.send(f"❌ Hot update failed:\n```{e}```")

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def reboot(self, ctx):
        """Reboots the bot"""
        await ctx.send("🔂 Rebooting bot...")
        python = sys.executable
        os.execv(python, [python] + sys.argv)

    @commands.hybrid_command()
    async def ratelimitcheck(self, ctx):
        try:
            await ctx.send("If you see this message, the bot is not rate limited.")
        except discord.HTTPException as e:
            if e.status == 429:
                print("Rate limited: Try again after", e.retry_after)
            else:
                await ctx.send(
                    "An error occurred while trying to send the message. Check console!!"
                )
                print(f"Unexpected HTTP error: {e}")


async def setup(bot):
    await bot.add_cog(Maintenance(bot))