from discord import Intents
import argparse
import math

BOT_VERSION: str = "2.1.5"
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

WELCOME_CHANNEL_ID: int = 1433809691422494770
BOT_CONSOLE_CHANNEL_ID: int = 1433808437657075903
COUNTING_REPORT_CHANNEL_ID: int = 1208782728083013673
COUNTING_CHANNEL_ID: int = 1433783925414563941
REPORT_LOG_CHANNEL_ID: int = 1433783978359259258
ADMIN_ROLE_ID: int = 1433784069954474048
QUARANTINE_ROLE_ID: int = 1433784445164322837
MEMBER_ROLE_ID: int = 1433810924174704701

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