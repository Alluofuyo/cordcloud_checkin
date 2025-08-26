import logging
import subprocess
import re
from http.cookies import SimpleCookie
from typing import Dict, Tuple, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


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


def _attempt_login_with_pydoll(base_url: str, username: str, password: str, user_agent: str) -> Optional[requests.Session]:
  """
  Attempt to login using pydoll, if available. Returns a requests.Session on success, or None on failure.
  This path is best-effort; if pydoll is not installed or fails, caller should fallback to curl path.
  """
  try:
    import pydoll  # type: ignore
  except Exception:
    logger.info("pydoll not available; skipping pydoll login path.")
    return None

  try:
    # NOTE: pydoll API is assumed; adjust if your pydoll usage differs.
    # The following is a conservative, generic automation flow.
    browser = pydoll.launch(headless=True, user_agent=user_agent)
    page = browser.new_page()
    login_url = urljoin(base_url, _LOGIN_PATH)
    page.goto(login_url)

    # Fill in known field names used by the site
    page.fill("input[name=email]", username)
    page.fill("input[name=passwd]", password)
    # Some sites have a submit button with type=submit or name=submit
    page.click("input[type=submit], button[type=submit]")
    page.wait_for_load_state("networkidle")

    # Extract cookies from the page context
    page_cookies = page.context.cookies()
    browser.close()

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
    return None


def login_and_get_session(url: str, username: str, password: str, user_agent: Optional[str] = None) -> requests.Session:
  """
  Attempt to obtain a logged-in requests.Session using (1) pydoll automation if available,
  otherwise (2) curl-based HTML fetch and cookie aggregation to bypass Cloudflare and submit login.
  """
  if user_agent is None:
    user_agent = (
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

  # First try pydoll if present
  session = _attempt_login_with_pydoll(url, username, password, user_agent)
  if session is not None:
    return session

  # Fallback to curl-based approach
  return _attempt_login_with_curl(url, username, password, user_agent)


def create_api_manager_with_cookies(url: str, username: str, password: str, user_agent: Optional[str] = None):
  """
  Helper to create ApiManager with a logged-in session (cookies pre-set), using the strategies above.
  """
  from api import ApiManager  # Local import to avoid circular deps on import-time

  session = login_and_get_session(url, username, password, user_agent)
  api_manager = ApiManager(url)
  api_manager.session = session
  return api_manager
