import asyncio
import threading
import time
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from fonbet import get_fonbet_esports_odds
from polymarket import get_polymarket_esports_odds

# ------------------- КОНФИГ -------------------
TOKEN = os.getenv("BOT_TOKEN", "8481745931:AAG_e4Dijnv_sFoYkXIe0ZFSZ34yeSnuoWs")
CHAT_ID = os.getenv("USER_ID")  # если нужно отправлять конкретному пользователю

# ------------------- ГЛОБАЛЬНЫЕ -------------------
bot_instance = None
loop = None
user_chat_id = None
TOTAL_BUDGET = 10000
monitoring_active = False

# ------------------- ПОТОКОБЕЗОПАСНАЯ ОТПРАВКА -------------------
def safe_send(text):
    """Отправка сообщения из любого потока."""
    if bot_instance and loop and user_chat_id:
        asyncio.run_coroutine_threadsafe(
            bot_instance.send_message(chat_id=user_chat_id, text=text),
            loop
        )

# ------------------- ЛОГИКА ВИЛОК (исправленная) -------------------
def clean_name(name):
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
    f = f_league.lower().replace(" ", "")
    p = p_league.lower().replace(" ", "")
    if "esports" in f or "esports" in p:
        return True
    for key in ["cs", "lol", "dota", "valorant"]:
        if key in f and key in p:
            return True
    return False

def analyze():
    """Возвращает (matched_pairs, surebets, fon_count, poly_count)"""
    fon_matches = get_fonbet_esports_odds()
    poly_matches = get_polymarket_esports_odds()
    if not fon_matches or not poly_matches:
        return [], [], 0, 0

    matched_pairs = []
    surebets = []

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

            if not leagues_compatible(f['league'], p['league']):
                continue

            tags = ["academy", "challengers", "youth", "junior"]
            if any(t in f_raw for t in tags) != any(t in p_raw for t in tags):
                continue

            direct = (f_t1_words & p_t1_words) and (f_t2_words & p_t2_words)
            cross = (f_t1_words & p_t2_words) and (f_t2_words & p_t1_words)

            if direct or cross:
                pair = {'f': f, 'p': p, 'order': 'direct' if direct else 'cross'}
                matched_pairs.append(pair)

                k1_f, k2_f = f['odds']
                k1_p, k2_p = p['odds']

                profit1 = 1/k1_f + 1/k2_p
                profit2 = 1/k2_f + 1/k1_p

                best = min(profit1, profit2)
                if best < 1.0:
                    profit_percent = (1 - best) * 100
                    type_bet = "П1(FON) + П2(POLY)" if best == profit1 else "П2(FON) + П1(POLY)"
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
    return matched_pairs, surebets, len(fon_matches), len(poly_matches)

def find_arbs_job():
    """Фоновая задача: ищет вилки и отправляет результат."""
    try:
        _, surebets, _, _ = analyze()
        if not surebets:
            safe_send("🔍 Вилок не найдено.")
            return
        text = "🚀 Найденные вилки (прибыль >1%):\n\n"
        for s in sorted(surebets, key=lambda x: x['profit'], reverse=True):
            text += f"{s['profit']:.2f}% | {s['f_match']}\n"
            text += f"Схема: {s['type']}\n"
            text += f"FON: {s['f_odds']}  POLY: {s['p_odds']}\n\n"
        safe_send(text)
    except Exception as e:
        safe_send(f"❌ Ошибка: {e}")

def all_matches_job():
    """Фоновая задача: отправляет все совпадения."""
    try:
        matched, _, _, _ = analyze()
        if not matched:
            safe_send("📋 Совпадений не найдено.")
            return
        chunk_size = 30
        for i in range(0, len(matched), chunk_size):
            chunk = matched[i:i+chunk_size]
            text = ""
            for pair in chunk:
                f = pair['f']
                p = pair['p']
                order = "прямой" if pair['order'] == 'direct' else "обратный"
                text += f"✅ {f['match']} ({f['league']}) vs {p['match']} ({p['league']}) [{order}]\n"
                text += f"FON: {f['odds']}  POLY: {p['odds']}\n\n"
            safe_send(text)
    except Exception as e:
        safe_send(f"❌ Ошибка: {e}")

# ------------------- КЛАВИАТУРЫ -------------------
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск вилок", callback_data="find_arbs"),
         InlineKeyboardButton("📋 Все совпадения", callback_data="all_matches")],
        [InlineKeyboardButton("📊 Статус", callback_data="status"),
         InlineKeyboardButton("💰 Бюджет", callback_data="budget")],
        [InlineKeyboardButton("▶️ Старт мониторинга", callback_data="start_monitoring"),
         InlineKeyboardButton("⏸️ Стоп мониторинга", callback_data="stop_monitoring")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_budget_keyboard():
    keyboard = [
        [InlineKeyboardButton("1000 RUB", callback_data="budget_1000"),
         InlineKeyboardButton("2000 RUB", callback_data="budget_2000"),
         InlineKeyboardButton("5000 RUB", callback_data="budget_5000")],
        [InlineKeyboardButton("10000 RUB", callback_data="budget_10000"),
         InlineKeyboardButton("Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ------------------- ОБРАБОТЧИКИ -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_chat_id
    user_chat_id = update.effective_chat.id
    text = (
        "🤖 *VilSS — Бот вилок*\n\n"
        f"💰 Бюджет: {TOTAL_BUDGET} RUB\n"
        f"🔄 Мониторинг: {'Активен' if monitoring_active else 'Остановлен'}"
    )
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global monitoring_active, TOTAL_BUDGET, user_chat_id

    query = update.callback_query
    await query.answer()
    data = query.data
    user_chat_id = query.message.chat.id

    if data == "find_arbs":
        await query.edit_message_text("🔍 Ищу вилки...", reply_markup=get_main_keyboard())
        threading.Thread(target=find_arbs_job).start()
        await asyncio.sleep(1)
        await query.edit_message_text("✅ Поиск завершён. Результаты в чате.", reply_markup=get_main_keyboard())

    elif data == "all_matches":
        await query.edit_message_text("📋 Собираю совпадения...", reply_markup=get_main_keyboard())
        threading.Thread(target=all_matches_job).start()
        await asyncio.sleep(1)
        await query.edit_message_text("✅ Отправка завершена.", reply_markup=get_main_keyboard())

    elif data == "status":
        text = (
            f"📊 Статус\n\n"
            f"🔄 Мониторинг: {'▶️ Активен' if monitoring_active else '⏸️ Стоп'}\n"
            f"💰 Бюджет: {TOTAL_BUDGET} RUB"
        )
        await query.edit_message_text(text, reply_markup=get_main_keyboard())

    elif data == "budget":
        await query.edit_message_text("💰 Выберите бюджет:", reply_markup=get_budget_keyboard())

    elif data.startswith("budget_"):
        amount = int(data.split("_")[1])
        TOTAL_BUDGET = amount
        await query.edit_message_text(f"✅ Бюджет: {amount} RUB", reply_markup=get_main_keyboard())

    elif data == "start_monitoring":
        if monitoring_active:
            await query.answer("Уже запущен ✅")
            return
        monitoring_active = True
        await query.edit_message_text("▶️ Мониторинг запущен", reply_markup=get_main_keyboard())

    elif data == "stop_monitoring":
        if not monitoring_active:
            await query.answer("Уже остановлен ⛔")
            return
        monitoring_active = False
        await query.edit_message_text("⏸️ Мониторинг остановлен", reply_markup=get_main_keyboard())

    elif data == "help":
        text = "📖 Кнопки:\n\n🔍 Поиск — ручной\n▶️ Старт — авто\n⏸️ Стоп — стоп авто\n📋 Все совпадения — показать все пары"
        await query.edit_message_text(text, reply_markup=get_main_keyboard())

    elif data == "back_to_main":
        await query.edit_message_text("Главное меню", reply_markup=get_main_keyboard())

# ------------------- МОНИТОРИНГ -------------------
def run_monitoring():
    global monitoring_active
    while True:
        if monitoring_active:
            try:
                find_arbs_job()
            except Exception as e:
                print("Ошибка мониторинга:", e)
        time.sleep(60)

# ------------------- MAIN -------------------
def main():
    global bot_instance, loop
    threading.Thread(target=run_monitoring, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    bot_instance = app.bot
    loop = asyncio.get_event_loop()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Бот запущен (ручной + мониторинг)")
    app.run_polling()

if __name__ == "__main__":
    main()