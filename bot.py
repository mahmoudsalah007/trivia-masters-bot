import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from questions import questions

TOKEN = os.environ.get("BOT_TOKEN", "8715809742:AAHAZb5kT2lFfz0AF5TReSAhDK0qR5mALnY")

# ======= TEXTS =======
texts = {
    "ar": {
        "welcome": "🏆 أهلاً بك في *Trivia Masters*!\n\nاختبر معلوماتك في مجالات متعددة!\nاختر لغتك:",
        "choose_topic": "🎯 اختر التيمة:",
        "choose_level": "📊 اختر مستوى الصعوبة:",
        "question_header": "❓ *سؤال {num} من {total}*\n\n{question}",
        "correct": "✅ إجابة صحيحة! +10 نقاط",
        "wrong": "❌ إجابة خاطئة!\nالإجابة الصحيحة: *{answer}*",
        "score": "🏆 *النتيجة النهائية*\n\nالنقاط: {score}/{total}\nالمستوى: {level}\n\n{emoji} {msg}",
        "play_again": "🔄 العب مرة أخرى",
        "change_lang": "🌍 تغيير اللغة",
        "topics": {"sports": "⚽ رياضة", "movies": "🎬 أفلام وسلاسل", "general": "🧠 ثقافة عامة", "history": "📜 تاريخ", "geography": "🌍 جغرافيا"},
        "levels": {"easy": "🟢 سهل", "medium": "🟡 متوسط", "hard": "🔴 صعب"},
        "msgs": {10: ("🌟", "ممتاز! أنت بطل حقيقي!"), 7: ("👏", "جيد جداً! استمر!"), 4: ("💪", "مش بطال! حاول تاني!"), 0: ("😅", "تحتاج مذاكرة أكتر!")},
    },
    "en": {
        "welcome": "🏆 Welcome to *Trivia Masters*!\n\nTest your knowledge across multiple topics!\nChoose your language:",
        "choose_topic": "🎯 Choose a topic:",
        "choose_level": "📊 Choose difficulty level:",
        "question_header": "❓ *Question {num} of {total}*\n\n{question}",
        "correct": "✅ Correct! +10 points",
        "wrong": "❌ Wrong!\nCorrect answer: *{answer}*",
        "score": "🏆 *Final Score*\n\nPoints: {score}/{total}\nLevel: {level}\n\n{emoji} {msg}",
        "play_again": "🔄 Play Again",
        "change_lang": "🌍 Change Language",
        "topics": {"sports": "⚽ Sports", "movies": "🎬 Movies & Series", "general": "🧠 General Knowledge", "history": "📜 History", "geography": "🌍 Geography"},
        "levels": {"easy": "🟢 Easy", "medium": "🟡 Medium", "hard": "🔴 Hard"},
        "msgs": {10: ("🌟", "Excellent! You're a true champion!"), 7: ("👏", "Great job! Keep it up!"), 4: ("💪", "Not bad! Try again!"), 0: ("😅", "Need more practice!")},
    },
}

def get_msg(lang, score, total):
    ratio = score / total if total else 0
    t = texts[lang]["msgs"]
    if ratio == 1: return t[10]
    elif ratio >= 0.7: return t[7]
    elif ratio >= 0.4: return t[4]
    else: return t[0]

def lang_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]])

def topic_keyboard(lang):
    t = texts[lang]["topics"]
    buttons = [[InlineKeyboardButton(v, callback_data=f"topic_{k}")] for k, v in t.items()]
    return InlineKeyboardMarkup(buttons)

def level_keyboard(lang):
    t = texts[lang]["levels"]
    buttons = [[InlineKeyboardButton(v, callback_data=f"level_{k}")] for k, v in t.items()]
    return InlineKeyboardMarkup(buttons)

def answer_keyboard(options):
    buttons = [[InlineKeyboardButton(opt, callback_data=f"ans_{opt}")] for opt in options]
    return InlineKeyboardMarkup(buttons)

# ======= HANDLERS =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🏆 *Trivia Masters*\n\nChoose your language / اختر لغتك:",
        parse_mode="Markdown",
        reply_markup=lang_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    ud = context.user_data

    # Language
    if data.startswith("lang_"):
        ud["lang"] = data.split("_")[1]
        lang = ud["lang"]
        await query.edit_message_text(
            texts[lang]["choose_topic"],
            reply_markup=topic_keyboard(lang)
        )

    # Topic
    elif data.startswith("topic_"):
        ud["topic"] = data.split("_")[1]
        lang = ud.get("lang", "ar")
        await query.edit_message_text(
            texts[lang]["choose_level"],
            reply_markup=level_keyboard(lang)
        )

    # Level
    elif data.startswith("level_"):
        ud["level"] = data.split("_")[1]
        lang = ud.get("lang", "ar")
        topic = ud.get("topic", "general")
        level = ud["level"]
        all_q = questions[lang][topic][level]
        ud["questions"] = random.sample(all_q, min(10, len(all_q)))
        ud["current"] = 0
        ud["score"] = 0
        await send_question(query, context)

    # Answer
    elif data.startswith("ans_"):
        answer = data[4:]
        lang = ud.get("lang", "ar")
        q_list = ud.get("questions", [])
        idx = ud.get("current", 0)
        if idx < len(q_list):
            correct = q_list[idx]["answer"]
            if answer == correct:
                ud["score"] = ud.get("score", 0) + 10
                msg = texts[lang]["correct"]
            else:
                msg = texts[lang]["wrong"].format(answer=correct)
            ud["current"] = idx + 1
            await query.edit_message_text(msg, parse_mode="Markdown")
            if ud["current"] < len(q_list):
                await send_question(query, context, new_msg=True)
            else:
                await send_score(query, context)

    # Play again
    elif data == "play_again":
        ud_lang = ud.get("lang", "ar")
        ud.clear()
        ud["lang"] = ud_lang
        lang = ud["lang"]
        await query.edit_message_text(
            texts[lang]["choose_topic"],
            reply_markup=topic_keyboard(lang)
        )

    # Change language
    elif data == "change_lang":
        await query.edit_message_text(
            "Choose your language / اختر لغتك:",
            reply_markup=lang_keyboard()
        )

async def send_question(query, context, new_msg=False):
    ud = context.user_data
    lang = ud.get("lang", "ar")
    q_list = ud.get("questions", [])
    idx = ud.get("current", 0)
    total = len(q_list)
    q = q_list[idx]
    text = texts[lang]["question_header"].format(
        num=idx + 1, total=total, question=q["q"]
    )
    options = q["options"][:]
    random.shuffle(options)
    kb = answer_keyboard(options)
    if new_msg:
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

async def send_score(query, context):
    ud = context.user_data
    lang = ud.get("lang", "ar")
    score = ud.get("score", 0)
    total = len(ud.get("questions", [])) * 10
    level = ud.get("level", "easy")
    emoji, msg = get_msg(lang, score, total)
    level_name = texts[lang]["levels"].get(level, level)
    text = texts[lang]["score"].format(
        score=score, total=total, level=level_name, emoji=emoji, msg=msg
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(texts[lang]["play_again"], callback_data="play_again"),
        InlineKeyboardButton(texts[lang]["change_lang"], callback_data="change_lang"),
    ]])
    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ar")
    msg = "اكتب /start للبدء 🎮" if lang == "ar" else "Type /start to begin 🎮"
    await update.message.reply_text(msg)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    print("✅ Trivia Masters Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
