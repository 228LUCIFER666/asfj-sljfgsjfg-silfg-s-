import time
import requests
import traceback
import urllib3
import re

from fonbet_esports_parser_v2 import get_fonbet_esports_odds
from polymarket_esports_parser_v2 import get_polymarket_esports_odds

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------- КОНФИГ -------------------
TOKEN = "8481745931:AAG_e4Dijnv_sFoYkXIe0ZFSZ34yeSnuoWs"
CHAT_ID = "1088479582"
TOTAL_BUDGET = 2000

sent = set()

# ------------------- ЛОГ -------------------
def log(msg, level="INFO"):
    now = time.strftime("%H:%M:%S")
    print(f"[{now}] {level} | {msg}")

# ------------------- TELEGRAM -------------------
def send_message(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text},
            timeout=10
        )
    except Exception as e:
        log(f"Telegram ошибка: {e}", "ERROR")

# ------------------- МАТЕМАТИКА -------------------
def calculate_profit(k1, k2):
    try:
        return (1 - (1/k1 + 1/k2)) * 100
    except:
        return -100

def calculate_stakes(k1, k2, budget):
    s1 = budget * k2 / (k1 + k2)
    s2 = budget - s1
    profit = s1 * k1 - budget
    return round(s1, 2), round(s2, 2), round(profit, 2)

# ------------------- УМНЫЙ МАТЧИНГ -------------------
def normalize(text):
    text = text.lower()
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_teams(match):
    if " vs " not in match:
        return None, None
    t1, t2 = match.split(" vs ", 1)
    return normalize(t1), normalize(t2)

def match_events(fb_match, pm_match):
    fb1, fb2 = extract_teams(fb_match)
    pm1, pm2 = extract_teams(pm_match)

    if not fb1 or not pm1:
        return False

    def score(a, b):
        return len(set(a.split()) & set(b.split()))

    direct = score(fb1, pm1) + score(fb2, pm2)
    cross = score(fb1, pm2) + score(fb2, pm1)

    return max(direct, cross) >= 1

# ------------------- ПОИСК ВИЛОК -------------------
def find_arbs():
    global sent

    log("Проверка вилок...", "INFO")

    fonbet_data = get_fonbet_esports_odds()
    poly_data = get_polymarket_esports_odds()

    log(f"Fonbet: {len(fonbet_data)}, Polymarket: {len(poly_data)}", "INFO")

    for fb in fonbet_data:
        for pm in poly_data:

            if not match_events(fb['match'], pm['match']):
                continue

            combos = [
                (fb['odds'][0], pm['odds'][0], "F1-P1"),
                (fb['odds'][1], pm['odds'][1], "F2-P2"),
                (fb['odds'][0], pm['odds'][1], "F1-P2"),
                (fb['odds'][1], pm['odds'][0], "F2-P1"),
            ]

            for kf, kp, tag in combos:
                profit = calculate_profit(kf, kp)

                if profit > 0.5:
                    s1, s2, net = calculate_stakes(kf, kp, TOTAL_BUDGET)

                    key = f"{fb['match']}|{tag}"

                    if key in sent:
                        continue

                    msg = (
                        f"🔥 ВИЛКА\n"
                        f"{fb['match']}\n\n"
                        f"📌 Fonbet: {kf}\n"
                        f"📌 Polymarket: {kp}\n\n"
                        f"💰 Ставки: {s1} / {s2} RUB\n"
                        f"📈 Профит: {profit:.2f}% | +{net} RUB"
                    )

                    log(f"{fb['match']} | {tag} | {profit:.2f}%", "ARB")
                    send_message(msg)

                    sent.add(key)
                    time.sleep(0.5)

# ------------------- ГЛАВНЫЙ ЦИКЛ -------------------
if __name__ == "__main__":
    log("Бот запущен", "START")

    while True:
        try:
            find_arbs()
        except Exception as e:
            log(f"Ошибка: {e}", "ERROR")
            traceback.print_exc()

        time.sleep(60)