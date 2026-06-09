#!/usr/bin/env python3
"""
⚽ World Cup 2026 Bot - بوت كأس العالم 2026
Professional Bilingual Arabic/English Telegram Bot
Version 2.0 - Full Edition
"""

import os
import logging
import random
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود! أضفه في Railway Variables")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
#  DATA — GROUPS
# ═══════════════════════════════════════════════════════

GROUPS = {
    "A": {"teams": ["🇲🇽 المكسيك / Mexico", "🇿🇦 جنوب أفريقيا / South Africa", "🇰🇷 كوريا الجنوبية / South Korea", "🇨🇿 التشيك / Czechia"]},
    "B": {"teams": ["🇨🇦 كندا / Canada", "🇧🇦 البوسنة / Bosnia", "🇶🇦 قطر / Qatar", "🇨🇭 سويسرا / Switzerland"]},
    "C": {"teams": ["🇺🇸 أمريكا / USA", "🇵🇾 باراغواي / Paraguay", "🇸🇪 السويد / Sweden", "🇹🇳 تونس / Tunisia"]},
    "D": {"teams": ["🇩🇪 ألمانيا / Germany", "🇨🇼 كوراساو / Curaçao", "🇳🇱 هولندا / Netherlands", "🇯🇵 اليابان / Japan"]},
    "E": {"teams": ["🇪🇸 إسبانيا / Spain", "🇧🇪 بلجيكا / Belgium", "🇸🇦 السعودية / Saudi Arabia", "🇮🇷 إيران / Iran"]},
    "F": {"teams": ["🇫🇷 فرنسا / France", "🇸🇳 السنغال / Senegal", "🇮🇶 العراق / Iraq", "🇳🇴 النرويج / Norway"]},
    "G": {"teams": ["🇧🇷 البرازيل / Brazil", "🇲🇦 المغرب / Morocco", "🇭🇹 هايتي / Haiti", "🇦🇺 أستراليا / Australia"]},
    "H": {"teams": ["🇵🇹 البرتغال / Portugal", "🇨🇴 كولومبيا / Colombia", "🇺🇿 أوزبكستان / Uzbekistan", "🇨🇩 الكونغو / DR Congo"]},
    "I": {"teams": ["🇦🇷 الأرجنتين / Argentina", "🇦🇹 النمسا / Austria", "🇩🇿 الجزائر / Algeria", "🇯🇴 الأردن / Jordan"]},
    "J": {"teams": ["🏴󠁧󠁢󠁥󠁮󠁧󠁿 إنجلترا / England", "🇭🇷 كرواتيا / Croatia", "🇵🇦 بنما / Panama", "🇬🇭 غانا / Ghana"]},
    "K": {"teams": ["🇮🇹 إيطاليا / Italy", "🇪🇨 الإكوادور / Ecuador", "🇨🇮 ساحل العاج / Ivory Coast", "🇹🇷 تركيا / Turkey"]},
    "L": {"teams": ["🇺🇾 أوروغواي / Uruguay", "🇨🇻 الرأس الخضراء / Cape Verde", "🇯🇲 جامايكا / Jamaica", "🇨🇱 تشيلي / Chile"]},
}

# ═══════════════════════════════════════════════════════
#  DATA — MATCHES
# ═══════════════════════════════════════════════════════

MATCHES_BY_DATE = {
    "2026-06-11": [
        {"home": "🇲🇽 Mexico", "away": "🇿🇦 South Africa", "time": "22:00", "group": "A", "stadium": "Estadio Azteca 🏟️", "city": "Mexico City"},
    ],
    "2026-06-12": [
        {"home": "🇨🇦 Canada", "away": "🇧🇦 Bosnia", "time": "20:00", "group": "B", "stadium": "BMO Field 🏟️", "city": "Toronto"},
        {"home": "🇰🇷 South Korea", "away": "🇨🇿 Czechia", "time": "23:00", "group": "A", "stadium": "Estadio Akron 🏟️", "city": "Guadalajara"},
    ],
    "2026-06-13": [
        {"home": "🇺🇸 USA", "away": "🇵🇾 Paraguay", "time": "02:00", "group": "C", "stadium": "SoFi Stadium 🏟️", "city": "Los Angeles"},
        {"home": "🇶🇦 Qatar", "away": "🇨🇭 Switzerland", "time": "20:00", "group": "B", "stadium": "Levi's Stadium 🏟️", "city": "San Francisco"},
        {"home": "🇧🇷 Brazil", "away": "🇲🇦 Morocco", "time": "23:00", "group": "G", "stadium": "SoFi Stadium 🏟️", "city": "Los Angeles"},
    ],
    "2026-06-14": [
        {"home": "🇭🇹 Haiti", "away": "🇦🇺 Australia", "time": "02:00", "group": "G", "stadium": "AT&T Stadium 🏟️", "city": "Dallas"},
        {"home": "🇩🇪 Germany", "away": "🇨🇼 Curaçao", "time": "18:00", "group": "D", "stadium": "Mercedes-Benz Stadium 🏟️", "city": "Atlanta"},
        {"home": "🇳🇱 Netherlands", "away": "🇯🇵 Japan", "time": "21:00", "group": "D", "stadium": "Gillette Stadium 🏟️", "city": "Boston"},
        {"home": "🇸🇦 Saudi Arabia", "away": "🇮🇷 Iran", "time": "23:00", "group": "E", "stadium": "Arrowhead Stadium 🏟️", "city": "Kansas City"},
    ],
    "2026-06-15": [
        {"home": "🇪🇸 Spain", "away": "🇨🇻 Cape Verde", "time": "17:00", "group": "E", "stadium": "Rose Bowl 🏟️", "city": "Los Angeles"},
        {"home": "🇧🇪 Belgium", "away": "🇪🇬 Egypt", "time": "20:00", "group": "E", "stadium": "Hard Rock Stadium 🏟️", "city": "Miami"},
        {"home": "🇩🇿 Algeria", "away": "🇯🇴 Jordan", "time": "23:00", "group": "I", "stadium": "MetLife Stadium 🏟️", "city": "New York"},
    ],
    "2026-06-16": [
        {"home": "🇫🇷 France", "away": "🇸🇳 Senegal", "time": "20:00", "group": "F", "stadium": "SoFi Stadium 🏟️", "city": "Los Angeles"},
        {"home": "🇮🇶 Iraq", "away": "🇳🇴 Norway", "time": "23:00", "group": "F", "stadium": "Lumen Field 🏟️", "city": "Seattle"},
        {"home": "🇦🇷 Argentina", "away": "🇦🇹 Austria", "time": "02:00", "group": "I", "stadium": "MetLife Stadium 🏟️", "city": "New York"},
    ],
    "2026-06-17": [
        {"home": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 England", "away": "🇭🇷 Croatia", "time": "20:00", "group": "J", "stadium": "AT&T Stadium 🏟️", "city": "Dallas"},
        {"home": "🇵🇹 Portugal", "away": "🇨🇴 Colombia", "time": "23:00", "group": "H", "stadium": "Allegiant Stadium 🏟️", "city": "Las Vegas"},
    ],
    "2026-06-18": [
        {"home": "🇮🇹 Italy", "away": "🇪🇨 Ecuador", "time": "20:00", "group": "K", "stadium": "Lincoln Financial Field 🏟️", "city": "Philadelphia"},
        {"home": "🇺🇾 Uruguay", "away": "🇨🇻 Cape Verde", "time": "23:00", "group": "L", "stadium": "NRG Stadium 🏟️", "city": "Houston"},
    ],
}

# ═══════════════════════════════════════════════════════
#  DATA — PREDICTIONS
# ═══════════════════════════════════════════════════════

PREDICTIONS = {
    "🇲🇽 Mexico vs 🇿🇦 South Africa": {
        "ar": (
            "🔮 *تحليل المباراة*\n\n"
            "🏟️ *الملعب:* أزتيكا — الأكثر سحراً في تاريخ كأس العالم\n"
            "📊 *التوقع:* المكسيك 2-0 جنوب أفريقيا\n\n"
            "💪 *نقاط قوة المكسيك:*\n"
            "• الجمهور المنزلي يرفع مستواهم بشكل استثنائي\n"
            "• هجوم سريع ومنظم على الأجنحة\n"
            "• خبرة كبيرة في مباريات الافتتاح\n\n"
            "⚠️ *خطر جنوب أفريقيا:*\n"
            "• دفاع منظم وصعب الاختراق\n"
            "• يلعبون بلا ضغط — أي هدف سيكون مفاجأة\n\n"
            "🎯 *نصيحة المراهنة:* المكسيك تسجل أولاً — احتمال 75%"
        ),
        "en": (
            "🔮 *Match Analysis*\n\n"
            "🏟️ *Venue:* Azteca — the most iconic WC stadium ever\n"
            "📊 *Prediction:* Mexico 2-0 South Africa\n\n"
            "💪 *Mexico strengths:*\n"
            "• Home crowd gives massive boost\n"
            "• Fast, organized wing play\n"
            "• Big opening match experience\n\n"
            "⚠️ *South Africa threat:*\n"
            "• Organized, hard-to-break defense\n"
            "• Nothing to lose mentality\n\n"
            "🎯 *Tip:* Mexico to score first — 75% probability"
        ),
    },
    "🇧🇷 Brazil vs 🇲🇦 Morocco": {
        "ar": (
            "🔮 *تحليل المباراة*\n\n"
            "📊 *التوقع:* البرازيل 2-1 المغرب\n\n"
            "💪 *نقاط قوة البرازيل:*\n"
            "• فينيسيوس جونيور — الأفضل في العالم حالياً\n"
            "• رودريغو وأندريك — جيل ذهبي جديد\n"
            "• إبداع فردي لا مثيل له\n\n"
            "⚠️ *خطر المغرب:*\n"
            "• أسد أطلس 2022 كانت الإحساس الحقيقي!\n"
            "• دفاع مدرب على أعلى مستوى\n"
            "• ملايين من الجمهور العربي يدعمهم\n\n"
            "🎯 *نصيحة:* مباراة مفتوحة — توقع أهدافاً في الشوطين"
        ),
        "en": (
            "🔮 *Match Analysis*\n\n"
            "📊 *Prediction:* Brazil 2-1 Morocco\n\n"
            "💪 *Brazil strengths:*\n"
            "• Vinicius Jr — arguably world's best right now\n"
            "• Rodrygo & Endrick — golden new generation\n"
            "• Unmatched individual brilliance\n\n"
            "⚠️ *Morocco threat:*\n"
            "• 2022 semifinalists — no team to underestimate!\n"
            "• World-class defensive organization\n"
            "• Massive Arab world support\n\n"
            "🎯 *Tip:* Open game — expect goals in both halves"
        ),
    },
    "🇫🇷 France vs 🇸🇳 Senegal": {
        "ar": (
            "🔮 *تحليل المباراة*\n\n"
            "📊 *التوقع:* فرنسا 2-1 السنغال\n\n"
            "💪 *نقاط قوة فرنسا:*\n"
            "• مبابي — الأسرع والأخطر في كرة القدم\n"
            "• جريزمان — عقل المنتخب الفرنسي\n"
            "• عمق هجومي لا نهاية له\n\n"
            "⚠️ *خطر السنغال:*\n"
            "• ساديو مانيه — بطل أفريقيا\n"
            "• روح جماعية استثنائية\n"
            "• انتصر على فرنسا من قبل!\n\n"
            "🎯 *نصيحة:* فرنسا مرشحة للقب — لكن السنغال ستقاوم بشراسة"
        ),
        "en": (
            "🔮 *Match Analysis*\n\n"
            "📊 *Prediction:* France 2-1 Senegal\n\n"
            "💪 *France strengths:*\n"
            "• Mbappe — fastest and most dangerous in football\n"
            "• Griezmann — the brain of Les Bleus\n"
            "• Endless attacking depth\n\n"
            "⚠️ *Senegal threat:*\n"
            "• Sadio Mane — African champion\n"
            "• Exceptional team spirit\n"
            "• Have beaten France before!\n\n"
            "🎯 *Tip:* France are title favorites — but Senegal will fight hard"
        ),
    },
    "🇦🇷 Argentina vs 🇦🇹 Austria": {
        "ar": (
            "🔮 *تحليل المباراة*\n\n"
            "📊 *التوقع:* الأرجنتين 3-0 النمسا\n\n"
            "💪 *نقاط قوة الأرجنتين:*\n"
            "• ليونيل ميسي — آخر رقصة في المونديال؟\n"
            "• ألفاريز ودي باول — ثنائي فتاك\n"
            "• حاملة اللقب وتريد الدفاع عنه بقوة\n\n"
            "⚠️ *ملاحظة على النمسا:*\n"
            "• رانيك بنى فريقاً منظماً ومجتهداً\n"
            "• لكن الفجوة في الموهبة كبيرة جداً\n\n"
            "🎯 *نصيحة:* ميسي يريد التاريخ — توقع عرضاً استثنائياً"
        ),
        "en": (
            "🔮 *Match Analysis*\n\n"
            "📊 *Prediction:* Argentina 3-0 Austria\n\n"
            "💪 *Argentina strengths:*\n"
            "• Lionel Messi — his last World Cup dance?\n"
            "• Alvarez & De Paul — lethal partnership\n"
            "• Defending champions with a point to prove\n\n"
            "⚠️ *Austria note:*\n"
            "• Rangnick built an organized, hardworking side\n"
            "• But the talent gap is simply too large\n\n"
            "🎯 *Tip:* Messi wants history — expect a masterclass"
        ),
    },
    "🇩🇿 Algeria vs 🇯🇴 Jordan": {
        "ar": (
            "🔮 *تحليل المباراة*\n\n"
            "📊 *التوقع:* الجزائر 2-0 الأردن\n\n"
            "💪 *نقاط قوة الجزائر:*\n"
            "• محرز — تجربة استثنائية في أكبر البطولات\n"
            "• مباراة عربية بامتياز — حماس الجمهور هائل\n"
            "• قوة جسدية وسرعة في الانتقال\n\n"
            "⚠️ *خطر الأردن:*\n"
            "• مفاجأة سارة بالتأهل لأول كأس عالم!\n"
            "• روح قتالية لا تُقهر\n"
            "• أي نقطة ستكون إنجازاً تاريخياً\n\n"
            "🎯 *نصيحة:* الجزائر المرشح الأقوى — لكن الأردن سيكافح بشرف"
        ),
        "en": (
            "🔮 *Match Analysis*\n\n"
            "📊 *Prediction:* Algeria 2-0 Jordan\n\n"
            "💪 *Algeria strengths:*\n"
            "• Mahrez — elite experience at the highest level\n"
            "• All-Arab clash generates massive energy\n"
            "• Physical strength and fast transitions\n\n"
            "⚠️ *Jordan threat:*\n"
            "• Historic first-ever World Cup qualification!\n"
            "• Unbreakable fighting spirit\n"
            "• Any point would be a historic achievement\n\n"
            "🎯 *Tip:* Algeria are favorites — Jordan will fight with honor"
        ),
    },
    "🇸🇦 Saudi Arabia vs 🇮🇷 Iran": {
        "ar": (
            "🔮 *تحليل المباراة*\n\n"
            "📊 *التوقع:* السعودية 1-1 إيران\n\n"
            "💪 *نقاط قوة السعودية:*\n"
            "• ذكريات 2022 ضد الأرجنتين لا تُنسى!\n"
            "• الدوري السعودي رفع مستوى اللاعبين\n"
            "• الفهد الأخضر يلعب بثقة عالية\n\n"
            "⚠️ *خطر إيران:*\n"
            "• منتخب منظم ومجتهد دائماً\n"
            "• هذه المباراة لها ثقل سياسي وعاطفي كبير\n"
            "• أزيمون يلهم اللاعبين للأداء فوق مستواهم\n\n"
            "🎯 *نصيحة:* مباراة مشحونة — توقع إيقاعاً عالياً وأهدافاً"
        ),
        "en": (
            "🔮 *Match Analysis*\n\n"
            "📊 *Prediction:* Saudi Arabia 1-1 Iran\n\n"
            "💪 *Saudi Arabia strengths:*\n"
            "• 2022 memories vs Argentina — belief is there!\n"
            "• Saudi Pro League raised player levels\n"
            "• Playing with high confidence\n\n"
            "⚠️ *Iran threat:*\n"
            "• Always organized and hardworking\n"
            "• Heavy political and emotional stakes\n"
            "• Players often over-perform in this fixture\n\n"
            "🎯 *Tip:* Charged atmosphere — expect high intensity and goals"
        ),
    },
}
# ═══════════════════════════════════════════════════════
#  DATA — STATS & RECORDS
# ═══════════════════════════════════════════════════════

STATS_MENU = {
    "titles": {
        "ar": (
            "🏆 *أكثر المنتخبات تتويجاً بكأس العالم*\n\n"
            "🥇 🇧🇷 البرازيل — 5 ألقاب (1958، 1962، 1970، 1994، 2002)\n"
            "🥈 🇩🇪 ألمانيا — 4 ألقاب (1954، 1974، 1990، 2014)\n"
            "🥈 🇮🇹 إيطاليا — 4 ألقاب (1934، 1938، 1982، 2006)\n"
            "🥉 🇦🇷 الأرجنتين — 3 ألقاب (1978، 1986، 2022)\n"
            "4️⃣ 🇫🇷 فرنسا — 2 لقب (1998، 2018)\n"
            "4️⃣ 🇺🇾 أوروغواي — 2 لقب (1930، 1950)\n"
            "4️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 إنجلترا — 1 لقب (1966)\n"
            "4️⃣ 🇪🇸 إسبانيا — 1 لقب (2010)\n\n"
            "🎯 *من سيرفع الكأس في 2026؟*"
        ),
        "en": (
            "🏆 *Most World Cup Titles*\n\n"
            "🥇 🇧🇷 Brazil — 5 titles (1958, 1962, 1970, 1994, 2002)\n"
            "🥈 🇩🇪 Germany — 4 titles (1954, 1974, 1990, 2014)\n"
            "🥈 🇮🇹 Italy — 4 titles (1934, 1938, 1982, 2006)\n"
            "🥉 🇦🇷 Argentina — 3 titles (1978, 1986, 2022)\n"
            "4️⃣ 🇫🇷 France — 2 titles (1998, 2018)\n"
            "4️⃣ 🇺🇾 Uruguay — 2 titles (1930, 1950)\n"
            "4️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England — 1 title (1966)\n"
            "4️⃣ 🇪🇸 Spain — 1 title (2010)\n\n"
            "🎯 *Who lifts the trophy in 2026?*"
        ),
    },
    "scorers": {
        "ar": (
            "⚽ *أكثر اللاعبين تسجيلاً في كأس العالم*\n\n"
            "🥇 🇩🇪 ميروسلاف كلوزه — 16 هدف\n"
            "🥈 🇧🇷 رونالدو نازاريو — 15 هدف\n"
            "🥉 🇩🇪 غيرد مولر — 14 هدف\n"
            "4️⃣ 🇫🇷 جوست فونتين — 13 هدف\n"
            "5️⃣ 🇦🇷 ليونيل ميسي — 13 هدف ⭐\n"
            "6️⃣ 🇧🇷 بيليه — 12 هدف\n"
            "7️⃣ 🇫🇷 كيليان مبابي — 12 هدف 🔥\n\n"
            "🎯 *هل سيتصدر مبابي القائمة في 2026؟*"
        ),
        "en": (
            "⚽ *All-Time World Cup Top Scorers*\n\n"
            "🥇 🇩🇪 Miroslav Klose — 16 goals\n"
            "🥈 🇧🇷 Ronaldo Nazário — 15 goals\n"
            "🥉 🇩🇪 Gerd Müller — 14 goals\n"
            "4️⃣ 🇫🇷 Just Fontaine — 13 goals\n"
            "5️⃣ 🇦🇷 Lionel Messi — 13 goals ⭐\n"
            "6️⃣ 🇧🇷 Pelé — 12 goals\n"
            "7️⃣ 🇫🇷 Kylian Mbappé — 12 goals 🔥\n\n"
            "🎯 *Will Mbappé top the list in 2026?*"
        ),
    },
    "wc2026_facts": {
        "ar": (
            "📊 *إحصائيات كأس العالم 2026*\n\n"
            "🌍 *الدول المضيفة:* أمريكا 🇺🇸 | المكسيك 🇲🇽 | كندا 🇨🇦\n"
            "⚽ *عدد الفرق:* 48 فريق (أكبر نسخة في التاريخ)\n"
            "🎮 *عدد المباريات:* 104 مباراة\n"
            "📅 *المدة:* 39 يوماً (11 يونيو — 19 يوليو)\n"
            "🏟️ *الملاعب:* 16 ملعب في 3 دول\n"
            "👥 *المشجعين المتوقعين:* 5+ مليون\n"
            "💰 *الجائزة الإجمالية:* 1 مليار دولار!\n"
            "📺 *المشاهدين المتوقعين:* 5+ مليار حول العالم\n\n"
            "🌟 *أبرز الملاعب:*\n"
            "🏟️ MetLife Stadium — نيويورك (82,500 مقعد)\n"
            "🏟️ Estadio Azteca — المكسيك (87,000 مقعد)\n"
            "🏟️ Rose Bowl — لوس أنجلوس (90,888 مقعد)"
        ),
        "en": (
            "📊 *World Cup 2026 Key Stats*\n\n"
            "🌍 *Hosts:* USA 🇺🇸 | Mexico 🇲🇽 | Canada 🇨🇦\n"
            "⚽ *Teams:* 48 (biggest ever)\n"
            "🎮 *Matches:* 104 total\n"
            "📅 *Duration:* 39 days (Jun 11 — Jul 19)\n"
            "🏟️ *Stadiums:* 16 across 3 nations\n"
            "👥 *Expected attendance:* 5+ million\n"
            "💰 *Prize money:* $1 Billion!\n"
            "📺 *Global viewers:* 5+ billion\n\n"
            "🌟 *Key Venues:*\n"
            "🏟️ MetLife Stadium — New York (82,500 seats)\n"
            "🏟️ Estadio Azteca — Mexico (87,000 seats)\n"
            "🏟️ Rose Bowl — Los Angeles (90,888 seats)"
        ),
    },
    "arab_teams": {
        "ar": (
            "🌙 *المنتخبات العربية في كأس العالم 2026*\n\n"
            "🇸🇦 *السعودية* — المجموعة E\n"
            "مع: إسبانيا 🇪🇸 | بلجيكا 🇧🇪 | إيران 🇮🇷\n"
            "⭐ أبطال لحظة 2022 ضد الأرجنتين!\n\n"
            "🇲🇦 *المغرب* — المجموعة G\n"
            "مع: البرازيل 🇧🇷 | هايتي 🇭🇹 | أستراليا 🇦🇺\n"
            "⭐ نصف نهائي 2022 — أسود الأطلس يطمحون للأعلى!\n\n"
            "🇩🇿 *الجزائر* — المجموعة I\n"
            "مع: الأرجنتين 🇦🇷 | النمسا 🇦🇹 | الأردن 🇯🇴\n"
            "⭐ مجموعة صعبة — لكن الجزائر قادرة على المفاجأة!\n\n"
            "🇹🇳 *تونس* — المجموعة C\n"
            "مع: أمريكا 🇺🇸 | باراغواي 🇵🇾 | السويد 🇸🇪\n"
            "⭐ النسر القرطاجي يريد التقدم للدور الثاني!\n\n"
            "🇮🇶 *العراق* — المجموعة F\n"
            "مع: فرنسا 🇫🇷 | السنغال 🇸🇳 | النرويج 🇳🇴\n"
            "⭐ عودة تاريخية للمونديال بعد غياب طويل!\n\n"
            "🇯🇴 *الأردن* — المجموعة I\n"
            "مع: الأرجنتين 🇦🇷 | النمسا 🇦🇹 | الجزائر 🇩🇿\n"
            "⭐ أول مشاركة في كأس العالم — إنجاز تاريخي!\n\n"
            "🇶🇦 *قطر* — المجموعة B\n"
            "مع: كندا 🇨🇦 | البوسنة 🇧🇦 | سويسرا 🇨🇭\n"
            "⭐ بطل مونديال 2022 يريد إثبات الذات!"
        ),
        "en": (
            "🌙 *Arab Teams at World Cup 2026*\n\n"
            "🇸🇦 *Saudi Arabia* — Group E\n"
            "vs: Spain 🇪🇸 | Belgium 🇧🇪 | Iran 🇮🇷\n"
            "⭐ Heroes of the 2022 Argentina shock!\n\n"
            "🇲🇦 *Morocco* — Group G\n"
            "vs: Brazil 🇧🇷 | Haiti 🇭🇹 | Australia 🇦🇺\n"
            "⭐ 2022 semifinalists — Atlas Lions aim higher!\n\n"
            "🇩🇿 *Algeria* — Group I\n"
            "vs: Argentina 🇦🇷 | Austria 🇦🇹 | Jordan 🇯🇴\n"
            "⭐ Tough group — but Algeria can surprise!\n\n"
            "🇹🇳 *Tunisia* — Group C\n"
            "vs: USA 🇺🇸 | Paraguay 🇵🇾 | Sweden 🇸🇪\n"
            "⭐ Eagles of Carthage want Round of 32!\n\n"
            "🇮🇶 *Iraq* — Group F\n"
            "vs: France 🇫🇷 | Senegal 🇸🇳 | Norway 🇳🇴\n"
            "⭐ Historic return to the World Cup stage!\n\n"
            "🇯🇴 *Jordan* — Group I\n"
            "vs: Argentina 🇦🇷 | Austria 🇦🇹 | Algeria 🇩🇿\n"
            "⭐ First ever World Cup — a historic achievement!\n\n"
            "🇶🇦 *Qatar* — Group B\n"
            "vs: Canada 🇨🇦 | Bosnia 🇧🇦 | Switzerland 🇨🇭\n"
            "⭐ 2022 hosts want to prove themselves!"
        ),
    },
    "favorites": {
        "ar": (
            "🎯 *المرشحون للقب — تحليل 2026*\n\n"
            "1️⃣ 🇫🇷 *فرنسا* — الأوفر حظاً\n"
            "مبابي في قمته + جيل ذهبي كامل\n"
            "نسبة الفوز: 18%\n\n"
            "2️⃣ 🇧🇷 *البرازيل* — الأبدية\n"
            "فينيسيوس + جيل جديد متهافت + الجوع للقب\n"
            "نسبة الفوز: 15%\n\n"
            "3️⃣ 🇦🇷 *الأرجنتين* — المدافعة\n"
            "ميسي + الكيمياء الفريدة بعد 2022\n"
            "نسبة الفوز: 14%\n\n"
            "4️⃣ 🇩🇪 *ألمانيا* — الآلة\n"
            "جيل جديد + فلسفة كرة جميلة\n"
            "نسبة الفوز: 12%\n\n"
            "5️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 *إنجلترا* — الموعد مع التاريخ؟\n"
            "بيلينغهام + ساكا + فودن — جيل استثنائي\n"
            "نسبة الفوز: 11%\n\n"
            "6️⃣ 🇪🇸 *إسبانيا* — اليافعون الخطرون\n"
            "يامال وبيدري ولامين — مستقبل الكرة\n"
            "نسبة الفوز: 10%"
        ),
        "en": (
            "🎯 *Title Favorites — 2026 Analysis*\n\n"
            "1️⃣ 🇫🇷 *France* — Top Favorites\n"
            "Mbappe at his peak + complete golden generation\n"
            "Win probability: 18%\n\n"
            "2️⃣ 🇧🇷 *Brazil* — The Eternal\n"
            "Vinicius + hungry new generation\n"
            "Win probability: 15%\n\n"
            "3️⃣ 🇦🇷 *Argentina* — The Defenders\n"
            "Messi + unique chemistry after 2022\n"
            "Win probability: 14%\n\n"
            "4️⃣ 🇩🇪 *Germany* — The Machine\n"
            "New generation + beautiful football philosophy\n"
            "Win probability: 12%\n\n"
            "5️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 *England* — Date with destiny?\n"
            "Bellingham + Saka + Foden — exceptional generation\n"
            "Win probability: 11%\n\n"
            "6️⃣ 🇪🇸 *Spain* — Dangerous Youngsters\n"
            "Yamal, Pedri, Lamine — the future of football\n"
            "Win probability: 10%"
        ),
    },
}

# ═══════════════════════════════════════════════════════
#  DATA — FUN FACTS
# ═══════════════════════════════════════════════════════

FUN_FACTS = [
    "⚽ كأس العالم 2026 هو الأكبر في التاريخ: 48 فريق، 104 مباراة، 3 دول مضيفة!\n🌍 The 2026 WC is the biggest ever: 48 teams, 104 matches, 3 host nations!",
    "🏟️ ملعب أزتيكا يستضيف مباريات الافتتاح — الوحيد الذي شهد نهائيَّين (1970 و1986)!\n🏟️ Azteca hosts the opener — the only stadium to stage two finals (1970 & 1986)!",
    "⭐ ميسي (13 هدف) على بُعد 3 أهداف فقط من سجل كلوزه الأبدي (16 هدف)!\n⭐ Messi (13 goals) is just 3 goals away from Klose's all-time record (16 goals)!",
    "🇸🇦 السعودية هزمت الأرجنتين في 2022 في واحدة من أكبر المفاجآت في تاريخ المونديال!\n🇸🇦 Saudi Arabia shocked Argentina in 2022 — one of the biggest upsets in WC history!",
    "🇲🇦 المغرب هو أول منتخب أفريقي وعربي يبلغ نصف نهائي كأس العالم في 2022!\n🇲🇦 Morocco became the first African & Arab team to reach a WC semifinal in 2022!",
    "💰 جائزة كأس العالم 2026 ستتجاوز المليار دولار لأول مرة في التاريخ!\n💰 The 2026 prize fund will exceed $1 billion for the first time in history!",
    "🇯🇴 الأردن يشارك لأول مرة في تاريخه في كأس العالم — إنجاز تاريخي للكرة العربية!\n🇯🇴 Jordan participate in their first-ever World Cup — a historic achievement!",
    "🇮🇶 العراق يعود لكأس العالم بعد غياب طويل — آخر مشاركة كانت عام 1986!\n🇮🇶 Iraq return to the World Cup after a long absence — last appearance was 1986!",
    "📺 كأس العالم 1994 في أمريكا — الأكثر مشاهدةً في التاريخ آنذاك. هل سيكسر 2026 الرقم؟\n📺 1994 WC in USA was the most-watched ever at the time. Will 2026 break the record?",
    "🌡️ المباريات ستُلعب في يونيو-يوليو في أمريكا الشمالية — درجات حرارة مختلفة بين المدن!\n🌡️ Matches in June-July across North America — wildly different temperatures city to city!",
    "🎯 فرنسا آخر منتخب فاز بكأسين متتاليين (1998-2018). هل تحقق الثلاثية؟\n🎯 France last won back-to-back titles (1998-2018). Can they complete the treble?",
    "🔢 بدلاً من 32 فريقاً كما كان سابقاً، تضم النسخة 2026 لأول مرة 48 منتخباً!\n🔢 For the first time ever, 2026 features 48 teams instead of the previous 32!",
]

# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════

user_lang = {}

def get_lang(uid): return user_lang.get(uid, "ar")
def today_str(): return date.today().strftime("%Y-%m-%d")

def main_keyboard(lang="ar"):
    if lang == "ar":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 مباريات اليوم", callback_data="today"),
             InlineKeyboardButton("⚽ مباريات الغد", callback_data="tomorrow")],
            [InlineKeyboardButton("🔮 التوقعات", callback_data="predictions"),
             InlineKeyboardButton("📊 إحصائيات", callback_data="stats")],
            [InlineKeyboardButton("🏆 المجموعات", callback_data="groups"),
             InlineKeyboardButton("🌙 المنتخبات العربية", callback_data="stat_arab_teams")],
            [InlineKeyboardButton("🌟 معلومة مثيرة", callback_data="fact"),
             InlineKeyboardButton("🌐 English", callback_data="lang_en")],
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Today's Matches", callback_data="today"),
             InlineKeyboardButton("⚽ Tomorrow", callback_data="tomorrow")],
            [InlineKeyboardButton("🔮 Predictions", callback_data="predictions"),
             InlineKeyboardButton("📊 Statistics", callback_data="stats")],
            [InlineKeyboardButton("🏆 Groups", callback_data="groups"),
             InlineKeyboardButton("🌙 Arab Teams", callback_data="stat_arab_teams")],
            [InlineKeyboardButton("🌟 Fun Fact", callback_data="fact"),
             InlineKeyboardButton("🌐 عربي", callback_data="lang_ar")],
        ])

def build_matches_text(date_key, lang="ar"):
    matches = MATCHES_BY_DATE.get(date_key, [])
    if not matches:
        return "😴 لا مباريات في هذا اليوم\n😴 No matches scheduled" if lang == "ar" else "😴 No matches scheduled today"
    label = "مباريات" if lang == "ar" else "Matches"
    grp_label = "المجموعة" if lang == "ar" else "Group"
    lines = [f"⚽ *{label} — {date_key}*\n{'─'*25}"]
    for m in matches:
        lines.append(
            f"\n🆚 *{m['home']}  vs  {m['away']}*\n"
            f"🕐 {m['time']} (GMT+1)  |  {grp_label} {m['group']}\n"
            f"🏟️ {m['stadium']}, {m['city']}"
        )
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════
#  HANDLERS
# ═══════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    name = update.effective_user.first_name or "Champion"
    wc_start = date(2026, 6, 11)
    days_left = (wc_start - date.today()).days
    countdown = f"⏳ *{days_left} يوم على الانطلاق!*" if lang == "ar" else f"⏳ *{days_left} days to kickoff!*"

    if lang == "ar":
        text = (
            f"🌍⚽ *أهلاً {name}!*\n\n"
            f"مرحباً في *بوت كأس العالم 2026* الرسمي!\n\n"
            f"🏆 *البطولة:* 11 يونيو — 19 يوليو 2026\n"
            f"🌎 *المضيفون:* أمريكا 🇺🇸 | المكسيك 🇲🇽 | كندا 🇨🇦\n"
            f"⭐ *48 فريق | 104 مباراة | 16 ملعب*\n\n"
            f"{countdown}\n\n"
            f"اختر ما تريد 👇"
        )
    else:
        text = (
            f"🌍⚽ *Welcome {name}!*\n\n"
            f"Your ultimate *World Cup 2026* companion!\n\n"
            f"🏆 *Tournament:* June 11 — July 19, 2026\n"
            f"🌎 *Hosts:* USA 🇺🇸 | Mexico 🇲🇽 | Canada 🇨🇦\n"
            f"⭐ *48 teams | 104 matches | 16 stadiums*\n\n"
            f"{countdown}\n\n"
            f"Choose what you need 👇"
        )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard(lang))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data
    back_main = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية | Main Menu", callback_data="back")]])

    # Language
    if data == "lang_en":
        user_lang[uid] = "en"
        await query.edit_message_text("🌐 *Switched to English!*\nChoose what you need 👇", parse_mode="Markdown", reply_markup=main_keyboard("en"))
        return
    if data == "lang_ar":
        user_lang[uid] = "ar"
        await query.edit_message_text("🌐 *تم التبديل للعربية!*\nاختر ما تريد 👇", parse_mode="Markdown", reply_markup=main_keyboard("ar"))
        return

    lang = get_lang(uid)

    # Today
    if data == "today":
        text = build_matches_text(today_str(), lang)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_main)

    # Tomorrow
    elif data == "tomorrow":
        tmr = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        text = build_matches_text(tmr, lang)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_main)

    # Predictions menu
    elif data == "predictions":
        title = "🔮 *اختر المباراة للتحليل:*" if lang == "ar" else "🔮 *Choose a match to analyze:*"
        pred_buttons = [[InlineKeyboardButton(m, callback_data=f"pred_{m}")] for m in PREDICTIONS]
        pred_buttons.append([InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")])
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(pred_buttons))

    # Single prediction
    elif data.startswith("pred_"):
        match_name = data[5:]
        pred = PREDICTIONS.get(match_name, {})
        text = f"🔮 *{match_name}*\n\n{pred.get(lang, pred.get('ar', '⚠️ غير متاح'))}"
        back = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع | Back", callback_data="predictions")]])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back)

    # Groups
    elif data == "groups":
        title = "🏆 *مجموعات كأس العالم 2026*\n\n" if lang == "ar" else "🏆 *World Cup 2026 Groups*\n\n"
        text = title
        for grp, info in GROUPS.items():
            text += f"*━━ Group {grp} ━━*\n"
            for t in info["teams"]:
                text += f"  • {t}\n"
            text += "\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_main)

    # Stats menu
    elif data == "stats":
        if lang == "ar":
            title = "📊 *اختر نوع الإحصائية:*"
            buttons = [
                [InlineKeyboardButton("🏆 أكثر المنتخبات تتويجاً", callback_data="stat_titles")],
                [InlineKeyboardButton("⚽ أكثر اللاعبين تهديفاً", callback_data="stat_scorers")],
                [InlineKeyboardButton("📈 إحصائيات 2026", callback_data="stat_wc2026_facts")],
                [InlineKeyboardButton("🎯 المرشحون للقب", callback_data="stat_favorites")],
                [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")],
            ]
        else:
            title = "📊 *Choose a stat category:*"
            buttons = [
                [InlineKeyboardButton("🏆 Most Titles", callback_data="stat_titles")],
                [InlineKeyboardButton("⚽ All-Time Top Scorers", callback_data="stat_scorers")],
                [InlineKeyboardButton("📈 2026 Key Stats", callback_data="stat_wc2026_facts")],
                [InlineKeyboardButton("🎯 Title Favorites", callback_data="stat_favorites")],
                [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")],
            ]
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    # Individual stat
    elif data.startswith("stat_"):
        key = data[5:]
        stat = STATS_MENU.get(key, {})
        text = stat.get(lang, stat.get("ar", "⚠️ غير متاح"))
        back = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع | Back", callback_data="stats" if key != "arab_teams" else "back")]])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back)

    # Fun fact
    elif data == "fact":
        fact = random.choice(FUN_FACTS)
        back = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 معلومة أخرى | Another", callback_data="fact")],
            [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")]
        ])
        await query.edit_message_text(
            f"🌟 *هل تعلم؟ | Did You Know?*\n\n{fact}",
            parse_mode="Markdown", reply_markup=back
        )

    # Back to main
    elif data == "back":
        name = query.from_user.first_name or "Champion"
        wc_start = date(2026, 6, 11)
        days_left = (wc_start - date.today()).days
        if lang == "ar":
            text = f"⚽ *القائمة الرئيسية*\n⏳ {days_left} يوم على انطلاق كأس العالم!\n\nاختر ما تريد يا {name} 👇"
        else:
            text = f"⚽ *Main Menu*\n⏳ {days_left} days to World Cup kickoff!\n\nChoose, {name} 👇"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard(lang))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    text = "⚽ استخدم الأزرار للتنقل! أو أرسل /start" if lang == "ar" else "⚽ Use the buttons to navigate! Or send /start"
    await update.message.reply_text(text, reply_markup=main_keyboard(lang))


# ═══════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("⚽ World Cup 2026 Bot v2.0 is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
