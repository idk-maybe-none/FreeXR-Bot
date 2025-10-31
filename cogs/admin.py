import discord
from discord.ext import commands
from config import ADMIN_ROLE_ID
import asyncio


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def slowmode(self, ctx, seconds: int):
        """Sets the slowmode for the current channel."""
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"This channel now has a slowmode of {seconds} seconds!")

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def resolve(self, ctx, msg_id: int = None):
        """Marks a report as resolved."""
        if not msg_id and ctx.message.reference:
            msg_id = ctx.message.reference.message_id

        if not msg_id:
            await ctx.send("Please reply to a report or provide a message ID.")
            return

        from utils.file_handlers import load_json, save_json
        from config import REPORTS_FILE

        report_log_map = load_json(REPORTS_FILE, {})
        report_id = str(msg_id)

        if report_id in report_log_map:
            del report_log_map[report_id]
            save_json(REPORTS_FILE, report_log_map)

            try:
                msg = await ctx.channel.fetch_message(msg_id)
                await msg.reply("✅ Marked as resolved. Further interaction closed.")
            except discord.NotFound:
                await ctx.send("Marked as resolved, but couldn't find the original message.")
        else:
            await ctx.send("That message isn't tracked as an active report.")

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def createchannel(self, ctx, msg_id: int = None):
        """Creates a private channel for a report."""
        if not msg_id and ctx.message.reference:
            msg_id = ctx.message.reference.message_id

        embed = None
        if msg_id:
            try:
                from config import REPORT_LOG_CHANNEL_ID
                log_channel = self.bot.get_channel(REPORT_LOG_CHANNEL_ID)
                report_msg = await log_channel.fetch_message(msg_id)
                if report_msg.embeds:
                    embed = report_msg.embeds[0]
            except discord.NotFound:
                await ctx.send("Couldn't find the report message.")
                return
            except Exception as e:
                await ctx.send(f"Error fetching report: {e}")
                return

        await ctx.send("What should the channel be called?")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            name_msg = await self.bot.wait_for("message", check=check, timeout=60)
            guild = ctx.guild
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True),
            }
            channel = await guild.create_text_channel(name=name_msg.content, overwrites=overwrites)
            await ctx.send(f"Created channel: {channel.mention}")

            if embed:
                await channel.send("Report linked to this channel:", embed=embed)

        except asyncio.TimeoutError:
            await ctx.send("Timed out.")
        except Exception as e:
            await ctx.send(f"Failed to create channel: {e}")

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def createchannelp(self, ctx, msg_id: int = None):
        """Creates a private channel for a report with the original reporter."""
        if not msg_id and ctx.message.reference:
            msg_id = ctx.message.reference.message_id

        if not msg_id:
            await ctx.send("Please reply to a report or provide a message ID.")
            return

        from utils.file_handlers import load_json
        from config import REPORTS_FILE

        report_log_map = load_json(REPORTS_FILE, {})
        report_id = str(msg_id)

        if report_id not in report_log_map:
            await ctx.send("Couldn't find the original reporter for that ID.")
            return

        user_id = report_log_map[report_id]
        guild = ctx.guild
        member = guild.get_member(user_id)

        if not member:
            await ctx.send("The original reporter is not in this server.")
            return

        await ctx.send("What should the channel be called?")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            name_msg = await self.bot.wait_for("message", check=check, timeout=60)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True),
                member: discord.PermissionOverwrite(read_messages=True),
            }
            channel = await guild.create_text_channel(name=name_msg.content, overwrites=overwrites)
            await ctx.send(f"Created private channel: {channel.mention} with access to {member.mention} given.")
        except asyncio.TimeoutError:
            await ctx.send("Timed out.")
        except Exception as e:
            await ctx.send(f"Failed to create channel: {e}")

    @commands.hybrid_command()
    @commands.has_role(ADMIN_ROLE_ID)
    async def listreport(self, ctx):
        """Lists all active reports."""
        from utils.file_handlers import load_json
        from config import REPORTS_FILE, REPORT_LOG_CHANNEL_ID

        report_log_map = load_json(REPORTS_FILE, {})
        if not report_log_map:
            await ctx.send("No reports found.")
            return

        log_channel = self.bot.get_channel(REPORT_LOG_CHANNEL_ID)
        report_lines = []

        for i, (msg_id, user_id) in enumerate(report_log_map.items()):
            try:
                msg = await log_channel.fetch_message(int(msg_id))
                title = msg.embeds[0].title if msg.embeds else "No Title"
                report_lines.append(f"{i + 1}. {title} (ID: {msg.id})")
            except discord.NotFound:
                report_lines.append(f"{i + 1}. [Message not found] (ID: {msg_id})")

        if report_lines:
            await ctx.send("**Active Reports:**\n" + "\n".join(report_lines))
        else:
            await ctx.send("No valid report messages found.")

    @commands.hybrid_command()
    async def role(self, ctx, role_id: int, user_id: int):
        """
        Toggles a role for a user.
        Only the user with ID 981463678698266664 is authorized to use this command.
        """
        allowed_user_id = 981463678698266664

        if ctx.author.id != allowed_user_id:
            await ctx.send("❌ You are not authorized to use this command.")
            return

        guild = ctx.guild
        member = guild.get_member(user_id)
        role = guild.get_role(role_id)

        if not member:
            await ctx.send("❌ User not found.")
            return
        if not role:
            await ctx.send("❌ Role not found.")
            return

        try:
            if role in member.roles:
                await member.remove_roles(role)
                await ctx.send(f"✅ Removed role **{role.name}** from {member.mention}.")
            else:
                await member.add_roles(role)
                await ctx.send(f"✅ Added role **{role.name}** to {member.mention}.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage that role.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to modify role: {e}")


async def setup(bot):
    await bot.add_cog(Admin(bot))