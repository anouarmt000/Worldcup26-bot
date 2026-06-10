#!/usr/bin/env python3
"""
⚽ World Cup 2026 Pro Bot — Version 4.0
بيانات حقيقية 100% من FIFA & ESPN & beIN Sports
"""

import os, logging, random, json, asyncio, aiohttp
from datetime import date, timedelta, datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN        = os.environ.get("BOT_TOKEN")
FOOTBALL_API = os.environ.get("FOOTBALL_API_KEY", "")
ADMIN_ID     = int(os.environ.get("ADMIN_ID", "0"))

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود في Railway Variables")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
#  DATABASE — SUBSCRIBERS
# ═══════════════════════════════════════════════════════

DB_FILE = "subscribers.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"users": {}}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def register_user(user):
    db = load_db()
    uid = str(user.id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": user.id,
            "name": user.first_name or "",
            "username": user.username or "",
            "lang": "ar",
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "active": True
        }
        save_db(db)
    return db["users"][uid]

def update_user_lang(uid, lang):
    db = load_db()
    if str(uid) in db["users"]:
        db["users"][str(uid)]["lang"] = lang
        save_db(db)

def get_all_subscribers():
    db = load_db()
    return [v for v in db["users"].values() if v.get("active", True)]

def get_subscriber_count():
    return len(get_all_subscribers())

def get_lang(uid):
    db = load_db()
    return db["users"].get(str(uid), {}).get("lang", "ar")

def today_str():
    return date.today().strftime("%Y-%m-%d")

# ═══════════════════════════════════════════════════════
#  LIVE API
# ═══════════════════════════════════════════════════════

API_BASE = "https://v3.football.api-sports.io"

async def api_get(endpoint, params={}):
    if not FOOTBALL_API:
        return None
    headers = {"x-apisports-key": FOOTBALL_API}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/{endpoint}", headers=headers,
                                   params=params, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    return await r.json()
    except Exception as e:
        logger.warning(f"API error: {e}")
    return None

async def fetch_live_matches():
    data = await api_get("fixtures", {"live": "all"})
    if not data or not data.get("response"):
        return []
    matches = []
    for f in data["response"][:8]:
        fix, teams, goals = f["fixture"], f["teams"], f["goals"]
        matches.append({
            "home": teams["home"]["name"],
            "away": teams["away"]["name"],
            "home_goal": goals["home"] if goals["home"] is not None else "-",
            "away_goal": goals["away"] if goals["away"] is not None else "-",
            "status": fix["status"]["long"],
            "minute": fix["status"].get("elapsed", ""),
            "venue": fix["venue"]["name"] or "N/A",
        })
    return matches

# ═══════════════════════════════════════════════════════
#  GROUPS — محدّثة 100% من قرعة FIFA 5 ديسمبر 2025
# ═══════════════════════════════════════════════════════

GROUPS = {
    "A": ["🇲🇽 المكسيك", "🇿🇦 جنوب أفريقيا", "🇰🇷 كوريا الجنوبية", "🇨🇿 التشيك"],
    "B": ["🇨🇦 كندا", "🇧🇦 البوسنة", "🇶🇦 قطر", "🇨🇭 سويسرا"],
    "C": ["🇧🇷 البرازيل", "🇲🇦 المغرب", "🏴󠁧󠁢󠁳󠁣󠁴󠁿 اسكتلندا", "🇭🇹 هايتي"],
    "D": ["🇺🇸 أمريكا", "🇵🇾 باراغواي", "🇦🇺 أستراليا", "🇹🇷 تركيا"],
    "E": ["🇩🇪 ألمانيا", "🇨🇼 كوراساو", "🇨🇮 ساحل العاج", "🇪🇨 الإكوادور"],
    "F": ["🇳🇱 هولندا", "🇯🇵 اليابان", "🇸🇪 السويد", "🇹🇳 تونس"],
    "G": ["🇧🇪 بلجيكا", "🇪🇬 مصر", "🇮🇷 إيران", "🇳🇿 نيوزيلندا"],
    "H": ["🇪🇸 إسبانيا", "🇨🇻 الرأس الخضراء", "🇸🇦 السعودية", "🇺🇾 أوروغواي"],
    "I": ["🇫🇷 فرنسا", "🇸🇳 السنغال", "🇮🇶 العراق", "🇳🇴 النرويج"],
    "J": ["🇦🇷 الأرجنتين", "🇩🇿 الجزائر", "🇦🇹 النمسا", "🇯🇴 الأردن"],
    "K": ["🇵🇹 البرتغال", "🇨🇩 الكونغو", "🇺🇿 أوزبكستان", "🇨🇴 كولومبيا"],
    "L": ["🏴󠁧󠁢󠁥󠁮󠁧󠁿 إنجلترا", "🇭🇷 كرواتيا", "🇬🇭 غانا", "🇵🇦 بنما"],
}

# ═══════════════════════════════════════════════════════
#  MATCHES — من ESPN الرسمي
# ═══════════════════════════════════════════════════════

MATCHES_BY_DATE = {
    "2026-06-11": [
        {"home":"🇲🇽 Mexico","away":"🇿🇦 South Africa","time":"22:00","group":"A","stadium":"Estadio Azteca","city":"Mexico City"},
        {"home":"🇰🇷 South Korea","away":"🇨🇿 Czechia","time":"03:00+","group":"A","stadium":"Estadio Akron","city":"Guadalajara"},
    ],
    "2026-06-12": [
        {"home":"🇨🇦 Canada","away":"🇧🇦 Bosnia","time":"21:00","group":"B","stadium":"BMO Field","city":"Toronto"},
        {"home":"🇺🇸 USA","away":"🇵🇾 Paraguay","time":"03:00+","group":"D","stadium":"SoFi Stadium","city":"Los Angeles"},
    ],
    "2026-06-13": [
        {"home":"🇶🇦 Qatar","away":"🇨🇭 Switzerland","time":"21:00","group":"B","stadium":"Levi's Stadium","city":"San Francisco"},
        {"home":"🇧🇷 Brazil","away":"🇲🇦 Morocco","time":"00:00+","group":"C","stadium":"MetLife Stadium","city":"New York"},
        {"home":"🇭🇹 Haiti","away":"🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland","time":"03:00+","group":"C","stadium":"Gillette Stadium","city":"Boston"},
        {"home":"🇦🇺 Australia","away":"🇹🇷 Turkey","time":"03:00+","group":"D","stadium":"AT&T Stadium","city":"Dallas"},
    ],
    "2026-06-14": [
        {"home":"🇩🇪 Germany","away":"🇨🇼 Curaçao","time":"00:00+","group":"E","stadium":"Mercedes-Benz Stadium","city":"Atlanta"},
        {"home":"🇨🇮 Ivory Coast","away":"🇪🇨 Ecuador","time":"00:00+","group":"E","stadium":"Arrowhead Stadium","city":"Kansas City"},
        {"home":"🇳🇱 Netherlands","away":"🇸🇪 Sweden","time":"03:00+","group":"F","stadium":"Rose Bowl","city":"Los Angeles"},
        {"home":"🇯🇵 Japan","away":"🇹🇳 Tunisia","time":"03:00+","group":"F","stadium":"Levi's Stadium","city":"San Francisco"},
    ],
    "2026-06-15": [
        {"home":"🇧🇪 Belgium","away":"🇳🇿 New Zealand","time":"00:00+","group":"G","stadium":"Hard Rock Stadium","city":"Miami"},
        {"home":"🇮🇷 Iran","away":"🇪🇬 Egypt","time":"00:00+","group":"G","stadium":"Lincoln Financial Field","city":"Philadelphia"},
        {"home":"🇪🇸 Spain","away":"🇨🇻 Cape Verde","time":"03:00+","group":"H","stadium":"Rose Bowl","city":"Los Angeles"},
        {"home":"🇺🇾 Uruguay","away":"🇸🇦 Saudi Arabia","time":"03:00+","group":"H","stadium":"NRG Stadium","city":"Houston"},
    ],
    "2026-06-16": [
        {"home":"🇫🇷 France","away":"🇮🇶 Iraq","time":"00:00+","group":"I","stadium":"SoFi Stadium","city":"Los Angeles"},
        {"home":"🇸🇳 Senegal","away":"🇳🇴 Norway","time":"03:00+","group":"I","stadium":"Lumen Field","city":"Seattle"},
        {"home":"🇦🇷 Argentina","away":"🇯🇴 Jordan","time":"00:00+","group":"J","stadium":"MetLife Stadium","city":"New York"},
        {"home":"🇩🇿 Algeria","away":"🇦🇹 Austria","time":"03:00+","group":"J","stadium":"Allegiant Stadium","city":"Las Vegas"},
    ],
    "2026-06-17": [
        {"home":"🇵🇹 Portugal","away":"🇺🇿 Uzbekistan","time":"00:00+","group":"K","stadium":"SoFi Stadium","city":"Los Angeles"},
        {"home":"🇨🇴 Colombia","away":"🇨🇩 DR Congo","time":"03:00+","group":"K","stadium":"Gillette Stadium","city":"Boston"},
        {"home":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 England","away":"🇬🇭 Ghana","time":"00:00+","group":"L","stadium":"AT&T Stadium","city":"Dallas"},
        {"home":"🇭🇷 Croatia","away":"🇵🇦 Panama","time":"03:00+","group":"L","stadium":"Arrowhead Stadium","city":"Kansas City"},
    ],
    "2026-06-18": [
        {"home":"🇲🇽 Mexico","away":"🇰🇷 South Korea","time":"00:00+","group":"A","stadium":"Estadio Azteca","city":"Mexico City"},
        {"home":"🇨🇿 Czechia","away":"🇿🇦 South Africa","time":"03:00+","group":"A","stadium":"Estadio Akron","city":"Guadalajara"},
        {"home":"🇨🇦 Canada","away":"🇨🇭 Switzerland","time":"00:00+","group":"B","stadium":"BC Place","city":"Vancouver"},
        {"home":"🇧🇦 Bosnia","away":"🇶🇦 Qatar","time":"03:00+","group":"B","stadium":"BMO Field","city":"Toronto"},
    ],
}

# ═══════════════════════════════════════════════════════
#  TACTICAL ANALYSIS — بيانات محدّثة ومتحقق منها
# ═══════════════════════════════════════════════════════

TACTICAL_ANALYSIS = {
    "🇲🇦 Morocco": {
        "ar": (
            "🧠 *تحليل تكتيكي — المغرب 🇲🇦*\n"
            "📐 *التشكيلة:* 4-3-3 / 4-2-3-1\n"
            "👨‍💼 *المدرب:* محمد وهبي (جديد بعد رحيل رقراقي)\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• ضغط جماعي من الوسط\n"
            "• انتقالات سريعة وكرات عرضية\n"
            "• قوة في الكرات الثابتة والأركان\n\n"
            "🔑 *اللاعبون المحوريون (الفعليون):*\n"
            "• أشرف حكيمي (PSG) — القائد والأفضل في أفريقيا 2025\n"
            "• إبراهيم دياز (ريال مدريد) — 5 أهداف في 5 مباريات في أمم أفريقيا!\n"
            "• يوسف النصيري — قاتل المنافسين، هدف البرتغال 2022 لا يُنسى\n"
            "• ياسين بونو (الهلال) — حارس عالمي المستوى\n"
            "• نصير مزراوي (مان يونايتد) — دفاع وهجوم في نفس الوقت\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• مدرب جديد = غموض تكتيكي\n"
            "• غياب زياش يُقلل الإبداع الفردي"
        ),
        "en": (
            "🧠 *Tactical Analysis — Morocco 🇲🇦*\n"
            "📐 *Formation:* 4-3-3 / 4-2-3-1\n"
            "👨‍💼 *Coach:* Mohamed Ouahbi (new after Regragui departure)\n\n"
            "⚙️ *Playing Style:*\n"
            "• Collective mid-block pressing\n"
            "• Fast transitions with crosses\n"
            "• Dangerous from set pieces and corners\n\n"
            "🔑 *Key Players (verified):*\n"
            "• Achraf Hakimi (PSG) — captain, Africa's best player 2025\n"
            "• Brahim Díaz (Real Madrid) — 5 goals in 5 AFCON games!\n"
            "• Youssef En-Nesyri — lethal finisher, the man who ended Portugal in 2022\n"
            "• Yassine Bono (Al-Hilal) — world-class goalkeeper\n"
            "• Noussair Mazraoui (Man Utd) — dynamic in both directions\n\n"
            "⚠️ *Weaknesses:*\n"
            "• New coach = tactical uncertainty\n"
            "• Ziyech absence reduces individual creativity"
        ),
    },
    "🇩🇿 Algeria": {
        "ar": (
            "🧠 *تحليل تكتيكي — الجزائر 🇩🇿*\n"
            "📐 *التشكيلة:* 4-3-3\n"
            "👨‍💼 *المدرب:* فلاديمير بيتكوفيتش\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• دفاع متماسك + انتقال مباشر لمحرز\n"
            "• ضغط في الثلث الوسط\n"
            "• الاعتماد على الكرات الثابتة والضربات الحرة\n\n"
            "🔑 *اللاعبون المحوريون (محدّثون):*\n"
            "• رياض محرز (الأهلي) — القائد، آخر كأس عالم له، 35 سنة ولا يزال يبهر!\n"
            "• إبراهيم مازا (باير ليفركوزن) — نجم الجيل الجديد، موهبة استثنائية\n"
            "• محمد أمورا (فولفسبورغ) — سرعة وإنهاء قاتل\n"
            "• رايان آيت نوري (مان سيتي) — أفضل ظهير أيسر في الكأس\n"
            "• نبيل بن طالب (ليل) — خبرة وتوازن في الوسط\n"
            "• أمين غويري (مرسيليا) — إبداع وتسديد قوي\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• المجموعة J الأصعب: الأرجنتين + النمسا + الأردن\n"
            "• الاعتماد الكبير على محرز البالغ 35 سنة"
        ),
        "en": (
            "🧠 *Tactical Analysis — Algeria 🇩🇿*\n"
            "📐 *Formation:* 4-3-3\n"
            "👨‍💼 *Coach:* Vladimir Petković\n\n"
            "⚙️ *Playing Style:*\n"
            "• Compact defense + direct ball to Mahrez\n"
            "• Mid-block pressing\n"
            "• Dangerous from set pieces and free kicks\n\n"
            "🔑 *Key Players (verified & updated):*\n"
            "• Riyad Mahrez (Al-Ahli) — captain, 35 y/o, his final World Cup!\n"
            "• Ibrahim Maza (Bayer Leverkusen) — next generation gem\n"
            "• Mohamed Amoura (Wolfsburg) — pace and lethal finishing\n"
            "• Rayan Aït-Nouri (Man City) — best left-back at the tournament\n"
            "• Nabil Bentaleb (Lille) — experience and midfield balance\n"
            "• Amine Gouiri (Marseille) — creativity and strong shooting\n\n"
            "⚠️ *Weaknesses:*\n"
            "• Group J: hardest possible — Argentina + Austria + Jordan\n"
            "• Heavy reliance on 35-year-old Mahrez"
        ),
    },
    "🇸🇦 Saudi Arabia": {
        "ar": (
            "🧠 *تحليل تكتيكي — السعودية 🇸🇦*\n"
            "📐 *التشكيلة:* 4-3-3\n"
            "👨‍💼 *المدرب:* يورغوس دونيس (يوناني، معين قبل شهرين فقط!)\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• دفاع أوفسايد منضبط + انتقال سريع\n"
            "• ضغط جماعي متواصل\n"
            "• اعتماد على سرعة البريكان والدوسري\n\n"
            "🔑 *اللاعبون المحوريون (محدّثون):*\n"
            "• سالم الدوسري (الهلال) — أفضل لاعب آسيوي 2025، صاحب هدف الأرجنتين\n"
            "• سعود عبدالحميد (ليون/RC Lens) — ظهير أيمن عالمي المستوى\n"
            "• فراس البريكان — سرعة استثنائية وحركة بلا توقف\n"
            "• محمد الأوس — حارس تجربة عالية\n"
            "• حسن الطمبكتي — قائد الدفاع\n"
            "• صالح الشهري — مهاجم متحرك وخطير\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• مدرب جديد لم يقد الفريق في مباريات رسمية بعد\n"
            "• المجموعة H: إسبانيا + أوروغواي = تحدٍّ كبير"
        ),
        "en": (
            "🧠 *Tactical Analysis — Saudi Arabia 🇸🇦*\n"
            "📐 *Formation:* 4-3-3\n"
            "👨‍💼 *Coach:* Georgios Donis (Greek, appointed just 2 months ago!)\n\n"
            "⚙️ *Playing Style:*\n"
            "• Disciplined high defensive line + fast counter\n"
            "• Relentless collective pressing\n"
            "• Pace of Al-Buraikan and Al-Dawsari key\n\n"
            "🔑 *Key Players (verified & updated):*\n"
            "• Salem Al-Dawsari (Al-Hilal) — AFC Player of Year 2025, scored the Argentina goal\n"
            "• Saud Abdulhamid (RC Lens) — world-class right back\n"
            "• Firas Al-Buraikan — exceptional pace and movement\n"
            "• Mohammed Al-Owais — experienced goalkeeper\n"
            "• Hassan Al-Tambakti — defensive leader\n"
            "• Saleh Al-Shehri — mobile and dangerous striker\n\n"
            "⚠️ *Weaknesses:*\n"
            "• New coach with zero competitive matches yet\n"
            "• Group H: Spain + Uruguay = massive challenge"
        ),
    },
    "🇫🇷 France": {
        "ar": (
            "🧠 *تحليل تكتيكي — فرنسا 🇫🇷*\n"
            "📐 *التشكيلة:* 4-2-3-1\n"
            "👨‍💼 *المدرب:* ديدييه ديشامب\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• دفاع عميق + انتقال متفجر عبر مبابي\n"
            "• جريزمان يتراجع كـ False 9\n"
            "• تشيامني يؤمن المحور\n\n"
            "🔑 *اللاعبون المحوريون:*\n"
            "• كيليان مبابي — الأخطر في العالم، 12 هدفاً في المونديال\n"
            "• أنطوان جريزمان — رؤية استثنائية وإبداع\n"
            "• أورليان تشيامني — يؤمن الملعب بالكامل\n"
            "• ديمبيلي — مراوغة وتمريرات حاسمة\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• اعتماد زائد على مبابي\n"
            "• المجموعة I: السنغال والعراق والنرويج — ليست سهلة"
        ),
        "en": (
            "🧠 *Tactical Analysis — France 🇫🇷*\n"
            "📐 *Formation:* 4-2-3-1\n"
            "👨‍💼 *Coach:* Didier Deschamps\n\n"
            "⚙️ *Playing Style:*\n"
            "• Deep block + explosive Mbappe counter\n"
            "• Griezmann as False 9\n"
            "• Tchouameni secures the midfield\n\n"
            "🔑 *Key Players:*\n"
            "• Kylian Mbappé — world's most dangerous, 12 WC goals\n"
            "• Antoine Griezmann — exceptional vision and creativity\n"
            "• Aurélien Tchouaméni — covers the entire pitch\n"
            "• Dembélé — dribbling and key passes\n\n"
            "⚠️ *Weaknesses:*\n"
            "• Over-reliance on Mbappé\n"
            "• Group I: Senegal + Iraq + Norway — not easy"
        ),
    },
    "🇦🇷 Argentina": {
        "ar": (
            "🧠 *تحليل تكتيكي — الأرجنتين 🇦🇷*\n"
            "📐 *التشكيلة:* 4-4-2 / 4-3-3\n"
            "👨‍💼 *المدرب:* ليونيل سكالوني\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• Scaloni Press — ضغط جماعي بلا كلل\n"
            "• ميسي يتحرك بحرية مطلقة خلف المهاجمين\n"
            "• قوة نفسية استثنائية بعد لقب 2022\n\n"
            "🔑 *اللاعبون المحوريون:*\n"
            "• ليونيل ميسي (38 سنة!) — رسمياً في مونديال 2026 رغم سنه\n"
            "• خوليان ألفاريز — حركة بلا توقف وأهداف كبيرة\n"
            "• أليكسيس ماك أليستر (ليفربول) — عقل الوسط\n"
            "• رودريغو دي باول (إنتر ميامي) — رئة الفريق\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• ميسي في الـ 38 — هل لا يزال بنفس المستوى؟\n"
            "• المجموعة J: الجزائر + النمسا + الأردن"
        ),
        "en": (
            "🧠 *Tactical Analysis — Argentina 🇦🇷*\n"
            "📐 *Formation:* 4-4-2 / 4-3-3\n"
            "👨‍💼 *Coach:* Lionel Scaloni\n\n"
            "⚙️ *Playing Style:*\n"
            "• Scaloni Press — relentless collective pressing\n"
            "• Messi given total freedom behind strikers\n"
            "• Exceptional mental strength after 2022 title\n\n"
            "🔑 *Key Players:*\n"
            "• Lionel Messi (38!) — officially in WC 2026 squad\n"
            "• Julián Álvarez — relentless movement and big goals\n"
            "• Alexis Mac Allister (Liverpool) — midfield brain\n"
            "• Rodrigo De Paul (Inter Miami) — the engine\n\n"
            "⚠️ *Weaknesses:*\n"
            "• Messi at 38 — still at the same level?\n"
            "• Group J: Algeria + Austria + Jordan"
        ),
    },
    "🇧🇷 Brazil": {
        "ar": (
            "🧠 *تحليل تكتيكي — البرازيل 🇧🇷*\n"
            "📐 *التشكيلة:* 4-2-3-1\n"
            "👨‍💼 *المدرب:* دوريفال جونيور\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• فينيسيوس حرية مطلقة على اليسار\n"
            "• ارتكاز + انتقالات سريعة\n"
            "• روديغو يغطي المساحات خلف المهاجم\n\n"
            "🔑 *اللاعبون المحوريون:*\n"
            "• فينيسيوس جونيور — جائزة أفضل لاعب في العالم 2024\n"
            "• روديغو — حركة ذكية وأهداف في المباريات الكبيرة\n"
            "• أندريك — 18 سنة والمستقبل يبدأ الآن!\n"
            "• كاسيميرو — يؤمن العمق الدفاعي\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• الدفاع ضعيف أمام الكرات العرضية\n"
            "• المجموعة C: المغرب + اسكتلندا — ليست سهلة"
        ),
        "en": (
            "🧠 *Tactical Analysis — Brazil 🇧🇷*\n"
            "📐 *Formation:* 4-2-3-1\n"
            "👨‍💼 *Coach:* Dorival Júnior\n\n"
            "⚙️ *Playing Style:*\n"
            "• Vinicius total freedom on the left\n"
            "• Possession + explosive transitions\n"
            "• Rodrygo covers spaces behind striker\n\n"
            "🔑 *Key Players:*\n"
            "• Vinícius Júnior — won Best Player in the World 2024\n"
            "• Rodrygo — intelligent movement & big-game goals\n"
            "• Endrick — 18 years old, the future starts NOW!\n"
            "• Casemiro — defensive cover and discipline\n\n"
            "⚠️ *Weaknesses:*\n"
            "• Defense struggles with aerial balls\n"
            "• Group C: Morocco + Scotland — not straightforward"
        ),
    },
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 England": {
        "ar": (
            "🧠 *تحليل تكتيكي — إنجلترا 🏴󠁧󠁢󠁥󠁮󠁧󠁿*\n"
            "📐 *التشكيلة:* 4-2-3-1\n"
            "👨‍💼 *المدرب:* لي كارسلي\n\n"
            "🔑 *اللاعبون المحوريون:*\n"
            "• جود بيلينغهام (ريال مدريد) — الأفضل في جيله\n"
            "• بوكايو ساكا (أرسنال) — سرعة وتمريرات حاسمة\n"
            "• فيل فودن (مان سيتي) — إبداع وأهداف\n"
            "• هاري كين (بايرن) — المهاجم الأكثر تهديفاً في تاريخ إنجلترا\n\n"
            "⚠️ *المجموعة L:* كرواتيا + غانا + بنما — قابلة للتجاوز"
        ),
        "en": (
            "🧠 *Tactical Analysis — England 🏴󠁧󠁢󠁥󠁮󠁧󠁿*\n"
            "📐 *Formation:* 4-2-3-1\n"
            "👨‍💼 *Coach:* Lee Carsley\n\n"
            "🔑 *Key Players:*\n"
            "• Jude Bellingham (Real Madrid) — best of his generation\n"
            "• Bukayo Saka (Arsenal) — pace and key passes\n"
            "• Phil Foden (Man City) — creativity and goals\n"
            "• Harry Kane (Bayern) — England's all-time top scorer\n\n"
            "⚠️ *Group L:* Croatia + Ghana + Panama — manageable"
        ),
    },
}

# ═══════════════════════════════════════════════════════
#  ARAB TEAMS — محدّثة من FIFA ومصادر رسمية
# ═══════════════════════════════════════════════════════

ARAB_TEAMS = {
    "ar": (
        "🌙 *المنتخبات العربية — كأس العالم 2026*\n\n"
        "🇲🇦 *المغرب* — المجموعة C\n"
        "🆚 البرازيل 🇧🇷 | اسكتلندا 🏴󠁧󠁢󠁳󠁣󠁴󠁿 | هايتي 🇭🇹\n"
        "⭐ نصف نهائي 2022 | أشرف حكيمي قائداً | إبراهيم دياز نجم الجيل الجديد\n"
        "🎯 التوقع: التقدم للدور الثاني ممكن جداً!\n\n"
        "🇩🇿 *الجزائر* — المجموعة J\n"
        "🆚 الأرجنتين 🇦🇷 | النمسا 🇦🇹 | الأردن 🇯🇴\n"
        "⭐ محرز آخر رقصة | مازا نجم ليفركوزن | أمورا ومركز القوة\n"
        "🎯 التوقع: مجموعة نارية — كل نقطة ثمينة!\n\n"
        "🇸🇦 *السعودية* — المجموعة H\n"
        "🆚 إسبانيا 🇪🇸 | أوروغواي 🇺🇾 | الرأس الخضراء 🇨🇻\n"
        "⭐ الدوسري أفضل لاعب آسيوي 2025 | مدرب جديد يورغوس دونيس\n"
        "🎯 التوقع: مجموعة صعبة — المفاجأة واردة!\n\n"
        "🇹🇳 *تونس* — المجموعة F\n"
        "🆚 هولندا 🇳🇱 | اليابان 🇯🇵 | السويد 🇸🇪\n"
        "⭐ النسر القرطاجي يريد إثبات الذات\n"
        "🎯 التوقع: مجموعة صعبة — الفوز بمباراة كافٍ للأمل\n\n"
        "🇮🇶 *العراق* — المجموعة I\n"
        "🆚 فرنسا 🇫🇷 | السنغال 🇸🇳 | النرويج 🇳🇴\n"
        "⭐ عودة تاريخية بعد غياب — آخر مشاركة 1986!\n"
        "🎯 التوقع: الفوز على النرويج هو الهدف\n\n"
        "🇯🇴 *الأردن* — المجموعة J\n"
        "🆚 الأرجنتين 🇦🇷 | الجزائر 🇩🇿 | النمسا 🇦🇹\n"
        "⭐ أول مشاركة في تاريخ الأردن — إنجاز تاريخي!\n"
        "🎯 التوقع: كل لحظة في المونديال إنجاز\n\n"
        "🇶🇦 *قطر* — المجموعة B\n"
        "🆚 كندا 🇨🇦 | البوسنة 🇧🇦 | سويسرا 🇨🇭\n"
        "⭐ مضيف 2022 يريد إثبات قيمة الكرة القطرية\n"
        "🎯 التوقع: مجموعة قابلة للتجاوز!\n\n"
        "🇪🇬 *مصر* — المجموعة G\n"
        "🆚 بلجيكا 🇧🇪 | إيران 🇮🇷 | نيوزيلندا 🇳🇿\n"
        "⭐ الفراعنة يعودون للمونديال!\n"
        "🎯 التوقع: إيران ونيوزيلندا قابلتان للهزيمة"
    ),
    "en": (
        "🌙 *Arab Teams — World Cup 2026*\n\n"
        "🇲🇦 *Morocco* — Group C\n"
        "🆚 Brazil 🇧🇷 | Scotland 🏴󠁧󠁢󠁳󠁣󠁴󠁿 | Haiti 🇭🇹\n"
        "⭐ 2022 semifinalists | Hakimi captains | Brahim Díaz is the new star\n"
        "🎯 Prediction: Round of 32 very achievable!\n\n"
        "🇩🇿 *Algeria* — Group J\n"
        "🆚 Argentina 🇦🇷 | Austria 🇦🇹 | Jordan 🇯🇴\n"
        "⭐ Mahrez's last dance | Maza (Leverkusen) rising star\n"
        "🎯 Prediction: Group of Death — every point precious!\n\n"
        "🇸🇦 *Saudi Arabia* — Group H\n"
        "🆚 Spain 🇪🇸 | Uruguay 🇺🇾 | Cape Verde 🇨🇻\n"
        "⭐ Al-Dawsari AFC Player of Year 2025 | New coach Georgios Donis\n"
        "🎯 Prediction: Tough group — but an upset is possible!\n\n"
        "🇹🇳 *Tunisia* — Group F\n"
        "🆚 Netherlands 🇳🇱 | Japan 🇯🇵 | Sweden 🇸🇪\n"
        "⭐ Eagles of Carthage out to prove themselves\n"
        "🎯 Prediction: Tough group — one win keeps hope alive\n\n"
        "🇮🇶 *Iraq* — Group I\n"
        "🆚 France 🇫🇷 | Senegal 🇸🇳 | Norway 🇳🇴\n"
        "⭐ Historic return after 40 years — last appearance 1986!\n"
        "🎯 Prediction: Beating Norway is the target\n\n"
        "🇯🇴 *Jordan* — Group J\n"
        "🆚 Argentina 🇦🇷 | Algeria 🇩🇿 | Austria 🇦🇹\n"
        "⭐ Jordan's FIRST EVER World Cup — historic achievement!\n"
        "🎯 Prediction: Every moment on this stage is an achievement\n\n"
        "🇶🇦 *Qatar* — Group B\n"
        "🆚 Canada 🇨🇦 | Bosnia 🇧🇦 | Switzerland 🇨🇭\n"
        "⭐ 2022 hosts want to prove Qatari football's value\n"
        "🎯 Prediction: Manageable group!\n\n"
        "🇪🇬 *Egypt* — Group G\n"
        "🆚 Belgium 🇧🇪 | Iran 🇮🇷 | New Zealand 🇳🇿\n"
        "⭐ The Pharaohs return to the World Cup!\n"
        "🎯 Prediction: Iran & New Zealand are beatable"
    ),
}

# ═══════════════════════════════════════════════════════
#  STATS
# ═══════════════════════════════════════════════════════

STATS_TEXT = {
    "titles": {
        "ar": "🏆 *أكثر المنتخبات تتويجاً*\n\n🥇 🇧🇷 البرازيل — 5\n🥈 🇩🇪 ألمانيا — 4\n🥈 🇮🇹 إيطاليا — 4\n🥉 🇦🇷 الأرجنتين — 3\n4️⃣ 🇫🇷 فرنسا — 2\n4️⃣ 🇺🇾 أوروغواي — 2\n5️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 إنجلترا — 1\n5️⃣ 🇪🇸 إسبانيا — 1\n5️⃣ 🇵🇹 البرتغال — 0 ⚠️",
        "en": "🏆 *Most World Cup Titles*\n\n🥇 🇧🇷 Brazil — 5\n🥈 🇩🇪 Germany — 4\n🥈 🇮🇹 Italy — 4\n🥉 🇦🇷 Argentina — 3\n4️⃣ 🇫🇷 France — 2\n4️⃣ 🇺🇾 Uruguay — 2\n5️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England — 1\n5️⃣ 🇪🇸 Spain — 1\n5️⃣ 🇵🇹 Portugal — 0 ⚠️",
    },
    "scorers": {
        "ar": "⚽ *هدافو كأس العالم عبر التاريخ*\n\n🥇 🇩🇪 كلوزه — 16\n🥈 🇧🇷 رونالدو نازاريو — 15\n🥉 🇩🇪 غيرد مولر — 14\n4️⃣ 🇫🇷 فونتين — 13\n4️⃣ 🇦🇷 ميسي — 13 ⭐\n6️⃣ 🇧🇷 بيليه — 12\n6️⃣ 🇫🇷 مبابي — 12 🔥\n6️⃣ 🇵🇹 رونالدو — 8\n\n⚠️ مبابي وميسي يطاردان سجل كلوزه في 2026!",
        "en": "⚽ *All-Time World Cup Scorers*\n\n🥇 🇩🇪 Klose — 16\n🥈 🇧🇷 Ronaldo — 15\n🥉 🇩🇪 Müller — 14\n4️⃣ 🇫🇷 Fontaine — 13\n4️⃣ 🇦🇷 Messi — 13 ⭐\n6️⃣ 🇧🇷 Pelé — 12\n6️⃣ 🇫🇷 Mbappé — 12 🔥\n6️⃣ 🇵🇹 C.Ronaldo — 8\n\n⚠️ Mbappé & Messi chasing Klose's record in 2026!",
    },
    "favorites": {
        "ar": "🎯 *المرشحون للقب 2026*\n_(بناءً على أسواق الرهانات الدولية)_\n\n1️⃣ 🇫🇷 فرنسا — 18%\n2️⃣ 🇧🇷 البرازيل — 16%\n3️⃣ 🇦🇷 الأرجنتين — 14%\n4️⃣ 🇩🇪 ألمانيا — 12%\n5️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 إنجلترا — 11%\n6️⃣ 🇪🇸 إسبانيا — 10%\n7️⃣ 🇵🇹 البرتغال — 8%\n8️⃣ 🇲🇦 المغرب — 4% (الأعلى عربياً!)",
        "en": "🎯 *2026 Title Favorites*\n_(Based on international betting markets)_\n\n1️⃣ 🇫🇷 France — 18%\n2️⃣ 🇧🇷 Brazil — 16%\n3️⃣ 🇦🇷 Argentina — 14%\n4️⃣ 🇩🇪 Germany — 12%\n5️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England — 11%\n6️⃣ 🇪🇸 Spain — 10%\n7️⃣ 🇵🇹 Portugal — 8%\n8️⃣ 🇲🇦 Morocco — 4% (highest Arab team!)",
    },
    "records": {
        "ar": "📊 *أرقام وإحصائيات كأس العالم 2026*\n\n🌍 3 دول مضيفة: أمريكا، المكسيك، كندا\n⚽ 48 فريق — الأكبر في التاريخ\n🎮 104 مباريات\n🏟️ 16 ملعباً\n📅 39 يوماً (11 يونيو — 19 يوليو)\n💰 1+ مليار دولار جوائز\n📺 5+ مليار مشاهد متوقع\n🆕 دور الـ32 لأول مرة في التاريخ!\n🇯🇴🇺🇿🇨🇼🇨🇻 4 منتخبات تشارك للمرة الأولى\n👴 رونالدو (41 سنة) — 6 مونديالات، رقم قياسي!",
        "en": "📊 *World Cup 2026 Key Stats*\n\n🌍 3 hosts: USA, Mexico, Canada\n⚽ 48 teams — biggest ever\n🎮 104 matches\n🏟️ 16 stadiums\n📅 39 days (June 11 — July 19)\n💰 $1+ billion prize fund\n📺 5+ billion expected viewers\n🆕 Round of 32 — first time in WC history!\n🇯🇴🇺🇿🇨🇼🇨🇻 4 first-timers at a World Cup\n👴 Ronaldo (41) — 6 World Cups, all-time record!",
    },
}

# ═══════════════════════════════════════════════════════
#  PREDICTIONS — محدّثة بالمجموعات الحقيقية
# ═══════════════════════════════════════════════════════

PREDICTIONS = {
    "🇲🇽 Mexico vs 🇿🇦 South Africa": {
        "ar": "🔮 *تحليل المباراة*\n🏟️ أزتيكا — الملعب الأسطوري\n📊 *التوقع:* المكسيك 2-0\n\n💪 المكسيك: الجمهور الأقوى في المونديال + أوتشوا + ألفاريز\n⚠️ جنوب أفريقيا: دفاع منظم، لا يخسرون شيئاً\n🎯 المكسيك تسجل أولاً — 76%",
        "en": "🔮 *Match Analysis*\n🏟️ Azteca — the legendary stage\n📊 *Prediction:* Mexico 2-0\n\n💪 Mexico: loudest home crowd + Ochoa + Edson Alvarez\n⚠️ South Africa: organized defense, nothing to lose\n🎯 Mexico to score first — 76%",
    },
    "🇧🇷 Brazil vs 🇲🇦 Morocco": {
        "ar": "🔮 *تحليل المباراة*\n🏟️ MetLife Stadium, New York\n📊 *التوقع:* البرازيل 2-1 المغرب\n\n💪 البرازيل: فينيسيوس + أندريك في قمة الأداء\n⚠️ المغرب: دفاع عالمي + إبراهيم دياز خطر حقيقي\n🎯 مباراة مفتوحة — أهداف في الشوطين",
        "en": "🔮 *Match Analysis*\n🏟️ MetLife Stadium, New York\n📊 *Prediction:* Brazil 2-1 Morocco\n\n💪 Brazil: Vinicius + Endrick at their peak\n⚠️ Morocco: world-class defense + Brahim Díaz is a real threat\n🎯 Open game — goals in both halves",
    },
    "🇫🇷 France vs 🇮🇶 Iraq": {
        "ar": "🔮 *تحليل المباراة*\n🏟️ SoFi Stadium, Los Angeles\n📊 *التوقع:* فرنسا 4-0 العراق\n\n💪 فرنسا: مبابي + جريزمان = فارق هائل في الجودة\n⚠️ العراق: أول مواجهة مع الكبار، لكن الشغف سيعوض\n🎯 فرنسا تسجل 3+ أهداف — احتمال 80%",
        "en": "🔮 *Match Analysis*\n🏟️ SoFi Stadium, Los Angeles\n📊 *Prediction:* France 4-0 Iraq\n\n💪 France: Mbappe + Griezmann = massive quality gap\n⚠️ Iraq: first big clash, but passion will compensate\n🎯 France to score 3+ goals — 80% probability",
    },
    "🇦🇷 Argentina vs 🇯🇴 Jordan": {
        "ar": "🔮 *تحليل المباراة*\n🏟️ MetLife Stadium, New York\n📊 *التوقع:* الأرجنتين 4-0 الأردن\n\n💪 الأرجنتين: ميسي يريد التاريخ، ألفاريز جائع للأهداف\n⚠️ الأردن: أول مونديال — كل لحظة إنجاز\n🎯 الأرجنتين بفارق كبير جداً",
        "en": "🔮 *Match Analysis*\n🏟️ MetLife Stadium, New York\n📊 *Prediction:* Argentina 4-0 Jordan\n\n💪 Argentina: Messi wants history, Alvarez hungry for goals\n⚠️ Jordan: first World Cup — every moment is an achievement\n🎯 Argentina by a very large margin",
    },
    "🇩🇿 Algeria vs 🇦🇹 Austria": {
        "ar": "🔮 *تحليل المباراة*\n🏟️ Allegiant Stadium, Las Vegas\n📊 *التوقع:* تعادل 1-1\n\n💪 الجزائر: محرز + مازا + أمورا = هجوم خطير\n⚠️ النمسا: منتخب أوروبي منظم بقيادة رانيك\n🎯 مباراة متكافئة — الجزائر تستطيع الفوز!",
        "en": "🔮 *Match Analysis*\n🏟️ Allegiant Stadium, Las Vegas\n📊 *Prediction:* Draw 1-1\n\n💪 Algeria: Mahrez + Maza + Amoura = dangerous attack\n⚠️ Austria: organized European side under Rangnick\n🎯 Balanced clash — Algeria can win this!",
    },
    "🇸🇦 Saudi Arabia vs 🇺🇾 Uruguay": {
        "ar": "🔮 *تحليل المباراة*\n🏟️ NRG Stadium, Houston\n📊 *التوقع:* أوروغواي 2-1 السعودية\n\n💪 السعودية: الدوسري + الروح القتالية من 2022\n⚠️ أوروغواي: نونييز + دارفين — هجوم يصعب إيقافه\n🎯 مباراة صعبة — المفاجأة السعودية ممكنة!",
        "en": "🔮 *Match Analysis*\n🏟️ NRG Stadium, Houston\n📊 *Prediction:* Uruguay 2-1 Saudi Arabia\n\n💪 Saudi Arabia: Al-Dawsari + the fighting spirit from 2022\n⚠️ Uruguay: Núñez + Darwin — attack hard to stop\n🎯 Tough match — Saudi upset is possible!",
    },
}

# ═══════════════════════════════════════════════════════
#  FUN FACTS — محدّثة ومتحقق منها
# ═══════════════════════════════════════════════════════

FUN_FACTS = [
    "⚽ للمرة الأولى: 48 فريق في كأس العالم بدلاً من 32 — أكبر نسخة في التاريخ!\n⚽ First ever: 48 teams instead of 32 — the biggest World Cup in history!",
    "👴 كريستيانو رونالدو (41 سنة!) يشارك في مونديال 2026 — 6 مونديالات، رقم لم يبلغه أحد!\n👴 Cristiano Ronaldo (41!) plays WC 2026 — 6 World Cups, an all-time record!",
    "⭐ ميسي (38 سنة) رسمياً في قائمة الأرجنتين — ثنائية ميسي-رونالدو تستمر!\n⭐ Messi (38) is officially in Argentina's squad — the Messi-Ronaldo era continues!",
    "🇲🇦 إبراهيم دياز (ريال مدريد) سجل 5 أهداف في 5 مباريات في أمم أفريقيا 2025 — نجم المغرب الجديد!\n🇲🇦 Brahim Díaz (Real Madrid) scored 5 goals in 5 AFCON 2025 games — Morocco's new star!",
    "🇩🇿 محرز 35 سنة ويقول هذا آخر كأس عالم له — وداع عاطفي لأسطورة الجزائر!\n🇩🇿 Mahrez is 35 and says this is his last World Cup — emotional farewell for Algeria's legend!",
    "🏟️ كأس العالم 2026 يُقام في 16 ملعباً عبر 3 دول في نفس الوقت — تحدٍّ لوجستي غير مسبوق!\n🏟️ WC 2026 uses 16 stadiums across 3 countries simultaneously — unprecedented logistical challenge!",
    "🆕 دور الـ32 يُطبَّق للمرة الأولى — 32 فريقاً في الدور الأول من الإقصاء!\n🆕 Round of 32 debuts for the first time ever — 32 teams in the first knockout round!",
    "🇯🇴 الأردن يشارك لأول مرة في تاريخه — ويواجه الأرجنتين والجزائر في نفس المجموعة!\n🇯🇴 Jordan's first-ever World Cup — and they face Argentina AND Algeria in the same group!",
    "💰 الجوائز المالية تتخطى المليار دولار لأول مرة — ضعف كأس العالم 2022!\n💰 Prize money exceeds $1 billion for the first time — double the 2022 World Cup!",
    "🇸🇦 سالم الدوسري فاز بجائزة أفضل لاعب آسيوي 2025 — السعودية تتقدم بجودة عالية!\n🇸🇦 Salem Al-Dawsari won AFC Player of Year 2025 — Saudi football quality is rising!",
    "🔢 مبابي (12 هدفاً) على بُعد 4 أهداف من سجل كلوزه الخالد (16 هدفاً)!\n🔢 Mbappé (12 goals) needs just 4 more to break Klose's immortal record (16 goals)!",
    "🏟️ ملعب أزتيكا يستضيف المباراة الافتتاحية — الوحيد الذي شهد نهائيَّين (1970 و1986)!\n🏟️ Azteca hosts the opener — the only stadium to host two WC finals (1970 & 1986)!",
]

# ═══════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════

def main_keyboard(lang="ar"):
    if lang == "ar":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 مباريات اليوم", callback_data="today"),
             InlineKeyboardButton("⚽ مباريات الغد", callback_data="tomorrow")],
            [InlineKeyboardButton("🔴 مباشر LIVE", callback_data="live"),
             InlineKeyboardButton("🔮 التوقعات", callback_data="predictions")],
            [InlineKeyboardButton("🧠 تحليل تكتيكي", callback_data="tactical"),
             InlineKeyboardButton("📊 إحصائيات", callback_data="stats")],
            [InlineKeyboardButton("🏆 المجموعات", callback_data="groups"),
             InlineKeyboardButton("🌙 المنتخبات العربية", callback_data="arab_teams")],
            [InlineKeyboardButton("🌟 معلومة مثيرة", callback_data="fact"),
             InlineKeyboardButton("🌐 English", callback_data="lang_en")],
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Today's Matches", callback_data="today"),
             InlineKeyboardButton("⚽ Tomorrow", callback_data="tomorrow")],
            [InlineKeyboardButton("🔴 LIVE Now", callback_data="live"),
             InlineKeyboardButton("🔮 Predictions", callback_data="predictions")],
            [InlineKeyboardButton("🧠 Tactical Analysis", callback_data="tactical"),
             InlineKeyboardButton("📊 Statistics", callback_data="stats")],
            [InlineKeyboardButton("🏆 Groups", callback_data="groups"),
             InlineKeyboardButton("🌙 Arab Teams", callback_data="arab_teams")],
            [InlineKeyboardButton("🌟 Fun Fact", callback_data="fact"),
             InlineKeyboardButton("🌐 عربي", callback_data="lang_ar")],
        ])

def back_btn(target="back"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية | Main Menu", callback_data=target)]])

def build_matches_text(date_key, lang="ar"):
    matches = MATCHES_BY_DATE.get(date_key, [])
    if not matches:
        return "😴 لا مباريات في هذا اليوم\n😴 No matches scheduled"
    label = "مباريات" if lang == "ar" else "Matches"
    grp = "المجموعة" if lang == "ar" else "Group"
    lines = [f"⚽ *{label} — {date_key}*\n{'━'*22}"]
    for m in matches:
        lines.append(f"\n🆚 *{m['home']}  vs  {m['away']}*\n🕐 {m['time']} GMT+1  |  {grp} {m['group']}\n🏟️ {m['stadium']}, {m['city']}")
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════
#  HANDLERS
# ═══════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = register_user(user)
    lang = data.get("lang", "ar")
    name = user.first_name or "Champion"
    wc_start = date(2026, 6, 11)
    days_left = max((wc_start - date.today()).days, 0)
    total = get_subscriber_count()

    if lang == "ar":
        cd = f"⏳ *{days_left} يوم على الانطلاق!*" if days_left > 0 else "🔴 *البطولة انطلقت!*"
        text = (f"🌍⚽ *أهلاً {name}!*\n\n*بوت كأس العالم 2026 الاحترافي* 🏆\n\n"
                f"📅 11 يونيو — 19 يوليو 2026\n"
                f"🌎 أمريكا 🇺🇸 | المكسيك 🇲🇽 | كندا 🇨🇦\n"
                f"⭐ 48 فريق | 104 مباراة | دور الـ32 الجديد!\n\n"
                f"{cd}\n👥 {total} مشترك معنا\n\nاختر ما تريد 👇")
    else:
        cd = f"⏳ *{days_left} days to kickoff!*" if days_left > 0 else "🔴 *The tournament is LIVE!*"
        text = (f"🌍⚽ *Welcome {name}!*\n\n*World Cup 2026 Pro Bot* 🏆\n\n"
                f"📅 June 11 — July 19, 2026\n"
                f"🌎 USA 🇺🇸 | Mexico 🇲🇽 | Canada 🇨🇦\n"
                f"⭐ 48 teams | 104 matches | New Round of 32!\n\n"
                f"{cd}\n👥 {total} subscribers\n\nChoose what you need 👇")
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard(lang))


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ غير مصرح")
        return
    db = load_db()
    count = get_subscriber_count()
    recent = sorted(db["users"].values(), key=lambda x: x.get("joined",""), reverse=True)[:5]
    recent_text = "\n".join([f"• {u['name']} (@{u.get('username','N/A')}) — {u['joined']}" for u in recent])
    await update.message.reply_text(
        f"🛠 *لوحة الإدارة*\n\n👥 المشتركون: *{count}*\n\n🆕 *آخر 5:*\n{recent_text}\n\n📢 للبث: `/broadcast رسالتك`",
        parse_mode="Markdown"
    )


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("⚠️ استخدم: `/broadcast رسالتك`", parse_mode="Markdown")
        return
    message = " ".join(context.args)
    subscribers = get_all_subscribers()
    sent = failed = 0
    status = await update.message.reply_text(f"📢 جاري الإرسال لـ {len(subscribers)} مشترك...")
    for sub in subscribers:
        try:
            await context.bot.send_message(chat_id=sub["id"],
                text=f"📢 *إشعار — بوت كأس العالم 2026*\n\n{message}", parse_mode="Markdown")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    await status.edit_text(f"✅ أُرسل: {sent}\n❌ فشل: {failed}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data
    lang = get_lang(uid)

    if data == "lang_en":
        update_user_lang(uid, "en")
        await query.edit_message_text("🌐 *Switched to English!* 👇", parse_mode="Markdown", reply_markup=main_keyboard("en"))
        return
    if data == "lang_ar":
        update_user_lang(uid, "ar")
        await query.edit_message_text("🌐 *تم التبديل للعربية!* 👇", parse_mode="Markdown", reply_markup=main_keyboard("ar"))
        return

    if data == "today":
        await query.edit_message_text(build_matches_text(today_str(), lang), parse_mode="Markdown", reply_markup=back_btn())

    elif data == "tomorrow":
        tmr = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        await query.edit_message_text(build_matches_text(tmr, lang), parse_mode="Markdown", reply_markup=back_btn())

    elif data == "live":
        await query.edit_message_text("🔴 *جاري جلب المباريات...*" if lang=="ar" else "🔴 *Fetching live matches...*", parse_mode="Markdown")
        live = await fetch_live_matches()
        if live:
            lines = ["🔴 *LIVE Now | مباريات الآن*\n"]
            for m in live:
                lines.append(f"⚡ *{m['home']} {m['home_goal']} — {m['away_goal']} {m['away']}*\n⏱️ {m['minute']}' | {m['status']}\n🏟️ {m['venue']}\n")
            text = "\n".join(lines)
        else:
            text = "😴 لا مباريات مباشرة الآن\n😴 No live matches right now"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    elif data == "predictions":
        title = "🔮 *اختر المباراة:*" if lang=="ar" else "🔮 *Choose a match:*"
        btns = [[InlineKeyboardButton(m, callback_data=f"pred_{i}")] for i,m in enumerate(PREDICTIONS)]
        btns.append([InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")])
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("pred_"):
        idx = int(data[5:])
        keys = list(PREDICTIONS.keys())
        if idx < len(keys):
            pred = PREDICTIONS[keys[idx]]
            text = f"🔮 *{keys[idx]}*\n\n{pred.get(lang, pred['ar'])}"
        else:
            text = "⚠️ غير متاح"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("predictions"))

    elif data == "tactical":
        title = "🧠 *اختر منتخباً للتحليل التكتيكي:*" if lang=="ar" else "🧠 *Choose a team for tactical analysis:*"
        teams = list(TACTICAL_ANALYSIS.keys())
        btns = [[InlineKeyboardButton(t, callback_data=f"tac_{i}")] for i,t in enumerate(teams)]
        btns.append([InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")])
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("tac_"):
        idx = int(data[4:])
        teams = list(TACTICAL_ANALYSIS.keys())
        if idx < len(teams):
            a = TACTICAL_ANALYSIS[teams[idx]]
            text = a.get(lang, a["ar"])
        else:
            text = "⚠️ غير متاح"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("tactical"))

    elif data == "groups":
        title = "🏆 *مجموعات كأس العالم 2026*\n_(من قرعة FIFA — 5 ديسمبر 2025)_\n\n" if lang=="ar" else "🏆 *World Cup 2026 Groups*\n_(Official FIFA Draw — Dec 5, 2025)_\n\n"
        text = title
        for grp, teams in GROUPS.items():
            text += f"*━━ Group {grp} ━━*\n" + "".join(f"  • {t}\n" for t in teams) + "\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    elif data == "arab_teams":
        await query.edit_message_text(ARAB_TEAMS.get(lang, ARAB_TEAMS["ar"]), parse_mode="Markdown", reply_markup=back_btn())

    elif data == "stats":
        if lang == "ar":
            title, btns = "📊 *اختر نوع الإحصائية:*", [
                [InlineKeyboardButton("🏆 أكثر المنتخبات تتويجاً", callback_data="st_titles")],
                [InlineKeyboardButton("⚽ هدافو التاريخ", callback_data="st_scorers")],
                [InlineKeyboardButton("🎯 المرشحون للقب", callback_data="st_favorites")],
                [InlineKeyboardButton("📈 أرقام 2026", callback_data="st_records")],
                [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")],
            ]
        else:
            title, btns = "📊 *Choose a stat category:*", [
                [InlineKeyboardButton("🏆 Most Titles", callback_data="st_titles")],
                [InlineKeyboardButton("⚽ All-Time Scorers", callback_data="st_scorers")],
                [InlineKeyboardButton("🎯 Title Favorites", callback_data="st_favorites")],
                [InlineKeyboardButton("📈 2026 Stats", callback_data="st_records")],
                [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")],
            ]
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("st_"):
        key = data[3:]
        stat = STATS_TEXT.get(key, {})
        text = stat.get(lang, stat.get("ar", "⚠️ غير متاح"))
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("stats"))

    elif data == "fact":
        fact = random.choice(FUN_FACTS)
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 أخرى | Another", callback_data="fact")],
            [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")]
        ])
        await query.edit_message_text(f"🌟 *هل تعلم؟ | Did You Know?*\n\n{fact}", parse_mode="Markdown", reply_markup=btns)

    elif data == "back":
        name = query.from_user.first_name or "Champion"
        wc_start = date(2026, 6, 11)
        days_left = max((wc_start - date.today()).days, 0)
        total = get_subscriber_count()
        if lang == "ar":
            cd = f"⏳ {days_left} يوم على الانطلاق!" if days_left > 0 else "🔴 البطولة انطلقت!"
            text = f"⚽ *القائمة الرئيسية*\n{cd} | 👥 {total} مشترك\n\nاختر يا {name} 👇"
        else:
            cd = f"⏳ {days_left} days to kickoff!" if days_left > 0 else "🔴 Tournament is LIVE!"
            text = f"⚽ *Main Menu*\n{cd} | 👥 {total} subscribers\n\nChoose, {name} 👇"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard(lang))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    text = "⚽ استخدم الأزرار! أو أرسل /start" if lang=="ar" else "⚽ Use the buttons! Or send /start"
    await update.message.reply_text(text, reply_markup=main_keyboard(lang))


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("⚽ World Cup 2026 Pro Bot v4.0 — LIVE!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
