import logging
import subprocess
import re
from http.cookies import SimpleCookie
from typing import Dict, Tuple, Optional
from urllib.parse import urljoin, urlparse

from pydoll.browser.chromium.chrome import Chrome
from pydoll.browser.options import ChromiumOptions
import requests
from bs4 import BeautifulSoup

import config


logger = logging.getLogger(__name__)

_LOGIN_PATH = "/auth/login"


def _run_curl_fetch(url: str, user_agent: str) -> Tuple[str, Dict[str, str]]:
  """
  Fetch a URL using curl, returning the HTML body and aggregated cookies parsed
  from all Set-Cookie headers seen during redirects.
  """
  command = [
    "curl",
    "-sS",
    "-L",          # follow redirects
    "-i",          # include response headers in the output
    "--compressed",
    "-A",
    user_agent,
    url,
  ]
  try:
    result = subprocess.run(
      command,
      check=True,
      capture_output=True,
      text=True,
    )
  except FileNotFoundError as e:
    raise RuntimeError("curl is not available on this system. Please install curl.") from e
  except subprocess.CalledProcessError as e:
    logger.error(f"curl failed: {e.stderr}")
    raise RuntimeError("curl failed to fetch the page") from e

  raw_output = result.stdout

  # Collect cookies from ALL Set-Cookie headers across all redirect responses
  cookie_map: Dict[str, str] = {}
  for match in re.finditer(r"(?im)^Set-Cookie:\s*([^\r\n]+)", raw_output):
    cookie_header_value = match.group(1)
    # Parse cookies from the header value, ignoring attributes
    parsed = SimpleCookie()
    try:
      parsed.load(cookie_header_value)
    except Exception:
      continue
    for name, morsel in parsed.items():
      cookie_map[name] = morsel.value

  # Extract the last response body (after the final header block)
  parts = re.split(r"\r?\n\r?\n", raw_output)
  html = parts[-1] if parts else raw_output
  return html, cookie_map


def _extract_csrf_token_from_html(html: str) -> Optional[str]:
  soup = BeautifulSoup(html, "html.parser")
  csrf_input = soup.find("input", {"name": "csrf_token"})
  if csrf_input and csrf_input.has_attr("value"):
    return csrf_input["value"]
  return None


def _populate_session_cookies(session: requests.Session, cookies: Dict[str, str], base_url: str) -> None:
  hostname = urlparse(base_url).hostname
  for name, value in cookies.items():
    session.cookies.set(name, value, domain=hostname)


def _attempt_login_with_curl(base_url: str, username: str, password: str, user_agent: str) -> requests.Session:
  login_url = urljoin(base_url, _LOGIN_PATH)
  html, cookies = _run_curl_fetch(login_url, user_agent)

  # Detect Cloudflare interstitial page and proceed anyway to try login (cookies may include CF clearances)
  if "Just a moment" in html and "cloudflare" in html.lower():
    logger.warning("Cloudflare interstitial detected; proceeding with cookies obtained via curl.")

  csrf_token = _extract_csrf_token_from_html(html)
  if csrf_token is None:
    logger.info("CSRF token not found in HTML. Will attempt login without CSRF token field.")

  session = requests.Session()
  session.headers.update({
    "User-Agent": user_agent,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
  })
  _populate_session_cookies(session, cookies, base_url)

  payload = {
    "email": username,
    "passwd": password,
    "code": "",
  }
  if csrf_token is not None:
    payload["csrf_token"] = csrf_token

  response = session.post(login_url, data=payload, allow_redirects=True, timeout=30)
  # Best-effort: If server returns JSON with ret field, that's ideal; otherwise, rely on cookies being set
  try:
    data = response.json()
    if isinstance(data, dict) and data.get("ret") == 1:
      logger.info("Login appears successful via curl path.")
    else:
      logger.info(f"Login response via curl path: {data}")
  except Exception:
    logger.info("Login response is not JSON; proceeding based on cookies.")

  return session


async def _attempt_login_with_pydoll(base_url: str, username: str, password: str, user_agent: Optional[str] = None) -> Optional[requests.Session]:
  """
  Attempt to login using pydoll (async). Returns a requests.Session on success, or None on failure.
  """
  browser = None
  try:
    options = ChromiumOptions()
    options.headless = config.PYDOLL_HEADLESS
    options.add_argument(f"--user-agent={config.PYDOLL_USER_AGENT}")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    

    browser = Chrome(options=options)
    tab = await browser.start()

    login_url = urljoin(base_url, _LOGIN_PATH)
    await tab.go_to(login_url)

    # Try to auto-bypass Cloudflare turnstile if present (best-effort)
    try:
      await tab.enable_auto_solve_cloudflare_captcha()
    except Exception:
      pass

    from pydoll.constants import By, Key
    email_input = await tab.find_or_wait_element(By.CSS_SELECTOR, "input[name=Email]", timeout=10, raise_exc=False)
    passwd_input = await tab.find_or_wait_element(By.CSS_SELECTOR, "input[name=Password]", timeout=10, raise_exc=False)
    submit_btn = await tab.find_or_wait_element(By.ID, "login", timeout=10, raise_exc=False)

    if email_input:
      await email_input.click()
      await email_input.insert_text(username)
    if passwd_input:
      await passwd_input.click()
      await passwd_input.insert_text(password)
    if submit_btn:
      await submit_btn.click()
    elif passwd_input:
      await passwd_input.press_keyboard_key(Key.ENTER)

    try:
      await tab.enable_network_events()
      import asyncio as _asyncio
      await _asyncio.sleep(3)
    except Exception:
      pass

    page_cookies = await tab.get_cookies()

    # Close browser before building session
    await browser.stop()
    browser = None

    session = requests.Session()
    session.headers.update({
      "User-Agent": user_agent,
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
      "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })

    hostname = urlparse(base_url).hostname
    for cookie in page_cookies:
      name = cookie.get("name")
      value = cookie.get("value")
      if name is None or value is None:
        continue
      domain = cookie.get("domain") or hostname
      session.cookies.set(name, value, domain=domain)

    return session
  except Exception as e:
    logger.error(f"pydoll automation failed: {e}")
    if browser is not None:
      try:
        await browser.stop()
      except Exception:
        pass
    return None


async def login_and_get_session(url: str, username: str, password: str) -> requests.Session:
  """
  Attempt to obtain a logged-in requests.Session using (1) pydoll automation if available,
  otherwise (2) curl-based HTML fetch and cookie aggregation to bypass Cloudflare and submit login.
  """
  user_agent = config.PYDOLL_USER_AGENT
  if user_agent is None or user_agent == "":
    user_agent = (
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

  # First try pydoll if present
  session = await _attempt_login_with_pydoll(url, username, password, user_agent)
  if session is not None:
    return session

  # Fallback to curl-based approach
  return _attempt_login_with_curl(url, username, password, user_agent)


async def create_api_manager_with_cookies(url: str, username: str, password: str):
  """
  Helper to create ApiManager with a logged-in session (cookies pre-set), using the strategies above.
  """
  from api import ApiManager  # Local import to avoid circular deps on import-time

  session = await login_and_get_session(url, username, password)
  api_manager = ApiManager(url)
  api_manager.session = session
  return api_manager
