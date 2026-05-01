import os
import logging
import google.generativeai as genai
from gtts import gTTS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ===================== SOZLAMALAR =====================
TELEGRAM_TOKEN = "8614312464:AAG7OtIAsN9eTzoOobqW32FBBkREHuWvpjk"
GEMINI_API_KEY = "AIzaSyClCUC4XrIA9muRTfA9NEUuG9pwwCPxqnM"
# ======================================================

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Gemini sozlash
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Foydalanuvchilar suhbat tarixi
user_chats = {}

SYSTEM_PROMPT = """Sen aqlli va do'stona AI yordamchisan.
Foydalanuvchi qaysi tilda yozsa, o'sha tilda javob ber.
O'zbek tilida yozsa o'zbek tilida, rus tilida rus tilida, ingliz tilida ingliz tilida javob ber.
Qisqa, aniq va foydali javoblar ber."""


def get_ai_response(user_id: int, user_message: str) -> str:
    """Gemini dan javob olish"""
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])

    chat = user_chats[user_id]
    response = chat.send_message(SYSTEM_PROMPT + "\n\nFoydalanuvchi: " + user_message)
    return response.text


def text_to_voice(text: str, user_id: int) -> str:
    """Matnni ovozga aylantirish"""
    audio_file = f"voice_{user_id}.mp3"
    try:
        tts = gTTS(text=text, lang="uz")
    except Exception:
        tts = gTTS(text=text, lang="ru")
    tts.save(audio_file)
    return audio_file


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🎤 Ovozli rejim", callback_data="voice_mode")],
        [InlineKeyboardButton("💬 Matnli rejim", callback_data="text_mode")],
        [InlineKeyboardButton("🗑 Tarixni tozalash", callback_data="clear_history")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Salom, {user.first_name}! 👋\n\n"
        "🤖 Men Gemini AI yordamchiman!\n"
        "✅ Har qanday tilda gaplasha olamiz\n"
        "✅ Matn va ovozli javob bera olaman\n\n"
        "Menga xohlagan narsani yozing!",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Komandalar:\n\n"
        "/start - Botni boshlash\n"
        "/help - Yordam\n"
        "/voice - Ovozli rejim\n"
        "/text - Matnli rejim\n"
        "/clear - Tarixni tozalash"
    )


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["voice_mode"] = True
    await update.message.reply_text("🎤 Ovozli rejim yoqildi!")


async def text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["voice_mode"] = False
    await update.message.reply_text("💬 Matnli rejim yoqildi!")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_chats[user_id] = model.start_chat(history=[])
    await update.message.reply_text("🗑 Tarix tozalandi!")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "voice_mode":
        context.user_data["voice_mode"] = True
        await query.edit_message_text("🎤 Ovozli rejim yoqildi! Xabar yozing...")
    elif query.data == "text_mode":
        context.user_data["voice_mode"] = False
        await query.edit_message_text("💬 Matnli rejim yoqildi! Xabar yozing...")
    elif query.data == "clear_history":
        user_id = query.from_user.id
        user_chats[user_id] = model.start_chat(history=[])
        await query.edit_message_text("🗑 Tarix tozalandi!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    voice_mode = context.user_data.get("voice_mode", False)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        ai_response = get_ai_response(user_id, user_message)
        await update.message.reply_text(ai_response)

        if voice_mode:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_voice")
            audio_file = text_to_voice(ai_response, user_id)
            with open(audio_file, "rb") as audio:
                await update.message.reply_voice(voice=audio)
            os.remove(audio_file)

    except Exception as e:
        logger.error(f"Xato: {e}")
        await update.message.reply_text(f"❌ Xato yuz berdi: {str(e)}")


def main():
    print("🤖 Gemini AI Bot ishga tushmoqda...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("voice", voice_command))
    app.add_handler(CommandHandler("text", text_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

