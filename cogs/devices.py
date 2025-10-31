import discord
from discord.ext import commands
import requests
import re

from utils.file_handlers import load_json, save_json
from config import DEVICES_FILE


class Devices(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.devices_data = load_json(DEVICES_FILE, {})

    @commands.hybrid_command(name="devices")
    async def devices_cmd(self, ctx, user: discord.User = None):
        """Lists your devices or another user's devices."""
        user_id = user.id if user else ctx.author.id
        user_devices = self.devices_data.get(str(user_id), [])
        if not user_devices:
            await ctx.send("No devices found for this user.")
            return
        msg = f"Devices for <@{user_id}>:\n"
        for idx, device in enumerate(user_devices, 1):
            msg += f"**{idx}.** {device['Name']} (`{device.get('Codename', 'N/A')}`)\n"
        await ctx.send(msg)

    @commands.hybrid_command(name="deviceinfo")
    async def deviceinfo_cmd(self, ctx, user: discord.User, device_id: int):
        """Shows info for a specific device."""
        user_id = user.id
        user_devices = self.devices_data.get(str(user_id), [])
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
                f"**Name:** {device.get('Name', '')}\n"
                f"**Model:** {device.get('Model', '')}\n"
                f"**Security Patch:** {device.get('Security Patch', '')}\n"
                f"**Build Version:** {device.get('Build Version', '')}\n"
                f"**Version on cocaine.trade:** {cocaine_trade_status}\n"
                f"**Vulnerable to:** None"
            )
            await ctx.send(msg)
        else:
            await ctx.send("Device not found for this user.")

    @commands.hybrid_command(name="deviceadd")
    async def deviceadd_cmd(self, ctx):
        """Add a device using a Discord modal."""

        class DeviceModal(discord.ui.Modal, title="Add Device"):
            name = discord.ui.TextInput(label="Name", required=True)
            model = discord.ui.TextInput(label="Model", required=True)
            patch = discord.ui.TextInput(label="Security Patch", required=True)
            build = discord.ui.TextInput(label="Build Version", required=True)

            async def on_submit(self, interaction: discord.Interaction):
                errors = []

                if "@" in self.name.value:
                    errors.append("**Name** cannot contain `@` symbols.")
                if "@" in self.model.value:
                    errors.append("**Model** cannot contain `@` symbols.")
                if "@" in self.patch.value:
                    errors.append("**Security Patch** cannot contain `@` symbols.")
                if "@" in self.build.value:
                    errors.append("**Build Version** cannot contain `@` symbols.")

                build_value = self.build.value.strip()
                if not (build_value.isdigit() and len(build_value) == 17):
                    errors.append(
                        "**Build Version** must be a 17-digit number (from `adb shell getprop ro.build.version.incremental`).")

                patch_value = self.patch.value.strip()
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", patch_value):
                    errors.append(
                        "**Security Patch** must be a date in YYYY-MM-DD format (from `adb shell getprop ro.build.version.security_patch`).")

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
                self.cog.devices_data.setdefault(user_id, []).append(device)
                save_json(DEVICES_FILE, self.cog.devices_data)

                await interaction.response.send_message("✅ Device added!", ephemeral=True)

        modal = DeviceModal()
        modal.cog = self
        if ctx.interaction:
            await ctx.interaction.response.send_modal(modal)
        else:
            await ctx.send("This command must be used as a slash command.")

    @commands.hybrid_command(name="deviceremove")
    async def deviceremove_cmd(self, ctx, device_id: int):
        """Remove one of your devices by its ID."""
        user_id = str(ctx.author.id)
        user_devices = self.devices_data.get(user_id, [])
        if 1 <= device_id <= len(user_devices):
            removed = user_devices.pop(device_id - 1)
            save_json(DEVICES_FILE, self.devices_data)
            await ctx.send(f"Removed device: {removed['Name']} (`{removed.get('Codename', 'N/A')}`)")
        else:
            await ctx.send("Device not found.")


async def setup(bot):
    await bot.add_cog(Devices(bot))