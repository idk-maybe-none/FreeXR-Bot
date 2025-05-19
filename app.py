# FreeXR Bot
# Made with love by ilovecats4606 <3
BOTVERSION = "1.0.2"
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

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.dm_messages = True
intents.members = True
start_time = time.time()

def get_uptime():
    seconds = int(time.time() - start_time)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"
bot = commands.Bot(command_prefix='.', intents=intents)

REPORT_LOG_CHANNEL_ID = 1361285583195869265
ADMIN_ROLE_ID = 1361291689683321004

with open("token", "r") as file:
    TOKEN = file.read().strip()
    
# In-memory report buffer per user
active_reports = {}
regex_filters = []

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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    os_info = platform.system()
    release = platform.release()
    architecture = platform.machine()
    python_version = platform.python_version()
    uptime = get_uptime()

    env_message = (f"✅ Bot is running in **{os_info} {release} ({architecture})** environment "
                   f"with **Python {python_version}**\n"
                   f"🛠 Version: **{BOTVERSION}**\n"
                   f"⏱ Load time: **{uptime}**")
    channel = bot.get_channel(1344235945674674258)
   	await channel.send(env_message)

    print(env_message)
RAW_URL = "https://raw.githubusercontent.com/FreeXR/FreeXR-Bot/refs/heads/main/app.py"
LOCAL_PATH = "/home/container/app.py" 

@bot.command()
async def update(ctx):
    if not is_admin(ctx.author):
        return await ctx.send("❌ You are not authorized to update the bot.")

    await ctx.send("📥 Downloading latest version of `app.py`...")

    try:
        response = requests.get(RAW_URL)
        response.raise_for_status()

        with open(LOCAL_PATH, "w", encoding="utf-8") as f:
            f.write(response.text)

        await ctx.send("✅ Update complete. Restarting bot...")

        # Restart the bot
        python = sys.executable
        os.execv(python, [python] + sys.argv)

    except Exception as e:
        await ctx.send(f"❌ Update failed:\n```{e}```")
   
@bot.command()
async def role(ctx, role_id: int, user_id: int):
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
@bot.command()
async def pin(ctx):
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

@bot.command()
async def unpin(ctx):
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

@bot.command()
async def report(ctx):
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Please DM me this command.")
        return

    await ctx.send(
        "You're reporting to the server admins.\n"
        "Please state your issue. Upload images as links (attachments won't work).\n"
        "When you're finished, type `.iamdone`."
    )
    active_reports[ctx.author.id] = []

@bot.command()
async def iamdone(ctx):
    if not isinstance(ctx.channel, discord.DMChannel):
        return

    user_id = ctx.author.id
    if user_id not in active_reports or not active_reports[user_id]:
        await ctx.send("No messages recorded or you haven't started a report with `.report`.")
        return

    channel = bot.get_channel(REPORT_LOG_CHANNEL_ID)
    report_content = "\n".join(active_reports[user_id])
    embed = discord.Embed(title="New Report", description=report_content, color=discord.Color.orange())
    embed.set_author(name=f"{ctx.author}", icon_url=ctx.author.display_avatar.url)

    report_message = await channel.send(embed=embed)

    # Save report to JSON
    report_log_map[str(report_message.id)] = user_id
    save_reports(report_log_map)

    await ctx.send("Thank you! Your report has been sent.")
    active_reports[user_id] = []


@bot.command()
@commands.has_role(ADMIN_ROLE_ID)
async def resolve(ctx, msg_id: int = None):
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
            await ctx.send("Marked as resolved, but couldn't find the original message.")

    else:
        await ctx.send("That message isn't tracked as an active report.")


@bot.command()
@commands.has_role(ADMIN_ROLE_ID)
async def createchannel(ctx, msg_id: int = None):
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
        name_msg = await bot.wait_for('message', check=check, timeout=60)
        guild = ctx.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True)
        }
        channel = await guild.create_text_channel(name=name_msg.content, overwrites=overwrites)
        await ctx.send(f"Created channel: {channel.mention}")

        if embed:
            await channel.send("Report linked to this channel:", embed=embed)

    except asyncio.TimeoutError:
        await ctx.send("Timed out.")
    except Exception as e:
        await ctx.send(f"Failed to create channel: {e}")


@bot.command()
@commands.has_role(ADMIN_ROLE_ID)
async def createchannelp(ctx, msg_id: int = None):
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
        name_msg = await bot.wait_for('message', check=check, timeout=60)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True),
            member: discord.PermissionOverwrite(read_messages=True)
        }
        channel = await guild.create_text_channel(name=name_msg.content, overwrites=overwrites)
        await ctx.send(f"Created private channel: {channel.mention} with access to {member.mention} given.")
    except asyncio.TimeoutError:
        await ctx.send("Timed out.")
    except Exception as e:
        await ctx.send(f"Failed to create channel: {e}")

@bot.command()
@commands.has_role(ADMIN_ROLE_ID)
async def listreport(ctx):
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

@bot.command()
async def block(ctx):
    if not is_admin(ctx.author):
        return await ctx.send("You don't have permission.")

    await ctx.send("Please enter the regex to block:")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        pattern = msg.content
        re.compile(pattern)  # Ensure it's valid
        regex_filters.append({"pattern": pattern, "enabled": True})
        save_filters()
        await ctx.send(f"Blocked regex added: `{pattern}`")
    except re.error:
        await ctx.send("Invalid regex pattern.")
    except TimeoutError:
        await ctx.send("Timeout. Please try again.")

@bot.command()
async def listregex(ctx):
    if not is_admin(ctx.author):
        return await ctx.send("You don't have permission.")

    if not regex_filters:
        return await ctx.send("No regex patterns are currently blocked.")

    message = "Blocked Regex Patterns:\n"
    for i, entry in enumerate(regex_filters):
        message += f"{i}. `{entry['pattern']}` - {'✅ Enabled' if entry['enabled'] else '❌ Disabled'}\n"
    message += "\nUse `.toggle <index>` to enable/disable a regex."
    await ctx.send(message)

@bot.command()
async def toggle(ctx, index: int):
    if not is_admin(ctx.author):
        return await ctx.send("You don't have permission.")

    if 0 <= index < len(regex_filters):
        regex_filters[index]['enabled'] = not regex_filters[index]['enabled']
        save_filters()
        await ctx.send(f"Toggled regex `{regex_filters[index]['pattern']}` to {'enabled' if regex_filters[index]['enabled'] else 'disabled'}.")
    else:
        await ctx.send("Invalid index.")

@bot.command()
async def unblock(ctx):
    if not is_admin(ctx.author):
        return await ctx.send("You don't have permission.")

    if not regex_filters:
        return await ctx.send("No regex patterns to remove.")

    await ctx.send("Please enter the index of the regex to remove:")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        index = int(msg.content)
        removed = regex_filters.pop(index)
        save_filters()
        await ctx.send(f"Removed regex `{removed['pattern']}`")
    except (ValueError, IndexError):
        await ctx.send("Invalid index.")
    except TimeoutError:
        await ctx.send("Timeout. Please try again.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Regex filter check
    for entry in regex_filters:
        if entry['enabled']:
            try:
                if re.search(entry['pattern'], message.content):
                    await message.delete()
                    try:
                        await message.author.send(
                            f"🚫 Your message was not allowed:\n`{message.content}`\n(Reason: Matches blocked pattern)"
                        )
                    except discord.Forbidden:
                        pass

                    log_channel = bot.get_channel(REPORT_LOG_CHANNEL_ID)
                    if log_channel:
                        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                        await log_channel.send(
                            f"🚨 **Blocked Message**\n"
                            f"**User:** {message.author.mention} (`{message.author.id}`)\n"
                            f"**Message:** `{message.content}`\n"
                            f"**Time:** {timestamp}"
                        )
                    return
            except re.error:
                continue

    # DM report tracking
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id in active_reports:
            active_reports[message.author.id].append(message.content)

    await bot.process_commands(message)
    
@bot.command()
async def status(ctx):
    os_info = platform.system()
    release = platform.release()
    architecture = platform.machine()
    python_version = platform.python_version()
    uptime = get_uptime()

    env_message = (f"✅ Bot is running in **{os_info} {release} ({architecture})** environment "
                   f"with **Python {python_version}**\n"
                   f"🛠 Version: **{BOTVERSION}**\n"
                   f"⏱ Uptime: **{uptime}**")

    await ctx.send(env_message)


bot.run(TOKEN)
