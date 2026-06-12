#!/usr/bin/env python3
"""
⚽ World Cup 2026 Pro Bot — Version 6.1 SMART EDITION
✅ Smart Caching System (كاش ذكي يحمي الـ API)
   - LIVE / مباريات: كاش 3 دقائق
   - Standings / Scorers: كاش 6 ساعات
✅ Auto-Update: النتائج والترتيب والهدافون تلقائياً
✅ نظام مشتركين كامل + بث جماعي + ملخص يومي
✅ بيانات محدّثة 100% من FIFA/ESPN
"""

import os, logging, random, json, asyncio, aiohttp
from datetime import date, timedelta, datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN        = os.environ.get("BOT_TOKEN")
FOOTBALL_API = os.environ.get("FOOTBALL_API_KEY", "")
ADMIN_ID     = int(os.environ.get("ADMIN_ID", "0"))
WC_LEAGUE    = int(os.environ.get("WC_LEAGUE_ID", "1"))
WC_SEASON    = 2026

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود في Railway Variables")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, PreCheckoutQueryHandler, filters
)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
#  SMART CACHE SYSTEM
#  يحمي الـ API من الاستنزاف تلقائياً
# ═══════════════════════════════════════════════════════

class SmartCache:
    def __init__(self):
        self._store = {}

    def set(self, key: str, value, ttl_seconds: int):
        self._store[key] = {
            "value": value,
            "expires": datetime.now().timestamp() + ttl_seconds,
            "ttl": ttl_seconds
        }

    def get(self, key: str):
        entry = self._store.get(key)
        if not entry:
            return None
        if datetime.now().timestamp() > entry["expires"]:
            return None
        return entry["value"]

    def is_expired(self, key: str) -> bool:
        return self.get(key) is None

    def time_left(self, key: str) -> int:
        entry = self._store.get(key)
        if not entry:
            return 0
        left = int(entry["expires"] - datetime.now().timestamp())
        return max(0, left)

    def force_expire(self, key: str):
        if key in self._store:
            self._store[key]["expires"] = 0

CACHE = SmartCache()

# TTL constants
TTL_LIVE       = 3   * 60        # 3 دقائق للمباريات الحية
TTL_RESULTS    = 5   * 60        # 5 دقائق للنتائج
TTL_FIXTURES   = 30  * 60        # 30 دقيقة للجدول

# ═══════════════════════════════════════════════════════
#  API CALL COUNTER (لمراقبة استهلاك الـ API)
# ═══════════════════════════════════════════════════════

def today_str():
    return date.today().strftime("%Y-%m-%d")

api_calls_today = {"date": today_str(), "count": 0}

def track_api_call():
    global api_calls_today
    today = today_str()
    if api_calls_today["date"] != today:
        api_calls_today = {"date": today, "count": 0}
    api_calls_today["count"] += 1
    logger.info(f"📡 API Call #{api_calls_today['count']} today")
    if api_calls_today["count"] >= 90:
        logger.warning(f"⚠️ API calls approaching daily limit: {api_calls_today['count']}/100")

# ═══════════════════════════════════════════════════════
#  DATABASE — SUBSCRIBERS
# ═══════════════════════════════════════════════════════

# ── Railway Volume: البيانات تُحفظ هنا بشكل دائم بين كل deploy ──
VOLUME_DIR = "/app/data"
os.makedirs(VOLUME_DIR, exist_ok=True)
DB_FILE = os.path.join(VOLUME_DIR, "subscribers.json")

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}}

def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"❌ Failed to save DB: {e}")

def register_user(user):
    db = load_db()
    uid = str(user.id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": user.id, "name": user.first_name or "",
            "username": user.username or "", "lang": "ar",
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M"), "active": True
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

# ═══════════════════════════════════════════════════════
#  API LAYER — كل دالة تمر عبر الكاش أولاً
# ═══════════════════════════════════════════════════════

API_BASE = "https://v3.football.api-sports.io"

async def _raw_api_get(endpoint: str, params: dict) -> dict | None:
    if not FOOTBALL_API:
        return None
    track_api_call()
    headers = {"x-apisports-key": FOOTBALL_API}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/{endpoint}", headers=headers,
                params=params, timeout=aiohttp.ClientTimeout(total=10)
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    remaining = r.headers.get("x-ratelimit-requests-remaining", "?")
                    logger.info(f"✅ API OK — {endpoint} | Remaining today: {remaining}")
                    return data
                else:
                    logger.warning(f"⚠️ API {r.status} — {endpoint}")
    except Exception as e:
        logger.error(f"❌ API Exception — {endpoint}: {e}")
    return None

# ── Live Matches (كاش 3 دقائق) ──────────────────────────
async def get_live_matches() -> list:
    cached = CACHE.get("live_matches")
    if cached is not None:
        logger.info(f"💾 Cache HIT: live_matches (expires in {CACHE.time_left('live_matches')}s)")
        return cached

    logger.info("🔄 Cache MISS: fetching live_matches from API")
    data = await _raw_api_get("fixtures", {"live": "all"})
    matches = []
    if data and data.get("response"):
        for f in data["response"][:10]:
            fix, teams, goals = f["fixture"], f["teams"], f["goals"]
            matches.append({
                "home": teams["home"]["name"], "away": teams["away"]["name"],
                "home_goal": goals["home"] if goals["home"] is not None else "-",
                "away_goal": goals["away"] if goals["away"] is not None else "-",
                "status": fix["status"]["long"],
                "minute": fix["status"].get("elapsed", ""),
                "venue": fix["venue"]["name"] or "N/A",
                "league": f.get("league", {}).get("name", ""),
            })

    CACHE.set("live_matches", matches, TTL_LIVE)
    return matches

# ── Today's Fixtures (كاش 30 دقيقة) ─────────────────────
async def get_today_fixtures() -> list:
    cached = CACHE.get("today_fixtures")
    if cached is not None:
        logger.info(f"💾 Cache HIT: today_fixtures")
        return cached

    logger.info("🔄 Cache MISS: fetching today_fixtures from API")
    today = today_str()
    data = await _raw_api_get("fixtures", {
        "league": WC_LEAGUE, "season": WC_SEASON, "date": today
    })
    fixtures = []
    if data and data.get("response"):
        for f in data["response"]:
            fix = f["fixture"]
            teams = f["teams"]
            goals = f["goals"]
            grp = f.get("league", {}).get("round", "")
            fixtures.append({
                "home": teams["home"]["name"],
                "away": teams["away"]["name"],
                "time": datetime.utcfromtimestamp(fix["timestamp"]).strftime("%H:%M") if fix.get("timestamp") else "TBD",
                "group": grp,
                "stadium": fix.get("venue", {}).get("name", "N/A"),
                "city": fix.get("venue", {}).get("city", ""),
                "status": fix["status"]["short"],
                "home_goal": goals["home"],
                "away_goal": goals["away"],
            })

    CACHE.set("today_fixtures", fixtures, TTL_FIXTURES)
    return fixtures

# ── Recent Results (كاش 5 دقائق) ─────────────────────────
async def get_recent_results() -> list:
    cached = CACHE.get("recent_results")
    if cached is not None:
        logger.info(f"💾 Cache HIT: recent_results")
        return cached

    logger.info("🔄 Cache MISS: fetching recent_results from API")
    data = await _raw_api_get("fixtures", {
        "league": WC_LEAGUE, "season": WC_SEASON,
        "status": "FT-AET-PEN", "last": 20
    })
    results = []
    if data and data.get("response"):
        for f in data["response"]:
            fix = f["fixture"]
            teams = f["teams"]
            goals = f["goals"]
            match_date = fix.get("date", "")[:10]
            grp = f.get("league", {}).get("round", "")
            results.append({
                "date": match_date,
                "home": teams["home"]["name"],
                "away": teams["away"]["name"],
                "home_goal": goals["home"] or 0,
                "away_goal": goals["away"] or 0,
                "group": grp,
                "winner": teams["home"]["winner"],
            })

    results.sort(key=lambda x: x["date"], reverse=True)
    CACHE.set("recent_results", results, TTL_RESULTS)
    return results

# ═══════════════════════════════════════════════════════
#  STATIC DATA
# ═══════════════════════════════════════════════════════

GROUPS_STATIC = {
    "A": ["🇲🇽 Mexico", "🇿🇦 South Africa", "🇰🇷 South Korea", "🇨🇿 Czechia"],
    "B": ["🇨🇦 Canada", "🇧🇦 Bosnia", "🇶🇦 Qatar", "🇨🇭 Switzerland"],
    "C": ["🇧🇷 Brazil", "🇲🇦 Morocco", "🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland", "🇭🇹 Haiti"],
    "D": ["🇺🇸 USA", "🇵🇾 Paraguay", "🇦🇺 Australia", "🇹🇷 Turkey"],
    "E": ["🇩🇪 Germany", "🇨🇼 Curaçao", "🇨🇮 Ivory Coast", "🇪🇨 Ecuador"],
    "F": ["🇳🇱 Netherlands", "🇯🇵 Japan", "🇸🇪 Sweden", "🇹🇳 Tunisia"],
    "G": ["🇧🇪 Belgium", "🇪🇬 Egypt", "🇮🇷 Iran", "🇳🇿 New Zealand"],
    "H": ["🇪🇸 Spain", "🇨🇻 Cape Verde", "🇸🇦 Saudi Arabia", "🇺🇾 Uruguay"],
    "I": ["🇫🇷 France", "🇸🇳 Senegal", "🇮🇶 Iraq", "🇳🇴 Norway"],
    "J": ["🇦🇷 Argentina", "🇩🇿 Algeria", "🇦🇹 Austria", "🇯🇴 Jordan"],
    "K": ["🇵🇹 Portugal", "🇨🇩 DR Congo", "🇺🇿 Uzbekistan", "🇨🇴 Colombia"],
    "L": ["🏴󠁧󠁢󠁥󠁮󠁧󠁿 England", "🇭🇷 Croatia", "🇬🇭 Ghana", "🇵🇦 Panama"],
}

MATCHES_BY_DATE = {
    # ── المرحلة الأولى ──────────────────────────────────────
    "2026-06-11": [
        {"home":"🇲🇽 Mexico","away":"🇿🇦 South Africa","time":"19:00","group":"A","stadium":"Mexico City Stadium","city":"Mexico City"},
        {"home":"🇰🇷 South Korea","away":"🇨🇿 Czechia","time":"02:00+","group":"A","stadium":"Estadio Guadalajara","city":"Zapopan"},
    ],
    "2026-06-12": [
        {"home":"🇨🇦 Canada","away":"🇧🇦 Bosnia","time":"19:00","group":"B","stadium":"Toronto Stadium","city":"Toronto"},
        {"home":"🇺🇸 USA","away":"🇵🇾 Paraguay","time":"01:00+","group":"D","stadium":"Los Angeles Stadium","city":"Los Angeles"},
    ],
    "2026-06-13": [
        {"home":"🇶🇦 Qatar","away":"🇨🇭 Switzerland","time":"19:00","group":"B","stadium":"San Francisco Stadium","city":"San Francisco"},
        {"home":"🇧🇷 Brazil","away":"🇲🇦 Morocco","time":"22:00","group":"C","stadium":"New York NJ Stadium","city":"New Jersey"},
        {"home":"🇭🇹 Haiti","away":"🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland","time":"01:00+","group":"C","stadium":"Boston Stadium","city":"Boston"},
        {"home":"🇦🇺 Australia","away":"🇹🇷 Turkey","time":"04:00+","group":"D","stadium":"BC Place","city":"Vancouver"},
    ],
    "2026-06-14": [
        {"home":"🇩🇪 Germany","away":"🇨🇼 Curaçao","time":"17:00","group":"E","stadium":"Houston Stadium","city":"Houston"},
        {"home":"🇳🇱 Netherlands","away":"🇯🇵 Japan","time":"20:00","group":"F","stadium":"Dallas Stadium","city":"Dallas"},
        {"home":"🇨🇮 Ivory Coast","away":"🇪🇨 Ecuador","time":"23:00","group":"E","stadium":"Philadelphia Stadium","city":"Philadelphia"},
        {"home":"🇸🇪 Sweden","away":"🇹🇳 Tunisia","time":"02:00+","group":"F","stadium":"Estadio Monterrey","city":"Guadalupe"},
    ],
    "2026-06-15": [
        {"home":"🇪🇸 Spain","away":"🇨🇻 Cape Verde","time":"16:00","group":"H","stadium":"Atlanta Stadium","city":"Atlanta"},
        {"home":"🇧🇪 Belgium","away":"🇪🇬 Egypt","time":"19:00","group":"G","stadium":"BC Place","city":"Vancouver"},
        {"home":"🇸🇦 Saudi Arabia","away":"🇺🇾 Uruguay","time":"22:00","group":"H","stadium":"Miami Stadium","city":"Miami"},
        {"home":"🇮🇷 Iran","away":"🇳🇿 New Zealand","time":"01:00+","group":"G","stadium":"Los Angeles Stadium","city":"Los Angeles"},
    ],
    "2026-06-16": [
        {"home":"🇫🇷 France","away":"🇸🇳 Senegal","time":"19:00","group":"I","stadium":"New York NJ Stadium","city":"New Jersey"},
        {"home":"🇮🇶 Iraq","away":"🇳🇴 Norway","time":"22:00","group":"I","stadium":"Boston Stadium","city":"Boston"},
        {"home":"🇦🇷 Argentina","away":"🇩🇿 Algeria","time":"01:00+","group":"J","stadium":"Kansas City Stadium","city":"Kansas City"},
        {"home":"🇦🇹 Austria","away":"🇯🇴 Jordan","time":"04:00+","group":"J","stadium":"San Francisco Stadium","city":"San Francisco"},
    ],
    "2026-06-17": [
        {"home":"🇵🇹 Portugal","away":"🇨🇩 DR Congo","time":"17:00","group":"K","stadium":"Houston Stadium","city":"Houston"},
        {"home":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 England","away":"🇭🇷 Croatia","time":"20:00","group":"L","stadium":"Dallas Stadium","city":"Dallas"},
        {"home":"🇬🇭 Ghana","away":"🇵🇦 Panama","time":"23:00","group":"L","stadium":"Toronto Stadium","city":"Toronto"},
        {"home":"🇺🇿 Uzbekistan","away":"🇨🇴 Colombia","time":"02:00+","group":"K","stadium":"Mexico City Stadium","city":"Mexico City"},
    ],
    "2026-06-18": [
        {"home":"🇨🇿 Czechia","away":"🇿🇦 South Africa","time":"16:00","group":"A","stadium":"Atlanta Stadium","city":"Atlanta"},
        {"home":"🇨🇭 Switzerland","away":"🇧🇦 Bosnia","time":"19:00","group":"B","stadium":"Los Angeles Stadium","city":"Los Angeles"},
        {"home":"🇨🇦 Canada","away":"🇶🇦 Qatar","time":"22:00","group":"B","stadium":"BC Place","city":"Vancouver"},
        {"home":"🇲🇽 Mexico","away":"🇰🇷 South Korea","time":"01:00+","group":"A","stadium":"Estadio Guadalajara","city":"Zapopan"},
    ],
    "2026-06-19": [
        {"home":"🇺🇸 USA","away":"🇦🇺 Australia","time":"19:00","group":"D","stadium":"Seattle Stadium","city":"Seattle"},
        {"home":"🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland","away":"🇲🇦 Morocco","time":"22:00","group":"C","stadium":"Boston Stadium","city":"Boston"},
        {"home":"🇧🇷 Brazil","away":"🇭🇹 Haiti","time":"00:30+","group":"C","stadium":"Philadelphia Stadium","city":"Philadelphia"},
        {"home":"🇵🇾 Paraguay","away":"🇹🇷 Turkey","time":"03:00+","group":"D","stadium":"Houston Stadium","city":"Houston"},
    ],
    "2026-06-20": [
        {"home":"🇩🇪 Germany","away":"🇨🇮 Ivory Coast","time":"19:00","group":"E","stadium":"Kansas City Stadium","city":"Kansas City"},
        {"home":"🇪🇨 Ecuador","away":"🇨🇼 Curaçao","time":"22:00","group":"E","stadium":"Miami Stadium","city":"Miami"},
        {"home":"🇯🇵 Japan","away":"🇸🇪 Sweden","time":"02:00+","group":"F","stadium":"Seattle Stadium","city":"Seattle"},
        {"home":"🇹🇳 Tunisia","away":"🇳🇱 Netherlands","time":"02:00+","group":"F","stadium":"Vancouver Stadium","city":"Vancouver"},
    ],
}

TACTICAL_ANALYSIS = {
    "🇲🇦 Morocco": {
        "ar": "🧠 *المغرب 🇲🇦*\n📐 4-3-3 | 👨‍💼 محمد وهبي\n\n🔑 *النجوم:*\n• أشرف حكيمي (PSG) — القائد، أفضل لاعب أفريقي 2025\n• إبراهيم دياز (ريال مدريد) — 5 أهداف في 5 مباريات AFCON!\n• يوسف النصيري — قاتل مرمى البرتغال 2022\n• ياسين بونو (الهلال) — حارس عالمي\n\n⚙️ ضغط جماعي + انتقالات سريعة + قوة في الكرات الثابتة\n⚠️ مدرب جديد = غموض تكتيكي",
        "en": "🧠 *Morocco 🇲🇦*\n📐 4-3-3 | 👨‍💼 Mohamed Ouahbi\n\n🔑 *Stars:*\n• Achraf Hakimi (PSG) — captain, Africa best 2025\n• Brahim Díaz (Real Madrid) — 5 goals in 5 AFCON games!\n• Youssef En-Nesyri — ended Portugal 2022\n• Yassine Bono (Al-Hilal) — world-class goalkeeper\n\n⚙️ Collective press + fast transitions + set-piece danger\n⚠️ New coach = tactical uncertainty",
    },
    "🇩🇿 Algeria": {
        "ar": "🧠 *الجزائر 🇩🇿*\n📐 4-3-3 | 👨‍💼 بيتكوفيتش\n\n🔑 *النجوم:*\n• رياض محرز (الأهلي) — 35 سنة، آخر كأس عالم!\n• إبراهيم مازا (ليفركوزن) — نجم الجيل الجديد\n• محمد أمورا (فولفسبورغ) — سرعة وإنهاء\n• رايان آيت نوري (مان سيتي) — أفضل ظهير أيسر\n\n⚙️ دفاع متماسك + انتقال مباشر لمحرز\n⚠️ المجموعة J: الأرجنتين + النمسا!",
        "en": "🧠 *Algeria 🇩🇿*\n📐 4-3-3 | 👨‍💼 Petković\n\n🔑 *Stars:*\n• Riyad Mahrez (Al-Ahli) — 35, FINAL World Cup!\n• Ibrahim Maza (Leverkusen) — next-gen gem\n• Mohamed Amoura (Wolfsburg) — pace & finishing\n• Rayan Aït-Nouri (Man City) — best left back\n\n⚙️ Compact defense + direct ball to Mahrez\n⚠️ Group J: Argentina + Austria!",
    },
    "🇸🇦 Saudi Arabia": {
        "ar": "🧠 *السعودية 🇸🇦*\n📐 4-3-3 | 👨‍💼 يورغوس دونيس\n\n🔑 *النجوم:*\n• سالم الدوسري — أفضل آسيوي 2025، هدف الأرجنتين!\n• سعود عبدالحميد (RC Lens) — ظهير أيمن عالمي\n• فراس البريكان — سرعة استثنائية\n• محمد الأوس — حارس ذو تجربة\n\n⚙️ أوفسايد منضبط + انتقال سريع\n⚠️ مدرب جديد + إسبانيا وأوروغواي!",
        "en": "🧠 *Saudi Arabia 🇸🇦*\n📐 4-3-3 | 👨‍💼 Georgios Donis\n\n🔑 *Stars:*\n• Salem Al-Dawsari — AFC Player of Year 2025!\n• Saud Abdulhamid (RC Lens) — world-class right back\n• Firas Al-Buraikan — exceptional pace\n• Mohammed Al-Owais — experienced goalkeeper\n\n⚙️ Disciplined offside trap + fast counter\n⚠️ New coach + Spain and Uruguay in group!",
    },
    "🇫🇷 France": {
        "ar": "🧠 *فرنسا 🇫🇷*\n📐 4-2-3-1 | 👨‍💼 ديشامب\n\n🔑 *النجوم:*\n• مبابي — 12 هدفاً في المونديال، الأخطر في العالم\n• جريزمان — رؤية وإبداع استثنائيان\n• تشيامني — رئة الوسط\n• ديمبيلي — مراوغة وتمريرات قاتلة\n\n⚙️ دفاع عميق + انتقال متفجر عبر مبابي\n⚠️ اعتماد زائد على مبابي",
        "en": "🧠 *France 🇫🇷*\n📐 4-2-3-1 | 👨‍💼 Deschamps\n\n🔑 *Stars:*\n• Mbappé — 12 WC goals, world's most dangerous\n• Griezmann — exceptional vision and creativity\n• Tchouaméni — midfield engine\n• Dembélé — dribbling and killer passes\n\n⚙️ Deep block + explosive counter through Mbappé\n⚠️ Over-reliance on Mbappé",
    },
    "🇦🇷 Argentina": {
        "ar": "🧠 *الأرجنتين 🇦🇷*\n📐 4-4-2 | 👨‍💼 سكالوني\n\n🔑 *النجوم:*\n• ميسي (38 سنة!) — رسمياً في المونديال\n• خوليان ألفاريز — حركة بلا توقف\n• ماك أليستر (ليفربول) — عقل الوسط\n• دي باول (إنتر ميامي) — رئة الفريق\n\n⚙️ Scaloni Press + ميسي بحرية مطلقة\n⚠️ ميسي في الـ38 — هل لا يزال في قمته؟",
        "en": "🧠 *Argentina 🇦🇷*\n📐 4-4-2 | 👨‍💼 Scaloni\n\n🔑 *Stars:*\n• Messi (38!) — officially in the squad\n• Julián Álvarez — relentless movement\n• Mac Allister (Liverpool) — midfield brain\n• De Paul (Inter Miami) — the engine\n\n⚙️ Relentless Scaloni Press + Messi total freedom\n⚠️ Messi at 38 — still at peak level?",
    },
    "🇧🇷 Brazil": {
        "ar": "🧠 *البرازيل 🇧🇷*\n📐 4-2-3-1 | 👨‍💼 دوريفال جونيور\n\n🔑 *النجوم:*\n• فينيسيوس جونيور — أفضل لاعب في العالم 2024\n• روديغو — أهداف في المباريات الكبيرة\n• أندريك — 18 سنة، المستقبل الآن!\n• كاسيميرو — العمق الدفاعي\n\n⚙️ ارتكاز + انتقالات متفجرة\n⚠️ دفاع ضعيف أمام الكرات العرضية",
        "en": "🧠 *Brazil 🇧🇷*\n📐 4-2-3-1 | 👨‍💼 Dorival Júnior\n\n🔑 *Stars:*\n• Vinícius Jr — Best Player in the World 2024\n• Rodrygo — big-game goals\n• Endrick — 18 years old, the future is NOW!\n• Casemiro — defensive cover\n\n⚙️ Possession + explosive transitions\n⚠️ Defense weak to aerial balls",
    },
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 England": {
        "ar": "🧠 *إنجلترا 🏴󠁧󠁢󠁥󠁮󠁧󠁿*\n📐 4-2-3-1 | 👨‍💼 لي كارسلي\n\n🔑 *النجوم:*\n• جود بيلينغهام (ريال مدريد) — الأفضل في جيله\n• بوكايو ساكا (أرسنال) — سرعة وتمريرات\n• فيل فودن (مان سيتي) — إبداع وأهداف\n• هاري كين — أكثر هداف في تاريخ إنجلترا\n\n⚠️ المجموعة L: كرواتيا + غانا + بنما",
        "en": "🧠 *England 🏴󠁧󠁢󠁥󠁮󠁧󠁿*\n📐 4-2-3-1 | 👨‍💼 Lee Carsley\n\n🔑 *Stars:*\n• Jude Bellingham (Real Madrid) — best of his generation\n• Bukayo Saka (Arsenal) — pace and assists\n• Phil Foden (Man City) — creativity and goals\n• Harry Kane — England's all-time top scorer\n\n⚠️ Group L: Croatia + Ghana + Panama",
    },
}

PREDICTIONS = {
    "🇲🇽 Mexico vs 🇿🇦 South Africa": {
        "ar": "🔮 *المكسيك vs جنوب أفريقيا*\n🏟️ Mexico City Stadium\n🕐 19:00 GMT — 11 يونيو\n📊 *التوقع:* 2-0 للمكسيك\n\n💪 المكسيك: جمهور أسطوري + أوتشوا + ألفاريز\n⚠️ جنوب أفريقيا: دفاع منظم وروح قتالية\n🎯 المكسيك تسجل أولاً: 76%",
        "en": "🔮 *Mexico vs South Africa*\n🏟️ Mexico City Stadium\n🕐 19:00 GMT — June 11\n📊 *Prediction:* Mexico 2-0\n\n💪 Mexico: legendary crowd + Ochoa + Alvarez\n⚠️ South Africa: organized, fighting spirit\n🎯 Mexico to score first: 76%",
    },
    "🇧🇷 Brazil vs 🇲🇦 Morocco": {
        "ar": "🔮 *البرازيل vs المغرب*\n🏟️ MetLife Stadium, New York\n📊 *التوقع:* 2-1 للبرازيل\n\n💪 البرازيل: فينيسيوس + أندريك\n⚠️ المغرب: دفاع عالمي + دياز خطر\n🎯 أهداف في الشوطين",
        "en": "🔮 *Brazil vs Morocco*\n🏟️ MetLife Stadium\n📊 *Prediction:* Brazil 2-1\n\n💪 Brazil: Vinicius + Endrick at peak\n⚠️ Morocco: world-class defense + Díaz threat\n🎯 Goals in both halves",
    },
    "🇫🇷 France vs 🇸🇳 Senegal": {
        "ar": "🔮 *فرنسا vs السنغال*\n🏟️ New York NJ Stadium\n🕐 19:00 GMT — 16 يونيو\n📊 *التوقع:* 2-1 لفرنسا\n\n💪 فرنسا: مبابي + جريزمان = خطر حقيقي\n⚠️ السنغال: ساديو ماني + روح أفريقية\n🎯 مباراة متوازنة لكن فرنسا تتقدم",
        "en": "🔮 *France vs Senegal*\n🏟️ New York NJ Stadium\n🕐 19:00 GMT — June 16\n📊 *Prediction:* France 2-1\n\n💪 France: Mbappe + Griezmann combo\n⚠️ Senegal: Mané + African spirit\n🎯 Balanced match but France edges it",
    },
    "🇦🇷 Argentina vs 🇩🇿 Algeria": {
        "ar": "🔮 *الأرجنتين vs الجزائر*\n🏟️ Kansas City Stadium\n🕐 01:00 GMT — 17 يونيو\n📊 *التوقع:* 2-1 للأرجنتين\n\n💪 الأرجنتين: ميسي + ألفاريز جائعان للدفاع عن اللقب\n⚠️ الجزائر: محرز + دفاع متماسك + صدمة ممكنة!\n🎯 مباراة صعبة — الأرجنتين بهدف الفارق",
        "en": "🔮 *Argentina vs Algeria*\n🏟️ Kansas City Stadium\n🕐 01:00 GMT — June 17\n📊 *Prediction:* Argentina 2-1\n\n💪 Argentina: defending champions, Messi + Alvarez\n⚠️ Algeria: Mahrez + organized defense — upset possible!\n🎯 Tough match — Argentina by one goal",
    },
    "🇩🇿 Algeria vs 🇦🇹 Austria": {
        "ar": "🔮 *الجزائر vs النمسا*\n🏟️ Allegiant Stadium, Las Vegas\n📊 *التوقع:* تعادل 1-1\n\n💪 الجزائر: محرز + مازا + أمورا\n⚠️ النمسا: منتخب أوروبي منظم\n🎯 مباراة متكافئة!",
        "en": "🔮 *Algeria vs Austria*\n🏟️ Allegiant Stadium\n📊 *Prediction:* Draw 1-1\n\n💪 Algeria: Mahrez + Maza + Amoura\n⚠️ Austria: organized European side\n🎯 Balanced clash — Algeria can win!",
    },
    "🇸🇦 Saudi Arabia vs 🇺🇾 Uruguay": {
        "ar": "🔮 *السعودية vs أوروغواي*\n🏟️ NRG Stadium, Houston\n📊 *التوقع:* 2-1 لأوروغواي\n\n💪 السعودية: الدوسري + روح 2022\n⚠️ أوروغواي: نونييز + دارفين مرعبان\n🎯 المفاجأة السعودية ممكنة!",
        "en": "🔮 *Saudi Arabia vs Uruguay*\n🏟️ NRG Stadium\n📊 *Prediction:* Uruguay 2-1\n\n💪 Saudi: Al-Dawsari + 2022 spirit\n⚠️ Uruguay: Núñez + Darwin = terrifying attack\n🎯 Saudi upset is possible!",
    },
}

ARAB_TEAMS = {
    "ar": "🌙 *المنتخبات العربية — كأس العالم 2026*\n\n🇲🇦 *المغرب* — المجموعة C\n🆚 البرازيل | اسكتلندا | هايتي | ⭐ نصف نهائي 2022!\n\n🇩🇿 *الجزائر* — المجموعة J\n🆚 الأرجنتين | النمسا | الأردن | ⭐ مجموعة نار!\n\n🇸🇦 *السعودية* — المجموعة H\n🆚 إسبانيا | أوروغواي | الرأس الخضراء | ⭐ أفضل آسيوي 2025!\n\n🇹🇳 *تونس* — المجموعة F\n🆚 هولندا | اليابان | السويد\n\n🇮🇶 *العراق* — المجموعة I\n🆚 فرنسا | السنغال | النرويج | ⭐ عودة بعد 40 سنة!\n\n🇯🇴 *الأردن* — المجموعة J\n🆚 الأرجنتين | الجزائر | النمسا | ⭐ أول مونديال!\n\n🇶🇦 *قطر* — المجموعة B\n🆚 كندا | البوسنة | سويسرا\n\n🇪🇬 *مصر* — المجموعة G\n🆚 بلجيكا | إيران | نيوزيلندا",
    "en": "🌙 *Arab Teams — World Cup 2026*\n\n🇲🇦 *Morocco* — Group C\n🆚 Brazil | Scotland | Haiti | ⭐ 2022 semifinalists!\n\n🇩🇿 *Algeria* — Group J\n🆚 Argentina | Austria | Jordan | ⭐ Group of Death!\n\n🇸🇦 *Saudi Arabia* — Group H\n🆚 Spain | Uruguay | Cape Verde | ⭐ AFC Player of Year 2025!\n\n🇹🇳 *Tunisia* — Group F\n🆚 Netherlands | Japan | Sweden\n\n🇮🇶 *Iraq* — Group I\n🆚 France | Senegal | Norway | ⭐ Back after 40 years!\n\n🇯🇴 *Jordan* — Group J\n🆚 Argentina | Algeria | Austria | ⭐ First ever WC!\n\n🇶🇦 *Qatar* — Group B\n🆚 Canada | Bosnia | Switzerland\n\n🇪🇬 *Egypt* — Group G\n🆚 Belgium | Iran | New Zealand",
}

STATS_TEXT = {
    "titles": {
        "ar": "🏆 *أكثر المنتخبات تتويجاً*\n\n🥇 🇧🇷 البرازيل — 5\n🥈 🇩🇪 ألمانيا — 4\n🥈 🇮🇹 إيطاليا — 4\n🥉 🇦🇷 الأرجنتين — 3\n4️⃣ 🇫🇷 فرنسا — 2\n4️⃣ 🇺🇾 أوروغواي — 2",
        "en": "🏆 *Most World Cup Titles*\n\n🥇 🇧🇷 Brazil — 5\n🥈 🇩🇪 Germany — 4\n🥈 🇮🇹 Italy — 4\n🥉 🇦🇷 Argentina — 3\n4️⃣ 🇫🇷 France — 2\n4️⃣ 🇺🇾 Uruguay — 2",
    },
    "history_scorers": {
        "ar": "⚽ *هدافو التاريخ*\n\n🥇 🇩🇪 كلوزه — 16\n🥈 🇧🇷 رونالدو — 15\n🥉 🇩🇪 مولر — 14\n4️⃣ 🇫🇷 فونتين — 13\n4️⃣ 🇦🇷 ميسي — 13 ⭐\n6️⃣ 🇧🇷 بيليه — 12\n6️⃣ 🇫🇷 مبابي — 12 🔥\n\n⚠️ مبابي يطارد سجل كلوزه في 2026!",
        "en": "⚽ *All-Time Scorers*\n\n🥇 🇩🇪 Klose — 16\n🥈 🇧🇷 Ronaldo — 15\n🥉 🇩🇪 Müller — 14\n4️⃣ 🇫🇷 Fontaine — 13\n4️⃣ 🇦🇷 Messi — 13 ⭐\n6️⃣ 🇧🇷 Pelé — 12\n6️⃣ 🇫🇷 Mbappé — 12 🔥",
    },
    "favorites": {
        "ar": "🎯 *المرشحون للقب 2026*\n\n1️⃣ 🇫🇷 فرنسا — 18%\n2️⃣ 🇧🇷 البرازيل — 16%\n3️⃣ 🇦🇷 الأرجنتين — 14%\n4️⃣ 🇩🇪 ألمانيا — 12%\n5️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 إنجلترا — 11%\n6️⃣ 🇪🇸 إسبانيا — 10%\n7️⃣ 🇵🇹 البرتغال — 8%\n8️⃣ 🇲🇦 المغرب — 4%",
        "en": "🎯 *2026 Title Favorites*\n\n1️⃣ 🇫🇷 France — 18%\n2️⃣ 🇧🇷 Brazil — 16%\n3️⃣ 🇦🇷 Argentina — 14%\n4️⃣ 🇩🇪 Germany — 12%\n5️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England — 11%\n6️⃣ 🇪🇸 Spain — 10%\n7️⃣ 🇵🇹 Portugal — 8%\n8️⃣ 🇲🇦 Morocco — 4%",
    },
    "records": {
        "ar": "📊 *إحصائيات 2026*\n\n🌍 3 دول مضيفة\n⚽ 48 فريق\n🎮 104 مباريات\n🏟️ 16 ملعباً\n📅 39 يوماً\n💰 1+ مليار دولار جوائز\n🆕 دور الـ32 للمرة الأولى!\n👴 رونالدو (41): 6 مونديالات!",
        "en": "📊 *2026 Key Stats*\n\n🌍 3 host nations\n⚽ 48 teams\n🎮 104 matches\n🏟️ 16 stadiums\n📅 39 days\n💰 $1B+ prize fund\n🆕 Round of 32 debuts!\n👴 Ronaldo (41): 6 WCs!",
    },
}

FUN_FACTS = [
    "⚽ للمرة الأولى: 48 فريق — أكبر كأس عالم في التاريخ!\n⚽ First ever: 48 teams — the biggest World Cup in history!",
    "👴 رونالدو (41 سنة) يشارك في 6 مونديالات — رقم لم يبلغه أحد!\n👴 Ronaldo (41!) plays his 6th World Cup — an all-time record!",
    "⭐ ميسي (38) رسمياً في قائمة الأرجنتين — ثنائية ميسي-رونالدو تستمر!\n⭐ Messi (38) officially in Argentina's squad — the rivalry continues!",
    "🇲🇦 إبراهيم دياز: 5 أهداف في 5 مباريات AFCON 2025 — نجم المغرب الجديد!\n🇲🇦 Brahim Díaz: 5 goals in 5 AFCON 2025 games — Morocco's new star!",
    "🇩🇿 محرز 35 سنة ويقول هذا آخر كأس عالم له!\n🇩🇿 Mahrez (35) says this is his final World Cup!",
    "🆕 دور الـ32 يُطبَّق للمرة الأولى في تاريخ كأس العالم!\n🆕 The Round of 32 debuts for the very first time in WC history!",
    "💰 الجوائز تتخطى المليار دولار — ضعف كأس العالم 2022!\n💰 Prize money exceeds $1B — double the 2022 edition!",
    "🔢 مبابي يحتاج 4 أهداف ليتخطى سجل كلوزه (16 هدفاً)!\n🔢 Mbappé needs just 4 goals to break Klose's immortal record!",
    "🏟️ أزتيكا استضاف نهائيَّين (1970 و1986) ويفتتح 2026!\n🏟️ Azteca hosted two finals (1970 & 1986) and opens 2026!",
    "🇯🇴 الأردن يواجه الأرجنتين والجزائر في أول مونديال له!\n🇯🇴 Jordan faces Argentina AND Algeria in their very first WC!",
]

# ═══════════════════════════════════════════════════════
#  TEXT BUILDERS
# ═══════════════════════════════════════════════════════

def build_matches_text(date_key, lang="ar", fixtures_from_api=None):
    if fixtures_from_api:
        label = "مباريات" if lang == "ar" else "Matches"
        grp = "المجموعة" if lang == "ar" else "Group"
        lines = [f"⚽ *{label} — {date_key}*\n{'━'*22}"]
        for m in fixtures_from_api:
            status = m.get("status", "")
            if status in ("FT", "AET", "PEN"):
                score = f"*{m['home_goal']} — {m['away_goal']}*"
                icon = "✅"
            elif status in ("1H", "2H", "HT", "ET"):
                score = f"🔴 *{m['home_goal']} — {m['away_goal']}*"
                icon = "🔴"
            else:
                score = f"🕐 {m['time']} GMT"
                icon = "⏰"
            lines.append(f"\n{icon} *{m['home']}  {score}  {m['away']}*\n{grp}: {m['group']}\n🏟️ {m['stadium']}")
        return "\n".join(lines)

    matches = MATCHES_BY_DATE.get(date_key, [])
    if not matches:
        return "😴 لا مباريات في هذا اليوم\n😴 No matches scheduled"
    label = "مباريات" if lang == "ar" else "Matches"
    grp = "المجموعة" if lang == "ar" else "Group"
    lines = [f"⚽ *{label} — {date_key}*\n{'━'*22}"]
    for m in matches:
        lines.append(f"\n🆚 *{m['home']}  vs  {m['away']}*\n🕐 {m['time']} GMT  |  {grp} {m['group']}\n🏟️ {m['stadium']}, {m['city']}")
    return "\n".join(lines)

def build_results_text(results: list, lang="ar") -> str:
    if not results:
        return "⏳ لا نتائج بعد — تابعنا بعد أول مباراة!\n⏳ No results yet — check back after the first match!"
    label = "نتائج المباريات" if lang == "ar" else "Match Results"
    grp = "المجموعة" if lang == "ar" else "Group"
    lines = [f"📊 *{label}*\n{'━'*22}"]
    by_date = {}
    for r in results:
        by_date.setdefault(r["date"], []).append(r)
    for d in sorted(by_date.keys(), reverse=True)[:5]:
        lines.append(f"\n📅 *{d}*")
        for m in by_date[d]:
            winner = ""
            if m["winner"] is True:
                winner = " 🏆"
            elif m["winner"] is False:
                winner = ""
            lines.append(f"⚽ {m['home']}{winner} *{m['home_goal']} — {m['away_goal']}* {m['away']}\n   {grp}: {m['group']}")
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════

def main_keyboard(lang="ar"):
    if lang == "ar":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 مباريات اليوم", callback_data="today"),
             InlineKeyboardButton("📊 النتائج", callback_data="results")],
            [InlineKeyboardButton("🔴 مباشر LIVE", callback_data="live"),
             InlineKeyboardButton("🏆 الترتيب", url="https://www.google.com/search?q=ترتيب+مجموعات+كأس+العالم+2026")],
            [InlineKeyboardButton("⚽ الهدافون", url="https://www.google.com/search?q=هدافين+كأس+العالم+2026"),
             InlineKeyboardButton("🔮 التوقعات", callback_data="predictions")],
            [InlineKeyboardButton("🧠 تحليل تكتيكي", callback_data="tactical"),
             InlineKeyboardButton("📈 إحصائيات", callback_data="stats")],
            [InlineKeyboardButton("🌙 المنتخبات العربية", callback_data="arab_teams"),
             InlineKeyboardButton("🌟 معلومة", callback_data="fact")],
            [InlineKeyboardButton("📺 شاهد المباراة", callback_data="watch"),
             InlineKeyboardButton("⭐ ادعم البوت", callback_data="support")],
            [InlineKeyboardButton("🌐 English", callback_data="lang_en")],
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Today's Matches", callback_data="today"),
             InlineKeyboardButton("📊 Results", callback_data="results")],
            [InlineKeyboardButton("🔴 LIVE Now", callback_data="live"),
             InlineKeyboardButton("🏆 Standings", url="https://www.google.com/search?q=World+Cup+2026+group+standings")],
            [InlineKeyboardButton("⚽ Top Scorers", url="https://www.google.com/search?q=World+Cup+2026+top+scorers"),
             InlineKeyboardButton("🔮 Predictions", callback_data="predictions")],
            [InlineKeyboardButton("🧠 Tactical Analysis", callback_data="tactical"),
             InlineKeyboardButton("📈 Statistics", callback_data="stats")],
            [InlineKeyboardButton("🌙 Arab Teams", callback_data="arab_teams"),
             InlineKeyboardButton("🌟 Fun Fact", callback_data="fact")],
            [InlineKeyboardButton("📺 Watch Match", callback_data="watch"),
             InlineKeyboardButton("⭐ Support Bot", callback_data="support")],
            [InlineKeyboardButton("🌐 عربي", callback_data="lang_ar")],
        ])

def back_btn(target="back"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية | Main Menu", callback_data=target)]])

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
    cd = ("🔴 *البطولة انطلقت!*" if lang=="ar" else "🔴 *The tournament is LIVE!*") if days_left == 0 \
         else (f"⏳ *{days_left} يوم على الانطلاق!*" if lang=="ar" else f"⏳ *{days_left} days to kickoff!*")

    if lang == "ar":
        text = (f"🌍⚽ *أهلاً {name}!*\n\n*بوت كأس العالم 2026 الاحترافي* 🏆\n\n"
                f"📅 11 يونيو — 19 يوليو 2026\n"
                f"🌎 أمريكا 🇺🇸 | المكسيك 🇲🇽 | كندا 🇨🇦\n"
                f"⭐ 48 فريق | 104 مباراة | دور الـ32 الجديد!\n\n"
                f"{cd}\n👥 {total} مشترك معنا\n\nاختر ما تريد 👇")
    else:
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

    # Cache status
    cache_info = (
        f"\n\n💾 *حالة الكاش:*\n"
        f"• LIVE: {CACHE.time_left('live_matches')//60}m متبقية\n"
        f"• مباريات اليوم: {CACHE.time_left('today_fixtures')//60}m متبقية\n"
        f"• النتائج: {CACHE.time_left('recent_results')//60}m متبقية\n"
        f"• API calls today: {api_calls_today['count']}/100\n"
        f"• 🏆 الترتيب + ⚽ الهدافون: Google Links ✅"
    )

    await update.message.reply_text(
        f"🛠 *لوحة الإدارة*\n\n👥 المشتركون: *{count}*\n\n🆕 *آخر 5:*\n{recent_text}"
        f"{cache_info}\n\n📢 `/broadcast رسالتك`\n📰 `/daily` ملخص يومي",
        parse_mode="Markdown"
    )


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("⚠️ `/broadcast رسالتك`", parse_mode="Markdown")
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


async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    tmr = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    tmr_matches = MATCHES_BY_DATE.get(tmr, [])
    results = await get_recent_results()
    today_results = [r for r in results if r["date"] == today_str()]

    lines = ["🌅 *ملخص يومي — بوت كأس العالم 2026*\n"]
    if today_results:
        lines.append("📊 *نتائج اليوم:*")
        for r in today_results:
            lines.append(f"• {r['home']} *{r['home_goal']} — {r['away_goal']}* {r['away']}")
        lines.append("")
    if tmr_matches:
        lines.append(f"📅 *مباريات الغد ({tmr}):*")
        for m in tmr_matches[:5]:
            lines.append(f"• {m['home']} vs {m['away']} 🕐{m['time']} GMT+1")
        lines.append("")
    lines.append("⚽ _شارك البوت مع أصدقائك!_")
    summary = "\n".join(lines)

    subscribers = get_all_subscribers()
    sent = failed = 0
    status = await update.message.reply_text(f"📰 جاري إرسال الملخص لـ {len(subscribers)} مشترك...")
    for sub in subscribers:
        try:
            await context.bot.send_message(chat_id=sub["id"], text=summary, parse_mode="Markdown")
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

    # Language
    if data == "lang_en":
        update_user_lang(uid, "en")
        await query.edit_message_text("🌐 *Switched to English!* 👇", parse_mode="Markdown", reply_markup=main_keyboard("en"))
        return
    if data == "lang_ar":
        update_user_lang(uid, "ar")
        await query.edit_message_text("🌐 *تم التبديل للعربية!* 👇", parse_mode="Markdown", reply_markup=main_keyboard("ar"))
        return

    # Today
    if data == "today":
        msg = "⏳ *جاري جلب مباريات اليوم...*" if lang=="ar" else "⏳ *Fetching today's matches...*"
        await query.edit_message_text(msg, parse_mode="Markdown")
        api_fixtures = await get_today_fixtures()
        text = build_matches_text(today_str(), lang, api_fixtures if api_fixtures else None)
        if api_fixtures:
            cache_note = f"\n\n_💾 {'محدّث' if lang=='ar' else 'Updated'} | {'التالي' if lang=='ar' else 'Next'}: {CACHE.time_left('today_fixtures')//60}m_"
            text += cache_note
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # Results
    elif data == "results":
        msg = "⏳ *جاري جلب النتائج...*" if lang=="ar" else "⏳ *Fetching results...*"
        await query.edit_message_text(msg, parse_mode="Markdown")
        results = await get_recent_results()
        text = build_results_text(results, lang)
        if results:
            text += f"\n\n_💾 {'التالي' if lang=='ar' else 'Next update'}: {CACHE.time_left('recent_results')//60}m_"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # Live
    elif data == "live":
        await query.edit_message_text("🔴 *جاري جلب المباريات...*" if lang=="ar" else "🔴 *Fetching live...*", parse_mode="Markdown")
        live = await get_live_matches()
        if live:
            lines = ["🔴 *مباريات الآن | LIVE Now*\n"]
            for m in live:
                lines.append(f"⚡ *{m['home']} {m['home_goal']} — {m['away_goal']} {m['away']}*\n⏱️ {m['minute']}' | {m['status']}\n🏟️ {m['venue']}\n")
            text = "\n".join(lines)
            text += f"\n_💾 {'التالي' if lang=='ar' else 'Next update'}: {CACHE.time_left('live_matches')//60}m_"
        else:
            text = "😴 لا مباريات مباشرة الآن\n😴 No live matches right now"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # Predictions
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
            text = pred.get(lang, pred["ar"])
        else:
            text = "⚠️ غير متاح"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("predictions"))

    # Tactical
    elif data == "tactical":
        title = "🧠 *اختر منتخباً:*" if lang=="ar" else "🧠 *Choose a team:*"
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

    # Stats
    elif data == "stats":
        if lang == "ar":
            title = "📈 *اختر نوع الإحصائية:*"
            btns = [
                [InlineKeyboardButton("🏆 أكثر المنتخبات تتويجاً", callback_data="st_titles")],
                [InlineKeyboardButton("⚽ هدافو التاريخ", callback_data="st_history_scorers")],
                [InlineKeyboardButton("🎯 المرشحون للقب", callback_data="st_favorites")],
                [InlineKeyboardButton("📊 أرقام 2026", callback_data="st_records")],
                [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")],
            ]
        else:
            title = "📈 *Choose a stat category:*"
            btns = [
                [InlineKeyboardButton("🏆 Most Titles", callback_data="st_titles")],
                [InlineKeyboardButton("⚽ All-Time Scorers", callback_data="st_history_scorers")],
                [InlineKeyboardButton("🎯 Title Favorites", callback_data="st_favorites")],
                [InlineKeyboardButton("📊 2026 Stats", callback_data="st_records")],
                [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")],
            ]
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("st_"):
        key = data[3:]
        stat = STATS_TEXT.get(key, {})
        text = stat.get(lang, stat.get("ar", "⚠️ غير متاح"))
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("stats"))

    # Arab teams
    elif data == "arab_teams":
        await query.edit_message_text(ARAB_TEAMS.get(lang, ARAB_TEAMS["ar"]), parse_mode="Markdown", reply_markup=back_btn())

    # Fun fact
    elif data == "fact":
        fact = random.choice(FUN_FACTS)
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 أخرى | Another", callback_data="fact")],
            [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")]
        ])
        await query.edit_message_text(f"🌟 *هل تعلم؟ | Did You Know?*\n\n{fact}", parse_mode="Markdown", reply_markup=btns)

    # Watch Match
    elif data == "watch":
        if lang == "ar":
            title = (
                "📺 *شاهد المباريات مباشرة*\n\n"
                "⚠️ _هذه روابط خارجية مستقلة عن البوت_\n"
                "اختر الموقع المفضل لديك 👇"
            )
        else:
            title = (
                "📺 *Watch Matches Live*\n\n"
                "⚠️ _External links, independent from this bot_\n"
                "Choose your preferred site 👇"
            )
        watch_btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 يلا شوت | Yalla Shoot", url="https://yalla-shooted.mov")],
            [InlineKeyboardButton("🔵 LiveTV مباشر", url="https://www.google.com/search?q=LiveTV+official+streaming+site")],
            [InlineKeyboardButton("🟣 كورة ستار | Kora Star", url="https://www.google.com/search?q=موقع+كورة+ستار+مباشر+الان")],
            [InlineKeyboardButton("🟡 بين سبورت | beIN Sport", url="https://www.beinsports.com/ar")],
            [InlineKeyboardButton("⚫ Sport365", url="https://www.google.com/search?q=Sport365+live+matches")],
            [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")],
        ])
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=watch_btns)

    # Support Bot — Telegram Stars
    elif data == "support":
        if lang == "ar":
            title = (
                "⭐ *ادعم بوت كأس العالم 2026*\n\n"
                "إذا أعجبك البوت وأفادك، يمكنك دعمنا بنجوم تيليجرام ⭐\n\n"
                "كل نجمة تساعدنا على:\n"
                "• 🔧 تطوير ميزات جديدة\n"
                "• 🌍 توسيع تغطية البطولة\n"
                "• ⚡ تحسين سرعة البوت\n\n"
                "اختر مبلغ الدعم 👇"
            )
        else:
            title = (
                "⭐ *Support World Cup 2026 Bot*\n\n"
                "If you enjoy the bot, support us with Telegram Stars ⭐\n\n"
                "Every star helps us:\n"
                "• 🔧 Build new features\n"
                "• 🌍 Expand tournament coverage\n"
                "• ⚡ Improve bot speed\n\n"
                "Choose a support amount 👇"
            )
        support_btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ 1 نجمة / 1 Star", callback_data="stars_1")],
            [InlineKeyboardButton("⭐⭐⭐ 3 نجوم / 3 Stars", callback_data="stars_3")],
            [InlineKeyboardButton("⭐⭐⭐⭐⭐ 5 نجوم / 5 Stars", callback_data="stars_5")],
            [InlineKeyboardButton("🌟 10 نجوم / 10 Stars", callback_data="stars_10")],
            [InlineKeyboardButton("💫 25 نجمة / 25 Stars", callback_data="stars_25")],
            [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")],
        ])
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=support_btns)

    elif data.startswith("stars_"):
        amount = int(data[6:])
        if lang == "ar":
            desc = f"⭐ دعم بوت كأس العالم 2026 بـ {amount} {'نجمة' if amount == 1 else 'نجوم'}"
        else:
            desc = f"⭐ Support World Cup 2026 Bot with {amount} {'Star' if amount == 1 else 'Stars'}"
        try:
            await context.bot.send_invoice(
                chat_id=uid,
                title="⚽ بوت كأس العالم 2026 | World Cup 2026 Bot",
                description=desc,
                payload=f"support_{amount}_stars_{uid}",
                currency="XTR",
                prices=[LabeledPrice(label="⭐ Telegram Stars", amount=amount)],
                provider_token="",
            )
            await query.answer()
        except Exception as e:
            logger.error(f"Invoice error: {e}")
            await query.answer("⚠️ حدث خطأ، حاول مجدداً | Error, try again", show_alert=True)

    # Back
    elif data == "back":
        name = query.from_user.first_name or "Champion"
        wc_start = date(2026, 6, 11)
        days_left = max((wc_start - date.today()).days, 0)
        total = get_subscriber_count()
        if lang == "ar":
            cd = "🔴 البطولة انطلقت!" if days_left == 0 else f"⏳ {days_left} يوم على الانطلاق!"
            text = f"⚽ *القائمة الرئيسية*\n{cd} | 👥 {total} مشترك\n\nاختر يا {name} 👇"
        else:
            cd = "🔴 Tournament is LIVE!" if days_left == 0 else f"⏳ {days_left} days to kickoff!"
            text = f"⚽ *Main Menu*\n{cd} | 👥 {total} subscribers\n\nChoose, {name} 👇"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard(lang))


async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يوافق على الدفع تلقائياً"""
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يرسل رسالة شكر بعد الدفع"""
    uid = update.effective_user.id
    lang = get_lang(uid)
    stars = update.message.successful_payment.total_amount
    name = update.effective_user.first_name or "Champion"

    if lang == "ar":
        text = (
            f"💛 *شكراً جزيلاً {name}!*\n\n"
            f"لقد دعمت البوت بـ *{stars} {'نجمة' if stars == 1 else 'نجوم'}* ⭐\n\n"
            f"دعمك يساعدنا على الاستمرار وتطوير البوت\n"
            f"لتغطية أفضل لكأس العالم 2026! 🏆\n\n"
            f"_شارك البوت مع أصدقائك ⚽_"
        )
    else:
        text = (
            f"💛 *Thank you so much, {name}!*\n\n"
            f"You supported the bot with *{stars} {'Star' if stars == 1 else 'Stars'}* ⭐\n\n"
            f"Your support helps us keep running and improving\n"
            f"for better World Cup 2026 coverage! 🏆\n\n"
            f"_Share the bot with your friends ⚽_"
        )
    await update.message.reply_text(text, parse_mode="Markdown")
    logger.info(f"⭐ Stars received: {stars} from {name} ({uid})")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    await update.message.reply_text(
        "⚽ استخدم الأزرار! أو أرسل /start" if lang=="ar" else "⚽ Use the buttons! Or send /start",
        reply_markup=main_keyboard(lang)
    )

# ═══════════════════════════════════════════════════════
#  AUTO BACKGROUND TASKS
# ═══════════════════════════════════════════════════════

async def auto_cache_warmer(app):
    """يحمّي الكاش تلقائياً — LIVE والنتائج والمباريات فقط"""
    await asyncio.sleep(30)
    logger.info("🔥 Auto cache warmer started (standings/scorers removed — using Google links)")
    while True:
        try:
            if CACHE.is_expired("today_fixtures"):
                logger.info("🔄 Auto-refreshing today fixtures...")
                await get_today_fixtures()
            if CACHE.is_expired("recent_results"):
                logger.info("🔄 Auto-refreshing recent results...")
                await get_recent_results()
        except Exception as e:
            logger.error(f"Cache warmer error: {e}")
        await asyncio.sleep(60)


async def post_init(app):
    asyncio.create_task(auto_cache_warmer(app))
    logger.info("✅ Background cache warmer scheduled")

# ═══════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("⚽ World Cup 2026 Pro Bot v7.1 — Google Links Edition — LIVE!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
