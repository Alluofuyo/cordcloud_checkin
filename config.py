import dotenv
import os
dotenv.load_dotenv()

USERNAME = os.getenv("CC_USERNAME")
PASSWORD = os.getenv("CC_PASSWORD")
API_URLS = os.getenv("CC_API_URLS").split(",") if os.getenv("CC_API_URLS") else ""
SHOULD_SEND_EMAIL = os.getenv("SHOULD_SEND_EMAIL") == "true"
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL").split(",") if os.getenv("RECEIVER_EMAIL") else ""

PYDOLL_HEADLESS = os.getenv("DOLL_BROWSER_HEADLESS") == "true"
PYDOLL_USER_AGENT = os.getenv("DOLL_USER_AGENT")