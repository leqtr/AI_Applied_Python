from dotenv import load_dotenv
import os

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY")
if not WEATHER_API_KEY or not BOT_TOKEN or not API_NINJAS_KEY:
    raise ValueError("Problem with tokens: WEATHER_API_KEY and/or BOT_TOKEN and/or API_NINJAS_KEY")
