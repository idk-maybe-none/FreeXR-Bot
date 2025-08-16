# FreeXR Bot
# Made with love by ilovecats4606 <3
BOTVERSION = "2.1.5"
DISABLED_IN_BETA = {"slowmode", "q", "uq"}
import discord
from discord.ext import commands
import asyncio
import json
from pathlib import Path
import re
import datetime
import os
import requests
import time
import platform
import sys
import tasklib
from discord.ext import tasks, commands
from discord.ext import commands
from datetime import datetime, timedelta
import git
from git import Repo
import argparse
parser = argparse.ArgumentParser(description="FreeXR Bot")
parser.add_argument("-t", "--token", type=str, help="Discord bot token")
args = parser.parse_args()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.dm_messages = True
intents.members = True
start_time = time.time()

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
                except Exception:
                    pass
        
def get_uptime():
    seconds = int(time.time() - start_time)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


bot = commands.Bot(command_prefix=".", intents=intents)

REPORT_LOG_CHANNEL_ID = 1361285583195869265
ADMIN_ROLE_ID = 1376159693021646900
QUARANTINE_ROLE_ID = 1373608273306976276

if args.token:
    TOKEN = args.token
else:
    with open("token", "r") as file:
        TOKEN = file.read().strip()

# In-memory report buffer per user
active_reports = {}
regex_filters = []

COUNT_FILE = "count_data.json"

IS_BETA = "b" in BOTVERSION.lower()

def load_count_data():
    if not os.path.exists(COUNT_FILE):
        return {"current_count": 0, "last_counter_id": None}
    with open(COUNT_FILE, "r") as f:
        return json.load(f)


def save_count_data(data):
    with open(COUNT_FILE, "w") as f:
        json.dump(data, f)


# JSON file path
REPORTS_FILE = Path("reports.json")


# Load/save report mapping
def load_reports():
    if REPORTS_FILE.exists():
        with open(REPORTS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_reports(data):
    with open(REPORTS_FILE, "w") as f:
        json.dump(data, f, indent=4)


report_log_map = load_reports()

FILTER_FILE = "filters.json"

REPO_URL = "https://github.com/FreeXR/FreeXR-Bot.git"
REPO_DIR = "FreeXR-Bot"
REPLIES_DIR = os.path.join(REPO_DIR, "quick_replies")

DEVICES_FILE = "devices.json"


def load_replies():
    replies = {}
    if not os.path.exists(REPLIES_DIR):
        return replies
    for filename in os.listdir(REPLIES_DIR):
        if filename.endswith(".md"):
            filepath = os.path.join(REPLIES_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().split("---")
                if len(content) >= 2:
                    summary_line = content[0].strip().splitlines()[0]
                    reply_text = content[1].strip()
                    command_name = filename[:-3]  # remove .md
                    replies[command_name] = (summary_line, reply_text)
    return replies


# Initial load
replies = load_replies()


# Load regex filters from file
def load_filters():
    if os.path.exists(FILTER_FILE):
        with open(FILTER_FILE, "r") as f:
            return json.load(f)
    return []


# Save regex filters to file
def save_filters():
    with open(FILTER_FILE, "w") as f:
        json.dump(regex_filters, f, indent=2)


regex_filters = load_filters()

def load_devices():
    if os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_devices(devices):
    with open(DEVICES_FILE, "w", encoding="utf-8") as f:
        json.dump(devices, f, indent=2)

devices_data = load_devices()

BACKUP_FILE = "message_backups.json"
if os.path.exists(BACKUP_FILE):
    with open(BACKUP_FILE, "r") as f:
        message_backups = json.load(f)
else:
    message_backups = {}


def save_backups():
    with open(BACKUP_FILE, "w") as f:
        json.dump(message_backups, f, indent=2)


@bot.event
async def on_ready():
    await bot.tree.sync()
    sys.stdout = DiscordConsoleLogger(bot, 1376528272204103721)
    sys.stderr = sys.stdout
    print(f"Logged in as {bot.user}")
    os_info = platform.system()
    release = platform.release()
    architecture = platform.machine()
    python_version = platform.python_version()
    uptime = get_uptime()

    env_message = (
        f"✅ Bot is running in **{os_info} {release} ({architecture})** environment "
        f"with **Python {python_version}**\n"
        f"🛠 Version: **{BOTVERSION}**\n"
        f"⏱ Load time: **{uptime}**"
    )
    if "b" in BOTVERSION.lower():
        env_message += "\n⚠️ Beta version detected – may be unstable! Potentially destructive commands have been disabled."
    channel = bot.get_channel(1376528272204103721)
    await channel.send(env_message)

    print(env_message)
    load_quarantine_data()
    # On startup, verify all quarantined users still have role, otherwise cleanup
    guild = bot.guilds[0]
    quarantine_role = guild.get_role(QUARANTINE_ROLE_ID)
    to_remove = []
    for user_id_str, unq_time_str in active_quarantines.items():
        user_id = int(user_id_str)
        member = guild.get_member(user_id)
        unq_time = datetime.fromisoformat(unq_time_str)
        if member is None:
            # Member not found in guild, remove from active
            to_remove.append(user_id_str)
            continue
        if quarantine_role not in member.roles:
            # Role missing, remove from active (maybe manually removed)
            to_remove.append(user_id_str)
    for user_id_str in to_remove:
        active_quarantines.pop(user_id_str)
    save_quarantine_data()

    check_quarantine_expiry.start()

@bot.event
async def on_member_join(member):
    welcome_channel_id = 1348562119469305958
    
    try:
        await member.add_roles(member.guild.get_role(1406195112714829899))
    except discord.Forbidden:
        print(f"Couldn't add role to {member} (permissions issue)")
        
    try:
        await member.send(
            "# 👋 Welcome to the server!\n Hello and welcome to FreeXR. We hack headsets to root them and unlock their bootloaders, and we appreciate you for joining. To get started, please read the https://discord.com/channels/1344235945238593547/1364918149404688454.\nWe hope you have a great stay here, and thank you for joining."
        )
    except discord.Forbidden:
        channel = member.guild.get_channel(welcome_channel_id)
        if channel:
            msg = await channel.send(
                f"{member.mention} 👋 Welcome to the server! Please read the https://discord.com/channels/1344235945238593547/1364918149404688454, and we hope you have a great stay here!.\n-# Psst! Your DMs are closed, so I couldn't send you a DM."
            )


RAW_URL = "https://raw.githubusercontent.com/FreeXR/FreeXR-Bot/refs/heads/main/app.py"
LOCAL_PATH = "/home/freexr/app.py"


@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def update(ctx):
    """
    Updates the bot by pulling the latest code from the repository and restarting.
    """
    await ctx.send("📥 Downloading latest version of `app.py`...")

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


@bot.hybrid_command()
async def role(ctx, role_id: int, user_id: int):
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


@bot.hybrid_command()
async def pin(ctx):
    """ 
    Pins a message that you reply to.
    Anyone can use this command.
    """
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


@bot.hybrid_command()
async def unpin(ctx):
    """ 
    Unpins a message that you reply to.
    Anyone can use this command.
    """
    if not ctx.message.reference:
        await ctx.send("Please reply to the message you want to unpin.")
        return

    try:
        msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        await msg.unpin()
        await ctx.send("📍 Message unpinned.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to unpin messages in this channel.")
    except discord.HTTPException as e:
        await ctx.send(f"Failed to unpin message: {e}")


@bot.hybrid_command()
async def report(ctx):
    """ 
    Starts a report in DMs.
    Only works in DMs.
    """
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please DM me this command.")
        return

    await ctx.send(
        "You're reporting to the server admins. All messages from this point will be recorded.\n"
        "Please state your issue. Upload images as links (attachments won't work).\n"
        "When you're finished, type `.iamdone`. Messages will stop being recorded."
    )
    active_reports[ctx.author.id] = []


@bot.tree.context_menu(name="Add to report")
async def add_to_report(interaction: discord.Interaction, message: discord.Message):
    user_id = interaction.user.id

    # Not in report
    if user_id not in active_reports:
        await interaction.response.send_message(
            "❌ You don't have an active report. Please start one by DMing me `.report`.",
            ephemeral=True,
        )
        return

    # Prepare the message info
    content = f"**Message from {message.author} in <#{message.channel.id}>:**\n{message.content}"
    active_reports[user_id].append(content)

    # Backup
    backup_entry = {
        "author": str(message.author),
        "channel_id": message.channel.id,
        "message_id": message.id,
        "content": message.content,
        "timestamp": str(message.created_at),
        "jump_url": message.jump_url,
    }
    if str(user_id) not in message_backups:
        message_backups[str(user_id)] = []
    message_backups[str(user_id)].append(backup_entry)
    save_backups()

    await interaction.response.send_message(
        "✅ Message added to your report.", ephemeral=True
    )


@bot.hybrid_command()
async def iamdone(ctx):
    """
    Ends the report and sends it to the admins.
    Only works in DMs.
    """
    if not isinstance(ctx.channel, discord.DMChannel):
        return

    user_id = ctx.author.id
    if user_id not in active_reports or not active_reports[user_id]:
        await ctx.send(
            "No messages recorded or you haven't started a report with `.report`."
        )
        return

    channel = bot.get_channel(REPORT_LOG_CHANNEL_ID)
    report_content = "\n".join(active_reports[user_id])
    extra = ""
    if str(user_id) in message_backups:
        extra += "\n\n**Attached messages:**\n"
        for entry in message_backups[str(user_id)]:
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

    report_log_map[str(report_message.id)] = user_id
    save_reports(report_log_map)

    await ctx.send("Thank you! Your report has been sent.")

    # Clear user's report data
    active_reports[user_id] = []
    if str(user_id) in message_backups:
        del message_backups[str(user_id)]
        save_backups()


@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def resolve(ctx, msg_id: int = None):
    """ 
    Marks a report as resolved.
    Only admins can use this command.
    Reply to a report message or provide its ID.
    """
    # Try to get message ID from reply if not given
    if not msg_id and ctx.message.reference:
        msg_id = ctx.message.reference.message_id

    if not msg_id:
        await ctx.send("Please reply to a report or provide a message ID.")
        return

    report_id = str(msg_id)

    if report_id in report_log_map:
        del report_log_map[report_id]
        save_reports(report_log_map)

        try:
            msg = await ctx.channel.fetch_message(msg_id)
            await msg.reply("✅ Marked as resolved. Further interaction closed.")
        except discord.NotFound:
            await ctx.send(
                "Marked as resolved, but couldn't find the original message."
            )

    else:
        await ctx.send("That message isn't tracked as an active report.")


@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def createchannel(ctx, msg_id: int = None):
    """ 
    Creates a private channel for a report.
    Only admins can use this command.
    Reply to a report message or provide its ID.
    """
    # Fallback to reply if no ID provided
    if not msg_id and ctx.message.reference:
        msg_id = ctx.message.reference.message_id

    embed = None
    if msg_id:
        try:
            log_channel = bot.get_channel(REPORT_LOG_CHANNEL_ID)
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
        name_msg = await bot.wait_for("message", check=check, timeout=60)
        guild = ctx.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(
                read_messages=True
            ),
        }
        channel = await guild.create_text_channel(
            name=name_msg.content, overwrites=overwrites
        )
        await ctx.send(f"Created channel: {channel.mention}")

        if embed:
            await channel.send("Report linked to this channel:", embed=embed)

    except asyncio.TimeoutError:
        await ctx.send("Timed out.")
    except Exception as e:
        await ctx.send(f"Failed to create channel: {e}")


@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def createchannelp(ctx, msg_id: int = None):
    """ 
    Creates a private channel for a report with the original reporter.
    Only admins can use this command.
    Reply to a report message or provide its ID.
    """
    if not msg_id and ctx.message.reference:
        msg_id = ctx.message.reference.message_id

    if not msg_id:
        await ctx.send("Please reply to a report or provide a message ID.")
        return

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
        name_msg = await bot.wait_for("message", check=check, timeout=60)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(
                read_messages=True
            ),
            member: discord.PermissionOverwrite(read_messages=True),
        }
        channel = await guild.create_text_channel(
            name=name_msg.content, overwrites=overwrites
        )
        await ctx.send(
            f"Created private channel: {channel.mention} with access to {member.mention} given."
        )
    except asyncio.TimeoutError:
        await ctx.send("Timed out.")
    except Exception as e:
        await ctx.send(f"Failed to create channel: {e}")


@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def listreport(ctx):
    """ 
    Lists all active reports.
    Only admins can use this command.
    """
    if not report_log_map:
        await ctx.send("No reports found.")
        return

    log_channel = bot.get_channel(REPORT_LOG_CHANNEL_ID)
    report_lines = []

    for i, (msg_id, user_id) in enumerate(report_log_map.items()):
        try:
            msg = await log_channel.fetch_message(int(msg_id))
            title = msg.embeds[0].title if msg.embeds else "No Title"
            report_lines.append(f"{i+1}. {title} (ID: {msg.id})")
        except discord.NotFound:
            report_lines.append(f"{i+1}. [Message not found] (ID: {msg_id})")

    if report_lines:
        await ctx.send("**Active Reports:**\n" + "\n".join(report_lines))
    else:
        await ctx.send("No valid report messages found.")


def is_admin(member):
    return any(role.id == ADMIN_ROLE_ID for role in member.roles)


@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def block(ctx):
    """ 
    Blocks a regex pattern from being sent in the server.
    Only admins can use this command.
    """
    # Only allow modal for slash commands
    if ctx.interaction:
        class RegexModal(discord.ui.Modal, title="Block Regex Pattern"):
            pattern = discord.ui.TextInput(label="Regex Pattern", required=True)

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    re.compile(self.pattern.value)  # Validate regex
                    regex_filters.append({"pattern": self.pattern.value, "enabled": True})
                    save_filters()
                    await interaction.response.send_message(f"Blocked regex added: `{self.pattern.value}`", ephemeral=True)
                except re.error:
                    await interaction.response.send_message("Invalid regex pattern.", ephemeral=True)

        await ctx.interaction.response.send_modal(RegexModal())
    else:
        await ctx.send("Please use the `/block` slash command to add a regex pattern.")



@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def listregex(ctx):
    """ 
    Lists all blocked regex patterns.
    Only admins can use this command.
    """
    if not regex_filters:
        return await ctx.send("No regex patterns are currently blocked.")

    message = "Blocked Regex Patterns:\n"
    for i, entry in enumerate(regex_filters):
        message += f"{i}. `{entry['pattern']}` - {'✅ Enabled' if entry['enabled'] else '❌ Disabled'}\n"
    message += "\nUse `.toggle <index>` to enable/disable a regex."
    await ctx.send(message)


def get_user_id(ctx, user_str):
    if user_str.isdigit():
        return int(user_str)
    if user_str.startswith("<@") and user_str.endswith(">"):
        return int(user_str.strip("<@!>"))
    member = ctx.guild.get_member_named(user_str)
    if member:
        return member.id
    return None

@bot.hybrid_command(name="devices")
async def devices_cmd(ctx, user: discord.User = None):
    """
    Lists your devices or another user's devices.
    Usage: .devices [@user]
    """
    user_id = user.id if user else ctx.author.id
    user_devices = devices_data.get(str(user_id), [])
    if not user_devices:
        await ctx.send("No devices found for this user.")
        return
    msg = f"Devices for <@{user_id}>:\n"
    for idx, device in enumerate(user_devices, 1):
        msg += f"**{idx}.** {device['Name']} (`{device['Codename']}`)\n"
    await ctx.send(msg)

@bot.hybrid_command(name="deviceinfo")
async def devicelist_cmd(ctx, user: discord.User, device_id: int):
    """
    Shows info for a specific device.
    Usage: .devicelist @user <device_id>
    """
    user_id = user.id
    user_devices = devices_data.get(str(user_id), [])
    if 1 <= device_id <= len(user_devices):
        device = user_devices[device_id - 1]
        cocaine_trade_status = "N/A"
        if device.get("Model", "").lower() == "eureka":
            try:
                resp = requests.get("https://cocaine.trade/Quest_3_firmware", timeout=10)
                if resp.ok:
                    if device.get("Build Version", "") in resp.text:
                        cocaine_trade_status = "True"
                    else:
                        cocaine_trade_status = "False"
                else:
                    cocaine_trade_status = "Unknown (site error)"
            except Exception:
                cocaine_trade_status = "Unknown (request failed)"
        msg = (
            f"**Device {device_id} for <@{user_id}>:**\n"
            f"**Name:** {device.get('Name','')}\n"
            f"**Model:** {device.get('Model','')}\n"
            f"**Security Patch:** {device.get('Security Patch','')}\n"
            f"**Build Version:** {device.get('Build Version','')}\n"
            f"**Version on cocaine.trade:** {cocaine_trade_status}\n"
            f"**Vulnerable to:** None"
        )
        await ctx.send(msg)
    else:
        await ctx.send("Device not found for this user.")

@bot.hybrid_command(name="deviceadd")
async def deviceadd_cmd(ctx):
    """
    Add a device using a Discord modal.
    Don't know why I made this command.
    """
# Sanitize input to remove @ symbols and escape markdown
    def sanitize_input(value: str) -> str:
        cleaned = value.strip().replace("@", "")  # Prevent mentions
        return discord.utils.escape_markdown(cleaned)

    class DeviceModal(discord.ui.Modal, title="Add Device"):
        name = discord.ui.TextInput(label="Name", required=True)
        model = discord.ui.TextInput(label="Model", required=True)
        patch = discord.ui.TextInput(label="Security Patch", required=True)
        build = discord.ui.TextInput(label="Build Version", required=True)

        async def on_submit(self, interaction: discord.Interaction):
            errors = []

            # Check for @
            if "@" in self.name.value:
                errors.append("**Name** cannot contain `@` symbols.")
            if "@" in self.model.value:
                errors.append("**Model** cannot contain `@` symbols.")
            if "@" in self.patch.value:
                errors.append("**Security Patch** cannot contain `@` symbols.")
            if "@" in self.build.value:
                errors.append("**Build Version** cannot contain `@` symbols.")

            # Validate Build Version: must be a 17 digit number
            build_value = self.build.value.strip()
            if not (build_value.isdigit() and len(build_value) == 17):
                errors.append("**Build Version** must be a 17-digit number (from `adb shell getprop ro.build.version.incremental`).")

            # Validate Security Patch: must be YYYY-MM-DD
            patch_value = self.patch.value.strip()
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", patch_value):
                errors.append("**Security Patch** must be a date in YYYY-MM-DD format (from `adb shell getprop ro.build.version.security_patch`).")

            if errors:
                await interaction.response.send_message(
                    "❌ There were errors with your input:\n" + "\n".join(errors),
                    ephemeral=True
                )
                return

            user_id = str(interaction.user.id)
            device = {
                "Name": self.name.value.strip(),
                "Model": self.model.value.strip(),
                "Security Patch": patch_value,
                "Build Version": build_value,
            }
            devices_data.setdefault(user_id, []).append(device)
            save_devices(devices_data)

            await interaction.response.send_message("✅ Device added!", ephemeral=True)

    # Use the interaction to send the modal
    if ctx.interaction:
        await ctx.interaction.response.send_modal(DeviceModal())
    else:
        await ctx.send("This command must be used as a slash command.")


@bot.hybrid_command(name="deviceremove")
async def deviceremove_cmd(ctx, device_id: int):
    """
    Remove one of your devices by its ID.
    Usage: .deviceremove <device_id>
    """
    user_id = str(ctx.author.id)
    user_devices = devices_data.get(user_id, [])
    if 1 <= device_id <= len(user_devices):
        removed = user_devices.pop(device_id - 1)
        save_devices(devices_data)
        await ctx.send(f"Removed device: {removed['Name']} (`{removed['Codename']}`)")
    else:
        await ctx.send("Device not found.")

@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def toggle(ctx, index: int):
    """ 
    Toggles a regex pattern.
    Only admins can use this command.
    """
    real_index = index - 1  # User sees 1-based, code uses 0-based
    if 0 <= real_index < len(regex_filters):
        regex_filters[real_index]["enabled"] = not regex_filters[real_index]["enabled"]
        save_filters()
        await ctx.send(
            f"Toggled regex `{regex_filters[real_index]['pattern']}` to {'enabled' if regex_filters[real_index]['enabled'] else 'disabled'}."
        )
    else:
        await ctx.send("Invalid index. Use the number shown in `.listregex`.")


@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def unblock(ctx):
    """ 
    Unblocks a regex pattern.
    Only admins can use this command.
    """
    if not regex_filters:
        return await ctx.send("No regex patterns to remove.")

    await ctx.send("Please enter the index of the regex to remove (as shown in `.listregex`):")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        index = int(msg.content)
        real_index = index - 1  # User sees 1-based, code uses 0-based
        removed = regex_filters.pop(real_index)
        save_filters()
        await ctx.send(f"Removed regex `{removed['pattern']}`")
    except (ValueError, IndexError):
        await ctx.send("Invalid index.")
    except TimeoutError:
        await ctx.send("Timeout. Please try again.")


@bot.hybrid_command()
async def status(ctx):
    """ 
    Displays the bot's status and environment information.
    """
    os_info = platform.system()
    release = platform.release()
    architecture = platform.machine()
    python_version = platform.python_version()
    uptime = get_uptime()

    env_message = (
        f"✅ Bot is running in **{os_info} {release} ({architecture})** environment "
        f"with **Python {python_version}**\n"
        f"🛠 Version: **{BOTVERSION}**\n"
        f"⏱ Uptime: **{uptime}**"
    )
    if "b" in BOTVERSION.lower():
        env_message += "\n⚠️ Beta version detected – may be unstable! Potentially destructive commands have been disabled."
    await ctx.send(env_message)


@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def slowmode(ctx, seconds: int):
    """ 
    Sets the slowmode for the current channel.
    Only admins can use this command.
    """
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"This channel now has a slowmode of {seconds} seconds!")


# File to store quarantine data persistently
QUARANTINE_DATA_FILE = "quarantine_data.json"
LOG_FILE = "quarantine_log.txt"

# Active quarantines dictionary: user_id -> unquarantine timestamp ISO string
active_quarantines = {}


def log_to_file(entry: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} - {entry}\n")


def save_quarantine_data():
    with open(QUARANTINE_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(active_quarantines, f)


def load_quarantine_data():
    global active_quarantines
    if os.path.exists(QUARANTINE_DATA_FILE):
        with open(QUARANTINE_DATA_FILE, "r", encoding="utf-8") as f:
            active_quarantines = json.load(f)
    else:
        active_quarantines = {}


def is_admin_quarantine():
    def predicate(ctx):
        return any(role.id == ADMIN_ROLE_ID for role in ctx.author.roles)

    return commands.check(predicate)


@bot.hybrid_command()
@is_admin_quarantine()
async def q(
    ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"
):
    """
    Quarantine a member for a duration (e.g. 10m, 1h, 1d).
    """
    quarantine_role = ctx.guild.get_role(QUARANTINE_ROLE_ID)
    if quarantine_role in member.roles:
        await ctx.send(f"{member.display_name} is already quarantined.")
        return

    # Parse duration
    try:
        amount = int(duration[:-1])
        unit = duration[-1].lower()
        if unit == "m":
            delta = timedelta(minutes=amount)
        elif unit == "h":
            delta = timedelta(hours=amount)
        elif unit == "d":
            delta = timedelta(days=amount)
        else:
            await ctx.send(
                "Invalid duration format. Use m (minutes), h (hours), or d (days)."
            )
            return
    except Exception as e:
        await ctx.send(
            f"Invalid duration format. Use m (minutes), h (hours), or d (days). Example: 10m, 1h, 2d {e}"
        )
        return

    await member.add_roles(
        quarantine_role, reason=f"Quarantine by {ctx.author} for {reason}"
    )
    unquarantine_time = datetime.utcnow() + delta
    active_quarantines[str(member.id)] = unquarantine_time.isoformat()
    save_quarantine_data()

    await ctx.send(
        f"{member.display_name} has been quarantined for {duration}. Reason: {reason}"
    )

    log_entry = f"{ctx.author} quarantined {member} for {duration}. Reason: {reason}"
    log_to_file(log_entry)

    log_channel = ctx.guild.get_channel(REPORT_LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="User Quarantined",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="By", value=ctx.author.mention, inline=True)
        embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await log_channel.send(embed=embed)


@bot.hybrid_command()
@is_admin_quarantine()
async def uq(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """
    Unquarantine a member immediately.
    """
    quarantine_role = ctx.guild.get_role(QUARANTINE_ROLE_ID)
    if quarantine_role not in member.roles:
        await ctx.send(f"{member.display_name} is not quarantined.")
        return

    await member.remove_roles(
        quarantine_role, reason=f"Unquarantined by {ctx.author} for {reason}"
    )
    active_quarantines.pop(str(member.id), None)
    save_quarantine_data()

    await ctx.send(f"{member.display_name} has been unquarantined. Reason: {reason}")

    log_entry = f"{ctx.author} unquarantined {member}. Reason: {reason}"
    log_to_file(log_entry)

    log_channel = ctx.guild.get_channel(REPORT_LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="User Unquarantined",
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="By", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await log_channel.send(embed=embed)


@tasks.loop(seconds=60)
async def check_quarantine_expiry():
    now = datetime.utcnow()
    guild = bot.guilds[0]
    quarantine_role = guild.get_role(QUARANTINE_ROLE_ID)
    to_remove = []

    for user_id_str, unq_time_str in active_quarantines.items():
        user_id = int(user_id_str)
        unq_time = datetime.fromisoformat(unq_time_str)
        if now >= unq_time:
            member = guild.get_member(user_id)
            if member and quarantine_role in member.roles:
                try:
                    await member.remove_roles(
                        quarantine_role, reason="Automatic quarantine expiry"
                    )
                except Exception as e:
                    print(f"Error removing quarantine role from {member}: {e}")

                log_entry = f"Automatic unquarantine for {member} (quarantine expired)."
                log_to_file(log_entry)

                log_channel = guild.get_channel(REPORT_LOG_CHANNEL_ID)
                if log_channel:
                    embed = discord.Embed(
                        title="Quarantine Expired",
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow(),
                    )
                    embed.add_field(name="User", value=member.mention)
                    embed.add_field(name="Reason", value="Quarantine time expired")
                    await log_channel.send(embed=embed)

            to_remove.append(user_id_str)

    for user_id_str in to_remove:
        active_quarantines.pop(user_id_str)
    if to_remove:
        save_quarantine_data()


@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def hotupdate(ctx):
    """
    Pulls everything from the repository, but does not restart the bot.
    """
    global replies
    try:
        await ctx.send("📥 Pulling everything from the repository...")
        if os.path.exists(REPO_DIR):
            repo = Repo(REPO_DIR)
            repo.remotes.origin.pull()
        else:
            Repo.clone_from(REPO_URL, REPO_DIR)
        replies = load_replies()
        await ctx.send("✅ Hot update complete.")
    except Exception as e:
        await ctx.send(f"❌ Hot update failed:\n```{e}```")


@bot.hybrid_command()
async def ratelimitcheck(ctx):
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


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    invisible_chars = ["\u200b", "\u200c", "\u200d", "\u200e", "\u200f"]
    content = message.content
    for ch in invisible_chars:
        content = content.replace(ch, "")
    content = content.strip()
    message.content = content  # Update message for command processing later

    for entry in regex_filters:
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

                    log_channel = bot.get_channel(REPORT_LOG_CHANNEL_ID)
                    if log_channel:
                        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                        await log_channel.send(
                            f"🚨 **Blocked Message**\n"
                            f"**User:** {message.author.mention} (`{message.author.id}`)\n"
                            f"**Message:** `{content}`\n"
                            f"**Time:** {timestamp}"
                        )
                    return
            except re.error:
                continue

    if message.channel.id == 1374296035798814804:
        data = load_count_data()
        current_count = data["current_count"]
        last_counter_id = data["last_counter_id"]

        if content.isdigit() and "\n" not in content:
            number = int(content)
            if number == current_count + 1 and message.author.id != last_counter_id:
                # Valid message
                data["current_count"] = number
                data["last_counter_id"] = message.author.id
                save_count_data(data)
                return
            else:
                reason = (
                    "Double message"
                    if message.author.id == last_counter_id
                    else "Incorrect number"
                )
        else:
            reason = "Invalid message format"

        data["current_count"] = 0
        data["last_counter_id"] = None
        save_count_data(data)

        await message.delete()
        countreport = bot.get_channel(1348562119469305958)
        count = bot.get_channel(1374296035798814804)
        if countreport:
            await countreport.send(
                f"⚠️ <@{message.author.id}> broke the counting streak in <#{message.channel.id}>! ({reason})"
            )
            await count.send("Streak has been broken! Start from 1.")
        return

    if content.startswith("."):
        cmd = content[1:]
        if cmd in replies:
            await message.channel.send(replies[cmd][1])
            return


    if isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id
        if user_id in active_reports and not content.startswith("."):
            active_reports[user_id].append(content)
            return

    await bot.process_commands(message)



@bot.hybrid_command()
@commands.has_role(ADMIN_ROLE_ID)
async def reboot(ctx):
    """
    Reboots the bot.
    Only admins can use this command.
    """
    await ctx.send("🔂 Rebooting bot...")
    python = sys.executable
    os.execv(python, [python] + sys.argv)


@bot.hybrid_command()
async def streak(ctx):
    """
    Displays the current counting streak.
    """
    data = load_count_data()
    await ctx.send(f"The current counting streak is **{data['current_count']}**.")

@bot.hybrid_command(name="replies")
async def replies_command(ctx):
    """Lists all available quick replies."""
    if not replies:
        await ctx.send("⚠️ No replies available.")
    response = "\n".join([f"* {key}: {val[0]}" for key, val in replies.items()])
    await ctx.send(f"```\n{response}\n```")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        print(f"Ignoring exception: CommandNotFound: '{ctx.message.content}'")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    elif isinstance(error, commands.MissingRole):
        await ctx.send(f"{ctx.author.mention}❌ You are not authorized to use this command.")
    else:
        print(f"Unhandled command error: {error}")
        
async def main():
    try:
        await bot.start(TOKEN)
    except discord.HTTPException as e:
        if e.status == 429:
            print(f"Startup failed: Rate limited. Retry after {e.retry_after} seconds.")
        else:
            print(f"Startup failed with HTTP error: {e}")
    except Exception as e:
        print(f"Startup failed with unexpected error: {e}")

if IS_BETA:
    for name in DISABLED_IN_BETA:
        if name in bot.all_commands:
            bot.remove_command(name)
asyncio.run(main())
