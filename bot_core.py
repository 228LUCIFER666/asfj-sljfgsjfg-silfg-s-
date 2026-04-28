import time
import requests
import re
import urllib3
from fonbet_esports_parser_v2 import get_fonbet_esports_odds
from polymarket_esports_parser_v2 import get_polymarket_esports_odds

urllib3.disable_warnings()

# ---------- CONFIG ----------
TOKEN = "8481745931:AAG_e4Dijnv_sFoYkXIe0ZFSZ34yeSnuoWs"
CHAT_ID = "1088479582"
TOTAL_BUDGET = 2000
MAX_PER_RUN = 5
DEBUG = False

sent = {}

# ---------- синонимы ----------
SYNONYMS = {
    "1win": "1w team", "1w team": "1win",
    "fnatic": "fnatic", "vitality": "team vitality",
    "team vitality": "vitality", "nigma galaxy": "nigma galaxy",
    "nigma": "nigma galaxy", "team lynx": "lynx", "lynx": "team lynx",
    "astralis": "astralis", "g2 esports": "g2",
    "g2": "g2 esports", "natus vincere": "navi",
    "navi": "natus vincere", "faze clan": "faze",
    "faze": "faze clan", "furia esports": "furia",
    "furia": "furia esports", "team heretics": "heretics",
    "heretics": "team heretics", "t1": "t1",
    "gen.g esports": "gen.g", "gen.g": "gen.g esports",
    "dplus kia": "dplus", "dplus": "dplus kia",
}

def apply_synonyms(name):
    key = name.lower().strip()
    return SYNONYMS.get(key, name).strip()

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
def clean(text):
    text = text.lower()
    text = re.sub(r'\([^)]*\)', '', text)                 # удаляем скобки
    text = re.sub(r'\b(team|esports|gaming|club)\b', '', text)
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_teams(match_str):
    if " vs " not in match_str:
        return None, None
    a, b = match_str.split(" vs ", 1)
    return clean(a), clean(b)

def team_words(name):
    """Возвращает множество слов (не обрезанных до первых двух букв)"""
    return set(name.split())

# ---------- MATCHING (ужесточённый) ----------
def match_events(fb_match, pm_match):
    fb1_raw, fb2_raw = extract_teams(fb_match)
    pm1_raw, pm2_raw = extract_teams(pm_match)
    if not fb1_raw or not pm1_raw:
        return None

    fb1 = apply_synonyms(fb1_raw)
    fb2 = apply_synonyms(fb2_raw)
    pm1 = apply_synonyms(pm1_raw)
    pm2 = apply_synonyms(pm2_raw)

    bad = {'tbd', 'tba', 'over', 'under', 'yes', 'no'}
    if any(t in bad for t in [fb1, fb2, pm1, pm2]):
        return None

    wfb1 = team_words(fb1)
    wfb2 = team_words(fb2)
    wpm1 = team_words(pm1)
    wpm2 = team_words(pm2)

    def teams_match(w1, w2, min_common=2):
        """True, если количество общих слов >= min_common"""
        return len(w1 & w2) >= min_common

    direct = teams_match(wfb1, wpm1) and teams_match(wfb2, wpm2)
    cross  = teams_match(wfb1, wpm2) and teams_match(wfb2, wpm1)

    if direct:
        return {
            'fb_team1': fb1_raw, 'fb_team2': fb2_raw,
            'pm_team1': pm1_raw, 'pm_team2': pm2_raw,
            'mapping': 'direct'
        }
    if cross:
        return {
            'fb_team1': fb1_raw, 'fb_team2': fb2_raw,
            'pm_team1': pm2_raw, 'pm_team2': pm1_raw,
            'mapping': 'cross'
        }
    return None

# ---------- MAIN ----------
def find_arbs():
    global sent
    log("Проверка вилок...")

    try:
        fonbet = get_fonbet_esports_odds()
        poly   = get_polymarket_esports_odds()
    except ImportError as e:
        log(f"Не найден модуль парсера: {e}", "ERROR")
        return

    log(f"Fonbet: {len(fonbet)} матчей, Polymarket: {len(poly)} матчей")

    sent_now = 0

    for fb in fonbet:
        best_profit = -100
        best_kf = best_kp = None
        best_team_fb = best_team_pm = None

        for pm in poly:
            mapping = match_events(fb['match'], pm['match'])
            if not mapping:
                continue

            kf1, kf2 = fb['odds']
            kp1, kp2 = pm['odds']

            if min(kf1, kf2, kp1, kp2) < 1.15 or max(kf1, kf2, kp1, kp2) > 5.0:
                continue

            if mapping['mapping'] == 'direct':
                p1 = profit(kf1, kp2)
                if p1 > best_profit:
                    best_profit = p1
                    best_kf, best_kp = kf1, kp2
                    best_team_fb = mapping['fb_team1']
                    best_team_pm = mapping['pm_team2']

                p2 = profit(kf2, kp1)
                if p2 > best_profit:
                    best_profit = p2
                    best_kf, best_kp = kf2, kp1
                    best_team_fb = mapping['fb_team2']
                    best_team_pm = mapping['pm_team1']
            else:  # cross
                p1 = profit(kf1, kp1)
                if p1 > best_profit:
                    best_profit = p1
                    best_kf, best_kp = kf1, kp1
                    best_team_fb = mapping['fb_team1']
                    best_team_pm = mapping['pm_team1']

                p2 = profit(kf2, kp2)
                if p2 > best_profit:
                    best_profit = p2
                    best_kf, best_kp = kf2, kp2
                    best_team_fb = mapping['fb_team2']
                    best_team_pm = mapping['pm_team2']

        if best_profit <= 1:
            continue

        match_key = clean(fb['match'])
        if match_key in sent and sent[match_key] >= best_profit:
            continue

        kf, kp = best_kf, best_kp
        s1, s2, net = stakes(kf, kp, TOTAL_BUDGET)
        league = fb.get('league', 'Esports')

        msg = (
            f"🔥 ВИЛКА ({league})\n"
            f"{fb['match']}\n\n"
            f"📌 Fonbet ({best_team_fb}): {kf}\n"
            f"📌 Polymarket ({best_team_pm}): {kp}\n\n"
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