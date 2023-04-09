import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import argparse
import requests
import subprocess
from requests.cookies import RequestsCookieJar
from requests.utils import dict_from_cookiejar, cookiejar_from_dict


def get_chrome_version():
    result = subprocess.run(['google-chrome', '--version'], stdout=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    version = output.strip().split()[-1]
    return version

def download_chromedriver(version):
    url = f"https://chromedriver.storage.googleapis.com/{version}/chromedriver_linux64.zip"
    response = requests.get(url)
    file_name = "chromedriver.zip"
    with open(file_name, "wb") as f:
        f.write(response.content)
    os.system("unzip chromedriver.zip")
    os.remove(file_name)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="CordCloud Checkin")
    parser.add_argument("-u", "--username", help="username", type=str,required=True)
    parser.add_argument("-p", "--password", help="password", type=str,required=True)
    parser.add_argument("-U","--url",help="cordcloud url",type=str,required=True)
    args=parser.parse_args()

    username = args.username
    password = args.password
    url = args.url
    
    chrome_version = get_chrome_version()
    download_chromedriver(chrome_version)
    
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,1024")
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument("--excludeSwitches=enable-automation")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = uc.Chrome(options=options,driver_executable_path = "./chromedriver/chromedriver")
    driver.implicitly_wait(10)
    try:

        driver.get(f'{url}/auth/login')

        email_input = driver.find_element(by=By.ID, value="email")
        email_input.send_keys(username)
        password_input = driver.find_element(by=By.ID, value="passwd")
        password_input.send_keys(password)
        driver.find_element(by=By.ID, value="login").click()
        text = driver.find_element(by=By.XPATH, value="/html/body/main/div[2]/section/div[2]/div[1]/div[1]/div/div[2]/p[2]").text
        print("Login success!")
        print(text)

        cookies = driver.get_cookies()
        c={}
        for cookie in cookies:
            cookie = dict(cookie)
            c[cookie["name"]] = cookie["value"]
        
        response = requests.post(f'{url}/user/checkin', cookies=c, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.52",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": url,
            "Referer": f"{url}/user"
        },timeout=10)

        print(response.json())
    
    except Exception as e:
        print(e)
    finally:
        driver.quit()
