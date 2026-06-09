#!/usr/bin/env python3
"""
⚽ World Cup 2026 Bot - بوت كأس العالم 2026
Bilingual Arabic/English Telegram Bot
"""

import os
import logging
import random
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Bot Token ─────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("BOT_TOKEN", "8817733030:AAHAIqTCQwJ-qoyN8cdn-LXSl9hBslXCCow")

# ─── World Cup 2026 Data ───────────────────────────────────────────────────────

GROUPS = {
    "A": {"teams": ["🇲🇽 Mexico", "🇿🇦 South Africa", "🇰🇷 South Korea", "🇨🇿 Czechia"]},
    "B": {"teams": ["🇨🇦 Canada", "🇧🇦 Bosnia", "🇶🇦 Qatar", "🇨🇭 Switzerland"]},
    "C": {"teams": ["🇺🇸 USA", "🇵🇾 Paraguay", "🇸🇪 Sweden", "🇹🇳 Tunisia"]},
    "D": {"teams": ["🇩🇪 Germany", "🇨🇼 Curaçao", "🇳🇱 Netherlands", "🇯🇵 Japan"]},
    "E": {"teams": ["🇪🇸 Spain", "🇧🇪 Belgium", "🇸🇦 Saudi Arabia", "🇮🇷 Iran"]},
    "F": {"teams": ["🇫🇷 France", "🇸🇳 Senegal", "🇮🇶 Iraq", "🇳🇴 Norway"]},
    "G": {"teams": ["🇧🇷 Brazil", "🇲🇦 Morocco", "🇭🇹 Haiti", "🇦🇺 Australia"]},
    "H": {"teams": ["🇵🇹 Portugal", "🇨🇴 Colombia", "🇺🇿 Uzbekistan", "🇨🇩 DR Congo"]},
    "I": {"teams": ["🇦🇷 Argentina", "🇦🇹 Austria", "🇩🇿 Algeria", "🇯🇴 Jordan"]},
    "J": {"teams": ["🏴󠁧󠁢󠁥󠁮󠁧󠁿 England", "🇭🇷 Croatia", "🇵🇦 Panama", "🇬🇭 Ghana"]},
    "K": {"teams": ["🇮🇹 Italy", "🇪🇨 Ecuador", "🇨🇮 Ivory Coast", "🇹🇷 Turkey"]},
    "L": {"teams": ["🇺🇾 Uruguay", "🇨🇻 Cape Verde", "🇯🇲 Jamaica", "🇨🇱 Chile"]},
}

# Today's matches (June 11 opener + sample upcoming)
MATCHES_BY_DATE = {
    "2026-06-11": [
        {"home": "🇲🇽 Mexico", "away": "🇿🇦 South Africa", "time": "22:00 GMT+1", "group": "A", "stadium": "Estadio Azteca"},
        {"home": "🇰🇷 South Korea", "away": "🇨🇿 Czechia", "time": "03:00 GMT+1", "group": "A", "stadium": "Estadio Akron"},
    ],
    "2026-06-12": [
        {"home": "🇨🇦 Canada", "away": "🇧🇦 Bosnia", "time": "20:00 GMT+1", "group": "B", "stadium": "BMO Field Toronto"},
        {"home": "🇺🇸 USA", "away": "🇵🇾 Paraguay", "time": "02:00 GMT+1", "group": "B", "stadium": "SoFi Stadium LA"},
    ],
    "2026-06-13": [
        {"home": "🇶🇦 Qatar", "away": "🇨🇭 Switzerland", "time": "20:00 GMT+1", "group": "B", "stadium": "Levi's Stadium SF"},
        {"home": "🇧🇷 Brazil", "away": "🇲🇦 Morocco", "time": "23:00 GMT+1", "group": "G", "stadium": "SoFi Stadium LA"},
        {"home": "🇭🇹 Haiti", "away": "🇦🇺 Australia", "time": "02:00 GMT+1", "group": "G", "stadium": "AT&T Stadium Dallas"},
    ],
    "2026-06-14": [
        {"home": "🇩🇪 Germany", "away": "🇨🇼 Curaçao", "time": "18:00 GMT+1", "group": "D", "stadium": "Mercedes-Benz Atlanta"},
        {"home": "🇳🇱 Netherlands", "away": "🇯🇵 Japan", "time": "21:00 GMT+1", "group": "D", "stadium": "Gillette Stadium Boston"},
        {"home": "🇸🇦 Saudi Arabia", "away": "🇮🇷 Iran", "time": "23:00 GMT+1", "group": "E", "stadium": "Arrowhead Kansas City"},
    ],
    "2026-06-15": [
        {"home": "🇪🇸 Spain", "away": "🇨🇻 Cape Verde", "time": "17:00 GMT+1", "group": "E", "stadium": "Rose Bowl LA"},
        {"home": "🇧🇪 Belgium", "away": "🇪🇬 Egypt", "time": "20:00 GMT+1", "group": "E", "stadium": "Hard Rock Stadium Miami"},
        {"home": "🇩🇿 Algeria", "away": "🇯🇴 Jordan", "time": "23:00 GMT+1", "group": "I", "stadium": "MetLife Stadium NY"},
    ],
    "2026-06-16": [
        {"home": "🇫🇷 France", "away": "🇸🇳 Senegal", "time": "20:00 GMT+1", "group": "F", "stadium": "SoFi Stadium LA"},
        {"home": "🇮🇶 Iraq", "away": "🇳🇴 Norway", "time": "23:00 GMT+1", "group": "F", "stadium": "Lumen Field Seattle"},
        {"home": "🇦🇷 Argentina", "away": "🇦🇹 Austria", "time": "02:00 GMT+1", "group": "I", "stadium": "MetLife Stadium NY"},
    ],
}

PREDICTIONS = {
    "🇲🇽 Mexico vs 🇿🇦 South Africa": {
        "ar": "🏆 المكسيك مرشحة للفوز بشكل واضح في الملعب الأسطوري أزتيكا أمام جماهيرها. كوارتارارو وفينيسيوس يصنعون الفارق.\n\n📊 توقع النتيجة: 2-0 المكسيك\n💡 نصيحة: راقب هجمات الجناح الأيسر للمكسيك",
        "en": "🏆 Mexico are clear favorites at home in the iconic Azteca. Expect an early goal to settle the nerves.\n\n📊 Predicted Score: Mexico 2-0 South Africa\n💡 Tip: Watch Mexico's left-wing attacks"
    },
    "🇧🇷 Brazil vs 🇲🇦 Morocco": {
        "ar": "🏆 البرازيل الأقوى على الورق، لكن المغرب أثبت أنه قادر على المفاجآت في 2022. مباراة مثيرة متوقعة!\n\n📊 توقع النتيجة: 2-1 البرازيل\n💡 نصيحة: مباراة مفتوحة، انتبه للأهداف في الشوط الثاني",
        "en": "🏆 Brazil are favorites but Morocco proved in 2022 they can upset anyone. Expect a tactical battle!\n\n📊 Predicted Score: Brazil 2-1 Morocco\n💡 Tip: Open game, goals likely in 2nd half"
    },
    "🇫🇷 France vs 🇸🇳 Senegal": {
        "ar": "🏆 فرنسا بمباي وجريزمان فريق مرعب، لكن السنغال تعرف كيف تواجه الكبار. مباراة إفريقية أوروبية مثيرة!\n\n📊 توقع النتيجة: 2-1 فرنسا\n💡 نصيحة: مانيه ورفاقه خطر حقيقي على أي دفاع",
        "en": "🏆 France with Mbappe & Griezmann are terrifying, but Senegal know how to fight. Exciting African-European clash!\n\n📊 Predicted Score: France 2-1 Senegal\n💡 Tip: Mane is a genuine threat to any defense"
    },
    "🇦🇷 Argentina vs 🇦🇹 Austria": {
        "ar": "🏆 الأرجنتين حاملة اللقب تبدأ مسيرة دفاعها عن الكأس. ميسي يريد وداعاً أسطورياً في آخر مونديال له!\n\n📊 توقع النتيجة: 3-0 الأرجنتين\n💡 نصيحة: ميسي جائع للتاريخ، توقع أداءً استثنائياً",
        "en": "🏆 Defending champions Argentina begin their title defense. Messi wants a legendary farewell in his last World Cup!\n\n📊 Predicted Score: Argentina 3-0 Austria\n💡 Tip: Messi is hungry for history — expect a masterclass"
    },
}

FUN_FACTS = [
    "⚽ كأس العالم 2026 هو الأكبر في التاريخ: 48 فريق، 104 مباراة، 3 دول مضيفة!\n🌍 The 2026 World Cup is the biggest ever: 48 teams, 104 matches, 3 host nations!",
    "🏟️ الملعب الأسطوري أزتيكا في المكسيك يستضيف المباراة الافتتاحية — وهو الملعب الوحيد الذي استضاف نهائيَّين!\n🏟️ Estadio Azteca hosted two finals (1970 & 1986) — and now opens the 2026 edition!",
    "⭐ ميسي ورونالدو قد يلتقيان في آخر كأس عالم لكليهما — المواجهة التاريخية الأخيرة!\n⭐ Messi & Ronaldo could meet in what may be their final World Cup — the ultimate farewell!",
    "🇸🇦 السعودية في المجموعة E مع إسبانيا وبلجيكا وإيران — مجموعة النار!\n🇸🇦 Saudi Arabia in Group E with Spain, Belgium & Iran — a true Group of Death!",
    "🇩🇿 الجزائر في المجموعة I مع الأرجنتين والنمسا والأردن — تحدٍّ كبير!\n🇩🇿 Algeria in Group I with Argentina, Austria & Jordan — what a challenge!",
    "🏆 البرازيل الأكثر تتويجاً بـ 5 ألقاب، تليها ألمانيا وإيطاليا بـ 4!\n🏆 Brazil leads all-time with 5 titles, followed by Germany & Italy with 4 each!",
    "📺 هذه المرة ستُبث المباريات في أوقات مناسبة للجمهور العربي (مساءً وليلاً)!\n📺 This edition features games at great times for Arab fans — evenings and nights!",
]

# ─── Language Detection ────────────────────────────────────────────────────────
user_lang = {}

def get_lang(user_id):
    return user_lang.get(user_id, "ar")

# ─── Helper ────────────────────────────────────────────────────────────────────
def today_str():
    return date.today().strftime("%Y-%m-%d")

def main_keyboard(lang="ar"):
    if lang == "ar":
        buttons = [
            [InlineKeyboardButton("📅 مباريات اليوم", callback_data="today"),
             InlineKeyboardButton("⚽ مباريات الغد", callback_data="tomorrow")],
            [InlineKeyboardButton("🔮 التوقعات", callback_data="predictions"),
             InlineKeyboardButton("🏆 المجموعات", callback_data="groups")],
            [InlineKeyboardButton("🌟 معلومة مثيرة", callback_data="fact"),
             InlineKeyboardButton("🌐 English", callback_data="lang_en")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton("📅 Today's Matches", callback_data="today"),
             InlineKeyboardButton("⚽ Tomorrow", callback_data="tomorrow")],
            [InlineKeyboardButton("🔮 Predictions", callback_data="predictions"),
             InlineKeyboardButton("🏆 Groups", callback_data="groups")],
            [InlineKeyboardButton("🌟 Fun Fact", callback_data="fact"),
             InlineKeyboardButton("🌐 عربي", callback_data="lang_ar")],
        ]
    return InlineKeyboardMarkup(buttons)

def build_matches_text(date_key, lang="ar"):
    matches = MATCHES_BY_DATE.get(date_key, [])
    if not matches:
        if lang == "ar":
            return "😴 لا مباريات في هذا اليوم"
        return "😴 No matches on this day"

    if lang == "ar":
        lines = [f"⚽ *مباريات {date_key}*\n"]
    else:
        lines = [f"⚽ *Matches on {date_key}*\n"]

    for m in matches:
        lines.append(
            f"🆚 {m['home']} vs {m['away']}\n"
            f"🕐 {m['time']}  |  {'المجموعة' if lang=='ar' else 'Group'} {m['group']}\n"
            f"🏟️ {m['stadium']}\n"
        )
    return "\n".join(lines)

# ─── Handlers ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    name = update.effective_user.first_name or "Champion"

    if lang == "ar":
        text = (
            f"🌍⚽ *أهلاً {name}!*\n\n"
            f"مرحباً في بوت كأس العالم 2026 الثنائي!\n\n"
            f"🏆 البطولة تبدأ *11 يونيو 2026* وتنتهي *19 يوليو*\n"
            f"🌎 الدول المضيفة: أمريكا 🇺🇸 | المكسيك 🇲🇽 | كندا 🇨🇦\n"
            f"⭐ 48 فريق | 104 مباراة | 39 يوم من الإثارة!\n\n"
            f"اختر ما تريد 👇"
        )
    else:
        text = (
            f"🌍⚽ *Welcome {name}!*\n\n"
            f"Your bilingual World Cup 2026 companion is here!\n\n"
            f"🏆 Tournament: *June 11 – July 19, 2026*\n"
            f"🌎 Hosts: USA 🇺🇸 | Mexico 🇲🇽 | Canada 🇨🇦\n"
            f"⭐ 48 teams | 104 matches | 39 days of drama!\n\n"
            f"Choose what you need 👇"
        )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard(lang))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    # Language switch
    if data == "lang_en":
        user_lang[uid] = "en"
        await query.edit_message_text("🌐 Switched to English! Choose an option:", reply_markup=main_keyboard("en"))
        return
    if data == "lang_ar":
        user_lang[uid] = "ar"
        await query.edit_message_text("🌐 تم التبديل للعربية! اختر ما تريد:", reply_markup=main_keyboard("ar"))
        return

    lang = get_lang(uid)

    # Today's matches
    if data == "today":
        text = build_matches_text(today_str(), lang)
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")]])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn)

    # Tomorrow's matches
    elif data == "tomorrow":
        from datetime import timedelta
        tmr = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        text = build_matches_text(tmr, lang)
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")]])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn)

    # Predictions
    elif data == "predictions":
        if lang == "ar":
            text = "🔮 *توقعات المباريات القادمة*\n\nاختر مباراة:\n\n"
        else:
            text = "🔮 *Match Predictions*\n\nChoose a match:\n\n"

        pred_buttons = []
        for match_name in PREDICTIONS.keys():
            pred_buttons.append([InlineKeyboardButton(match_name, callback_data=f"pred_{match_name}")])
        pred_buttons.append([InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(pred_buttons))

    # Individual prediction
    elif data.startswith("pred_"):
        match_name = data[5:]
        pred = PREDICTIONS.get(match_name, {})
        if pred:
            text = f"🔮 *{match_name}*\n\n"
            text += pred.get(lang, pred.get("ar", ""))
        else:
            text = "⚠️ Prediction not available yet"
        back_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع | Back", callback_data="predictions")]
        ])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn)

    # Groups
    elif data == "groups":
        if lang == "ar":
            text = "🏆 *مجموعات كأس العالم 2026*\n\n"
        else:
            text = "🏆 *World Cup 2026 Groups*\n\n"

        for grp, info in GROUPS.items():
            text += f"*المجموعة {grp}* | *Group {grp}*\n"
            for team in info["teams"]:
                text += f"  • {team}\n"
            text += "\n"

        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")]])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn)

    # Fun Fact
    elif data == "fact":
        fact = random.choice(FUN_FACTS)
        back_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 معلومة أخرى | Another Fact", callback_data="fact")],
            [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")]
        ])
        await query.edit_message_text(f"🌟 *Did You Know? هل تعلم؟*\n\n{fact}", parse_mode="Markdown", reply_markup=back_btn)

    # Back to main
    elif data == "back":
        name = query.from_user.first_name or "Champion"
        if lang == "ar":
            text = f"⚽ *القائمة الرئيسية* — اختر ما تريد يا {name}:"
        else:
            text = f"⚽ *Main Menu* — What do you need, {name}?"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard(lang))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    if lang == "ar":
        text = "⚽ استخدم الأزرار للتنقل! أو أرسل /start للبداية من جديد."
    else:
        text = "⚽ Use the buttons to navigate! Or send /start to restart."
    await update.message.reply_text(text, reply_markup=main_keyboard(lang))


# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("⚽ World Cup 2026 Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
