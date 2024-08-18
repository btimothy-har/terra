from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-1.5-flash"
DEFAULT_TEMP = 0.2
MAX_TOKEN_VALUES = [512, 1024, 2048, 4096]
DEFAULT_MAX_TOKENS = 2048

API_ENDPOINT = "http://api:8000"
