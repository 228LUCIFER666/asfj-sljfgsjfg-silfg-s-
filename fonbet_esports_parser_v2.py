import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re

def get_fonbet_esports_odds():
    print("Fonbet Esports: запуск парсера...")
    driver = None

    for attempt in range(3):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--window-size=1280,800')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            options.add_argument('--disable-features=RendererCodeIntegrity')
            options.add_argument('--disable-gpu')
            options.add_argument('--remote-debugging-port=0')

            # Задаём путь к Chromium (для Linux-окружения)
            options.binary_location = "/usr/bin/chromium"

            # Устанавливаем драйвер
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.get('https://fon.bet/sports/esports?lang=ru')
            print("Жду загрузки 12 секунд...")
            time.sleep(12)

            body_text = driver.find_element("tag name", "body").text
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
                                events.append({"match": match_name, "odds": odds_found[:2]})
                                print(f"  {match_name} | {odds_found[0]}, {odds_found[1]}")
                                i = j
                                continue
                i += 1

            print(f"Fonbet Esports: собрано {len(events)} матчей.")
            return events

        except Exception as e:
            print(f"Попытка {attempt+1} не удалась: {e}")
            if driver:
                driver.quit()
            time.sleep(3)
        finally:
            if driver:
                driver.quit()

    print("❌ Fonbet Esports: не удалось запустить Chrome после 3 попыток.")
    return []