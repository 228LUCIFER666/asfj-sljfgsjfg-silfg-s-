import time, requests, re, urllib3
from fonbet_esports_parser_v2 import get_fonbet_esports_odds
from polymarket_esports_parser_v2 import get_polymarket_esports_odds
urllib3.disable_warnings()

TOKEN = "8481745931:AAG_e4Dijnv_sFoYkXIe0ZFSZ34yeSnuoWs"
CHAT_ID = "1088479582"
TOTAL_BUDGET = 2000
MAX_PER_RUN = 5
sent = {}

SYNONYMS = {
    "1win":"1w team","1w team":"1win","fnatic":"fnatic","vitality":"team vitality",
    "team vitality":"vitality","nigma galaxy":"nigma galaxy","nigma":"nigma galaxy",
    "team lynx":"lynx","lynx":"team lynx","astralis":"astralis","g2 esports":"g2",
    "g2":"g2 esports","natus vincere":"navi","navi":"natus vincere",
    "faze clan":"faze","faze":"faze clan","furia esports":"furia",
    "furia":"furia esports","team heretics":"heretics","heretics":"team heretics",
    "t1":"t1","gen.g esports":"gen.g","gen.g":"gen.g esports","dplus kia":"dplus",
    "dplus":"dplus kia",
}
def apply_synonyms(name): return SYNONYMS.get(name.lower().strip(), name).strip()

def log(msg, level="INFO"): print(f"[{time.strftime('%H:%M:%S')}] {level} | {msg}")

def send_message(text):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e: log(f"TG error: {e}", "ERROR")

def profit(k1,k2): return (1 - (1/k1 + 1/k2))*100
def stakes(k1,k2,budget):
    s1 = budget*k2/(k1+k2); s2 = budget - s1; net = s1*k1 - budget
    return round(s1,2), round(s2,2), round(net,2)

def clean(text):
    text = text.lower()
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\b(academy|youth|team|esports|gaming|club)\b', '', text)
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_teams(match_str):
    if " vs " not in match_str: return None, None
    a, b = match_str.split(" vs ", 1)
    return clean(a), clean(b)

def team_key(name):
    words = name.split()
    return ' '.join(w[:2] if len(w)>2 else w for w in words)

def match_events(fb_match, pm_match):
    fb1, fb2 = extract_teams(fb_match)
    pm1, pm2 = extract_teams(pm_match)
    if not fb1 or not pm1: return False
    fb1=apply_synonyms(fb1); fb2=apply_synonyms(fb2)
    pm1=apply_synonyms(pm1); pm2=apply_synonyms(pm2)
    bad = {'tbd','tba','over','under','yes','no'}
    if any(t in bad for t in [fb1, fb2, pm1, pm2]): return False
    k1,k2 = team_key(fb1), team_key(fb2)
    p1,p2 = team_key(pm1), team_key(pm2)
    def similar(a,b): return a==b or (a and b and (a in b or b in a))
    return (similar(k1,p1) and similar(k2,p2)) or (similar(k1,p2) and similar(k2,p1))

def find_arbs():
    global sent
    log("Проверка вилок...")
    try:
        fonbet = get_fonbet_esports_odds()
        poly = get_polymarket_esports_odds()
    except ImportError as e: log(f"Не найден модуль: {e}", "ERROR"); return
    log(f"Fonbet: {len(fonbet)} матчей, Polymarket: {len(poly)} матчей")
    sent_now = 0
    for fb in fonbet:
        best_profit = -100
        best_kf = best_kp = None
        for pm in poly:
            if not match_events(fb['match'], pm['match']): continue
            kf1,kf2 = fb['odds']; kp1,kp2 = pm['odds']
            if min(kf1,kf2,kp1,kp2)<1.2 or max(kf1,kf2,kp1,kp2)>5.0: continue
            p1 = profit(kf1,kp2)
            if p1>best_profit: best_profit=p1; best_kf,best_kp=kf1,kp2
            p2 = profit(kf2,kp1)
            if p2>best_profit: best_profit=p2; best_kf,best_kp=kf2,kp1
        if best_profit <= 1: continue
        match_key = clean(fb['match'])
        if match_key in sent and sent[match_key]>=best_profit: continue
        kf,kp = best_kf,best_kp
        s1,s2,net = stakes(kf,kp,TOTAL_BUDGET)
        league = fb.get('league','Esports')
        msg = (f"🔥 ВИЛКА ({league})\n{fb['match']}\n\n"
               f"📌 Fonbet: {kf}\n📌 Polymarket: {kp}\n\n"
               f"💰 Ставки: {s1} / {s2}\n📈 Профит: {best_profit:.2f}% | +{net} RUB")
        log(f"{fb['match']} | {best_profit:.2f}%", "ARB")
        send_message(msg)
        sent[match_key] = best_profit
        sent_now += 1
        if sent_now >= MAX_PER_RUN: return