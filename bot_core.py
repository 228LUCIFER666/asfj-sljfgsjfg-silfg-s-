import time
import requests
import traceback
import urllib3
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

# ------------------- ТОЧНЫЙ МАТЧИНГ -------------------
def extract_teams_from_match(match_name):
    if " vs " in match_name:
        parts = match_name.split(" vs ", 1)
        if len(parts) == 2:
            return parts[0].strip().lower(), parts[1].strip().lower()
    return None, None

def normalize_team_name(team_name):
    import re
    team_name = re.sub(r'\([^)]*\)', '', team_name)
    team_name = re.sub(r'\s+', ' ', team_name)
    return team_name.strip().lower()

def match_events(fb_match, pm_match):
    fb_team1, fb_team2 = extract_teams_from_match(fb_match)
    pm_team1, pm_team2 = extract_teams_from_match(pm_match)
    
    if not fb_team1 or not pm_team1:
        return False
    
    fb_team1 = normalize_team_name(fb_team1)
    fb_team2 = normalize_team_name(fb_team2)
    pm_team1 = normalize_team_name(pm_team1)
    pm_team2 = normalize_team_name(pm_team2)
    
    return (fb_team1 == pm_team1 and fb_team2 == pm_team2) or \
           (fb_team1 == pm_team2 and fb_team2 == pm_team1)

# ------------------- ПОИСК ВИЛОК -------------------
def find_arbs():
    global sent

    log("Проверка вилок...", "INFO")

    fonbet_data = get_fonbet_esports_odds()
    poly_data = get_polymarket_esports_odds()

    log(f"Fonbet: {len(fonbet_data)}, Polymarket: {len(poly_data)}", "INFO")

    candidates = []

    for fb in fonbet_data:
        team1, team2 = extract_teams_from_match(fb['match'])
        
        for pm in poly_data:
            if not match_events(fb['match'], pm['match']):
                continue
            
            profit1 = calculate_profit(fb['odds'][0], pm['odds'][1])
            
            if profit1 > 0.5:
                s1, s2, net = calculate_stakes(fb['odds'][0], pm['odds'][1], TOTAL_BUDGET)
                key = f"{fb['match']}_FONBET_{team1}_POLY_{team2}"
                
                if key not in sent:
                    msg = (
                        f"🔥 ВИЛКА\n"
                        f"{fb['match']}\n\n"
                        f"📌 Fonbet ({team1}): {fb['odds'][0]}\n"
                        f"📌 Polymarket ({team2}): {pm['odds'][1]:.2f}\n\n"
                        f"💰 Ставки: {s1} / {s2} RUB\n"
                        f"📈 Профит: {profit1:.2f}% | +{net} RUB"
                    )
                    candidates.append((key, profit1, msg))
                    log(f"{fb['match']} | {team1}(F)+{team2}(P) | {profit1:.2f}%", "ARB")
            
            profit2 = calculate_profit(fb['odds'][1], pm['odds'][0])
            
            if profit2 > 0.5:
                s1, s2, net = calculate_stakes(fb['odds'][1], pm['odds'][0], TOTAL_BUDGET)
                key = f"{fb['match']}_FONBET_{team2}_POLY_{team1}"
                
                if key not in sent:
                    msg = (
                        f"🔥 ВИЛКА\n"
                        f"{fb['match']}\n\n"
                        f"📌 Fonbet ({team2}): {fb['odds'][1]}\n"
                        f"📌 Polymarket ({team1}): {pm['odds'][0]:.2f}\n\n"
                        f"💰 Ставки: {s1} / {s2} RUB\n"
                        f"📈 Профит: {profit2:.2f}% | +{net} RUB"
                    )
                    candidates.append((key, profit2, msg))
                    log(f"{fb['match']} | {team2}(F)+{team1}(P) | {profit2:.2f}%", "ARB")
    
    for key, profit, msg in candidates:
        if key not in sent:
            send_message(msg)
            sent.add(key)
            time.sleep(0.5)