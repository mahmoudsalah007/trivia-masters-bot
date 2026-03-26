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

# ======= LEVELS SYSTEM =======
LEVELS = [
    (0,     "🥉 مبتدئ",        "Beginner"),
    (500,   "🥈 متعلم",         "Learner"),
    (1500,  "🥇 متمكن",         "Skilled"),
    (3000,  "💎 محترف",         "Pro"),
    (6000,  "🔥 خبير",          "Expert"),
    (10000, "⚡ متقدم",          "Advanced"),
    (15000, "🌟 نجم",            "Star"),
    (22000, "👑 بطل",            "Champion"),
    (30000, "🏆 أسطورة",         "Legend"),
    (50000, "🌌 أسطورة عظمى",   "Grand Legend"),
]

def get_level(xp, lang="ar"):
    level_num = 0
    for i, (req, ar, en) in enumerate(LEVELS):
        if xp >= req:
            level_num = i
    req, ar, en = LEVELS[level_num]
    next_req = LEVELS[level_num + 1][0] if level_num + 1 < len(LEVELS) else None
    name = ar if lang == "ar" else en
    return level_num + 1, name, next_req

SHOP_ITEMS = {
    "hint":     {"ar": "💡 تلميح (يحذف إجابتين خاطئتين)", "en": "💡 Hint (removes 2 wrong answers)", "price": 50},
    "skip":     {"ar": "⏭️ تخطي السؤال",                   "en": "⏭️ Skip Question",                  "price": 30},
    "double":   {"ar": "⚡ نقاط مضاعفة (جولة كاملة)",      "en": "⚡ Double Points (full round)",      "price": 100},
    "shield":   {"ar": "🛡️ درع (يحمي من خسارة سلسلة)",    "en": "🛡️ Shield (protects streak)",       "price": 80},
}

ACHIEVEMENTS = {
    "first_game":    {"ar": "🎮 أول جولة!",          "en": "🎮 First Game!",         "req": 1,   "type": "games"},
    "games_10":      {"ar": "🎯 لاعب متمرس (10)",    "en": "🎯 Veteran (10 games)",  "req": 10,  "type": "games"},
    "games_50":      {"ar": "🏅 محترف (50 جولة)",    "en": "🏅 Pro (50 games)",      "req": 50,  "type": "games"},
    "perfect_game":  {"ar": "⭐ جولة مثالية!",        "en": "⭐ Perfect Game!",       "req": 1,   "type": "perfect"},
    "streak_3":      {"ar": "🔥 سلسلة 3 أيام",       "en": "🔥 3 Day Streak",        "req": 3,   "type": "streak"},
    "streak_7":      {"ar": "🔥🔥 أسبوع كامل!",      "en": "🔥🔥 Full Week!",        "req": 7,   "type": "streak"},
    "score_1000":    {"ar": "💰 ألف نقطة!",           "en": "💰 1000 Points!",        "req": 1000,"type": "score"},
    "score_10000":   {"ar": "💎 عشرة آلاف نقطة!",    "en": "💎 10K Points!",         "req": 10000,"type": "score"},
}

DAILY_MISSIONS = [
    {"ar": "العب 3 جولات اليوم",       "en": "Play 3 games today",         "type": "games",   "req": 3,  "reward": 100},
    {"ar": "احصل على 5 إجابات صحيحة", "en": "Get 5 correct answers",      "type": "correct", "req": 5,  "reward": 80},
    {"ar": "العب جولة على مستوى صعب", "en": "Play a hard difficulty game", "type": "hard",    "req": 1,  "reward": 150},
    {"ar": "احصل على جولة مثالية",    "en": "Get a perfect game",          "type": "perfect", "req": 1,  "reward": 200},
    {"ar": "العب في تيمتين مختلفتين", "en": "Play 2 different topics",     "type": "topics",  "req": 2,  "reward": 120},
]

# ======= DATA =======
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(data, uid, name="Player"):
    uid = str(uid)
    if uid not in data:
        data[uid] = {
            "name": name,
            "xp": 0,
            "coins": 100,
            "games_played": 0,
            "correct_answers": 0,
            "total_questions": 0,
            "perfect_games": 0,
            "last_daily": "",
            "daily_streak": 0,
            "lang": "ar",
            "inventory": {"hint": 0, "skip": 0, "double": 0, "shield": 0},
            "achievements": [],
            "daily_mission": None,
            "mission_progress": {},
            "topics_today": [],
        }
    if "inventory" not in data[uid]:
        data[uid]["inventory"] = {"hint": 0, "skip": 0, "double": 0, "shield": 0}
    if "achievements" not in data[uid]:
        data[uid]["achievements"] = []
    if "coins" not in data[uid]:
        data[uid]["coins"] = 100
    return data[uid]

def check_achievements(user, lang):
    new_achievements = []
    earned = user.get("achievements", [])
    for key, ach in ACHIEVEMENTS.items():
        if key in earned:
            continue
        t = ach["type"]
        req = ach["req"]
        unlocked = False
        if t == "games" and user.get("games_played", 0) >= req:
            unlocked = True
        elif t == "perfect" and user.get("perfect_games", 0) >= req:
            unlocked = True
        elif t == "streak" and user.get("daily_streak", 0) >= req:
            unlocked = True
        elif t == "score" and user.get("xp", 0) >= req:
            unlocked = True
        if unlocked:
            earned.append(key)
            name = ach["ar"] if lang == "ar" else ach["en"]
            new_achievements.append(name)
    user["achievements"] = earned
    return new_achievements

# ======= KEYBOARDS =======
def main_menu_keyboard(lang, user):
    lvl_num, lvl_name, _ = get_level(user.get("xp", 0), lang)
    coins = user.get("coins", 0)
    if lang == "ar":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 العب الآن", callback_data="goto_topics")],
            [InlineKeyboardButton("🏅 المتصدرين", callback_data="leaderboard"),
             InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")],
            [InlineKeyboardButton("🎁 مكافأة يومية", callback_data="daily"),
             InlineKeyboardButton("📋 مهمتي اليوم", callback_data="mission")],
            [InlineKeyboardButton("🛒 المتجر", callback_data="shop"),
             InlineKeyboardButton("🏆 إنجازاتي", callback_data="achievements")],
            [InlineKeyboardButton("🌍 تغيير اللغة", callback_data="change_lang")],
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", callback_data="goto_topics")],
            [InlineKeyboardButton("🏅 Leaderboard", callback_data="leaderboard"),
             InlineKeyboardButton("📊 My Stats", callback_data="stats")],
            [InlineKeyboardButton("🎁 Daily Reward", callback_data="daily"),
             InlineKeyboardButton("📋 Daily Mission", callback_data="mission")],
            [InlineKeyboardButton("🛒 Shop", callback_data="shop"),
             InlineKeyboardButton("🏆 Achievements", callback_data="achievements")],
            [InlineKeyboardButton("🌍 Change Language", callback_data="change_lang")],
        ])

def topic_keyboard(lang):
    topics = {
        "sports":    ("⚽ رياضة",         "⚽ Sports"),
        "movies":    ("🎬 أفلام وسلاسل",  "🎬 Movies"),
        "general":   ("🧠 ثقافة عامة",    "🧠 General"),
        "history":   ("📜 تاريخ",         "📜 History"),
        "geography": ("🌍 جغرافيا",       "🌍 Geography"),
    }
    buttons = []
    for k, (ar, en) in topics.items():
        label = ar if lang == "ar" else en
        buttons.append([InlineKeyboardButton(label, callback_data=f"topic_{k}")])
    back = "🏠 القائمة الرئيسية" if lang == "ar" else "🏠 Main Menu"
    buttons.append([InlineKeyboardButton(back, callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def level_keyboard(lang, user):
    levels = {
        "easy":   ("🟢 سهل   — 10 XP/سؤال",   "🟢 Easy   — 10 XP/Q"),
        "medium": ("🟡 متوسط — 20 XP/سؤال",   "🟡 Medium — 20 XP/Q"),
        "hard":   ("🔴 صعب   — 30 XP/سؤال",   "🔴 Hard   — 30 XP/Q"),
    }
    inv = user.get("inventory", {})
    buttons = []
    for k, (ar, en) in levels.items():
        label = ar if lang == "ar" else en
        buttons.append([InlineKeyboardButton(label, callback_data=f"level_{k}")])

    # Power-ups
    powerups = []
    if inv.get("hint", 0) > 0:
        lbl = f"💡 تلميح ({inv['hint']})" if lang == "ar" else f"💡 Hint ({inv['hint']})"
        powerups.append(InlineKeyboardButton(lbl, callback_data="use_hint"))
    if inv.get("double", 0) > 0:
        lbl = f"⚡ مضاعفة ({inv['double']})" if lang == "ar" else f"⚡ Double ({inv['double']})"
        powerups.append(InlineKeyboardButton(lbl, callback_data="use_double"))
    if powerups:
        buttons.append(powerups)

    back = "🏠 القائمة الرئيسية" if lang == "ar" else "🏠 Main Menu"
    buttons.append([InlineKeyboardButton(back, callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def answer_keyboard(options, lang, user, show_hint=False, hint_used=False):
    buttons = []
    for opt in options:
        buttons.append([InlineKeyboardButton(opt, callback_data=f"ans_{opt}")])
    action_row = []
    inv = user.get("inventory", {})
    if not hint_used and inv.get("hint", 0) > 0:
        lbl = "💡 استخدم تلميح" if lang == "ar" else "💡 Use Hint"
        action_row.append(InlineKeyboardButton(lbl, callback_data="use_hint_now"))
    if inv.get("skip", 0) > 0:
        lbl = "⏭️ تخطي" if lang == "ar" else "⏭️ Skip"
        action_row.append(InlineKeyboardButton(lbl, callback_data="skip_question"))
    if action_row:
        buttons.append(action_row)
    return InlineKeyboardMarkup(buttons)

def shop_keyboard(lang, user):
    coins = user.get("coins", 0)
    buttons = []
    for key, item in SHOP_ITEMS.items():
        name = item["ar"] if lang == "ar" else item["en"]
        price = item["price"]
        inv_count = user.get("inventory", {}).get(key, 0)
        lbl = f"{name} | {price}🪙 (لديك: {inv_count})" if lang == "ar" else f"{name} | {price}🪙 (have: {inv_count})"
        buttons.append([InlineKeyboardButton(lbl, callback_data=f"buy_{key}")])
    back = "🏠 القائمة الرئيسية" if lang == "ar" else "🏠 Main Menu"
    buttons.append([InlineKeyboardButton(back, callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def end_keyboard(lang):
    if lang == "ar":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 العب مرة أخرى", callback_data="goto_topics")],
            [InlineKeyboardButton("🏅 المتصدرين", callback_data="leaderboard"),
             InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")],
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Again", callback_data="goto_topics")],
            [InlineKeyboardButton("🏅 Leaderboard", callback_data="leaderboard"),
             InlineKeyboardButton("📊 My Stats", callback_data="stats")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ])

def lang_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]])

# ======= HELPERS =======
def xp_for_level(lang, ud):
    level_name = ud.get("level", "easy")
    return {"easy": 10, "medium": 20, "hard": 30}.get(level_name, 10)

def coins_for_correct():
    return random.randint(3, 8)

def build_profile(user, lang):
    xp = user.get("xp", 0)
    lvl_num, lvl_name, next_xp = get_level(xp, lang)
    coins = user.get("coins", 0)
    games = user.get("games_played", 0)
    correct = user.get("correct_answers", 0)
    total_q = user.get("total_questions", 0)
    accuracy = round((correct / total_q * 100) if total_q > 0 else 0)
    streak = user.get("daily_streak", 0)
    perfect = user.get("perfect_games", 0)
    progress = ""
    if next_xp:
        pct = int((xp / next_xp) * 10)
        bar = "█" * pct + "░" * (10 - pct)
        progress = f"\n[{bar}] {xp}/{next_xp} XP"
    if lang == "ar":
        return (
            f"👤 *{user.get('name', 'لاعب')}*\n"
            f"{lvl_name} — المستوى {lvl_num}{progress}\n\n"
            f"🪙 الكوينز: {coins}\n"
            f"🎮 الجولات: {games}\n"
            f"✅ الدقة: {accuracy}%\n"
            f"⭐ جولات مثالية: {perfect}\n"
            f"🔥 السلسلة: {streak} يوم"
        )
    else:
        return (
            f"👤 *{user.get('name', 'Player')}*\n"
            f"{lvl_name} — Level {lvl_num}{progress}\n\n"
            f"🪙 Coins: {coins}\n"
            f"🎮 Games: {games}\n"
            f"✅ Accuracy: {accuracy}%\n"
            f"⭐ Perfect Games: {perfect}\n"
            f"🔥 Streak: {streak} days"
        )

# ======= HANDLERS =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid = update.effective_user.id
    name = update.effective_user.first_name or "Player"
    user = get_user(data, uid, name)
    user["name"] = name
    save_data(data)
    context.user_data.clear()

    # Loading screen effect
    msg = await update.message.reply_text("🎮 *Trivia Masters* جاري التحميل...\n⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛", parse_mode="Markdown")
    import asyncio
    for i in range(1, 11):
        bar = "🟩" * i + "⬛" * (10 - i)
        await asyncio.sleep(0.3)
        try:
            await msg.edit_text(f"🎮 *Trivia Masters* جاري التحميل...\n{bar}", parse_mode="Markdown")
        except:
            pass

    lang = user.get("lang", "ar")
    await msg.edit_text(
        "Choose your language / اختر لغتك:",
        reply_markup=lang_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data_store = load_data()
    uid = query.from_user.id
    name = query.from_user.first_name or "Player"
    user = get_user(data_store, uid, name)
    d = query.data
    ud = context.user_data
    lang = ud.get("lang", user.get("lang", "ar"))

    # Language
    if d.startswith("lang_"):
        lang = d.split("_")[1]
        ud["lang"] = lang
        user["lang"] = lang
        save_data(data_store)
        welcome = f"🏆 *Trivia Masters*\n\n{build_profile(user, lang)}"
        await query.edit_message_text(welcome, parse_mode="Markdown", reply_markup=main_menu_keyboard(lang, user))

    # Main menu
    elif d == "main_menu":
        data_store = load_data()
        user = get_user(data_store, uid, name)
        profile = build_profile(user, lang)
        await query.edit_message_text(f"🏆 *Trivia Masters*\n\n{profile}", parse_mode="Markdown", reply_markup=main_menu_keyboard(lang, user))

    # Topics
    elif d == "goto_topics":
        label = "🎯 اختر التيمة:" if lang == "ar" else "🎯 Choose a topic:"
        await query.edit_message_text(label, reply_markup=topic_keyboard(lang))

    # Change lang
    elif d == "change_lang":
        await query.edit_message_text("Choose your language / اختر لغتك:", reply_markup=lang_keyboard())

    # Topic selected
    elif d.startswith("topic_"):
        ud["topic"] = d.split("_")[1]
        label = "📊 اختر مستوى الصعوبة:" if lang == "ar" else "📊 Choose difficulty:"
        await query.edit_message_text(label, reply_markup=level_keyboard(lang, user))

    # Use hint before game
    elif d == "use_hint":
        if user.get("inventory", {}).get("hint", 0) > 0:
            ud["hint_active"] = True
            msg = "💡 التلميح سيُفعّل في أول سؤال!" if lang == "ar" else "💡 Hint will activate on first question!"
            await query.answer(msg, show_alert=True)

    # Use double before game
    elif d == "use_double":
        if user.get("inventory", {}).get("double", 0) > 0:
            ud["double_active"] = True
            user["inventory"]["double"] -= 1
            save_data(data_store)
            msg = "⚡ النقاط المضاعفة فعّالة لهذه الجولة!" if lang == "ar" else "⚡ Double points active for this round!"
            await query.answer(msg, show_alert=True)

    # Level selected
    elif d.startswith("level_"):
        ud["level"] = d.split("_")[1]
        topic = ud.get("topic", "general")
        level = ud["level"]
        q_list = get_questions(lang, topic, level, 10)
        ud["questions"] = q_list
        ud["current"] = 0
        ud["score"] = 0
        ud["xp_gained"] = 0
        ud["coins_gained"] = 0
        ud["hint_used"] = False
        ud["topics_played"] = ud.get("topics_played", set())
        if isinstance(ud["topics_played"], list):
            ud["topics_played"] = set(ud["topics_played"])
        ud["topics_played"].add(topic)
        await send_question(query, context, user)

    # Hint during game
    elif d == "use_hint_now":
        inv = user.get("inventory", {})
        if inv.get("hint", 0) > 0 and not ud.get("hint_used", False):
            inv["hint"] -= 1
            ud["hint_used"] = True
            save_data(data_store)
            await resend_question_with_hint(query, context, user)
        else:
            msg = "مفيش تلميحات!" if lang == "ar" else "No hints available!"
            await query.answer(msg, show_alert=True)

    # Skip question
    elif d == "skip_question":
        inv = user.get("inventory", {})
        if inv.get("skip", 0) > 0:
            inv["skip"] -= 1
            ud["current"] = ud.get("current", 0) + 1
            save_data(data_store)
            q_list = ud.get("questions", [])
            if ud["current"] < len(q_list):
                await send_question(query, context, user, new_msg=True)
            else:
                await finalize_game(query, context, data_store, user, uid)
        else:
            msg = "مفيش تخطيات!" if lang == "ar" else "No skips available!"
            await query.answer(msg, show_alert=True)

    # Answer
    elif d.startswith("ans_"):
        answer = d[4:]
        q_list = ud.get("questions", [])
        idx = ud.get("current", 0)
        if idx < len(q_list):
            correct = q_list[idx]["answer"]
            xp_per_q = xp_for_level(lang, ud)
            multiplier = 2 if ud.get("double_active") else 1
            if answer == correct:
                earned_xp = xp_per_q * multiplier
                earned_coins = coins_for_correct() * multiplier
                ud["score"] = ud.get("score", 0) + (10 * multiplier)
                ud["xp_gained"] = ud.get("xp_gained", 0) + earned_xp
                ud["coins_gained"] = ud.get("coins_gained", 0) + earned_coins
                ud["hint_used"] = False
                if lang == "ar":
                    msg = f"✅ *إجابة صحيحة!*\n+{earned_xp} XP  |  +{earned_coins} 🪙"
                else:
                    msg = f"✅ *Correct!*\n+{earned_xp} XP  |  +{earned_coins} 🪙"
            else:
                ud["hint_used"] = False
                if lang == "ar":
                    msg = f"❌ *إجابة خاطئة!*\nالصحيحة: *{correct}*"
                else:
                    msg = f"❌ *Wrong!*\nCorrect: *{correct}*"
            ud["current"] = idx + 1
            await query.edit_message_text(msg, parse_mode="Markdown")
            if ud["current"] < len(q_list):
                await send_question(query, context, user, new_msg=True)
            else:
                await finalize_game(query, context, data_store, user, uid)

    # Daily reward
    elif d == "daily":
        today = datetime.date.today().isoformat()
        last = user.get("last_daily", "")
        if last == today:
            msg = "⏰ استلمت مكافأتك اليوم!\nتعالى بكره 😊" if lang == "ar" else "⏰ Already claimed today!\nCome back tomorrow 😊"
            await query.edit_message_text(msg, reply_markup=main_menu_keyboard(lang, user))
        else:
            yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
            streak = user.get("daily_streak", 0)
            streak = streak + 1 if last == yesterday else 1
            bonus_coins = 50 + (streak * 10)
            bonus_xp = 20 + (streak * 5)
            user["last_daily"] = today
            user["daily_streak"] = streak
            user["coins"] = user.get("coins", 0) + bonus_coins
            user["xp"] = user.get("xp", 0) + bonus_xp
            save_data(data_store)
            if lang == "ar":
                msg = f"🎁 *مكافأة يومية!*\n\n+{bonus_coins} 🪙 كوينز\n+{bonus_xp} ⭐ XP\n🔥 السلسلة: {streak} يوم متتالي"
            else:
                msg = f"🎁 *Daily Reward!*\n\n+{bonus_coins} 🪙 Coins\n+{bonus_xp} ⭐ XP\n🔥 Streak: {streak} days"
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=main_menu_keyboard(lang, user))

    # Shop
    elif d == "shop":
        coins = user.get("coins", 0)
        title = f"🛒 *المتجر* | 🪙 {coins}" if lang == "ar" else f"🛒 *Shop* | 🪙 {coins}"
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=shop_keyboard(lang, user))

    # Buy item
    elif d.startswith("buy_"):
        item_key = d.split("_")[1]
        item = SHOP_ITEMS.get(item_key)
        if item:
            price = item["price"]
            coins = user.get("coins", 0)
            if coins >= price:
                user["coins"] = coins - price
                user.setdefault("inventory", {})[item_key] = user["inventory"].get(item_key, 0) + 1
                save_data(data_store)
                name_item = item["ar"] if lang == "ar" else item["en"]
                msg = f"✅ اشتريت {name_item}!" if lang == "ar" else f"✅ Purchased {name_item}!"
                await query.answer(msg, show_alert=True)
                title = f"🛒 *المتجر* | 🪙 {user['coins']}" if lang == "ar" else f"🛒 *Shop* | 🪙 {user['coins']}"
                await query.edit_message_text(title, parse_mode="Markdown", reply_markup=shop_keyboard(lang, user))
            else:
                msg = "🪙 مفيش كوينز كافية!" if lang == "ar" else "🪙 Not enough coins!"
                await query.answer(msg, show_alert=True)

    # Achievements
    elif d == "achievements":
        earned = user.get("achievements", [])
        lines = []
        for key, ach in ACHIEVEMENTS.items():
            name_a = ach["ar"] if lang == "ar" else ach["en"]
            if key in earned:
                lines.append(f"✅ {name_a}")
            else:
                lines.append(f"🔒 {name_a}")
        title = "🏆 *إنجازاتي*" if lang == "ar" else "🏆 *Achievements*"
        await query.edit_message_text(f"{title}\n\n" + "\n".join(lines), parse_mode="Markdown", reply_markup=main_menu_keyboard(lang, user))

    # Stats
    elif d == "stats":
        profile = build_profile(user, lang)
        title = "📊 *إحصائياتي*" if lang == "ar" else "📊 *My Stats*"
        await query.edit_message_text(f"{title}\n\n{profile}", parse_mode="Markdown", reply_markup=main_menu_keyboard(lang, user))

    # Mission
    elif d == "mission":
        today = datetime.date.today().isoformat()
        mission = user.get("daily_mission")
        mission_date = user.get("mission_date", "")
        if not mission or mission_date != today:
            mission = random.choice(DAILY_MISSIONS)
            user["daily_mission"] = mission
            user["mission_date"] = today
            user["mission_progress"] = 0
            user["mission_done"] = False
            save_data(data_store)
        progress = user.get("mission_progress", 0)
        req = mission["req"]
        done = user.get("mission_done", False)
        m_name = mission["ar"] if lang == "ar" else mission["en"]
        reward = mission["reward"]
        bar_pct = min(int((progress / req) * 10), 10)
        bar = "🟩" * bar_pct + "⬛" * (10 - bar_pct)
        if lang == "ar":
            status = "✅ مكتملة!" if done else f"جارٍ: {progress}/{req}"
            msg = f"📋 *مهمة اليوم*\n\n{m_name}\n\n[{bar}] {status}\n\n🎁 المكافأة: {reward} 🪙"
        else:
            status = "✅ Done!" if done else f"Progress: {progress}/{req}"
            msg = f"📋 *Daily Mission*\n\n{m_name}\n\n[{bar}] {status}\n\n🎁 Reward: {reward} 🪙"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=main_menu_keyboard(lang, user))

    # Leaderboard
    elif d == "leaderboard":
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        all_users = [(v.get("name", "?"), v.get("xp", 0)) for v in data_store.values() if v.get("xp", 0) > 0]
        all_users.sort(key=lambda x: x[1], reverse=True)
        top = all_users[:10]
        if not top:
            board = "مفيش لاعبين بعد 🚀" if lang == "ar" else "No players yet 🚀"
        else:
            lines = [f"{medals[i]} {n} — {x} XP" for i, (n, x) in enumerate(top)]
            board = "\n".join(lines)
        title = "🏅 *أعلى اللاعبين*" if lang == "ar" else "🏅 *Top Players*"
        await query.edit_message_text(f"{title}\n\n{board}", parse_mode="Markdown", reply_markup=main_menu_keyboard(lang, user))

async def send_question(query, context, user, new_msg=False):
    ud = context.user_data
    lang = ud.get("lang", "ar")
    q_list = ud.get("questions", [])
    idx = ud.get("current", 0)
    total = len(q_list)
    q = q_list[idx]
    options = q["options"][:]
    random.shuffle(options)
    ud["current_options"] = options
    ud["hint_used"] = ud.get("hint_used", False)
    xp_per_q = xp_for_level(lang, ud)
    multiplier = 2 if ud.get("double_active") else 1
    score = ud.get("score", 0)
    if lang == "ar":
        header = (
            f"❓ *سؤال {idx+1} من {total}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💫 XP لهذا السؤال: +{xp_per_q * multiplier}\n"
            f"🏆 النقاط الحالية: {score}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"{q['q']}"
        )
    else:
        header = (
            f"❓ *Question {idx+1} of {total}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💫 XP this Q: +{xp_per_q * multiplier}\n"
            f"🏆 Current Score: {score}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"{q['q']}"
        )
    kb = answer_keyboard(options, lang, user, hint_used=ud.get("hint_used", False))
    if new_msg:
        await query.message.reply_text(header, parse_mode="Markdown", reply_markup=kb)
    else:
        await query.edit_message_text(header, parse_mode="Markdown", reply_markup=kb)

async def resend_question_with_hint(query, context, user):
    ud = context.user_data
    lang = ud.get("lang", "ar")
    q_list = ud.get("questions", [])
    idx = ud.get("current", 0)
    q = q_list[idx]
    correct = q["answer"]
    options = ud.get("current_options", q["options"][:])
    wrong = [o for o in options if o != correct]
    random.shuffle(wrong)
    reduced = [correct, wrong[0]] if len(wrong) > 0 else options
    random.shuffle(reduced)
    xp_per_q = xp_for_level(lang, ud)
    total = len(q_list)
    score = ud.get("score", 0)
    if lang == "ar":
        header = (
            f"💡 *تلميح مفعّل!*\n❓ *سؤال {idx+1} من {total}*\n"
            f"🏆 النقاط: {score}\n━━━━━━━━━━━━━━━\n\n{q['q']}"
        )
    else:
        header = (
            f"💡 *Hint Active!*\n❓ *Question {idx+1} of {total}*\n"
            f"🏆 Score: {score}\n━━━━━━━━━━━━━━━\n\n{q['q']}"
        )
    kb = answer_keyboard(reduced, lang, user, hint_used=True)
    await query.edit_message_text(header, parse_mode="Markdown", reply_markup=kb)

async def finalize_game(query, context, data_store, user, uid):
    ud = context.user_data
    lang = ud.get("lang", "ar")
    score = ud.get("score", 0)
    xp_gained = ud.get("xp_gained", 0)
    coins_gained = ud.get("coins_gained", 0)
    total = len(ud.get("questions", [])) * 10
    level = ud.get("level", "easy")
    is_perfect = score == total

    # Update user stats
    user["xp"] = user.get("xp", 0) + xp_gained
    user["coins"] = user.get("coins", 0) + coins_gained
    user["games_played"] = user.get("games_played", 0) + 1
    user["correct_answers"] = user.get("correct_answers", 0) + (score // 10)
    user["total_questions"] = user.get("total_questions", 0) + len(ud.get("questions", []))
    if is_perfect:
        user["perfect_games"] = user.get("perfect_games", 0) + 1
    if level == "hard":
        user["hard_games"] = user.get("hard_games", 0) + 1

    # Update mission
    today = datetime.date.today().isoformat()
    mission = user.get("daily_mission")
    mission_date = user.get("mission_date", "")
    if mission and mission_date == today and not user.get("mission_done", False):
        progress = user.get("mission_progress", 0)
        t = mission.get("type", "")
        if t == "games": progress += 1
        elif t == "correct": progress += (score // 10)
        elif t == "hard" and level == "hard": progress += 1
        elif t == "perfect" and is_perfect: progress += 1
        elif t == "topics":
            topics_played = ud.get("topics_played", set())
            progress = len(topics_played)
        user["mission_progress"] = progress
        if progress >= mission["req"] and not user.get("mission_done", False):
            user["mission_done"] = True
            user["coins"] = user.get("coins", 0) + mission["reward"]

    # Check achievements
    new_ach = check_achievements(user, lang)
    save_data(data_store)

    # Level info
    lvl_num, lvl_name, next_xp = get_level(user["xp"], lang)

    # Score message
    ratio = score / total if total else 0
    if ratio == 1:
        emoji, result = "🌟", ("أنت أسطورة! جولة مثالية!" if lang == "ar" else "PERFECT! You're a legend!")
    elif ratio >= 0.7:
        emoji, result = "👏", ("ممتاز! استمر!" if lang == "ar" else "Great job! Keep going!")
    elif ratio >= 0.4:
        emoji, result = "💪", ("مش بطال! حاول تاني!" if lang == "ar" else "Not bad! Try again!")
    else:
        emoji, result = "😅", ("تحتاج مذاكرة!" if lang == "ar" else "Need more practice!")

    if lang == "ar":
        msg = (
            f"🏁 *نهاية الجولة!*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{emoji} {result}\n\n"
            f"🏆 النقاط: {score}/{total}\n"
            f"⭐ XP مكتسب: +{xp_gained}\n"
            f"🪙 كوينز: +{coins_gained}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 مستواك الحالي: {lvl_name}\n"
            f"💫 إجمالي XP: {user['xp']}"
        )
    else:
        msg = (
            f"🏁 *Game Over!*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{emoji} {result}\n\n"
            f"🏆 Score: {score}/{total}\n"
            f"⭐ XP Earned: +{xp_gained}\n"
            f"🪙 Coins: +{coins_gained}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 Level: {lvl_name}\n"
            f"💫 Total XP: {user['xp']}"
        )

    if new_ach:
        ach_text = "\n".join(new_ach)
        bonus = "🎉 *إنجازات جديدة!*\n" if lang == "ar" else "🎉 *New Achievements!*\n"
        msg += f"\n\n{bonus}{ach_text}"

    if user.get("mission_done") and mission:
        reward = mission["reward"]
        bonus_msg = f"\n\n✅ *مهمة اليوم مكتملة! +{reward} 🪙*" if lang == "ar" else f"\n\n✅ *Daily Mission Complete! +{reward} 🪙*"
        msg += bonus_msg

    await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=end_keyboard(lang))

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ar")
    msg = "اكتب /start للبدء 🎮" if lang == "ar" else "Type /start to begin 🎮"
    await update.message.reply_text(msg)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    print("✅ Trivia Masters V3 - ULTIMATE BOT is running!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
