import time
import re
# Импортируем pyvirtualdisplay
from pyvirtualdisplay import Display
import undetected_chromedriver as uc

def get_fonbet_esports_odds():
    print("Fonbet Esports: запуск парсера...")
    driver = None
    # Запускаем виртуальный дисплей
    display = Display(visible=0, size=(1920, 1080))
    display.start()
    print("  Виртуальный дисплей запущен.")

    for attempt in range(3):
        try:
            # Используем uc.Chrome() вместо старого webdriver
            # Патчим под последний хром, убираем лишнее.
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            # Отключаем отладочные фичи, которые могли мешать
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-features=RendererCodeIntegrity')
            # Явно указываем, где лежит браузер
            options.binary_location = "/usr/bin/chromium"

            print(f"  Попытка {attempt+1}: запуск undetected-chromedriver...")
            driver = uc.Chrome(options=options, version_main=147)

            driver.set_page_load_timeout(45)
            driver.get('https://fon.bet/sports/esports?lang=ru')
            print("  Жду загрузки (18 секунд)...")
            time.sleep(18)

            # ... (остальной код парсинга без изменений) ...
            # Извлекаем текст страницы ровно так же, как и было.
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
            print(f"  Попытка {attempt+1} не удалась: {e}")
            if driver:
                driver.quit()
            time.sleep(8)
        finally:
            if driver:
                driver.quit()

    print("❌ Fonbet Esports: не удалось запустить Chrome после 3 попыток.")
    # Останавливаем виртуальный дисплей в конце
    display.stop()
    return []