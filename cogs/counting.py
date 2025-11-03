from discord.ext import commands

from utils.file_handlers import load_json, save_json
from config import COUNTING_CHANNEL_ID, COUNTING_REPORT_CHANNEL_ID, MATH_CONSTANTS, COUNT_FILE
from expr import evaluate, errors


class Counting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def streak(self, ctx):
        data = load_json(COUNT_FILE, {"current_count": 0, "last_counter_id": None})
        await ctx.send(f"The current counting streak is **{data['current_count']}**.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == COUNTING_CHANNEL_ID and not message.author.bot:
            data = load_json(COUNT_FILE, {"current_count": 0, "last_counter_id": None})
            current_count = data["current_count"]
            last_counter_id = data["last_counter_id"]
            content = message.content

            try:
                number = evaluate(content, variables=MATH_CONSTANTS)

                if number == current_count + 1 and message.author.id != last_counter_id:
                    data["current_count"] = number
                    data["last_counter_id"] = message.author.id
                    save_json(COUNT_FILE, data)
                    return
                else:
                    if message.author.id == last_counter_id:
                        reason = "Double counting - same user consecutively"
                    elif number != current_count + 1:
                        reason = f"Incorrect number - expected {current_count + 1}, got {number}"
                    else:
                        reason = "Unknown error"

            except errors.ParsingError as e:
                """
                TODO: Ignore if error is Gibberish, InvalidSyntax, BadOperation because they all may mean that it's not math expression, or it's just: 2**2 instead of 2^2
                TODO: Maybe implement custom error handler so instead of Invalid mathematical expression: Overflow, it says: Don't try to break this, and maybe even mutes for 15 minutes because of that
                (But first ask someone, it's just my ideas of improving it)
                """
                reason = f"Invalid mathematical expression: {e.friendly}"
            except Exception as e:
                reason = f"Unknown error: {e}"

            data["current_count"] = 0
            data["last_counter_id"] = None
            save_json(COUNT_FILE, data)

            await message.delete()
            count_report = self.bot.get_channel(COUNTING_REPORT_CHANNEL_ID)
            count = self.bot.get_channel(COUNTING_CHANNEL_ID)
            if count_report:
                await count_report.send(
                    f"⚠️ <@{message.author.id}> broke the counting streak in <#{message.channel.id}>! ({reason})"
                )
                await count.send("Streak has been broken! Start from 1.")


async def setup(bot):
    await bot.add_cog(Counting(bot))