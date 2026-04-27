import asyncio
import threading
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import bot_core
from bot_core import find_arbs

# ------------------- КОНФИГ -------------------
TOKEN = "8481745931:AAG_e4Dijnv_sFoYkXIe0ZFSZ34yeSnuoWs"
CHAT_ID = "1088479582"

# ------------------- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ -------------------
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
    welcome_text = (
        "🤖 *VilSS — Бот поиска арбитражных вилок*\n\n"
        "Я анализирую коэффициенты на киберспортивные матчи и нахожу "
        "гарантированно прибыльные ситуации (вилки).\n\n"
        f"📊 *Текущий бюджет:* {bot_core.TOTAL_BUDGET} RUB\n"
        "🔄 *Мониторинг:* Активен (каждую минуту)\n"
        "🎮 *Платформы:* Fonbet + Polymarket\n\n"
        "Используйте кнопки меню для управления ботом 👇"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global monitoring_active
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "find_arbs":
        await query.edit_message_text("🔍 Поиск вилок... Пожалуйста, подождите.")
        def run_search():
            try:
                find_arbs()
            except Exception as e:
                print(f"Ошибка поиска: {e}")
        threading.Thread(target=run_search).start()
        await asyncio.sleep(2)
        await query.edit_message_text("✅ Поиск завершён. Проверьте уведомления!", reply_markup=get_main_keyboard())

    elif data == "status":
        status_text = (
            "📊 *Статус системы*\n\n"
            f"🤖 Бот: Активен\n"
            f"🔄 Мониторинг: {'▶️ Активен' if monitoring_active else '⏸️ Остановлен'}\n"
            f"💰 Бюджет: {bot_core.TOTAL_BUDGET} RUB\n"
            f"🎮 Источники: Fonbet + Polymarket\n"
            f"⏱️ Интервал: 60 секунд"
        )
        await query.edit_message_text(status_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

    elif data == "budget":
        await query.edit_message_text("💰 Выберите бюджет:", reply_markup=get_budget_keyboard())

    elif data.startswith("budget_"):
        amount = int(data.split("_")[1])
        bot_core.TOTAL_BUDGET = amount
        await query.edit_message_text(f"✅ Бюджет установлен: {amount} RUB", reply_markup=get_main_keyboard())

    elif data == "start_monitoring":
        monitoring_active = True
        await query.edit_message_text("▶️ Мониторинг запущен.", reply_markup=get_main_keyboard())

    elif data == "stop_monitoring":
        monitoring_active = False
        await query.edit_message_text("⏸️ Мониторинг остановлен.", reply_markup=get_main_keyboard())

    elif data == "help":
        help_text = (
            "📖 *Инструкция*\n\n"
            "🔍 *Поиск вилок* — ручной запуск проверки\n"
            "📊 *Статус* — просмотр текущих настроек\n"
            "💰 *Бюджет* — изменение суммы для расчёта ставок\n"
            "▶️ *Старт/Стоп* — управление автоматическим мониторингом"
        )
        await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

    elif data == "back_to_main":
        await query.edit_message_text("Главное меню:", reply_markup=get_main_keyboard())

# ------------------- ФОНОВЫЙ МОНИТОРИНГ -------------------
def run_monitoring():
    global monitoring_active
    from bot_core import find_arbs
    while True:
        if monitoring_active:
            try:
                find_arbs()
            except Exception as e:
                print(f"Мониторинг ошибка: {e}")
        time.sleep(60)

# ------------------- MAIN -------------------
def main():
    threading.Thread(target=run_monitoring, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("Telegram бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()