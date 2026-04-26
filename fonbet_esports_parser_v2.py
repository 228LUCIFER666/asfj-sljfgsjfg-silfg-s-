import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_fonbet_esports_odds():
    print("Fonbet Esports: запуск парсера...")

    url = "https://fon.bet/sports/esports?lang=ru"

    for attempt in range(3):
        driver = None

        try:
            options = webdriver.ChromeOptions()

            # 🔥 БАЗА
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")

            # 🔥 СТАБИЛЬНОСТЬ (КРИТИЧНО)
            options.add_argument("--single-process")
            options.add_argument("--no-zygote")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-browser-side-navigation")
            options.add_argument("--disable-features=VizDisplayCompositor")

            # анти-детект
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--user-agent=Mozilla/5.0")

            # 🔥 УБИРАЕМ НАГРУЗКУ
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.managed_default_content_settings.stylesheets": 2,
            }
            options.add_experimental_option("prefs", prefs)

            options.binary_location = "/usr/bin/chromium"

            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=options)

            driver.set_page_load_timeout(30)

            try:
                driver.get(url)
            except Exception as e:
               