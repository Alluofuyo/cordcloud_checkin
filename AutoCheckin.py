import argparse
import os
import subprocess
import sys
import stat
import zipfile

import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def unzip(src, dest):
    if os.path.exists(src):
        with zipfile.ZipFile(src, "r") as zf:
            zf.extractall(dest)
    else:
        print("cannot find the zip file to unzip.")


class ChromeDriverDownloader:
    def __init__(self, version: str, platform: str):
        self._current_name = ""
        self._version = version
        self._version_str = self._version.split('.')
        self._platform = platform
        self._chrome_driver_version_list = []
        self._base_url = "https://chromedriver.storage.googleapis.com"
        self._testing_url = "https://googlechromelabs.github.io"

    def _get_latest_version(self):
        main_version = '.'.join(self._version_str[:3])
        response = requests.get(f"{self._base_url}/LATEST_RELEASE_{main_version}")
        return response.text

    def download_chromedriver(self):
        major_version = self._version_str[0]
        print(f"major version is {major_version}")
        if int(major_version) >= 115:
            return self._download_testing()
        latest_version = self._get_latest_version()
        return self._download(latest_version)

    def _download(self, version):
        url = f"{self._base_url}/{version}/chromedriver_{self._platform}.zip"
        print(f"downloading chrome driver from {url}")
        response = requests.get(url)
        file_name = "chromedriver.zip"
        with open(file_name, "wb") as f:
            f.write(response.content)
        return self._unzipfile(file_name)

    def _unzipfile(self, file_name):
        if os.path.exists(file_name):
            print("download chrome driver successfully.")
            unzip(file_name, "chromedriver")
            os.remove(file_name)
            if (self._platform == "linux64" or self._platform == "mac64") and os.path.exists(
                    "./chromedriver/chromedriver-linux64/chromedriver"):
                chromedriver_file="./chromedriver/chromedriver-linux64/chromedriver"
                print(f"unzip chromedriver to {chromedriver_file}")
                #os.chmod(chromedriver_file,stat.S_IRWXG)
                os.system(f"chmod a+rwx {chromedriver_file}")
                return chromedriver_file
            elif self._platform == "win32" and os.path.exists("./chromedriver-win64/chromedriver.exe"):
                chromedriver_file="./chromedriver-win64/chromedriver.exe"
                print(f"unzip chromedriver to {chromedriver_file}")
                os.chmod(chromedriver_file,stat.S_IRWXG)
                return chromedriver_file
            else:
                print("unzip chromedriver failed.")
                exit(-1)

    def _download_testing(self):
        response = requests.get(
            f"https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json")
        url = ""
        print(response.json())
        if self._platform == "linux64":
            url = list(filter(lambda item: item["platform"] == "linux64", list(
                response.json()["channels"]["Stable"]["downloads"]["chromedriver"])))[0]["url"]
        elif self._platform == "mac64":
            url = list(filter(lambda item: item["platform"] == "mac-x64", list(
                response.json()["channels"]["Stable"]["downloads"]["chromedriver"])))[0]["url"]
        elif self._platform == "win32":
            url = list(filter(lambda item: item["platform"] == "win64", list(
                response.json()["channels"]["Stable"]["downloads"]["chromedriver"])))[0]["url"]
        download_response = requests.get(url)
        file_name = "chromedriver.zip"
        with open(file_name, "wb") as f:
            f.write(download_response.content)
        return self._unzipfile(file_name)


def get_chrome_version():
    result = subprocess.run(['google-chrome', '--version'], stdout=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    version = output.strip().split()[-1]
    print(f"google chrome version: {version}")
    return version


def parse_arguments():
    parser = argparse.ArgumentParser(description="CordCloud Checkin")
    parser.add_argument("-u", "--username", help="username", type=str, required=True)
    parser.add_argument("-p", "--password", help="password", type=str, required=True)

    parser.add_argument("-U", "--url", help="cordcloud url", type=str, required=True)
    parser.add_argument("--chrome_path", help="chrome browser path", type=str)
    parser.add_argument("--chrome_version", help="chrome version", type=str)
    parser.add_argument("--debug",help="debug options",action="store_true")
    return parser.parse_args()


def start_checkin(username, password, url, chrome_path, chromedriver_path, debug=False):
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,1024")
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument("--excludeSwitches=enable-automation")
    options.add_argument("--disable-blink-features=AutomationControlled")
    if chrome_path:
        driver = uc.Chrome(options=options, browser_executable_path=chrome_path,
                           driver_executable_path=chromedriver_path)
    else:
        driver = uc.Chrome(options=options, driver_executable_path=chromedriver_path)
    if debug:
        print(f"browser_executable_path: {chrome_path}")
        print(f"driver_executable_path: {chromedriver_path}")

    driver.implicitly_wait(10)
    try:
        
        driver.get(f'{url}/auth/login')
        if debug:
            print(f"get page url: f{driver.current_url}")
            print(f"page sources: f{driver.page_source}")
        email_input = driver.find_element(by=By.ID, value="email")
        email_input.send_keys(username)
        password_input = driver.find_element(by=By.ID, value="passwd")
        password_input.send_keys(password)
        driver.find_element(by=By.ID, value="login").click()
        if debug:
            print(f"get page url: f{driver.current_url}")
            print(f"page sources: f{driver.page_source}")
        text = driver.find_element(by=By.XPATH,
                                   value="/html/body/main/div[2]/section/div[2]/div[1]/div[1]/div/div[2]/p[2]").text
        print("Login success!")
        print(text)

        cookies = driver.get_cookies()
        c = {}
        for cookie in cookies:
            cookie = dict(cookie)
            c[cookie["name"]] = cookie["value"]
        
        response = requests.post(f'{url}/user/checkin', cookies=c, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.52",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": url,
            "Referer": f"{url}/user"
        }, timeout=10)
        if debug:
            print(f"post elapsed time: {response.elapsed}")
            print(f"post url: {response.url}")
            print(f"post status code: {response.status_code}")
            print(f"post headers: {response.headers}")
            print(f"post text: {response.text}")
        print(response.json())

    except Exception as e:
        print(e)
    finally:
        driver.quit()


def download_chromedriver(chrome_version):
    os_type = sys.platform
    platform = "linux64"
    if os_type == "linux":
        platform = "linux64"
        if not chrome_version:
            chrome_version = get_chrome_version()
    elif os_type == "win32":
        platform = "win32"
        if not chrome_version:
            print("please specify the chrome version, if you are in Windows.")
            exit(-1)
    elif os_type == "darwin":
        platform = "mac64"
        if not chrome_version:
            chrome_version = get_chrome_version()
    downloader = ChromeDriverDownloader(chrome_version, platform)
    return downloader.download_chromedriver()


def main():
    args = parse_arguments()

    username = args.username
    password = args.password
    url = args.url

    chrome_path = args.chrome_path
    chrome_version = args.chrome_version

    chromedriver_path = download_chromedriver(chrome_version)
    start_checkin(username, password, url, chrome_path, chromedriver_path,args.debug)


if __name__ == '__main__':
    main()
