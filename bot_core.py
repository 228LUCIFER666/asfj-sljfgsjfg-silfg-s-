import time
import requests
import re
import urllib3
from fonbet_esports_parser_v2 import get_fonbet_esports_odds
from polymarket_esports_parser_v2 import get_polymarket_esports_odds

urllib3.disable_warnings()

# ---------- CONFIG ----------
TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
TOTAL_BUDGET = 2000
MAX_PER_RUN = 5

sent = {}

# ---------- LOG ----------
def log(msg, level="INFO"):
    print(f"[{time.strftime('%H:%M:%S')}] {level} | {msg}")

# ---------- TELEGRAM ----------
def send_message(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text},
            timeout=10
        )
    except Exception as e:
        log(f"TG error: {e}", "ERROR")

# ---------- MATH ----------
def profit(k1, k2):
    return (1 - (1/k1 + 1/k2)) * 100

def stakes(k1, k2, budget):
    s1 = budget * k2 / (k1 + k2)
    s2 = budget - s1
    net = s1 * k1 - budget
    return round(s1, 2), round(s2, 2), round(net, 2)

# ---------- NORMALIZE ----------
def clean(name):
    name = name.lower()
    name = re.sub(r'\([^)]*\)', '', name)
    name = re.sub(r'\bacademy\b|\byouth\b|\bteam\b|\besports\b|\bgaming\b', '', name)
    name = re.sub(r'[^a-z0-9 ]', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def extract_teams(match_str):
    if " vs " not in match_str:
        return None, None
    a, b = match_str.split(" vs ", 1)
    return clean(a), clean(b)

# ---------- MATCHING (улучшенный) ----------
def match_events(fb_match, pm_match):
    fb1, fb2 = extract_teams(fb_match)
    pm1, pm2 = extract_teams(pm_match)
    if not fb1 or not pm1:
        return False

    def score(x, y):
        # количество общих слов + бонус за точное совпадение
        wx = set(x.split())
        wy = set(y.split())
        base = len(wx & wy)
        if x == y:
            base += 10
        return base

    direct = score(fb1, pm1) + score(fb2, pm2)
    cross  = score(fb1, pm2) + score(fb2, pm1)

    # Порог: минимум 2 общих слова (или одно, но точное совпадение)
    return direct >= 2 or cross >= 2

# ---------- MAIN ----------
def find_arbs():
    global sent
    log("Проверка вилок...")

    fonbet = get_fonbet_esports_odds()
    poly   = get_polymarket_esports_odds()
    log(f"Fonbet: {len(fonbet)} матчей, Polymarket: {len(poly)} матчей")

    sent_now = 0

    for fb in fonbet:
        best_profit = -100
        best_kf = best_kp = None

        for pm in poly:
            if not match_events(fb['match'], pm['match']):
                continue

            kf1, kf2 = fb['odds']
            kp1, kp2 = pm['odds']

            # Фильтр мусора
            if min(kf1, kf2, kp1, kp2) < 1.3 or max(kf1, kf2, kp1, kp2) > 4.5:
                continue

            # Две возможные вилки
            p1 = profit(kf1, kp2)
            if p1 > best_profit:
                best_profit = p1
                best_kf, best_kp = kf1, kp2

            p2 = profit(kf2, kp1)
            if p2 > best_profit:
                best_profit = p2
                best_kf, best_kp = kf2, kp1

        if best_profit <= 3:
            continue

        match_key = clean(fb['match'])
        if match_key in sent and sent[match_key] >= best_profit:
            continue

        kf, kp = best_kf, best_kp
        s1, s2, net = stakes(kf, kp, TOTAL_BUDGET)

        msg = (
            f"🔥 ВИЛКА\n"
            f"{fb['match']}\n\n"
            f"📌 Fonbet: {kf}\n"
            f"📌 Polymarket: {kp}\n\n"
            f"💰 Ставки: {s1} / {s2}\n"
            f"📈 Профит: {best_profit:.2f}% | +{net} RUB"
        )

        log(f"{fb['match']} | {best_profit:.2f}%", "ARB")
        send_message(msg)
        sent[match_key] = best_profit
        sent_now += 1
        if sent_now >= MAX_PER_RUN:
            return

# ---------- LOOP ----------
if __name__ == "__main__":
    log("Бот запущен", "START")
    while True:
        try:
            find_arbs()
        except Exception as e:
            log(f"Ошибка: {e}", "ERROR")
        time.sleep(60)