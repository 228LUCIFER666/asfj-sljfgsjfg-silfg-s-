import requests

URL = "https://line-lb54-w.bk6bba-resources.com/ma/events/list"

# Актуальные киберспортивные sportId (61 штука)
ESPORT_IDS = {
    78562, 78691, 82460, 86077, 87433, 99029, 99302, 99432, 104719, 105055,
    108404, 108900, 115130, 115232, 118783, 119178, 119473, 120197, 121042,
    124218, 128301, 133266, 134976, 135675, 136923, 136924, 136925, 137074,
    137533, 137584, 137756, 137757, 138347, 138393, 138512, 139083, 139876,
    140053, 140368, 140428, 140454, 140677, 140828, 140830, 140837, 141081,
    141154, 141188, 141206, 141303, 141348, 141354, 141367
}

# Пары factorId для основного исхода (П1, П2)
WIN_FACTOR_PAIRS = [
    (910, 912),   # CS:GO, частично LoL
    (921, 923),   # Dota 2
    (3262, 3263), # Dota 2 (альтернативный)
    (1696, 1697), # вероятно LoL/CS:GO
]

# Маркеры дисциплин (оставляем без изменений)
LOL_MARKERS = [
    "invictus", "anyone's legend", "weibo", "top esports", "ninjas in pyjamas",
    "jd gaming", "team we", "bilibili", "thundertalk", "lgd", "ultra prime",
    "edward gaming", "lng", "nongshim", "t1", "kt rolster", "hanwha",
    "gen.g", "dplus", "fearx", "dn soopers", "brion", "krx", "challengers",
    "flyquest", "team liquid", "titan esports club"
]
CSGO_MARKERS = [
    "vitality", "fut esports", "astralis", "g2 esports", "natus vincere",
    "faze", "furia", "gamerlegion", "illwill", "johnny speeds",
    "nemiga", "eternal fire", "sharks esports", "gentle mates",
    "astral", "9ine", "team 33", "magic", "tricked", "100 thieves",
    "tdk", "passion", "fokus", "heretics", "los heretics",
    "giantx", "ucam", "fnatic", "shifters", "galions", "solary",
    "sk gaming", "pcific", "karmine corp", "bbl", "eternal fire",
    "miami heretics", "vancouver surge", "toronto koi", "optic texas",
    "g2 minnesota", "falcons force", "sharks", "havu gaming",
    "navi junior", "algo", "aeterna", "yawara", "alzon",
    "cloud9", "dignitas", "exile", "onion team", "virtus.pro",
    "team yandex", "mvk", "ground zero gaming", "big", "teamorangegaming",
    "anonymo esports", "docisk", "once upon a team", "dynasty",
    "pcific", "su esports", "vicigaming", "cloud dawning",
    "ursa", "havu gaming", "prestige esport", "prestige",
    "kru esports", "100 thieves", "xlg", "titan esports",
    "mouz", "spirit", "g2 ares"
]
DOTA_MARKERS = [
    "lynx", "south america rejects", "power rangers", "l1ga team",
    "nigma galaxy", "1w team", "1win", "xtreme gaming", "roar gaming",
    "yakult brothers", "mideng dreamer", "team refuser", "team resilience",
    "tundra esports"
]
VALORANT_MARKERS = [
    "sentinels", "100 thieves", "loud", "cloud9", "drx", "paper rex",
    "leviatan", "paiN gaming", "gen.g esports", "team secret",
    "nongshim redforce", "global esports", "t1", "full sense",
    "sygaming", "edward gaming"
]

def classify_league(team1, team2, competition):
    combined = f"{team1} {team2} {competition}".lower()
    if any(m in combined for m in LOL_MARKERS):
        return "LoL"
    if any(m in combined for m in CSGO_MARKERS):
        return "CS:GO"
    if any(m in combined for m in DOTA_MARKERS):
        return "Dota 2"
    if any(m in combined for m in VALORANT_MARKERS):
        return "Valorant"
    return None

def get_fonbet_esports_odds():
    print("Fonbet API: запуск...")

    try:
        r = requests.get(URL, params={
            "lang": "ru",
            "version": "0",
            "scopeMarket": "1600"
        }, timeout=10)

        if r.status_code != 200:
            print("Ошибка запроса:", r.status_code)
            return []

        data = r.json()
        events = data.get("events", [])
        custom_factors = data.get("customFactors", [])

        print(f"events: {len(events)}")
        print(f"customFactors: {len(custom_factors)}")

        # eventId → коэффициенты (основной исход)
        odds_by_event = {}
        for block in custom_factors:
            try:
                event_id = block.get("e") or block.get("eventId")
                if not event_id:
                    continue
                factors = block.get("factors", [])
                if not factors:
                    continue

                # Проверяем все известные пары factorId для основного исхода
                for pid1, pid2 in WIN_FACTOR_PAIRS:
                    val1 = None
                    val2 = None
                    for item in factors:
                        fid = item.get("f") or item.get("factorId")
                        v = item.get("v")
                        if fid == pid1 and isinstance(v, (int, float)):
                            val1 = v
                        elif fid == pid2 and isinstance(v, (int, float)):
                            val2 = v
                        if val1 is not None and val2 is not None:
                            break
                    if val1 and val2 and 1.2 < val1 < 5 and 1.2 < val2 < 5:
                        odds_by_event[event_id] = [val1, val2]
                        break  # нашли нужную пару, другие не проверяем
            except:
                continue

        print(f"odds_by_event: {len(odds_by_event)}")

        results = []
        for ev in events:
            try:
                event_id = ev.get("id")
                if event_id not in odds_by_event:
                    continue

                team1 = ev.get("team1")
                team2 = ev.get("team2")
                if not team1 or not team2:
                    continue

                sport_id = ev.get("sportId")
                if sport_id not in ESPORT_IDS:
                    continue

                competition = ev.get("competitionName") or ""
                league = classify_league(team1, team2, competition)
                if league is None:
                    continue

                odds = odds_by_event[event_id]
                match = f"{team1} vs {team2}"
                print(f"[{league}] {match} {odds}")
                results.append({
                    "match": match,
                    "odds": odds,
                    "league": league
                })
            except:
                continue

        print(f"\n✅ Найдено матчей: {len(results)}")
        return results

    except Exception as e:
        print("❌ Глобальная ошибка:", e)
        return []


if __name__ == "__main__":
    res = get_fonbet_esports_odds()
    print("\nРезультат:")
    for r in res:
        print(f"[{r['league']}] {r['match']} : {r['odds']}")
    input("\nНажми Enter...")