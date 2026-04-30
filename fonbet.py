import requests
import urllib3

# Отключаем предупреждения об SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://line-lb54-w.bk6bba-resources.com/ma/events/list"

# Полный список ID киберспорта
ESPORT_IDS = {
    78562, 78691, 82460, 86077, 87433, 99029, 99302, 99432, 104719, 105055,
    108404, 108900, 115130, 115232, 118783, 119178, 119473, 120197, 121042,
    124218, 128301, 133266, 134976, 135675, 136923, 136924, 136925, 137074,
    137533, 137584, 137756, 137757, 138347, 138393, 138512, 139083, 139876,
    140053, 140368, 140428, 140454, 140677, 140828, 140830, 140837, 141081,
    141154, 141188, 141206, 141303, 141348, 141354, 141367
}

SPORT_ID_MAP = {
    78562: "LoL",
    78691: "CS:GO",
    82460: "Dota 2",
    140837: "Valorant"
}

WIN_FACTOR_PAIRS = [
    (910, 912), (921, 923), (930, 931), (1696, 1697), (1736, 1737),
]

def get_fonbet_esports_odds():
    print("Fonbet API: запуск (Ультра-охват v2.2)...")
    try:
        r = requests.get(URL, params={
            "lang": "ru", 
            "version": "0", 
            "scopeMarket": "1600"
        }, timeout=15, verify=False)
        
        if r.status_code != 200:
            print(f"Ошибка сервера: {r.status_code}")
            return []

        data = r.json()
        events = data.get("events", [])
        custom_factors = data.get("customFactors", [])
        
        print(f"Событий в линии: {len(events)}")

        # 1. Собираем коэффициенты
        odds_by_event = {}
        for block in custom_factors:
            event_id = block.get("e") or block.get("eventId")
            factors = block.get("factors", [])
            
            for (id1, id2) in WIN_FACTOR_PAIRS:
                v1 = v2 = None
                for item in factors:
                    fid = item.get("f") or item.get("factorId")
                    if fid == id1: v1 = item.get("v")
                    elif fid == id2: v2 = item.get("v")
                
                if v1 is not None and v2 is not None:
                    try:
                        v1, v2 = float(v1), float(v2)
                        if v1 > 1.01 and v2 > 1.01:
                            odds_by_event[event_id] = [v1, v2]
                            break
                    except: continue

        # 2. Формируем список матчей
        results = []
        for ev in events:
            sport_id = ev.get("sportId")
            event_id = ev.get("id")
            parent_id = ev.get("parentId")

            if sport_id in ESPORT_IDS:
                team1 = ev.get("team1")
                team2 = ev.get("team2")
                
                # Ищем кэфы сначала по ID события, затем по Parent ID
                current_odds = odds_by_event.get(event_id) or odds_by_event.get(parent_id)

                if not team1 or not team2 or not current_odds:
                    continue

                # Определяем лигу
                league = SPORT_ID_MAP.get(sport_id, "Esports")
                if league == "Esports":
                    comp_name = (ev.get("competitionName") or "").lower()
                    if "dota" in comp_name: league = "Dota 2"
                    elif any(x in comp_name for x in ["counter", "cs:", "cs2"]): league = "CS:GO"
                    elif any(x in comp_name for x in ["league of legends", "lol"]): league = "LoL"
                    elif "valorant" in comp_name: league = "Valorant"

                results.append({
                    "match": f"{team1} vs {team2}",
                    "odds": current_odds,
                    "league": league
                })

        # Убираем дубликаты (бывает, когда Parent и Child события попадают вместе)
        unique_results = []
        seen_matches = set()
        for res in results:
            match_key = f"{res['match']}_{res['league']}"
            if match_key not in seen_matches:
                unique_results.append(res)
                seen_matches.add(match_key)

        print(f"✅ Найдено уникальных матчей: {len(unique_results)}")
        return unique_results

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

if __name__ == "__main__":
    # Тестовый запуск
    matches = get_fonbet_esports_odds()
    
    print("\n--- ПЕРВЫЕ 20 МАТЧЕЙ ---")
    for i, m in enumerate(matches[:20]):
        print(f"{i+1}. [{m['league']}] {m['match']} | {m['odds']}")
    
    # Добавлена пауза для консоли Windows
    input("\nНажми Enter, чтобы выйти...")