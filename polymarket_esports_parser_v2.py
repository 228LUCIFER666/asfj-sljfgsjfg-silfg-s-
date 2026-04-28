import requests
import json

BUILD_ID = "build-TfctsWXpff2fKS"   # можно обновить при необходимости

def get_polymarket_esports_odds():
    print("=== Polymarket Esports (CS:GO + Dota 2 + LoL) ===")
    headers = {"User-Agent": "Mozilla/5.0"}
    matches = []

    # ---------- CS:GO (проверенный русский эндпоинт) ----------
    cs_url = f"https://polymarket.com/_next/data/{BUILD_ID}/ru/sports/esports/games.json?league=esports"
    try:
        resp = requests.get(cs_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            cs_events = find_events_recursive(resp.json())
            print(f"CS:GO загружено: {len(cs_events)} событий")
            matches.extend(parse_cs_style(cs_events, "CS:GO"))
        else:
            print(f"CS:GO ошибка {resp.status_code}")
    except Exception as e:
        print(f"CS:GO ошибка: {e}")

    # ---------- LoL (series_id=10311) ----------
    lol_url = "https://gamma-api.polymarket.com/events?series_id=10311&closed=false&limit=100"
    try:
        resp = requests.get(lol_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            raw = resp.json()
            lol_events = [ev for ev in raw if 'markets' in ev and not ev.get('closed')]
            print(f"LoL загружено: {len(lol_events)} событий")
            matches.extend(parse_gamma_events(lol_events, "LoL"))
        else:
            print(f"LoL ошибка {resp.status_code}")
    except Exception as e:
        print(f"LoL ошибка: {e}")

    # ---------- Dota 2 (tag_id=102366) ----------
    dota_url = "https://gamma-api.polymarket.com/events?tag_id=102366&closed=false&limit=100"
    try:
        resp = requests.get(dota_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            raw = resp.json()
            dota_events = [ev for ev in raw if 'markets' in ev and not ev.get('closed')]
            print(f"Dota 2 загружено: {len(dota_events)} событий")
            matches.extend(parse_gamma_events(dota_events, "Dota 2"))
        else:
            print(f"Dota 2 ошибка {resp.status_code}")
    except Exception as e:
        print(f"Dota 2 ошибка: {e}")

    print(f"\nВсего матчей собрано: {len(matches)}")
    return matches


# ---------- утилиты ----------
def find_events_recursive(obj):
    results = []
    if isinstance(obj, dict):
        if 'title' in obj and 'markets' in obj:
            results.append(obj)
        for v in obj.values():
            results.extend(find_events_recursive(v))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(find_events_recursive(item))
    return results


def parse_cs_style(events, league_name):
    matches = []
    for ev in events:
        try:
            title = ev['title'].lower()
            markets = ev.get('markets', [])
            if not markets:
                continue
            if any(x in title for x in ["odd", "even"]):
                continue
            for m in markets:
                outcomes = m.get('outcomes', [])
                prices = m.get('outcomePrices', [])
                if len(outcomes) < 2 or len(prices) < 2:
                    continue
                if isinstance(outcomes[0], str):
                    t1, t2 = outcomes[0], outcomes[1]
                elif isinstance(outcomes[0], dict):
                    t1 = outcomes[0].get('title', '')
                    t2 = outcomes[1].get('title', '')
                else:
                    continue
                t1, t2 = t1.strip(), t2.strip()
                if any(x in t1.lower() or x in t2.lower() for x in ["yes","no","over","under","odd","even"]):
                    continue
                if not (t1.lower() in title or t2.lower() in title):
                    continue
                p1, p2 = float(prices[0]), float(prices[1])
                if p1 <= 0.01 or p2 <= 0.01:
                    continue
                k1, k2 = round(1/p1, 2), round(1/p2, 2)
                match_name = f"{t1} vs {t2}"
                matches.append({'match': match_name, 'odds': [k1, k2], 'league': league_name})
                break
        except:
            continue
    return matches


def parse_gamma_events(events, league_name):
    """Парсинг Gamma API (LoL, Dota 2) — используется ТОЛЬКО основной рынок (Match Winner)"""
    matches = []
    for ev in events:
        try:
            markets = ev.get('markets', [])
            if not markets:
                continue

            winner_market = None
            # 1) Приоритет: рынок с groupItemTitle "Match Winner" (основной исход матча)
            for m in markets:
                if m.get("groupItemTitle") == "Match Winner":
                    winner_market = m
                    break

            # 2) Если не нашли Match Winner, ищем moneyline без признаков дочернего рынка
            if not winner_market:
                for m in markets:
                    if m.get("sportsMarketType") == "moneyline":
                        title = m.get("groupItemTitle", "")
                        # Пропускаем явно дочерние (Game 1, Map 2 и т.п.)
                        if any(w in title.lower() for w in ["game ", "map ", "handicap"]):
                            continue
                        winner_market = m
                        break

            if not winner_market:
                continue   # нет подходящего рынка — игнорируем событие

            raw_out = winner_market.get('outcomes', '[]')
            raw_pr = winner_market.get('outcomePrices', '[]')
            try:
                outcomes = json.loads(raw_out) if isinstance(raw_out, str) else raw_out
                prices = json.loads(raw_pr) if isinstance(raw_pr, str) else raw_pr
            except:
                continue

            if len(outcomes) < 2 or len(prices) < 2:
                continue
            t1, t2 = outcomes[0].strip(), outcomes[1].strip()
            if any(x in t1.lower() or x in t2.lower() for x in ["yes","no","over","under"]):
                continue

            p1, p2 = float(prices[0]), float(prices[1])
            if p1 <= 0.01 or p2 <= 0.01:
                continue
            k1, k2 = round(1/p1, 2), round(1/p2, 2)

            match_name = f"{t1} vs {t2}"
            matches.append({'match': match_name, 'odds': [k1, k2], 'league': league_name})
        except:
            continue
    return matches


if __name__ == "__main__":
    res = get_polymarket_esports_odds()
    print("\nРезультат:")
    for r in res:
        print(f"[{r['league']}] {r['match']} : {r['odds']}")
    input("\nНажми Enter...")