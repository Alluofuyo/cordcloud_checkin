import time
import requests
import os
import dotenv
import logging

from api import ApiManager, CsrfError, LoginError, CheckInError
from requests.exceptions import JSONDecodeError
from pydoll_login import create_api_manager_with_cookies
dotenv.load_dotenv()

USERNAME = os.getenv("CC_USERNAME")
PASSWORD = os.getenv("CC_PASSWORD")
API_URLS = os.getenv("CC_API_URLS").split(",") if os.getenv("CC_API_URLS") else ""
SHOULD_SEND_EMAIL = os.getenv("SHOULD_SEND_EMAIL") == "true"
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL").split(",") if os.getenv("RECEIVER_EMAIL") else ""


logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def check_url_connection(urls):
  results = []
  for url in urls:
    try:
      start_time = time.time()
      response = requests.get(url, allow_redirects=True, timeout=30)
      end_time = time.time()
      response_time = end_time - start_time
      if response.status_code == 200:
        logger.info(f"URL {url} is connected in {response_time:.2f} seconds")
        results.append({
          "url": url,
          "response_time": response_time,
          "status": "available",
          "used": False
        })
      else:
        logger.warn(f"URL {url} is not connected")
        results.append({
          "url": url,
          "response_time": -1,
          "status": "unavailable",
          "used": False
        })
    except requests.exceptions.RequestException as e:
      logger.warn(f"URL {url} is not connected")
      results.append({
        "url": url,
        "response_time": -1,
        "status": "error",
        "used": False
      })
  return results

def pick_one_best(results):
  best_result = None
  best_response_time = float('inf')
  for result in results:
    if result["status"] == "available" and not result["used"] and result["response_time"] < best_response_time:
      best_result = result
      best_response_time = result["response_time"]
  return best_result


def switch_url(results):
  return pick_one_best(results)


def do_check_in(url):
  api_manager = ApiManager(url)
  try:
    result = api_manager.login(USERNAME, PASSWORD)
    if result["ret"] == 0:
      logger.error(result["msg"])
      return False
    result = api_manager.check_in()
    if result["ret"] == 0 and result["msg"] != "您似乎已经签到过了...":
      logger.error(result["msg"])
      return False
    if result["ret"] == 1 and 'trafficInfo' in result:
      logger.info(result["msg"])
      logger.info(f"今日已用流量 {result['trafficInfo']['todayUsedTraffic']}, 历史使用流量 {result['trafficInfo']['lastUsedTraffic']}, 剩余流量 {result['trafficInfo']['unUsedTraffic']}, 总流量 {result['traffic']}")
      return True
    logger.error(result["msg"])
    return False
  except (CsrfError, LoginError, CheckInError) as e:
    if "403" in str(e):
      logger.warn("API 403 detected, falling back to pydoll login.")
      fallback_manager = create_api_manager_with_cookies(url, USERNAME, PASSWORD)
      result = fallback_manager.check_in()
      if result["ret"] == 0 and result["msg"] != "您似乎已经签到过了...":
        logger.error(result["msg"])
        return False
      if result["ret"] == 1 and 'trafficInfo' in result:
        logger.info(result["msg"])
        logger.info(f"今日已用流量 {result['trafficInfo']['todayUsedTraffic']}, 历史使用流量 {result['trafficInfo']['lastUsedTraffic']}, 剩余流量 {result['trafficInfo']['unUsedTraffic']}, 总流量 {result['traffic']}")
        return True
      logger.error(result["msg"])
      return False
    else:
      raise

def main():
  results = check_url_connection(API_URLS)
  best_result = pick_one_best(results)
  finished = False
  while not finished:
    try:
      best_result["used"] = True
      success = do_check_in(best_result["url"])
      if success:
        logger.info("成功完成签到")
        finished = True
      else:
        logger.error("签到失败")
        finished = True
    except (CsrfError, LoginError, CheckInError, JSONDecodeError) as e:
      logger.error(e)
      time.sleep(5)
      best_result = switch_url(results)
      if best_result is None:
        logger.error("没有可用的URL")
        finished = True
    except Exception as e:
      logger.error(e)
      time.sleep(5)
      finished = True

if __name__ == "__main__":
  main()
