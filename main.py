from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
import logging

logging.basicConfig(level=logging.INFO)

# Этапы диалога
TEXT, LINK, PHOTO, BOT_LINK, WAIT_TEXT, WAIT_LINK = range(6)

# Хранилище данных
user_data_temp = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data_temp.pop(update.effective_chat.id, None)  # сбросим данные

    keyboard = [
        [InlineKeyboardButton("✏️ Ввести текст", callback_data="text_input")],
        [InlineKeyboardButton("🚫 Пропустить", callback_data="skip_text")]
    ]
    await update.message.reply_text("Хочешь добавить текст к сообщению?",
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    return TEXT

# Обработка выбора: ввод текста или пропуск
async def handle_text_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "text_input":
        await query.edit_message_text("Введите текст:")
        return WAIT_TEXT
    else:
        user_data_temp[query.from_user.id] = {"text": ""}
        await query.edit_message_text("Хочешь добавить ссылку к сообщению?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Ввести ссылку", callback_data="link_input")],
                [InlineKeyboardButton("🚫 Пропустить", callback_data="skip_link")]
            ])
        )
        return LINK

# Получаем текст
async def get_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data_temp[update.effective_chat.id] = {"text": update.message.text}
    await update.message.reply_text("Хочешь добавить ссылку к сообщению?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Ввести ссылку", callback_data="link_input")],
            [InlineKeyboardButton("🚫 Пропустить", callback_data="skip_link")]
        ])
    )
    return LINK

# Обработка выбора: ввод ссылки или пропуск
async def handle_link_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "link_input":
        await query.edit_message_text("Введите ссылку:")
        return WAIT_LINK
    else:
        user_data_temp[query.from_user.id]["link"] = ""
        await query.edit_message_text("Отправьте изображение (или нажмите Пропустить)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚫 Пропустить", callback_data="skip_photo")]
            ])
        )
        return PHOTO

# Получаем ссылку
async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data_temp[update.effective_chat.id]["link"] = update.message.text
    await update.message.reply_text("Отправьте изображение (или нажмите Пропустить)",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Пропустить", callback_data="skip_photo")]
        ])
    )
    return PHOTO

# Обработка фото или текста (если случайно отправил текст)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
        user_data_temp[update.effective_chat.id]["photo"] = photo_file_id
    else:
        user_data_temp[update.effective_chat.id]["photo"] = ""

    await update.message.reply_text("Введите ссылку на бота (например: https://t.me/your_bot):")
    return BOT_LINK

# Обработка кнопки "Пропустить" для фото
async def skip_photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    user_data_temp[update.callback_query.from_user.id]["photo"] = ""
    await update.callback_query.edit_message_text("Введите ссылку на бота (например: https://t.me/your_bot):")
    return BOT_LINK

# Получаем финальную ссылку на бота и отправляем сообщение
async def get_bot_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_chat.id
    data = user_data_temp.get(user_id, {})
    data["bot_link"] = update.message.text

    bot_username = data["bot_link"].split("https://t.me/")[-1].strip("/")
    start_param = "gift123"  # можно заменить на любой параметр

    url_with_param = f"https://t.me/{bot_username}?start={start_param}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Get a gift", url=url_with_param)]
    ])

    parts = []
    if data.get("text"):
        parts.append(data["text"])
    if data.get("link"):
        parts.append(data["link"])
    final_text = "\n".join(parts) if parts else " "

    if data.get("photo"):
        await update.message.reply_photo(
            photo=data["photo"],
            caption=final_text,
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text=final_text,
            reply_markup=keyboard
        )

    user_data_temp.pop(user_id, None)
    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.")
    user_data_temp.pop(update.effective_chat.id, None)
    return ConversationHandler.END

# Запуск бота
import os
def main():
    BOT_TOKEN = "7882247659:AAGzrdYeTyOF46BsBsaIWDtRpJnYUxDI_rk"
    # BOT_TOKEN = os.getenv("BOT_TOKEN")  # ✅ загрузка токена из переменной среды
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TEXT: [CallbackQueryHandler(handle_text_choice)],
            WAIT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_text)],
            LINK: [CallbackQueryHandler(handle_link_choice)],
            WAIT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],
            PHOTO: [
                MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_photo),
                CallbackQueryHandler(skip_photo_callback, pattern="skip_photo")
            ],
            BOT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bot_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True  # 💡 Позволяет снова вызвать /start в любом состоянии
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()

