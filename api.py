import requests
from bs4 import BeautifulSoup
import logging


class CsrfError(Exception):
  pass
class LoginError(Exception):
  pass
class CheckInError(Exception):
  pass


logger = logging.getLogger(__name__)

_LOGIN_PATH = "/auth/login"
_USER_CHECK_IN = "/user/checkin"

class ApiManager:
  def __init__(self, url: str):
    self.url = url
    self.session = requests.Session()
  
  def _parse_csrf_token(self, response: requests.Response):
    soup = BeautifulSoup(response.text, "html.parser")
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    return csrf_token

  def _get_csrf_token(self):
    response = self.session.get(
      f"{self.url}{_LOGIN_PATH}"
    )
    if response.status_code == 200:
      return self._parse_csrf_token(response)
    else:
      raise CsrfError(f"Get CSRF token failed: {response.status_code} {response.text}")

  def login(self, username: str, password: str):
    logger.info(f"Login to {self.url} with username {username}")
    csrf_token = self._get_csrf_token()
    if csrf_token is None:
      csrf_token = ""
    response = self.session.post(
      f"{self.url}{_LOGIN_PATH}",
      data={
          "email": username, 
          "passwd": password,
          "code": "",
          "csrf_token": csrf_token
        }
    )
    if response.status_code == 200:
      return response.json()
    else:
      raise LoginError(f"Login failed: {response.status_code} {response.text}")
  
  def check_in(self):
    response = self.session.post(
      f"{self.url}{_USER_CHECK_IN}"
    )
    if response.status_code == 200:
      return response.json()
    else:
      raise CheckInError(f"Check in failed: {response.status_code} {response.text}")
  
  def switch_url(self, url: str):
    self.url = url
    self.session = requests.Session()