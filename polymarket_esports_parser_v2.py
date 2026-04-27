import requests


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
            try:
                title = event.get('title', '')
                markets = event.get('markets', [])

                if not markets:
                    continue

                title_lower = title.lower()

                # ❌ отсекаем мусор по названию
                if any(x in title_lower for x in ["odd", "even"]):
                    continue

                found = False

                # 🔥 ищем ПРАВИЛЬНЫЙ рынок
                for m in markets:
                    outcomes = m.get('outcomes', [])
                    prices = m.get('outcomePrices', [])

                    if len(outcomes) < 2 or len(prices) < 2:
                        continue

                    # --- получаем команды ---
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

                    # ❌ убираем мусор
                    bad_words = ["yes", "no", "odd", "even"]
                    if any(x in team1_l or x in team2_l for x in bad_words):
                        continue

                    # 🔥 КЛЮЧЕВОЙ ФИЛЬТР — команды должны быть в title
                    if team1_l not in title_lower or team2_l not in title_lower:
                        continue

                    # --- коэффициенты ---
                    try:
                        prob1 = float(prices[0])
                        prob2 = float(prices[1])

                        if prob1 <= 0.01 or prob2 <= 0.01:
                            continue

                        k1 = 1.0 / prob1
                        k2 = 1.0 / prob2

                        # ❌ убираем мусор 2.0 / 2.0
                        if abs(k1 - 2.0) < 0.01 and abs(k2 - 2.0) < 0.01:
                            continue

                    except:
                        continue

                    match_name = f"{team1} vs {team2}"

                    print(f"  {match_name}: {k1:.2f} / {k2:.2f}")

                    matches.append({
                        'match': match_name,
                        'odds': [k1, k2]
                    })

                    found = True
                    break  # нашли нужный market → выходим

                if not found:
                    continue

            except Exception:
                continue

        print(f"Polymarket Esports: собрано {len(matches)} матчей")
        return matches

    except Exception as e:
        print(f"Ошибка парсинга Polymarket: {e}")
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


if __name__ == "__main__":
    res = get_polymarket_esports_odds()

    print("\nРезультат:")
    for r in res:
        print(r)

    input("\nНажми Enter...")