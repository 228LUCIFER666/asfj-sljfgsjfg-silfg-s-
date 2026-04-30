import time
import sys

# === НАСТРОЙКА ИМПОРТОВ ===
try:
    from fonbet import get_fonbet_esports_odds
    from polymarket import get_polymarket_esports_odds
except ImportError as e:
    print(f"❌ ОШИБКА ИМПОРТА: {e}")
    input("\nНажми Enter...")
    sys.exit()

def clean_name(name):
    """Очистка названий команд для точного сравнения.
    Возвращает множество значимых слов."""
    if not name:
        return set()
    garbage = [
        "esports", "gaming", "team", "club", "esport", "academy",
        "youth", "challengers", "junior", "ltd", "fe", "female",
        "blue", "red", "white", "black", "rising", "pro", "ph"
    ]
    name = name.lower()
    for ch in [".", "-", "(", ")", ",", "'", ":", ";", "!"]:
        name = name.replace(ch, " ")
    parts = name.split()
    return {p for p in parts if p not in garbage and len(p) > 1}

def leagues_compatible(f_league, p_league):
    """Мягкая проверка совместимости лиг.
    'Esports' считается универсальной категорией."""
    f = f_league.lower().replace(" ", "")
    p = p_league.lower().replace(" ", "")
    # Если одна из лиг общая («esports»), считаем совместимыми
    if "esports" in f or "esports" in p:
        return True
    # Проверяем ключевые слова для конкретных дисциплин
    for key in ["cs", "lol", "dota", "valorant"]:
        if key in f and key in p:
            return True
    return False

def find_surebets():
    try:
        print(f"[{time.strftime('%H:%M:%S')}] СБОР ДАННЫХ...")
        fon_matches = get_fonbet_esports_odds()
        poly_matches = get_polymarket_esports_odds()
        
        if not fon_matches or not poly_matches:
            print("⚠️ Ошибка: Данные не получены.")
            return

        # 1. ВЫВОД ВСЕГО СПИСКА FONBET
        print("\n" + "="*35 + " ВСЕ МАТЧИ FONBET " + "="*35)
        for i, m in enumerate(fon_matches):
            print(f"{i+1:3}. [{m['league']:8}] {m['match']:40} | Кэфы: {m['odds']}")

        # 2. ВЫВОД ВСЕГО СПИСКА POLYMARKET
        print("\n" + "="*35 + " ВСЕ МАТЧИ POLYMARKET " + "="*35)
        for i, m in enumerate(poly_matches):
            print(f"{i+1:3}. [{m['league']:8}] {m['match']:40} | Кэфы: {m['odds']}")

        matched_pairs = []
        surebets = []

        # 3. УЛУЧШЕННАЯ ЛОГИКА СОПОСТАВЛЕНИЯ (без жёсткой группировки по лигам)
        for f in fon_matches:
            f_raw = f['match'].lower()
            if " vs " not in f_raw:
                continue
            f_t1, f_t2 = f_raw.split(" vs ")
            f_t1_words = clean_name(f_t1)
            f_t2_words = clean_name(f_t2)

            for p in poly_matches:
                p_raw = p['match'].lower()
                if " vs " not in p_raw:
                    continue
                p_t1, p_t2 = p_raw.split(" vs ")
                p_t1_words = clean_name(p_t1)
                p_t2_words = clean_name(p_t2)

                # Проверка совместимости лиг
                if not leagues_compatible(f['league'], p['league']):
                    continue

                # Игнорируем матчи, где есть признак академии/молодёжки только в одном источнике
                tags = ["academy", "challengers", "youth", "junior"]
                f_has = any(t in f_raw for t in tags)
                p_has = any(t in p_raw for t in tags)
                if f_has != p_has:
                    continue

                # Проверяем совпадение команд (прямой и обратный порядок)
                direct = (f_t1_words & p_t1_words) and (f_t2_words & p_t2_words)
                cross  = (f_t1_words & p_t2_words) and (f_t2_words & p_t1_words)

                if direct or cross:
                    pair = {'f': f, 'p': p, 'order': 'direct' if direct else 'cross'}
                    matched_pairs.append(pair)

                    # Правильный расчёт вилки с учётом порядка команд
                    k1_f, k2_f = f['odds']
                    k1_p, k2_p = p['odds']

                    # Формулы одинаковы для прямого и обратного порядка,
                    # потому что мы всегда сопоставляем П1(FON) с П2(POLY) и наоборот,
                    # но при cross порядке команды уже переставлены, и это учтено.
                    profit1 = (1/k1_f + 1/k2_p)  # П1(FON) + П2(POLY)
                    profit2 = (1/k2_f + 1/k1_p)  # П2(FON) + П1(POLY)

                    best_profit = min(profit1, profit2)
                    if best_profit < 1.0:
                        profit_percent = (1 - best_profit) * 100
                        if best_profit == profit1:
                            type_bet = "П1(FON) + П2(POLY)"
                        else:
                            type_bet = "П2(FON) + П1(POLY)"
                        if pair['order'] == 'cross':
                            type_bet += " [обр.порядок]"
                        surebets.append({
                            'profit': profit_percent,
                            'f_match': f['match'],
                            'p_match': p['match'],
                            'f_odds': f['odds'],
                            'p_odds': p['odds'],
                            'type': type_bet
                        })

        # --- ИТОГОВЫЙ ОТЧЕТ ---
        print("\n" + "="*30 + " РЕЗУЛЬТАТ СОПОСТАВЛЕНИЯ (УСПЕШНО) " + "="*30)
        for i, m in enumerate(matched_pairs):
            order = "(прямой)" if m['order'] == 'direct' else "(обратный)"
            print(f"✅ {m['f']['match']} <--> {m['p']['match']} {order}")

        print("\n" + "="*30 + " НАЙДЕННЫЕ ВИЛКИ (ФИЛЬТРОВАННЫЕ) " + "="*30)
        if not surebets:
            print("Вилок не найдено. Ждем обновления линий...")
        else:
            for s in sorted(surebets, key=lambda x: x['profit'], reverse=True):
                print(f"🚀 {s['profit']:.2f}% | {s['f_match']}")
                print(f"   Схема: {s['type']}")
                print(f"   FON: {s['f_odds']} | POLY: {s['p_odds']}")
                print("-" * 40)

        print(f"\n📊 ИТОГО: FON={len(fon_matches)}, POLY={len(poly_matches)}")
        print(f"🔗 Связано реальных пар: {len(matched_pairs)}")
        print(f"💰 Найдено честных вилок: {len(surebets)}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ ОШИБКА: {e}")

if __name__ == "__main__":
    find_surebets()
    input("\nНажми Enter для выхода...")