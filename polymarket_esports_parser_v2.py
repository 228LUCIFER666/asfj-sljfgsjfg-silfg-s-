import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ------------------- FIND EVENTS -------------------
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


# ------------------- GET TOURNAMENTS -------------------
def get_tournaments(league):
    url = f"https://polymarket.com/_next/data/build-TfctsWXpff2fKS/en/esports/{league}/games.json?league={league}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code != 200:
            return []

        data = r.json()

        # 🔥 защита от редиректа / мусора
        if "pageProps" not in data:
            print(f"❌ {league}: нет pageProps")
            return []

        queries = data["pageProps"].get("dehydratedState", {}).get("queries", [])

        tournaments = []

        for q in queries:
            key = q.get("queryKey", [])

            if isinstance(key, list) and "esports-sidebar-tournaments" in key:
                for t in q["state"]["data"].get("tournaments", []):
                    tournaments.append(t["slug"])

        return tournaments

    except Exception as e:
        print(f"Ошибка турниров ({league}): {e}")
        return []


# ------------------- GET MATCHES -------------------
def get_matches(league, tournament):
    url = f"https://polymarket.com/_next/data/build-TfctsWXpff2fKS/en/esports/{league}/{tournament}.json?league={league}&tournament={tournament}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code != 200:
            return []

        data = r.json()

        if "pageProps" not in data:
            return []

        queries = data["pageProps"].get("dehydratedState", {}).get("queries", [])

        events = []

        for q in queries:
            d = q.get("state", {}).get("data", {})

            if isinstance(d, dict) and "markets" in d:
                events.append(d)

        return events

    except Exception as e:
        print(f"Ошибка матчей ({league}/{tournament}): {e}")
        return []


# ------------------- MAIN -------------------
def get_polymarket_esports_odds():
    print("Polymarket (CS2 + Dota): загрузка...")

    leagues = ["counter-strike", "dota-2"]

    matches = []

    for league in leagues:
        print(f"\nЛига: {league}")

        tournaments = get_tournaments(league)

        if not tournaments:
            print("❌ турниры не найдены")
            continue

        for t in tournaments:
            events = get_matches(league, t)

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
                        bad_words = ["yes", "no", "odd", "even"]
                        if any(x in team1_l or x in team2_l for x in bad_words):
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

    print(f"\nPolymarket: собрано {len(matches)} матчей")
    return matches


# ------------------- TEST -------------------
if __name__ == "__main__":
    res = get_polymarket_esports_odds()

    print("\nРезультат:")
    for r in res:
        print(r)

    input("\nEnter...")