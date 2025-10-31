from discord import Intents
import argparse
import math

BOT_VERSION: str = "2.1.6"
DISABLED_IN_BETA: set[str] = {"slowmode", "q", "uq"}

MATH_CONSTANTS: dict[str, float] = {
    'pi': math.pi,
    'e': math.e,
    'tau': math.tau,
    'inf': math.inf,
    'nan': math.nan,
    'π': math.pi,
    'τ': math.tau,
    'φ': (1 + math.sqrt(5)) / 2,
    'gamma': 0.57721566490153286060,
    'c': 299792458,
    'G': 6.67430e-11,
    'h': 6.62607015e-34,
}

WELCOME_CHANNEL_ID: int = 1348562119469305958
BOT_CONSOLE_CHANNEL_ID: int = 1376528272204103721
COUNTING_REPORT_CHANNEL_ID: int = 1348562119469305958  # IDK, but maybe it'll be better if just be same as COUNTING_CHANNEL_ID, but then how to reply?
COUNTING_CHANNEL_ID: int = 1374296035798814804
REPORT_LOG_CHANNEL_ID: int = 1361285583195869255
ADMIN_ROLE_ID: int = 1376159693021646900
QUARANTINE_ROLE_ID: int = 1373608273306976276
MEMBER_ROLE_ID: int = 1406195112714829899  # IDK what role this really is

intents = Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.dm_messages = True
intents.members = True

COUNT_FILE: str = "data/count_data.json"
REPORTS_FILE: str = "data/reports.json"
FILTER_FILE: str = "data/filters.json"
DEVICES_FILE: str = "data/devices.json"
BACKUP_FILE: str = "data/message_backups.json"
QUARANTINE_DATA_FILE: str = "data/quarantine_data.json"
QUARANTINE_LOG_FILE: str = "data/quarantine_log.txt"

REPO_URL: str = "https://github.com/FreeXR/FreeXR-Bot.git"
REPO_DIR: str = "FreeXR-Bot"
REPLIES_DIR: str = "quick_replies"

parser = argparse.ArgumentParser(description="FreeXR Bot")
parser.add_argument("-t", "--token", type=str, help="Discord bot token")
args = parser.parse_args()

if args.token:
    TOKEN: str = args.token
else:
    with open("token", "r") as file:
        TOKEN: str = file.read().strip()