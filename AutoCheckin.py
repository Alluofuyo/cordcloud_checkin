import argparse
import json
import os.path
import sys

import requests
from requests.cookies import RequestsCookieJar
from requests.utils import dict_from_cookiejar, cookiejar_from_dict


def login(email: str, passwd: str, code: str = "", remember_me: bool = False):
    response = requests.post("https://www.cordcloud.one/auth/login",
                             data={
                                 "email": email,
                                 "passwd": passwd,
                                 "code": code,
                                 "remember_me": "week" if remember_me else ""
                             },
                             headers={
                                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, "
                                               "like Gecko) Chrome/100.0.4896.75 Safari/537.36 Edg/100.0.1185.36",
                                 "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                                 "Accept": "application/json, text/javascript, */*; q=0.01",
                                 "X-Requested-With": "XMLHttpRequest",
                                 "Origin": "https://www.cordcloud.one",
                                 "Referer": "https://www.cordcloud.one/auth/login"
                             })
    response.encoding = "utf-8"
    result = response.json()
    if result["ret"] == 1:
        print(result["msg"])
        return response.cookies
    else:
        return None


def save_cookies(cookies: RequestsCookieJar):
    try:
        with open("cookies.txt", "w") as f:
            json.dump(dict_from_cookiejar(cookies), f)
            print("Save cookies to file successfully.")
    except json.decoder.JSONDecodeError:
        print("Save cookies to file failed.")


def read_cookies():
    try:
        with open("cookies.txt", "r") as f:
            cookies = cookiejar_from_dict(json.load(f))
            print("Read cookies from file successfully.")
        return cookies
    except json.decoder.JSONDecodeError:
        print("Read cookies from file failed.")
        return None


def check_cookies_expired(cookies: RequestsCookieJar):
    response = requests.get("https://www.cordcloud.one/user", cookies=cookies)
    if response.status_code == 200:
        return False
    else:
        return True


def checkin(cookies: RequestsCookieJar):
    response = requests.post("https://www.cordcloud.one/user/checkin", cookies=cookies,
                             headers={
                                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, "
                                               "like Gecko) Chrome/100.0.4896.75 Safari/537.36 Edg/100.0.1185.36",
                                 "Accept": "application/json, text/javascript, */*; q=0.01",
                                 "X-Requested-With": "XMLHttpRequest",
                                 "Origin": "https://www.cordcloud.one",
                                 "Referer": "https://www.cordcloud.one/user"
                             })
    response.encoding = "utf-8"
    result = response.json()
    if result["ret"] == 1:
        print(result)
    else:
        print(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", help="username", type=str)
    parser.add_argument("-p", "--password", help="password", type=str)
    args = parser.parse_args()
    username = args.username
    password = args.password
    if username is None or password is None:
        print("Please input username and password.")
        exit(1)
    cks = None
    if os.path.exists("cookies.txt"):
        cks = read_cookies()
    if check_cookies_expired(cks) or cks is None:
        print("Cookies expired, login again.")
        for i in range(3):
            cks = login(username, password, "", True)
            if cks is not None:
                save_cookies(cks)
                print("login success.")
                checkin(cks)
                break
            else:
                print("login failed. Try again.")
    else:
        checkin(cks)
