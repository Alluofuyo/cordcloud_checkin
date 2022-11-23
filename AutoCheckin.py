import argparse
import json
import os.path

import requests
from requests.cookies import RequestsCookieJar
from requests.utils import dict_from_cookiejar, cookiejar_from_dict

cordcoud_url = "https://www.cordc.net"


def login(email: str, passwd: str, ck: str, code: str = "", remember_me: bool = False):
    response = requests.post(cordcoud_url + "/auth/login",
                             data={
                                 "email": email,
                                 "passwd": passwd,
                                 "code": code,
                                 "remember_me": "week" if remember_me else ""
                             },
                             headers={
                                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.52",
                                 "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                                 "Accept": "application/json, text/javascript, */*; q=0.01",
                                 "Referer": f"{cordcoud_url}/auth/login",
                             }, cookies={ck.split("=")[0]: ck.split("=")[1]})
    response.encoding = "utf-8"
    print(response.request.headers)
    print(response.headers)
    result = response.json()
    print(result)
    if result["ret"] == 1:
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
    if cookies is None:
        return True
    response = requests.get(cordcoud_url + "/user", cookies=cookies)
    if response.status_code == 200:
        print("Cookies are valid.")
        return False
    else:
        print("Cookies are invalid.")
        return True


def checkin(cookies: RequestsCookieJar):
    response = requests.post(cordcoud_url + "/user/checkin", cookies=cookies,
                             headers={
                                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.52",
                                 "Accept": "application/json, text/javascript, */*; q=0.01",
                                 "X-Requested-With": "XMLHttpRequest",
                                 "Origin": f"{cordcoud_url}",
                                 "Referer": f"{cordcoud_url}/user"
                             })
    response.encoding = "utf-8"
    print(response.request.headers)
    print(response.headers)
    result = response.json()
    print(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="CordCloud Checkin")
    parser.add_argument("-u", "--username", help="username", type=str)
    parser.add_argument("-p", "--password", help="password", type=str)
    parser.add_argument("-c", "--cookie", help="set the cloudflare clearance cookie", type=str)
    parser.add_argument("-k", "--keep-cookie", help="keep cookies", action="store_true", default=False)
    args = parser.parse_args()

    username = args.username
    password = args.password
    cookie = args.cookie
    keep_cookie = args.keep_cookie
    if username is None or password is None:
        print("Please input username and password.")
        exit(1)
    cks = None

    if keep_cookie and os.path.exists("cookies.txt"):
        cks = read_cookies()
    if check_cookies_expired(cks):
        print("Cookies expired, login again.")
        for i in range(3):
            cks = login(username, password, cookie, "", True)
            print("login success.")
            if cks is not None:
                if keep_cookie:
                    save_cookies(cks)
                checkin(cks)
                break
            else:
                print("login failed. Try again.")
    else:
        checkin(cks)
