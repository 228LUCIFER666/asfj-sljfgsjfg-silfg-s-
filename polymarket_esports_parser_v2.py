import requests
import json

def get_polymarket_esports_odds():
    print("Polymarket Esports: загружаю матчи...")
    headers = {"User-Agent": "Mozilla/5.0"}

    url = "https://polymarket.com/_next/data/build-TfctsWXpff2fKS/ru/sports/esports/games.json?league=esports"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"Ошибка: {resp.status_code}")
            return []

        data = resp.json()
        events = find_events(data)
        print(f"Найдено событий: {len(events)}")

        matches = []
        for event in events:
            title = event.get('title', '')
            markets = event.get('markets', [])
            if not markets:
                continue

            market = markets[0]
            outcomes = market.get('outcomes', [])
            outcome_labels = []
            if len(outcomes) >= 2:
                if isinstance(outcomes[0], str):
                    outcome_labels = [outcomes[0], outcomes[1]]
                elif isinstance(outcomes[0], dict):
                    outcome_labels = [outcomes[0].get('title', 'Yes'), outcomes[1].get('title', 'No')]
                else:
                    outcome_labels = ['Yes', 'No']
            else:
                outcome_labels = ['Yes', 'No']

            prices = market.get('outcomePrices', [])
            if len(prices) < 2:
                continue

            try:
                prob_yes = float(prices[0])
                prob_no = float(prices[1])
                if prob_yes <= 0.01 or prob_no <= 0.01:
                    continue

                k1 = 1.0 / prob_yes
                k2 = 1.0 / prob_no

                matches.append({
                    'match': title,
                    'odds': [k1, k2],
                    'probs': [prob_yes, prob_no],
                    'outcome_labels': outcome_labels
                })
                print(f"  {title}: {outcome_labels[0]}={k1:.2f} / {outcome_labels[1]}={k2:.2f}")
            except (ValueError, KeyError):
                continue

        print(f"Polymarket Esports: собрано {len(matches)} матчей")
        return matches

    except Exception as e:
        print(f"Ошибка парсинга Polymarket Esports: {e}")
        return []

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