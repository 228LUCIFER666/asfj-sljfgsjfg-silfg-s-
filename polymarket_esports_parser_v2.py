import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}

LEAGUES = ["dota-2", "counter-strike"]


def get_tournaments(league):
    url = f"https://polymarket.com/_next/data/build-TfctsWXpff2fKS/en/esports/{league}/games.json?league={league}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    data = r.json()

    queries = data["pageProps"]["dehydratedState"]["queries"]

    tournaments = []

    for q in queries:
        key = q.get("queryKey", [])
        if isinstance(key, list) and "esports-sidebar-tournaments" in key:
            for t in q["state"]["data"]["tournaments"]:
                tournaments.append(t["slug"])

    return tournaments


def get_matches(league, tournament):
    url = f"https://polymarket.com/_next/data/build-TfctsWXpff2fKS/en/esports/{league}/{tournament}.json?league={league}&tournament={tournament}"

    r = requests.get(url, headers=HEADERS, timeout=15)
    data = r.json()

    queries = data["pageProps"]["dehydratedState"]["queries"]

    events = []

    for q in queries:
        d = q.get("state", {}).get("data", {})
        if isinstance(d, dict) and "markets" in d:
            events.append(d)

    return events


def extract_odds(events):
    results = []

    for event in events:
        markets = event.get("markets", [])

        for m in markets:
            if m.get("groupItemTitle") != "Match Winner":
                continue

            outcomes = m.get("outcomes", [])
            prices = m.get("outcomePrices", [])

            if len(outcomes) != 2:
                continue

            try:
                p1 = float(prices[0])
                p2 = float(prices[1])

                if p1 < 0.02 or p2 < 0.02:
                    continue

                k1 = 1 / p1
                k2 = 1 / p2

                results.append({
                    "match": f"{outcomes[0]} vs {outcomes[1]}",
                    "odds": [k1, k2]
                })

            except:
                continue

    return results


def get_polymarket_esports_odds():
    print("Polymarket (CS2 + Dota): загрузка...")

    all_matches = []

    for league in LEAGUES:
        print(f"\nЛига: {league}")

        tournaments = get_tournaments(league)

        for t in tournaments:
            events = get_matches(league, t)
            matches = extract_odds(events)
            all_matches.extend(matches)

    print(f"\nВсего матчей: {len(all_matches)}")
    return all_matches