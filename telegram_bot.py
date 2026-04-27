import asyncio
import threading
import time
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import bot_core
from bot_core import find_arbs

# ------------------- КОНФИГ -------------------
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("USER_ID")

# ------------------- ГЛОБАЛЬНЫЕ -------------------
monitoring_active = True

# ------------------- КЛАВИАТУРЫ -------------------
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск вилок", callback_data="find_arbs")],
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

# ------------------- КОМАНДЫ -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *VilSS — Бот вилок*\n\n"
        f"💰 Бюджет: {bot_core.TOTAL_BUDGET} RUB\n"
        f"🔄 Мониторинг: {'Активен' if monitoring_active else 'Остановлен'}"
    )
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=get_main_keyboard())

# ------------------- CALLBACK -------------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global monitoring_active

    query = update.callback_query
    await query.answer()
    data = query.data

    # 🔥 ПОИСК ВИЛОК (с очисткой)
    if data == "find_arbs":
        bot_core.sent.clear()  # ← ВОТ ГЛАВНОЕ

        try:
            await query.edit_message_text("🔍 Поиск вилок...", reply_markup=get_main_keyboard())
        except:
            pass

        def run():
            try:
                find_arbs()
            except Exception as e:
                print("Ошибка поиска:", e)

        threading.Thread(target=run).start()

        await asyncio.sleep(2)

        try:
            await query.edit_message_text("✅ Поиск завершён. Проверьте уведомления!", reply_markup=get_main_keyboard())
        except:
            pass

    # -------------------
    elif data == "status":
        text = (
            f"📊 Статус\n\n"
            f"🔄 Мониторинг: {'▶️ Активен' if monitoring_active else '⏸️ Стоп'}\n"
            f"💰 Бюджет: {bot_core.TOTAL_BUDGET} RUB"
        )

        try:
            await query.edit_message_text(text, reply_markup=get_main_keyboard())
        except:
            pass

    # -------------------
    elif data == "budget":
        try:
            await query.edit_message_text("💰 Выберите бюджет:", reply_markup=get_budget_keyboard())
        except:
            pass

    elif data.startswith("budget_"):
        amount = int(data.split("_")[1])
        bot_core.TOTAL_BUDGET = amount

        try:
            await query.edit_message_text(f"✅ Бюджет: {amount} RUB", reply_markup=get_main_keyboard())
        except:
            pass

    # -------------------
    elif data == "start_monitoring":
        if monitoring_active:
            await query.answer("Уже запущен ✅")
            return

        monitoring_active = True

        try:
            await query.edit_message_text("▶️ Мониторинг запущен", reply_markup=get_main_keyboard())
        except:
            pass

    elif data == "stop_monitoring":
        if not monitoring_active:
            await query.answer("Уже остановлен ⛔")
            return

        monitoring_active = False

        try:
            await query.edit_message_text("⏸️ Мониторинг остановлен", reply_markup=get_main_keyboard())
        except:
            pass

    # -------------------
    elif data == "help":
        text = "📖 Кнопки:\n\n🔍 Поиск — ручной\n▶️ Старт — авто\n⏸️ Стоп — стоп авто"

        try:
            await query.edit_message_text(text, reply_markup=get_main_keyboard())
        except:
            pass

    elif data == "back_to_main":
        try:
            await query.edit_message_text("Главное меню", reply_markup=get_main_keyboard())
        except:
            pass

# ------------------- МОНИТОРИНГ -------------------
def run_monitoring():
    global monitoring_active

    while True:
        if monitoring_active:
            try:
                find_arbs()
            except Exception as e:
                print("Ошибка мониторинга:", e)

        time.sleep(60)

# ------------------- MAIN -------------------
def main():
    threading.Thread(target=run_monitoring, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()