import os
import time
import datetime
import requests
import sys
import traceback
import urllib3
from bs4 import BeautifulSoup
from fonbet_esports_parser_v2 import get_fonbet_esports_odds
from polymarket_esports_parser_v2 import get_polymarket_esports_odds

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------- Конфигурация -------------------
TOKEN = "8481745931:AAG_e4Dijnv_sFoYkXIe0ZFSZ34yeSnuoWs"
CHAT_ID = "1088479582"
TOTAL_BUDGET = 2000
sent = set()

# ------------------- Логирование -------------------
def log(message, level="INFO"):
    now = time.strftime("%H:%M:%S")
    prefixes = {
        "INFO": "ℹ️ INFO",
        "WARN": "⚠️ WARN",
        "ERROR": "❌ ERROR",
        "ARB": "🔥 ARB",
        "TG": "📨 TG",
        "PROXY": "🌐 PROXY",
        "START": "🚀 START"
    }
    prefix = prefixes.get(level, f"[{level}]")
    print(f"[{now}] {prefix}  {message}")

def print_banner():
    banner = r"""
    ██╗   ██╗██╗██╗     ███████╗    ██╗   ██╗██████╗ 
    ██║   ██║██║██║     ██╔════╝    ██║   ██║╚════██╗
    ██║   ██║██║██║     ███████╗    ██║   ██║ █████╔╝
    ╚██╗ ██╔╝██║██║     ╚════██║    ██║   ██║ ╚═══██╗
     ╚████╔╝ ██║███████╗███████║    ╚██████╔╝██████╔╝
      ╚═══╝  ╚═╝╚══════╝╚══════╝     ╚═════╝ ╚═════╝ 
    """
    print(banner)
    log("VilSS v3 запущен (серверная версия)", "START")
    log(f"Дата: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "START")
    log("Парсеры: Fonbet + Polymarket | Бюджет: 2000 RUB", "START")
    print("-" * 60)

# ------------------- Отправка в Telegram (без прокси) -------------------
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    for attempt in range(3):
        try:
            resp = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=15)
            if resp.json().get("ok"):
                log("Сообщение отправлено в Telegram", "TG")
                return
            else:
                log(f"Ошибка отправки: {resp.json().get('description', 'неизвестно')}", "ERROR")
        except Exception as e:
            log(f"Попытка {attempt+1}: {e}", "ERROR")
            time.sleep(2)
    log("Не удалось отправить сообщение в Telegram после всех попыток", "ERROR")

# ------------------- Расчёт ставок -------------------
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

# ------------------- Сопоставление матчей -------------------
def extract_teams(name):
    name = name.split(':')[-1]
    name = name.split('(')[0].strip()
    for sep in [' vs ', ' против ']:
        if sep in name:
            return [x.strip().lower() for x in name.split(sep, 1)]
    return [w.lower() for w in name.split() if len(w) > 2]

def normalize_team(team_name):
    words = team_name.replace('_', ' ').lower().split()
    stop = {'team', 'esports', 'gaming', 'school', 'university', 'academy', 
            'white', 'black', 'red', 'blue', 'club', 'e-sports', 'the'}
    return {w for w in words if w not in stop and len(w) > 1}

def match_events(name1, name2):
    teams1 = extract_teams(name1)
    teams2 = extract_teams(name2)

    if len(teams1) < 2 or len(teams2) < 2:
        set1 = set(w.lower() for w in name1.split() if len(w) > 2)
        set2 = set(w.lower() for w in name2.split() if len(w) > 2)
        return len(set1 & set2) >= 2

    n1a, n1b = normalize_team(teams1[0]), normalize_team(teams1[1])
    n2a, n2b = normalize_team(teams2[0]), normalize_team(teams2[1])
    match1 = (n1a & n2a) and (n1b & n2b)
    match2 = (n1a & n2b) and (n1b & n2a)
    return match1 or match2

# ------------------- Поиск вилок (последовательный сбор) -------------------
def find_arbs():
    global sent
    log("Проверка вилок...", "INFO")

    # Последовательный запуск для экономии памяти
    fonbet_data = get_fonbet_esports_odds()
    poly_data = get_polymarket_esports_odds()

    log(f"Fonbet: {len(fonbet_data)} матчей, Polymarket: {len(poly_data)} матчей", "INFO")

    candidates = []
    for fb in fonbet_data:
        if ' vs ' in fb['match']:
            team1, team2 = fb['match'].split(' vs ', 1)
        else:
            team1, team2 = '', ''

        for pm in poly_data:
            if not match_events(fb['match'], pm['match']):
                continue

            # П1 Fonbet vs первый исход Polymarket
            profit = calculate_profit(fb['odds'][0], pm['odds'][0])
            if profit > 0.5:
                s1, s2, net = calculate_stakes(fb['odds'][0], pm['odds'][0], TOTAL_BUDGET)
                key = f"{fb['match']}|fb1-pm1"
                msg = (f"🔥 ВИЛКА (Esports)\n"
                       f"{fb['match']}\n"
                       f"Fonbet {team1}: {fb['odds'][0]} | Ставка: {s1} RUB\n"
                       f"Polymarket {pm['outcome_labels'][0]}: {pm['odds'][0]:.2f} | Ставка: {s2} RUB\n"
                       f"Профит: {profit:.2f}% (Чистая прибыль: {net} RUB)")
                candidates.append((key, profit, msg, fb['match']))

            # П2 Fonbet vs второй исход Polymarket
            profit = calculate_profit(fb['odds'][1], pm['odds'][1])
            if profit > 0.5:
                s1, s2, net = calculate_stakes(fb['odds'][1], pm['odds'][1], TOTAL_BUDGET)
                key = f"{fb['match']}|fb2-pm2"
                msg = (f"🔥 ВИЛКА (Esports)\n"
                       f"{fb['match']}\n"
                       f"Fonbet {team2}: {fb['odds'][1]} | Ставка: {s1} RUB\n"
                       f"Polymarket {pm['outcome_labels'][1]}: {pm['odds'][1]:.2f} | Ставка: {s2} RUB\n"
                       f"Профит: {profit:.2f}% (Чистая прибыль: {net} RUB)")
                candidates.append((key, profit, msg, fb['match']))

    best = {}
    for key, profit, msg, match in candidates:
        if key not in best or profit > best[key][0]:
            best[key] = (profit, msg, match)

    for key, (profit, msg, match) in best.items():
        if key not in sent:
            log(f"{match} | профит {profit:.2f}%", "ARB")
            send_message(msg)
            sent.add(key)

# ------------------- Главный цикл -------------------
if __name__ == "__main__":
    print_banner()
    log("Мониторинг запущен", "START")
    while True:
        try:
            find_arbs()
        except Exception as e:
            log(f"Ошибка в find_arbs: {e}", "ERROR")
            traceback.print_exc()
        time.sleep(60)   # пауза между циклами