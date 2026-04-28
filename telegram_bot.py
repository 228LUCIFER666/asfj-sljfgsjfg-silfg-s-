import asyncio, threading, time, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import bot_core
from bot_core import find_arbs, TOTAL_BUDGET

TOKEN = os.getenv("BOT_TOKEN") or "8481745931:AAG_e4Dijnv_sFoYkXIe0ZFSZ34yeSnuoWs"
CHAT_ID = os.getenv("USER_ID") or "1088479582"

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск вилок", callback_data="find_arbs")],
        [InlineKeyboardButton("📊 Статус", callback_data="status"),
         InlineKeyboardButton("💰 Бюджет", callback_data="budget")],
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (f"🤖 *VilSS — Бот вилок*\n\n"
            f"💰 Бюджет: {TOTAL_BUDGET} RUB\n"
            "⚙️ Режим: ручной (нажмите «Поиск вилок»)\n\n"
            "Бот отправляет только после вашего запроса.")
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "find_arbs":
        bot_core.sent.clear()
        await query.edit_message_text("🔍 Ищу вилки...", reply_markup=get_main_keyboard())
        def run():
            try: find_arbs()
            except Exception as e: print("Ошибка поиска:", e)
        threading.Thread(target=run).start()
        await asyncio.sleep(3)
        await query.edit_message_text("✅ Поиск завершён. Проверьте уведомления!", reply_markup=get_main_keyboard())

    elif data == "status":
        text = (f"📊 Статус\n\n⚙️ Режим: ручной\n💰 Бюджет: {TOTAL_BUDGET} RUB\n"
                "🔍 Нажмите «Поиск вилок» для проверки.")
        await query.edit_message_text(text, reply_markup=get_main_keyboard())

    elif data == "budget":
        await query.edit_message_text("💰 Выберите бюджет:", reply_markup=get_budget_keyboard())

    elif data.startswith("budget_"):
        amount = int(data.split("_")[1])
        bot_core.TOTAL_BUDGET = amount
        await query.edit_message_text(f"✅ Бюджет установлен: {amount} RUB", reply_markup=get_main_keyboard())

    elif data == "help":
        text = ("📖 *Помощь*\n\n"
                "🔍 *Поиск вилок* — найти вилки прямо сейчас.\n"
                "📊 *Статус* — текущие настройки.\n"
                "💰 *Бюджет* — изменить сумму для расчёта ставок.\n\n"
                "Бот не ведёт автоматический мониторинг!")
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=get_main_keyboard())

    elif data == "back_to_main":
        await query.edit_message_text("Главное меню", reply_markup=get_main_keyboard())

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("Бот запущен (ручной режим)")
    app.run_polling()

if __name__ == "__main__":
    main()