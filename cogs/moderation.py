import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import re
import asyncio

from config import ADMIN_ROLE_ID, QUARANTINE_ROLE_ID, QUARANTINE_DATA_FILE, BACKUP_FILE, FILTER_FILE, REPORT_LOG_CHANNEL_ID, QUARANTINE_LOG_FILE
from utils.file_handlers import load_json, save_json
from utils.helpers import log_to_file, clean_message_content


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.context_menu = None
        self.bot = bot
        self.active_reports = {}
        self.regex_filters = load_json(FILTER_FILE, [])
        self.active_quarantines = load_json(QUARANTINE_DATA_FILE, {})
        self.message_backups = load_json(BACKUP_FILE, {})

        self.check_quarantine_expiry.start()

    def cog_unload(self):
        self.check_quarantine_expiry.cancel()
        self.bot.tree.remove_command("Add to report", type=discord.AppCommandType.message)

    async def cog_load(self):
        self.context_menu = discord.app_commands.ContextMenu(
            name="Add to report",
            callback=self.add_to_report,
        )
        self.bot.tree.add_command(self.context_menu)

    @commands.hybrid_command()
    async def report(self, ctx):
        """Starts a report in DMs."""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("Please DM me this command.")
            return

        await ctx.send(
            "You're reporting to the server admins. All messages from this point will be recorded.\n"
            "Please state your issue. Upload images as links (attachments won't work).\n"
            "When you're finished, type `.iamdone`. Messages will stop being recorded."
        )
        self.active_reports[ctx.author.id] = []

    #@discord.app_commands.context_menu(name="Add to report")
    async def add_to_report(self, interaction: discord.Interaction, message: discord.Message):
        user_id = interaction.user.id

        if user_id not in self.active_reports:
            await interaction.response.send_message(
                "❌ You don't have an active report. Please start one by DMing me `.report`.",
                ephemeral=True,
            )
            return

        content = f"**Message from {message.author} in <#{message.channel.id}>:**\n{message.content}"
        self.active_reports[user_id].append(content)

        backup_entry = {
            "author": str(message.author),
            "channel_id": message.channel.id,
            "message_id": message.id,
            "content": message.content,
            "timestamp": str(message.created_at),
            "jump_url": message.jump_url,
        }
        if str(user_id) not in self.message_backups:
            self.message_backups[str(user_id)] = []
        self.message_backups[str(user_id)].append(backup_entry)
        save_json(BACKUP_FILE, self.message_backups)

        await interaction.response.send_message("✅ Message added to your report.", ephemeral=True)

    @commands.hybrid_command()
    async def iamdone(self, ctx):
        """Ends the report and sends it to the admins."""
        if not isinstance(ctx.channel, discord.DMChannel):
            return

        user_id = ctx.author.id
        if user_id not in self.active_reports or not self.active_reports[user_id]:
            await ctx.send("No messages recorded or you haven't started a report with `.report`.")
            return

        channel = self.bot.get_channel(REPORT_LOG_CHANNEL_ID)
        report_content = "\n".join(self.active_reports[user_id])
        extra = ""
        if str(user_id) in self.message_backups:
            extra += "\n\n**Attached messages:**\n"
            for entry in self.message_backups[str(user_id)]:
                extra += (
                    f"[Jump to message]({entry['jump_url']}) | "
                    f"**{entry['author']}** ({entry['timestamp']}):\n"
                    f"{entry['content']}\n\n"
                )

        full_content = report_content + extra

        embed = discord.Embed(
            title="New Report",
            description=full_content[:4000],
            color=discord.Color.orange(),
        )
        embed.set_author(name=f"{ctx.author}", icon_url=ctx.author.display_avatar.url)

        report_message = await channel.send(embed=embed)

        from utils.file_handlers import load_json, save_json
        report_log_map = load_json(REPORTS_FILE, {})
        report_log_map[str(report_message.id)] = user_id
        save_json(REPORTS_FILE, report_log_map)

        await ctx.send("Thank you! Your report has been sent.")

        self.active_reports[user_id] = []
        if str(user_id) in self.message_backups:
            del self.message_backups[str(user_id)]
            save_json(BACKUP_FILE, self.message_backups)

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def block(self, ctx):
        """Blocks a regex pattern from being sent in the server."""
        if ctx.interaction:
            class RegexModal(discord.ui.Modal, title="Block Regex Pattern"):
                pattern = discord.ui.TextInput(label="Regex Pattern", required=True)

                async def on_submit(self, interaction: discord.Interaction):
                    try:
                        re.compile(self.pattern.value)
                        self.cog.regex_filters.append({"pattern": self.pattern.value, "enabled": True})
                        save_json(FILTER_FILE, self.cog.regex_filters)
                        await interaction.response.send_message(f"Blocked regex added: `{self.pattern.value}`",
                                                                ephemeral=True)
                    except re.error:
                        await interaction.response.send_message("Invalid regex pattern.", ephemeral=True)

            modal = RegexModal()
            modal.cog = self
            await ctx.interaction.response.send_modal(modal)
        else:
            await ctx.send("Please use the `/block` slash command to add a regex pattern.")

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def listregex(self, ctx):
        """Lists all blocked regex patterns."""
        if not self.regex_filters:
            return await ctx.send("No regex patterns are currently blocked.")

        message = "Blocked Regex Patterns:\n"
        for i, entry in enumerate(self.regex_filters):
            message += f"{i}. `{entry['pattern']}` - {'✅ Enabled' if entry['enabled'] else '❌ Disabled'}\n"
        message += "\nUse `.toggle <index>` to enable/disable a regex."
        await ctx.send(message)

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def toggle(self, ctx, index: int):
        """Toggles a regex pattern."""
        real_index = index - 1
        if 0 <= real_index < len(self.regex_filters):
            self.regex_filters[real_index]["enabled"] = not self.regex_filters[real_index]["enabled"]
            save_json(FILTER_FILE, self.regex_filters)
            await ctx.send(
                f"Toggled regex `{self.regex_filters[real_index]['pattern']}` to {'enabled' if self.regex_filters[real_index]['enabled'] else 'disabled'}.")
        else:
            await ctx.send("Invalid index. Use the number shown in `.listregex`.")

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def unblock(self, ctx):
        """Unblocks a regex pattern."""
        if not self.regex_filters:
            return await ctx.send("No regex patterns to remove.")

        await ctx.send("Please enter the index of the regex to remove (as shown in `.listregex`):")

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            index = int(msg.content)
            real_index = index - 1
            removed = self.regex_filters.pop(real_index)
            save_json(FILTER_FILE, self.regex_filters)
            await ctx.send(f"Removed regex `{removed['pattern']}`")
        except (ValueError, IndexError):
            await ctx.send("Invalid index.")
        except asyncio.TimeoutError:
            await ctx.send("Timeout. Please try again.")

    @staticmethod  # IDK if this is dirty fix, it just works
    def is_admin_quarantine():
        def predicate(ctx):
            return any(role.id == ADMIN_ROLE_ID for role in ctx.author.roles)

        return commands.check(predicate)

    @commands.hybrid_command()
    @is_admin_quarantine()
    async def q(self, ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        """Quarantine a member for a duration (e.g. 10m, 1h, 1d)."""
        quarantine_role = ctx.guild.get_role(QUARANTINE_ROLE_ID)
        if quarantine_role in member.roles:
            await ctx.send(f"{member.display_name} is already quarantined.")
            return

        try:
            amount = int(duration[:-1])
            unit = duration[-1].lower()
            if unit == 'm':
                delta = timedelta(minutes=amount)
            elif unit == 'h':
                delta = timedelta(hours=amount)
            elif unit == 'd':
                delta = timedelta(days=amount)
            else:
                await ctx.send("Invalid duration format. Use m (minutes), h (hours), or d (days).")
                return
        except Exception as e:
            await ctx.send(
                f"Invalid duration format. Use m (minutes), h (hours), or d (days). Example: 10m, 1h, 2d {e}")
            return

        await member.add_roles(quarantine_role, reason=f"Quarantine by {ctx.author} for {reason}")
        unquarantine_time = datetime.now(timezone.utc) + delta
        self.active_quarantines[str(member.id)] = unquarantine_time.isoformat()
        save_json(QUARANTINE_DATA_FILE, self.active_quarantines)

        await ctx.send(f"{member.display_name} has been quarantined for {duration}. Reason: {reason}")

        log_entry = f"{ctx.author} quarantined {member} for {duration}. Reason: {reason}"
        log_to_file(log_entry, QUARANTINE_LOG_FILE)

        log_channel = ctx.guild.get_channel(REPORT_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="User Quarantined",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="User", value=member.mention, inline=True)
            embed.add_field(name="By", value=ctx.author.mention, inline=True)
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await log_channel.send(embed=embed)

    @commands.hybrid_command()
    @is_admin_quarantine()
    async def uq(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Unquarantine a member immediately."""
        quarantine_role = ctx.guild.get_role(QUARANTINE_ROLE_ID)
        if quarantine_role not in member.roles:
            await ctx.send(f"{member.display_name} is not quarantined.")
            return

        await member.remove_roles(quarantine_role, reason=f"Unquarantined by {ctx.author} for {reason}")
        self.active_quarantines.pop(str(member.id), None)
        save_json(QUARANTINE_DATA_FILE, self.active_quarantines)

        await ctx.send(f"{member.display_name} has been unquarantined. Reason: {reason}")

        log_entry = f"{ctx.author} unquarantined {member}. Reason: {reason}"
        log_to_file(log_entry, QUARANTINE_LOG_FILE)

        log_channel = ctx.guild.get_channel(REPORT_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="User Unquarantined",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="User", value=member.mention, inline=True)
            embed.add_field(name="By", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await log_channel.send(embed=embed)

    @tasks.loop(seconds=60)
    async def check_quarantine_expiry(self):
        """Check for expired quarantines."""
        now = datetime.now(timezone.utc)
        guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild:
            return

        quarantine_role = guild.get_role(QUARANTINE_ROLE_ID)
        to_remove = []

        for user_id_str, unq_time_str in self.active_quarantines.items():
            user_id = int(user_id_str)
            unq_time = datetime.fromisoformat(unq_time_str)
            if now >= unq_time:
                member = guild.get_member(user_id)
                if member and quarantine_role in member.roles:
                    try:
                        await member.remove_roles(quarantine_role, reason="Automatic quarantine expiry")
                    except Exception as e:
                        print(f"Error removing quarantine role from {member}: {e}")

                    log_entry = f"Automatic unquarantine for {member} (quarantine expired)."
                    log_to_file(log_entry, QUARANTINE_LOG_FILE)

                    log_channel = guild.get_channel(REPORT_LOG_CHANNEL_ID)
                    if log_channel:
                        embed = discord.Embed(
                            title="Quarantine Expired",
                            color=discord.Color.blue(),
                            timestamp=datetime.now(timezone.utc),
                        )
                        embed.add_field(name="User", value=member.mention)
                        embed.add_field(name="Reason", value="Quarantine time expired")
                        await log_channel.send(embed=embed)

                to_remove.append(user_id_str)

        for user_id_str in to_remove:
            self.active_quarantines.pop(user_id_str)
        if to_remove:
            save_json(QUARANTINE_DATA_FILE, self.active_quarantines)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle message filtering and report collection."""
        if message.author.bot:
            return

        content = clean_message_content(message.content)
        message.content = content

        for entry in self.regex_filters:
            if entry["enabled"]:
                try:
                    if re.search(entry["pattern"], content):
                        await message.delete()
                        try:
                            await message.author.send(
                                f"🚫 Your message was not allowed:\n`{content}`\n(Reason: Matches blocked pattern)"
                            )
                        except discord.Forbidden:
                            pass

                        log_channel = self.bot.get_channel(REPORT_LOG_CHANNEL_ID)
                        if log_channel:
                            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                            await log_channel.send(
                                f"🚨 **Blocked Message**\n"
                                f"**User:** {message.author.mention} (`{message.author.id}`)\n"
                                f"**Message:** `{content}`\n"
                                f"**Time:** {timestamp}"
                            )
                        return
                except re.error:
                    continue

        if isinstance(message.channel, discord.DMChannel):
            user_id = message.author.id
            if user_id in self.active_reports and not content.startswith("."):
                self.active_reports[user_id].append(content)
                return


async def setup(bot):
    await bot.add_cog(Moderation(bot))