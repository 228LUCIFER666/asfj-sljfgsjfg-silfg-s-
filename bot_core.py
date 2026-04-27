import time
import requests
import urllib3
import re
from fonbet_esports_parser_v2 import get_fonbet_esports_odds
from polymarket_esports_parser_v2 import get_polymarket_esports_odds

urllib3.disable_warnings()

# ------------------- CONFIG -------------------
TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
TOTAL_BUDGET = 2000

sent = {}

# ------------------- LOG -------------------
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
        log(f"TG error: {e}", "ERROR")

# ------------------- MATH -------------------
def calculate_profit(k1, k2):
    return (1 - (1/k1 + 1/k2)) * 100

def calculate_stakes(k1, k2, budget):
    s1 = budget * k2 / (k1 + k2)
    s2 = budget - s1
    profit = s1 * k1 - budget
    return round(s1, 2), round(s2, 2), round(profit, 2)

# ------------------- NORMALIZE -------------------
def normalize(text):
    text = text.lower()
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\bacademy\b|\byouth\b|\bteam\b', '', text)
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_teams(match):
    if " vs " not in match:
        return None, None
    t1, t2 = match.split(" vs ", 1)
    return normalize(t1), normalize(t2)

# ------------------- MATCHING -------------------
def match_events(fb_match, pm_match):
    fb1, fb2 = extract_teams(fb_match)
    pm1, pm2 = extract_teams(pm_match)

    if not fb1 or not pm1:
        return False

    def score(a, b):
        return len(set(a.split()) & set(b.split()))

    direct = score(fb1, pm1) + score(fb2, pm2)
    cross = score(fb1, pm2) + score(fb2, pm1)

    return max(direct, cross) >= 2

# ------------------- MAIN -------------------
def find_arbs():
    global sent

    log("Проверка вилок...")

    fonbet = get_fonbet_esports_odds()
    poly = get_polymarket_esports_odds()

    log(f"Fonbet: {len(fonbet)}, Polymarket: {len(poly)}")

    MAX_PER_RUN = 5
    sent_now = 0

    for fb in fonbet:
        best_profit = 0
        best_data = None

        for pm in poly:
            if not match_events(fb['match'], pm['match']):
                continue

            kf1, kf2 = fb['odds']
            kp1, kp2 = pm['odds']

            # 🔥 фильтр мусора
            if min(kf1, kf2, kp1, kp2) < 1.3:
                continue
            if max(kf1, kf2, kp1, kp2) > 4.5:
                continue

            p1 = calculate_profit(kf1, kp2)
            p2 = calculate_profit(kf2, kp1)

            if p1 > best_profit:
                best_profit = p1
                best_data = (kf1, kp2)

            if p2 > best_profit:
                best_profit = p2
                best_data = (kf2, kp1)

        match_key = normalize(fb['match'])

        # 🔥 анти-спам + обновление только если профит вырос
        if best_profit > 3:
            if match_key in sent and sent[match_key] >= best_profit:
                continue

            kf, kp = best_data
            s1, s2, net = calculate_stakes(kf, kp, TOTAL_BUDGET)

            msg = (
                f"🔥 ВИЛКА\n"
                f"{fb['match']}\n\n"
                f"📌 Fonbet: {kf}\n"
                f"📌 Polymarket: {kp:.2f}\n\n"
                f"💰 Ставки: {s1} / {s2}\n"
                f"📈 Профит: {best_profit:.2f}% | +{net} RUB"
            )

            log(f"{fb['match']} | {best_profit:.2f}%", "ARB")

            send_message(msg)
            sent[match_key] = best_profit

            sent_now += 1
            if sent_now >= MAX_PER_RUN:
                return

# ------------------- LOOP -------------------
if __name__ == "__main__":
    log("Бот запущен", "START")

    while True:
        try:
            find_arbs()
        except Exception as e:
            log(f"Ошибка: {e}", "ERROR")

        time.sleep(60)