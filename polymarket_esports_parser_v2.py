import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ------------------- RECURSIVE SEARCH -------------------
def find_events(obj):
    results = []

    if isinstance(obj, dict):
        if 'title' in obj and 'markets' in obj:
            results.append(obj)

        for v in obj.values():
            results.extend(find_events(v))

    elif isinstance(obj, list):
        for item in obj:
            results.extend(find_events(item))

    return results


# ------------------- PARSE ONE LEAGUE -------------------
def parse_league(league):
    print(f"\nЛига: {league}")

    url = f"https://polymarket.com/_next/data/build-TfctsWXpff2fKS/en/esports/{league}/games.json?league={league}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code != 200:
            print("❌ ошибка запроса")
            return []

        data = r.json()

        events = find_events(data)

        print(f"Найдено событий: {len(events)}")

        matches = []

        for event in events:
            try:
                title = event.get('title', '')
                markets = event.get('markets', [])

                if not markets:
                    continue

                title_lower = title.lower()

                # ❌ мусор
                if any(x in title_lower for x in ["odd", "even"]):
                    continue

                for m in markets:
                    outcomes = m.get('outcomes', [])
                    prices = m.get('outcomePrices', [])

                    if len(outcomes) < 2 or len(prices) < 2:
                        continue

                    # команды
                    if isinstance(outcomes[0], str):
                        team1 = outcomes[0]
                        team2 = outcomes[1]
                    elif isinstance(outcomes[0], dict):
                        team1 = outcomes[0].get('title', '')
                        team2 = outcomes[1].get('title', '')
                    else:
                        continue

                    team1_l = team1.lower()
                    team2_l = team2.lower()

                    # ❌ мусор команды
                    if any(x in team1_l or x in team2_l for x in ["yes", "no", "odd", "even"]):
                        continue

                    # --- коэффициенты ---
                    try:
                        prob1 = float(prices[0])
                        prob2 = float(prices[1])

                        if prob1 <= 0.01 or prob2 <= 0.01:
                            continue

                        k1 = 1.0 / prob1
                        k2 = 1.0 / prob2

                    except:
                        continue

                    match_name = f"{team1} vs {team2}"

                    print(f"  {match_name}: {k1:.2f} / {k2:.2f}")

                    matches.append({
                        'match': match_name,
                        'odds': [k1, k2]
                    })

                    break

            except:
                continue

        return matches

    except Exception as e:
        print(f"Ошибка ({league}): {e}")
        return []


# ------------------- MAIN -------------------
def get_polymarket_esports_odds():
    print("Polymarket (CS2 + Dota): загрузка...")

    leagues = ["counter-strike", "dota-2"]

    all_matches = []

    for league in leagues:
        res = parse_league(league)
        all_matches.extend(res)

    print(f"\nPolymarket: всего матчей {len(all_matches)}")
    return all_matches


# ------------------- TEST -------------------
if __name__ == "__main__":
    res = get_polymarket_esports_odds()

    print("\nРезультат:")
    for r in res:
        print(r)

    input("\nEnter...")