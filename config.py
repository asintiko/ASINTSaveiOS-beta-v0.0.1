import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

# Load environment variables from the .env file in the current directory
load_dotenv()

# Retrieve the token and base_url from the environment
TOKEN = os.getenv("TOKEN")
BASE_URL = os.getenv("BASE_URL")


def _resolve_sqlite_path(url: str | None) -> str | None:
    """Resolve relative SQLite URLs against the project root."""
    if not url:
        return url

    try:
        parsed = make_url(url)
    except Exception:
        return url

    if not parsed.drivername.startswith("sqlite"):
        return url

    database = parsed.database
    if not database:
        return url

    db_path = Path(database)
    if db_path.is_absolute():
        return url

    absolute_path = (Path(__file__).resolve().parent / db_path).resolve()
    updated = parsed.set(database=absolute_path.as_posix())
    return str(updated)


DATABASE_URL = _resolve_sqlite_path(os.getenv("DATABASE_URL"))
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST")
WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", "8080"))
MAIN_BOT_PATH = os.getenv("MAIN_BOT_PATH")

# OTHER_BOTS_PATH is the prefix for mirror bot webhooks, as expected by main.py and other parts of the original code
OTHER_BOTS_PATH = os.getenv("OTHER_BOTS_PATH") 

# OTHER_BOTS_URL is the full URL template for setting webhooks for mirror bots
# It's constructed here if BASE_URL and OTHER_BOTS_PATH are defined (for webhook mode)
OTHER_BOTS_URL = None

if BASE_URL and OTHER_BOTS_PATH:
    OTHER_BOTS_URL = f"{BASE_URL.rstrip('/')}/{OTHER_BOTS_PATH.lstrip('/')}/{{bot_token}}"

ADMIN_IDS_ENV = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = tuple(
    int(admin_id.strip())
    for admin_id in ADMIN_IDS_ENV.split(",")
    if admin_id.strip().isdigit()
)

RESET_DB_ON_START = os.getenv('RESET_DB_ON_START', 'false').lower() == 'true'
RUN_VIA_POLLING_STR = os.getenv("RUN_VIA_POLLING", "false")
RUN_VIA_POLLING = RUN_VIA_POLLING_STR.lower() == "true"
LOG_LANGUAGE = os.getenv("LOG_LANGUAGE", "ru")

CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")
CRYPTOBOT_ASSET = os.getenv("CRYPTOBOT_ASSET", "USDT")
CRYPTOBOT_POLL_INTERVAL = float(os.getenv("CRYPTOBOT_POLL_INTERVAL", "5"))
CRYPTOBOT_POLL_TIMEOUT = float(os.getenv("CRYPTOBOT_POLL_TIMEOUT", "300"))

# Validation (optional, but good practice)
if TOKEN is None:
    raise ValueError("TOKEN is not set in the .env file.")

if DATABASE_URL is None:
    raise ValueError("DATABASE_URL is not set in the .env file.")

if not RUN_VIA_POLLING:
    if BASE_URL is None or BASE_URL == "https://example.com":
        raise ValueError("BASE_URL is not set or is a placeholder in the .env file for webhook mode.")
    if WEB_SERVER_HOST is None:
        raise ValueError("WEB_SERVER_HOST is not set in the .env file for webhook mode.")
    if MAIN_BOT_PATH is None:
        raise ValueError("MAIN_BOT_PATH is not set in the .env file for webhook mode.")
    if OTHER_BOTS_PATH is None:
        # This might be optional if mirror bot functionality is not used
        print("Warning: OTHER_BOTS_PATH is not set in .env, mirror bot creation might not work in webhook mode.")
    if OTHER_BOTS_URL is None and OTHER_BOTS_PATH is not None:
        print("Warning: OTHER_BOTS_URL could not be constructed, check BASE_URL and OTHER_BOTS_PATH in .env for webhook mode.")
