import requests
import json
import re
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
TIMEOUT = 15
RETRIES = 3
RETRY_DELAY = 2

GAMMA_BASE = "https://gamma-api.polymarket.com"
LOL_SERIES_ID = 10311
DOTA_TAG_ID = 102366


def fetch_with_retries(url, retries=RETRIES):
    """GET-запрос с повторными попытками."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            print(f"[Попытка {attempt}/{retries}] {url}: {e}")
            if attempt < retries:
                time.sleep(RETRY_DELAY)
    return None


def get_build_id():
    """Извлекает buildId из HTML страницы киберспорта."""
    print("Получаю BUILD_ID...")
    resp = fetch_with_retries("https://polymarket.com/ru/sports/esports")
    if not resp:
        return None
    # Ищем buildId в JavaScript-вставке
    match = re.search(r'"buildId"\s*:\s*"([^"]+)"', resp.text)
    if match:
        return match.group(1)
    # Запасной вариант – __NEXT_DATA__ (может отсутствовать)
    match = re.search(r'__NEXT_DATA__\s*=\s*({.*?});', resp.text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            return data.get("buildId")
        except:
            pass
    return None


def find_events_recursive(obj):
    """Рекурсивно ищет объекты с 'title' и 'markets'."""
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
    """Парсинг событий из _next/data (старый формат)."""
    matches = []
    for ev in events:
        try:
            title = ev['title'].lower()
            markets = ev.get('markets', [])
            if not markets:
                continue
            # Пропускаем чёт/нечет
            if "odd" in title or "even" in title:
                continue

            for m in markets:
                outcomes = m.get('outcomes', [])
                prices = m.get('outcomePrices', [])
                if len(outcomes) < 2 or len(prices) < 2:
                    continue

                # Определяем имена команд
                if isinstance(outcomes[0], str):
                    t1, t2 = outcomes[0], outcomes[1]
                elif isinstance(outcomes[0], dict):
                    t1 = outcomes[0].get('title', '')
                    t2 = outcomes[1].get('title', '')
                else:
                    continue

                t1, t2 = t1.strip(), t2.strip()
                # Пропускаем бинарные исходы
                if any(x in t1.lower() or x in t2.lower()
                       for x in ["yes", "no", "over", "under", "odd", "even"]):
                    continue
                # Команды должны присутствовать в названии события
                if not (t1.lower() in title or t2.lower() in title):
                    continue

                p1, p2 = float(prices[0]), float(prices[1])
                if p1 <= 0.01 or p2 <= 0.01:
                    continue

                k1, k2 = round(1 / p1, 2), round(1 / p2, 2)
                match_name = f"{t1} vs {t2}"
                matches.append({
                    'match': match_name,
                    'odds': [k1, k2],
                    'league': league_name
                })
                break  # берём только первый подходящий рынок для каждого события
        except:
            continue
    return matches


def fetch_gamma_paginated(params):
    """Загружает все события из Gamma API с пагинацией."""
    all_events = []
    offset = 0
    limit = 100
    base = params.copy()
    base['closed'] = 'false'
    base['limit'] = limit

    while True:
        query = base.copy()
        query['offset'] = offset
        url = GAMMA_BASE + "/events?" + "&".join(
            f"{k}={v}" for k, v in query.items()
        )
        resp = fetch_with_retries(url)
        if not resp:
            break
        data = resp.json()
        events = data if isinstance(data, list) else data.get('events', [])
        if not events:
            break
        all_events.extend(events)
        if len(events) < limit:
            break
        offset += limit
        time.sleep(0.3)  # вежливая пауза
    return all_events


def find_winner_market(markets):
    """Ищет рынок победителя матча (Match Winner / Moneyline)."""
    # Точное совпадение "Match Winner"
    for m in markets:
        if m.get("groupItemTitle", "").strip().lower() == "match winner":
            return m
    # Moneyline без карт/гандикапов
    for m in markets:
        if m.get("sportsMarketType") == "moneyline":
            title = m.get("groupItemTitle", "").lower()
            if not any(w in title for w in ["game", "map", "handicap", "total"]):
                return m
    # Один рынок на всё событие
    if len(markets) == 1:
        return markets[0]
    return None


def parse_market(market):
    """Безопасно извлекает исходы и цены из рынка."""
    raw_out = market.get('outcomes', '[]')
    raw_pr = market.get('outcomePrices', '[]')
    try:
        outcomes = json.loads(raw_out) if isinstance(raw_out, str) else raw_out
        prices = json.loads(raw_pr) if isinstance(raw_pr, str) else raw_pr
    except:
        return None, None
    return outcomes, prices


def extract_match(market, league):
    """Создаёт словарь с информацией о матче из данных рынка."""
    outcomes, prices = parse_market(market)
    if not outcomes or not prices or len(outcomes) < 2 or len(prices) < 2:
        return None

    names = []
    for o in outcomes[:2]:
        if isinstance(o, dict):
            names.append(o.get('title', '').strip())
        else:
            names.append(str(o).strip())

    # Фильтр бинарных исходов
    if any(bad in n.lower()
           for n in names
           for bad in ["yes", "no", "over", "under", "odd", "even"]):
        return None

    try:
        p1, p2 = float(prices[0]), float(prices[1])
    except:
        return None
    if p1 <= 0.01 or p2 <= 0.01:
        return None

    k1, k2 = round(1 / p1, 2), round(1 / p2, 2)
    match_name = f"{names[0]} vs {names[1]}"

    return {
        'match': match_name,
        'odds': [k1, k2],
        'league': league
    }


def get_polymarket_esports_odds():
    """Основная функция, возвращающая список матчей (для импорта)."""
    print("=== Polymarket Esports (CS:GO, LoL, Dota 2) ===\n")
    matches = []

    # ---------- CS:GO ----------
    try:
        build_id = get_build_id()
        if not build_id:
            print("❌ BUILD_ID не получен, CS:GO пропущен.")
        else:
            print(f"BUILD_ID = {build_id}")
            cs_url = (
                f"https://polymarket.com/_next/data/{build_id}"
                f"/ru/sports/esports/games.json?league=esports"
            )
            resp = fetch_with_retries(cs_url)
            if resp and resp.status_code == 200:
                cs_events = find_events_recursive(resp.json())
                print(f"[CS:GO] Загружено событий: {len(cs_events)}")
                matches.extend(parse_cs_style(cs_events, "CS:GO"))
            else:
                print("[CS:GO] Ошибка загрузки данных")
    except Exception as e:
        print(f"[CS:GO] Критическая ошибка: {e}")

    # ---------- LoL ----------
    try:
        print("\nЗагружаем LoL...")
        lol_events = fetch_gamma_paginated({"series_id": LOL_SERIES_ID})
        print(f"[LoL] Загружено событий: {len(lol_events)}")
        for ev in lol_events:
            if ev.get('closed'):
                continue
            markets = ev.get('markets', [])
            wm = find_winner_market(markets)
            if wm:
                m = extract_match(wm, "LoL")
                if m:
                    matches.append(m)
    except Exception as e:
        print(f"[LoL] Ошибка: {e}")

    # ---------- Dota 2 ----------
    try:
        print("\nЗагружаем Dota 2...")
        dota_events = fetch_gamma_paginated({"tag_id": DOTA_TAG_ID})
        print(f"[Dota 2] Загружено событий: {len(dota_events)}")
        for ev in dota_events:
            if ev.get('closed'):
                continue
            markets = ev.get('markets', [])
            wm = find_winner_market(markets)
            if wm:
                m = extract_match(wm, "Dota 2")
                if m:
                    matches.append(m)
    except Exception as e:
        print(f"[Dota 2] Ошибка: {e}")

    # ---------- Удаление дубликатов ----------
    unique = {}
    for m in matches:
        key = f"{m['league']}|{m['match']}"
        if key not in unique:
            unique[key] = m
    matches = list(unique.values())

    print(f"\n{'='*40}")
    print(f"Итого матчей: {len(matches)}")
    print(f"{'='*40}\n")
    return matches


if __name__ == "__main__":
    results = get_polymarket_esports_odds()
    for r in results:
        print(f"[{r['league']}] {r['match']} : {r['odds']}")
    input("\nНажми Enter...")