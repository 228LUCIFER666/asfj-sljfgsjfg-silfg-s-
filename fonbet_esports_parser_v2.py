import requests

URL = "https://line-lb54-w.bk6bba-resources.com/ma/events/list"

# 🔥 ключевые слова для киберспорта
ESPORTS_KEYWORDS = [
    "esports", "gaming", "team", "academy", "clan",
    "navi", "g2", "fnatic", "vitality", "faze",
    "liquid", "astralis", "heroic", "spirit",
    "valorant", "cs", "dota", "league"
]


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

        # 🔥 eventId → коэффициенты
        odds_by_event = {}

        for block in custom_factors:
            try:
                event_id = block.get("e") or block.get("eventId")
                if not event_id:
                    continue

                factors = block.get("factors", [])
                odds = []

                for item in factors:
                    val = item.get("v")

                    if isinstance(val, (int, float)) and 1.1 < val < 10:
                        odds.append(val)

                        if len(odds) == 2:
                            break

                if len(odds) == 2:
                    odds_by_event[event_id] = odds

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

                # 🔥 ФИЛЬТР КИБЕРСПОРТА
                name = f"{team1} {team2}".lower()
                if not any(k in name for k in ESPORTS_KEYWORDS):
                    continue

                odds = odds_by_event[event_id]

                match = f"{team1} vs {team2}"
                print(match, odds)

                results.append({
                    "match": match,
                    "odds": odds
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
        print(r)

    input("\nНажми Enter...")