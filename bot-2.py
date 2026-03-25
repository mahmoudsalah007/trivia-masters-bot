import os
import json
import random
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from questions import get_questions

TOKEN = os.environ.get("BOT_TOKEN", "8715809742:AAHAZb5kT2lFfz0AF5TReSAhDK0qR5mALnY")
DATA_FILE = "user_data.json"

# ======= DATA MANAGEMENT =======
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(data, uid):
    uid = str(uid)
    if uid not in data:
        data[uid] = {
            "name": "",
            "total_score": 0,
            "games_played": 0,
            "correct_answers": 0,
            "total_questions": 0,
            "last_daily": "",
            "daily_streak": 0,
            "lang": "ar"
        }
    return data[uid]

# ======= TEXTS =======
texts = {
    "ar": {
        "welcome": "🏆 أهلاً بك في *Trivia Masters*!\n\nاختبر معلوماتك في مجالات متعددة!\nاختر لغتك:",
        "choose_topic": "🎯 اختر التيمة:",
        "choose_level": "📊 اختر مستوى الصعوبة:",
        "question_header": "❓ *سؤال {num} من {total}*\n\n{question}",
        "correct": "✅ إجابة صحيحة! +10 نقاط",
        "wrong": "❌ إجابة خاطئة!\nالإجابة الصحيحة: *{answer}*",
        "score": "🏆 *النتيجة النهائية*\n\nالنقاط: {score}/{total}\n\n{emoji} {msg}",
        "play_again": "🔄 العب مرة أخرى",
        "change_lang": "🌍 تغيير اللغة",
        "main_menu": "🏠 القائمة الرئيسية",
        "leaderboard_btn": "🏅 المتصدرين",
        "stats_btn": "📊 إحصائياتي",
        "daily_btn": "🎁 مكافأة يومية",
        "play_btn": "🎮 العب الآن",
        "topics": {
            "sports": "⚽ رياضة",
            "movies": "🎬 أفلام وسلاسل",
            "general": "🧠 ثقافة عامة",
            "history": "📜 تاريخ",
            "geography": "🌍 جغرافيا"
        },
        "levels": {
            "easy": "🟢 سهل",
            "medium": "🟡 متوسط",
            "hard": "🔴 صعب"
        },
        "msgs": {
            "perfect": ("🌟", "مثالي! أنت بطل حقيقي!"),
            "great": ("👏", "جيد جداً! استمر!"),
            "ok": ("💪", "مش بطال! حاول تاني!"),
            "bad": ("😅", "تحتاج مذاكرة أكتر!")
        },
        "daily_claimed": "🎁 *مكافأة يومية!*\n\nحصلت على *{points} نقطة* مكافأة!\n🔥 سلسلة: {streak} يوم متتالي",
        "daily_already": "⏰ استلمت مكافأتك اليوم بالفعل!\nتعالى بكره عشان تاخد مكافأتك الجديدة 😊",
        "stats": "📊 *إحصائياتك*\n\n🏆 إجمالي النقاط: {total_score}\n🎮 عدد الجولات: {games}\n✅ إجابات صحيحة: {correct}/{total_q}\n📈 نسبة النجاح: {accuracy}%\n🔥 سلسلة يومية: {streak} يوم",
        "leaderboard": "🏅 *أعلى 10 لاعبين*\n\n{board}",
        "no_players": "مفيش لاعبين بعد، كن أول واحد! 🚀",
    },
    "en": {
        "welcome": "🏆 Welcome to *Trivia Masters*!\n\nTest your knowledge across multiple topics!\nChoose your language:",
        "choose_topic": "🎯 Choose a topic:",
        "choose_level": "📊 Choose difficulty level:",
        "question_header": "❓ *Question {num} of {total}*\n\n{question}",
        "correct": "✅ Correct! +10 points",
        "wrong": "❌ Wrong!\nCorrect answer: *{answer}*",
        "score": "🏆 *Final Score*\n\nPoints: {score}/{total}\n\n{emoji} {msg}",
        "play_again": "🔄 Play Again",
        "change_lang": "🌍 Change Language",
        "main_menu": "🏠 Main Menu",
        "leaderboard_btn": "🏅 Leaderboard",
        "stats_btn": "📊 My Stats",
        "daily_btn": "🎁 Daily Reward",
        "play_btn": "🎮 Play Now",
        "topics": {
            "sports": "⚽ Sports",
            "movies": "🎬 Movies & Series",
            "general": "🧠 General Knowledge",
            "history": "📜 History",
            "geography": "🌍 Geography"
        },
        "levels": {
            "easy": "🟢 Easy",
            "medium": "🟡 Medium",
            "hard": "🔴 Hard"
        },
        "msgs": {
            "perfect": ("🌟", "Perfect! You're a true champion!"),
            "great": ("👏", "Great job! Keep it up!"),
            "ok": ("💪", "Not bad! Try again!"),
            "bad": ("😅", "Need more practice!")
        },
        "daily_claimed": "🎁 *Daily Reward!*\n\nYou earned *{points} points*!\n🔥 Streak: {streak} days in a row",
        "daily_already": "⏰ You already claimed today's reward!\nCome back tomorrow for your next reward 😊",
        "stats": "📊 *Your Statistics*\n\n🏆 Total Score: {total_score}\n🎮 Games Played: {games}\n✅ Correct Answers: {correct}/{total_q}\n📈 Accuracy: {accuracy}%\n🔥 Daily Streak: {streak} days",
        "leaderboard": "🏅 *Top 10 Players*\n\n{board}",
        "no_players": "No players yet, be the first! 🚀",
    },
}

medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def get_msg_key(score, total):
    ratio = score / total if total else 0
    if ratio == 1: return "perfect"
    elif ratio >= 0.7: return "great"
    elif ratio >= 0.4: return "ok"
    else: return "bad"

def main_menu_keyboard(lang):
    t = texts[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t["play_btn"], callback_data="goto_topics")],
        [InlineKeyboardButton(t["leaderboard_btn"], callback_data="leaderboard"),
         InlineKeyboardButton(t["stats_btn"], callback_data="stats")],
        [InlineKeyboardButton(t["daily_btn"], callback_data="daily"),
         InlineKeyboardButton(t["change_lang"], callback_data="change_lang")],
    ])

def topic_keyboard(lang):
    t = texts[lang]["topics"]
    buttons = [[InlineKeyboardButton(v, callback_data=f"topic_{k}")] for k, v in t.items()]
    buttons.append([InlineKeyboardButton(texts[lang]["main_menu"], callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def level_keyboard(lang):
    t = texts[lang]["levels"]
    buttons = [[InlineKeyboardButton(v, callback_data=f"level_{k}")] for k, v in t.items()]
    buttons.append([InlineKeyboardButton(texts[lang]["main_menu"], callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def answer_keyboard(options):
    return InlineKeyboardMarkup([[InlineKeyboardButton(opt, callback_data=f"ans_{opt}")] for opt in options])

def end_keyboard(lang):
    t = texts[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t["play_again"], callback_data="goto_topics")],
        [InlineKeyboardButton(t["leaderboard_btn"], callback_data="leaderboard"),
         InlineKeyboardButton(t["stats_btn"], callback_data="stats")],
        [InlineKeyboardButton(t["main_menu"], callback_data="main_menu")],
    ])

def lang_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]])

# ======= HANDLERS =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid = update.effective_user.id
    user = get_user(data, uid)
    user["name"] = update.effective_user.first_name or "Player"
    save_data(data)
    context.user_data.clear()
    await update.message.reply_text(
        "🏆 *Trivia Masters*\n\nChoose your language / اختر لغتك:",
        parse_mode="Markdown",
        reply_markup=lang_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data_store = load_data()
    uid = query.from_user.id
    user = get_user(data_store, uid)
    d = query.data
    ud = context.user_data
    lang = ud.get("lang", user.get("lang", "ar"))

    # Language
    if d.startswith("lang_"):
        lang = d.split("_")[1]
        ud["lang"] = lang
        user["lang"] = lang
        save_data(data_store)
        await query.edit_message_text(
            f"{'أهلاً' if lang == 'ar' else 'Welcome'} *{query.from_user.first_name}*! 🎉",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(lang)
        )

    # Main menu
    elif d == "main_menu":
        await query.edit_message_text(
            f"🏆 *Trivia Masters*",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(lang)
        )

    # Go to topics
    elif d == "goto_topics":
        await query.edit_message_text(
            texts[lang]["choose_topic"],
            reply_markup=topic_keyboard(lang)
        )

    # Change lang
    elif d == "change_lang":
        await query.edit_message_text(
            "Choose your language / اختر لغتك:",
            reply_markup=lang_keyboard()
        )

    # Topic
    elif d.startswith("topic_"):
        ud["topic"] = d.split("_")[1]
        await query.edit_message_text(
            texts[lang]["choose_level"],
            reply_markup=level_keyboard(lang)
        )

    # Level
    elif d.startswith("level_"):
        ud["level"] = d.split("_")[1]
        topic = ud.get("topic", "general")
        level = ud["level"]
        q_list = get_questions(lang, topic, level, 10)
        ud["questions"] = q_list
        ud["current"] = 0
        ud["score"] = 0
        await send_question(query, context)

    # Answer
    elif d.startswith("ans_"):
        answer = d[4:]
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
                # Save stats
                score = ud.get("score", 0)
                total_q = len(q_list)
                user["total_score"] = user.get("total_score", 0) + score
                user["games_played"] = user.get("games_played", 0) + 1
                user["correct_answers"] = user.get("correct_answers", 0) + (score // 10)
                user["total_questions"] = user.get("total_questions", 0) + total_q
                save_data(data_store)
                await send_score(query, context)

    # Daily reward
    elif d == "daily":
        today = datetime.date.today().isoformat()
        last = user.get("last_daily", "")
        if last == today:
            await query.edit_message_text(
                texts[lang]["daily_already"],
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard(lang)
            )
        else:
            yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
            streak = user.get("daily_streak", 0)
            if last == yesterday:
                streak += 1
            else:
                streak = 1
            bonus = 50 + (streak * 10)
            user["last_daily"] = today
            user["daily_streak"] = streak
            user["total_score"] = user.get("total_score", 0) + bonus
            save_data(data_store)
            await query.edit_message_text(
                texts[lang]["daily_claimed"].format(points=bonus, streak=streak),
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard(lang)
            )

    # Stats
    elif d == "stats":
        total_q = user.get("total_questions", 0)
        correct = user.get("correct_answers", 0)
        accuracy = round((correct / total_q * 100) if total_q > 0 else 0)
        text = texts[lang]["stats"].format(
            total_score=user.get("total_score", 0),
            games=user.get("games_played", 0),
            correct=correct,
            total_q=total_q,
            accuracy=accuracy,
            streak=user.get("daily_streak", 0)
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard(lang))

    # Leaderboard
    elif d == "leaderboard":
        all_users = [(v.get("name", "?"), v.get("total_score", 0)) for v in data_store.values() if v.get("total_score", 0) > 0]
        all_users.sort(key=lambda x: x[1], reverse=True)
        top = all_users[:10]
        if not top:
            board_text = texts[lang]["no_players"]
        else:
            lines = [f"{medals[i]} {name} — {score}" for i, (name, score) in enumerate(top)]
            board_text = "\n".join(lines)
        await query.edit_message_text(
            texts[lang]["leaderboard"].format(board=board_text),
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(lang)
        )

async def send_question(query, context, new_msg=False):
    ud = context.user_data
    lang = ud.get("lang", "ar")
    q_list = ud.get("questions", [])
    idx = ud.get("current", 0)
    total = len(q_list)
    q = q_list[idx]
    text = texts[lang]["question_header"].format(num=idx + 1, total=total, question=q["q"])
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
    key = get_msg_key(score, total)
    emoji, msg = texts[lang]["msgs"][key]
    text = texts[lang]["score"].format(score=score, total=total, emoji=emoji, msg=msg)
    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=end_keyboard(lang))

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ar")
    msg = "اكتب /start للبدء 🎮" if lang == "ar" else "Type /start to begin 🎮"
    await update.message.reply_text(msg)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    print("✅ Trivia Masters V2 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
