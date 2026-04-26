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

            # 🔥 СТАБИЛЬНОСТЬ
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
                print("  Ошибка загрузки:", e)
                driver.quit()
                continue

            print("  Жду загрузки...")

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                print("  Страница не загрузилась")
                driver.quit()
                continue

            time.sleep(3)

            body_text = driver.find_element(By.TAG_NAME, "body").text
            lines = body_text.split('\n')

            events = []
            i = 0

            while i < len(lines) - 3:
                line = lines[i].strip()

                if '—' in line:
                    parts = line.split('—')

                    if len(parts) == 2:
                        team1 = parts[0].strip()
                        team2 = parts[1].strip()

                        if team1 and team2 and any(c.isalpha() for c in team1) and any(c.isalpha() for c in team2):

                            j = i + 1
                            odds_found = []

                            while j < len(lines) and len(odds_found) < 2:
                                curr = lines[j].strip()

                                if not curr or ':' in curr or '—' in curr:
                                    j += 1
                                    continue

                                numbers = re.findall(r'\b\d+\.\d+\b', curr)

                                for num in numbers:
                                    val = float(num)
                                    if val > 1.0:
                                        odds_found.append(val)
                                        if len(odds_found) == 2:
                                            break

                                j += 1

                            if len(odds_found) >= 2:
                                match_name = f"{team1} vs {team2}"
                                events.append({
                                    "match": match_name,
                                    "odds": odds_found[:2]
                                })

                                print(f"  {match_name} | {odds_found[0]}, {odds_found[1]}")

                                i = j
                                continue

                i += 1

            print(f"Fonbet Esports: собрано {len(events)} матчей.")
            return events

        except Exception as e:
            print(f"  Попытка {attempt+1} не удалась: {e}")
            if driver:
                driver.quit()
            time.sleep(5)

        finally:
            if driver:
                driver.quit()

    print("❌ Fonbet Esports: не удалось запустить Chrome после 3 попыток.")
    return []