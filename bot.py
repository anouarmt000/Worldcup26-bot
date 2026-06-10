#!/usr/bin/env python3
"""
⚽ World Cup 2026 Pro Bot
Version 3.0 — Professional Edition
• Live data from API-Football (api-sports.io)
• Built-in subscriber management system
• Admin broadcast panel
• Tactical analysis & advanced stats
• Bilingual AR/EN
"""

import os, logging, random, json, asyncio, aiohttp
from datetime import date, timedelta, datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN        = os.environ.get("BOT_TOKEN")
FOOTBALL_API = os.environ.get("FOOTBALL_API_KEY", "")   # api-sports.io key
ADMIN_ID     = int(os.environ.get("ADMIN_ID", "0"))      # your Telegram numeric ID

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود في Railway Variables")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, ConversationHandler, filters
)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  SUBSCRIBER DATABASE  (JSON file — simple & reliable)
# ═══════════════════════════════════════════════════════════════════

DB_FILE = "subscribers.json"

def load_db() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"users": {}}

def save_db(db: dict):
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
        logger.info(f"New subscriber: {user.first_name} ({user.id})")
    return db["users"][uid]

def update_user_lang(uid: int, lang: str):
    db = load_db()
    if str(uid) in db["users"]:
        db["users"][str(uid)]["lang"] = lang
        save_db(db)

def get_all_subscribers() -> list:
    db = load_db()
    return [v for v in db["users"].values() if v.get("active", True)]

def get_subscriber_count() -> int:
    return len(get_all_subscribers())

# ═══════════════════════════════════════════════════════════════════
#  LIVE API — api-sports.io (free tier: 100 req/day)
# ═══════════════════════════════════════════════════════════════════

API_BASE = "https://v3.football.api-sports.io"
WC2026_ID = 1 # Will be updated once WC 2026 has official ID

async def api_get(endpoint: str, params: dict = {}) -> dict | None:
    if not FOOTBALL_API:
        return None
    headers = {"x-apisports-key": FOOTBALL_API}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/{endpoint}", headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    return await r.json()
    except Exception as e:
        logger.warning(f"API error: {e}")
    return None

async def fetch_live_matches() -> list:
    data = await api_get("fixtures", {"live": "all"})
    if not data or not data.get("response"):
        return []
    matches = []
    for f in data["response"][:8]:
        fix = f["fixture"]
        teams = f["teams"]
        goals = f["goals"]
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

async def fetch_standings(league_id: int, season: int) -> str:
    data = await api_get("standings", {"league": league_id, "season": season})
    if not data or not data.get("response"):
        return None
    try:
        standings = data["response"][0]["league"]["standings"][0]
        lines = []
        for t in standings[:10]:
            lines.append(
                f"{t['rank']}. {t['team']['name']} — "
                f"*{t['points']} pts* | "
                f"W{t['all']['win']} D{t['all']['draw']} L{t['all']['lose']}"
            )
        return "\n".join(lines)
    except:
        return None

async def fetch_team_stats(team_id: int, league_id: int, season: int) -> str:
    data = await api_get("teams/statistics", {"team": team_id, "league": league_id, "season": season})
    if not data or not data.get("response"):
        return None
    try:
        s = data["response"]
        name = s["team"]["name"]
        form = s.get("form", "N/A")
        goals_for = s["goals"]["for"]["total"]["total"]
        goals_ag  = s["goals"]["against"]["total"]["total"]
        biggest_win = s["biggest"].get("wins", {}).get("away", "N/A")
        return (
            f"📊 *{name} — Season Stats*\n\n"
            f"📈 Form (last 5): `{form[-5:]}`\n"
            f"⚽ Goals scored: *{goals_for}*\n"
            f"🛡 Goals conceded: *{goals_ag}*\n"
            f"🏆 Biggest win: *{biggest_win}*"
        )
    except:
        return None

# ═══════════════════════════════════════════════════════════════════
#  STATIC DATA
# ═══════════════════════════════════════════════════════════════════

GROUPS = {
    "A": ["🇲🇽 Mexico", "🇿🇦 South Africa", "🇰🇷 South Korea", "🇨🇿 Czechia"],
    "B": ["🇨🇦 Canada", "🇧🇦 Bosnia", "🇶🇦 Qatar", "🇨🇭 Switzerland"],
    "C": ["🇺🇸 USA", "🇵🇾 Paraguay", "🇸🇪 Sweden", "🇹🇳 Tunisia"],
    "D": ["🇩🇪 Germany", "🇨🇼 Curaçao", "🇳🇱 Netherlands", "🇯🇵 Japan"],
    "E": ["🇪🇸 Spain", "🇧🇪 Belgium", "🇸🇦 Saudi Arabia", "🇮🇷 Iran"],
    "F": ["🇫🇷 France", "🇸🇳 Senegal", "🇮🇶 Iraq", "🇳🇴 Norway"],
    "G": ["🇧🇷 Brazil", "🇲🇦 Morocco", "🇭🇹 Haiti", "🇦🇺 Australia"],
    "H": ["🇵🇹 Portugal", "🇨🇴 Colombia", "🇺🇿 Uzbekistan", "🇨🇩 DR Congo"],
    "I": ["🇦🇷 Argentina", "🇦🇹 Austria", "🇩🇿 Algeria", "🇯🇴 Jordan"],
    "J": ["🏴󠁧󠁢󠁥󠁮󠁧󠁿 England", "🇭🇷 Croatia", "🇵🇦 Panama", "🇬🇭 Ghana"],
    "K": ["🇮🇹 Italy", "🇪🇨 Ecuador", "🇨🇮 Ivory Coast", "🇹🇷 Turkey"],
    "L": ["🇺🇾 Uruguay", "🇨🇻 Cape Verde", "🇯🇲 Jamaica", "🇨🇱 Chile"],
}

MATCHES_BY_DATE = {
    "2026-06-11": [{"home":"🇲🇽 Mexico","away":"🇿🇦 South Africa","time":"22:00","group":"A","stadium":"Estadio Azteca","city":"Mexico City"}],
    "2026-06-12": [
        {"home":"🇨🇦 Canada","away":"🇧🇦 Bosnia","time":"20:00","group":"B","stadium":"BMO Field","city":"Toronto"},
        {"home":"🇰🇷 South Korea","away":"🇨🇿 Czechia","time":"23:00","group":"A","stadium":"Estadio Akron","city":"Guadalajara"},
    ],
    "2026-06-13": [
        {"home":"🇺🇸 USA","away":"🇵🇾 Paraguay","time":"02:00","group":"C","stadium":"SoFi Stadium","city":"Los Angeles"},
        {"home":"🇶🇦 Qatar","away":"🇨🇭 Switzerland","time":"20:00","group":"B","stadium":"Levi's Stadium","city":"San Francisco"},
        {"home":"🇧🇷 Brazil","away":"🇲🇦 Morocco","time":"23:00","group":"G","stadium":"SoFi Stadium","city":"Los Angeles"},
    ],
    "2026-06-14": [
        {"home":"🇩🇪 Germany","away":"🇨🇼 Curaçao","time":"18:00","group":"D","stadium":"Mercedes-Benz Stadium","city":"Atlanta"},
        {"home":"🇳🇱 Netherlands","away":"🇯🇵 Japan","time":"21:00","group":"D","stadium":"Gillette Stadium","city":"Boston"},
        {"home":"🇸🇦 Saudi Arabia","away":"🇮🇷 Iran","time":"23:00","group":"E","stadium":"Arrowhead Stadium","city":"Kansas City"},
    ],
    "2026-06-15": [
        {"home":"🇪🇸 Spain","away":"🇨🇻 Cape Verde","time":"17:00","group":"E","stadium":"Rose Bowl","city":"Los Angeles"},
        {"home":"🇧🇪 Belgium","away":"🇪🇬 Egypt","time":"20:00","group":"E","stadium":"Hard Rock Stadium","city":"Miami"},
        {"home":"🇩🇿 Algeria","away":"🇯🇴 Jordan","time":"23:00","group":"I","stadium":"MetLife Stadium","city":"New York"},
    ],
    "2026-06-16": [
        {"home":"🇫🇷 France","away":"🇸🇳 Senegal","time":"20:00","group":"F","stadium":"SoFi Stadium","city":"Los Angeles"},
        {"home":"🇮🇶 Iraq","away":"🇳🇴 Norway","time":"23:00","group":"F","stadium":"Lumen Field","city":"Seattle"},
        {"home":"🇦🇷 Argentina","away":"🇦🇹 Austria","time":"02:00","group":"I","stadium":"MetLife Stadium","city":"New York"},
    ],
    "2026-06-17": [
        {"home":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 England","away":"🇭🇷 Croatia","time":"20:00","group":"J","stadium":"AT&T Stadium","city":"Dallas"},
        {"home":"🇵🇹 Portugal","away":"🇨🇴 Colombia","time":"23:00","group":"H","stadium":"Allegiant Stadium","city":"Las Vegas"},
    ],
    "2026-06-18": [
        {"home":"🇮🇹 Italy","away":"🇪🇨 Ecuador","time":"20:00","group":"K","stadium":"Lincoln Financial Field","city":"Philadelphia"},
        {"home":"🇺🇾 Uruguay","away":"🇨🇻 Cape Verde","time":"23:00","group":"L","stadium":"NRG Stadium","city":"Houston"},
    ],
}

TACTICAL_ANALYSIS = {
    "🇲🇽 Mexico": {
        "ar": (
            "🧠 *تحليل تكتيكي — المكسيك*\n\n"
            "📐 *التشكيلة المعتادة:* 4-3-3\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• ضغط عالٍ في ملعب الخصم (Gegenpressing)\n"
            "• انتقال سريع من الدفاع للهجوم في 3-4 تمريرات\n"
            "• الاعتماد على الأجنحة السريعة للتمركز خلف الدفاع\n\n"
            "🔑 *اللاعبون المحوريون:*\n"
            "• رائول خيمينيز — مرجع الهجوم\n"
            "• إيرفينج لوزانو — السرعة على اليمين\n"
            "• إيداير مورالس — قلب الوسط\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• الدفاع يتعرض للضغط أمام الكرات الثابتة\n"
            "• يفقد التنظيم أمام الضغط العالي"
        ),
        "en": (
            "🧠 *Tactical Analysis — Mexico*\n\n"
            "📐 *Formation:* 4-3-3\n\n"
            "⚙️ *Playing Style:*\n"
            "• High pressing (Gegenpressing)\n"
            "• Fast transition — 3-4 pass counter-attacks\n"
            "• Wide wingers making runs in behind\n\n"
            "🔑 *Key Players:*\n"
            "• Raúl Jiménez — target man\n"
            "• Hirving Lozano — pace on the right\n"
            "• Edson Álvarez — midfield anchor\n\n"
            "⚠️ *Weaknesses:*\n"
            "• Vulnerable to set pieces\n"
            "• Loses shape under high press"
        ),
    },
    "🇫🇷 France": {
        "ar": (
            "🧠 *تحليل تكتيكي — فرنسا*\n\n"
            "📐 *التشكيلة:* 4-2-3-1\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• دفاع منظم وعميق ثم انتقال متفجر\n"
            "• مبابي على الجناح الأيسر يمنح عمقاً تهديدياً دائماً\n"
            "• جريزمان يتراجع ليصنع الفرص كـ False 9\n"
            "• تشيامني وكانتي يؤمنان المحور\n\n"
            "🔑 *اللاعبون المحوريون:*\n"
            "• مبابي — سرعة مطلقة وإنهاء قاتل\n"
            "• جريزمان — رؤية استثنائية وإبداع\n"
            "• ديمبيلي — مراوغة وتمريرات حاسمة\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• الاعتماد الزائد على مبابي\n"
            "• تراجع الأداء أمام الضغط الجماعي العالي"
        ),
        "en": (
            "🧠 *Tactical Analysis — France*\n\n"
            "📐 *Formation:* 4-2-3-1\n\n"
            "⚙️ *Playing Style:*\n"
            "• Deep defensive block + explosive counter\n"
            "• Mbappe on left provides constant depth threat\n"
            "• Griezmann drops as False 9 to create\n"
            "• Tchouameni & Kante secure the midfield\n\n"
            "🔑 *Key Players:*\n"
            "• Mbappe — pace & lethal finishing\n"
            "• Griezmann — vision and creativity\n"
            "• Dembele — dribbling & key passes\n\n"
            "⚠️ *Weaknesses:*\n"
            "• Over-reliance on Mbappe\n"
            "• Can struggle vs high collective pressing"
        ),
    },
    "🇦🇷 Argentina": {
        "ar": (
            "🧠 *تحليل تكتيكي — الأرجنتين*\n\n"
            "📐 *التشكيلة:* 4-4-2 / 4-3-3\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• ضغط جماعي بلا كلل (Scaloni Press)\n"
            "• تحرك ميسي الحر يخلق تفوقاً عددياً في الوسط\n"
            "• الجانبان ألفاريز ودي باول يقطعان المسافات بسرعة\n"
            "• قوة نفسية استثنائية بعد 2022\n\n"
            "🔑 *اللاعبون المحوريون:*\n"
            "• ميسي — يصنع ويسجل من أي موقع\n"
            "• ألفاريز — حركة بلا توقف في المنطقة\n"
            "• دي باول — رئة الفريق في الوسط\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• إذا أُوقف ميسي تراجع التهديد\n"
            "• قد يعاني ضد الفرق التي تلعب بـ 5 مدافعين"
        ),
        "en": (
            "🧠 *Tactical Analysis — Argentina*\n\n"
            "📐 *Formation:* 4-4-2 / 4-3-3\n\n"
            "⚙️ *Playing Style:*\n"
            "• Relentless collective pressing (Scaloni Press)\n"
            "• Messi's free role creates midfield overloads\n"
            "• Alvarez & De Paul cover ground rapidly\n"
            "• Exceptional mental strength post-2022\n\n"
            "🔑 *Key Players:*\n"
            "• Messi — creates and scores from anywhere\n"
            "• Alvarez — relentless movement in the box\n"
            "• De Paul — the engine in midfield\n\n"
            "⚠️ *Weaknesses:*\n"
            "• If Messi is neutralized, threat drops sharply\n"
            "• Can struggle vs 5-back defensive setups"
        ),
    },
    "🇧🇷 Brazil": {
        "ar": (
            "🧠 *تحليل تكتيكي — البرازيل*\n\n"
            "📐 *التشكيلة:* 4-2-3-1\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• كرة ارتكاز مع انتقالات سريعة على الأجنحة\n"
            "• فينيسيوس يلعب على اليسار بحرية مطلقة\n"
            "• رودريغو يغطي المساحات خلف المهاجم\n"
            "• كاسيميرو يؤمن العمق الدفاعي\n\n"
            "🔑 *اللاعبون المحوريون:*\n"
            "• فينيسيوس جونيور — الأخطر في العالم\n"
            "• رودريغو — حركة ذكية وأهداف كبيرة\n"
            "• أندريك — المستقبل يبدأ الآن\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• الدفاع يفتقر للصلابة أمام الكرات العرضية\n"
            "• يعاني نفسياً أحياناً في المباريات الكبيرة"
        ),
        "en": (
            "🧠 *Tactical Analysis — Brazil*\n\n"
            "📐 *Formation:* 4-2-3-1\n\n"
            "⚙️ *Playing Style:*\n"
            "• Possession-based with explosive wing transitions\n"
            "• Vinicius given total freedom on the left\n"
            "• Rodrygo covers spaces behind the striker\n"
            "• Casemiro provides defensive cover\n\n"
            "🔑 *Key Players:*\n"
            "• Vinicius Jr — most dangerous player in world\n"
            "• Rodrygo — intelligent movement & big goals\n"
            "• Endrick — the future starts now\n\n"
            "⚠️ *Weaknesses:*\n"
            "• Defense lacks aerial strength\n"
            "• Can underperform mentally in big moments"
        ),
    },
    "🇩🇿 Algeria": {
        "ar": (
            "🧠 *تحليل تكتيكي — الجزائر*\n\n"
            "📐 *التشكيلة:* 4-3-3 / 4-2-3-1\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• ضغط متوسط وانتقال سريع للهجوم\n"
            "• محرز يلعب بحرية خلف المهاجمين\n"
            "• الاعتماد على الكرات الثابتة والضربات الحرة\n"
            "• دفاع مركزي قوي وصعب الاختراق\n\n"
            "🔑 *اللاعبون المحوريون:*\n"
            "• رياض محرز — أفضل لاعب عربي في التاريخ\n"
            "• بغداد بونجاح — مرجع الهجوم\n"
            "• إسماعيل بن ناصر — قلب الوسط\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• يتراجع الأداء بغياب محرز\n"
            "• يعاني أمام الفرق التي تتقن الكرة طويلاً"
        ),
        "en": (
            "🧠 *Tactical Analysis — Algeria*\n\n"
            "📐 *Formation:* 4-3-3 / 4-2-3-1\n\n"
            "⚙️ *Playing Style:*\n"
            "• Medium press with rapid counter-attacking\n"
            "• Mahrez roams freely behind strikers\n"
            "• Dangerous from set pieces and free kicks\n"
            "• Strong central defense hard to break down\n\n"
            "🔑 *Key Players:*\n"
            "• Riyad Mahrez — best Arab player of his era\n"
            "• Baghdad Bounedjah — target striker\n"
            "• Ismail Bennacer — midfield engine\n\n"
            "⚠️ *Weaknesses:*\n"
            "• Performance drops significantly without Mahrez\n"
            "• Can struggle vs teams that dominate possession"
        ),
    },
    "🇸🇦 Saudi Arabia": {
        "ar": (
            "🧠 *تحليل تكتيكي — السعودية*\n\n"
            "📐 *التشكيلة:* 4-3-3 / 5-4-1\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• دفاع أوفسايد منضبط على مستوى عالٍ\n"
            "• الانتقال السريع — الأسلوب الذي صنع معجزة 2022\n"
            "• ضغط جماعي متواصل يرهق الخصم\n"
            "• التركيز الشديد والإيمان بالنفس بعد الأرجنتين\n\n"
            "🔑 *اللاعبون المحوريون:*\n"
            "• سالم الدوسري — قائد وصانع الفوارق\n"
            "• فراس البريكان — سرعة ولياقة استثنائية\n"
            "• محمد الباييّ — عقل الوسط\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• الكرة الثابتة الدفاعية نقطة ضعف\n"
            "• يعاني أمام الفرق ذات الجودة الفردية العالية"
        ),
        "en": (
            "🧠 *Tactical Analysis — Saudi Arabia*\n\n"
            "📐 *Formation:* 4-3-3 / 5-4-1\n\n"
            "⚙️ *Playing Style:*\n"
            "• Disciplined high defensive line (offside trap)\n"
            "• Rapid transition — the formula that beat Argentina\n"
            "• Relentless collective pressing\n"
            "• Mental strength & belief after 2022\n\n"
            "🔑 *Key Players:*\n"
            "• Salem Al-Dawsari — captain and difference-maker\n"
            "• Firas Al-Buraikan — exceptional pace & fitness\n"
            "• Mohamed Al-Burayk — midfield brain\n\n"
            "⚠️ *Weaknesses:*\n"
            "• Defensive set pieces are a weak point\n"
            "• Struggles vs teams with high individual quality"
        ),
    },
    "🇲🇦 Morocco": {
        "ar": (
            "🧠 *تحليل تكتيكي — المغرب*\n\n"
            "📐 *التشكيلة:* 4-3-3 / 4-1-4-1\n\n"
            "⚙️ *أسلوب اللعب:*\n"
            "• دفاع متماسك كتلة صلبة يصعب اختراقها\n"
            "• الانتقالات السريعة بعد استعادة الكرة\n"
            "• الضغط في الثلث الوسط لاستنزاف الخصم\n"
            "• رهبة نفسية بعد إنجاز نصف النهائي 2022\n\n"
            "🔑 *اللاعبون المحوريون:*\n"
            "• حكيم زياش — إبداع وتمريرات قاتلة\n"
            "• يوسف النصيري — مهاجم خطير ونهائيات قوية\n"
            "• ياسين بونو — أفضل حارس أفريقي\n\n"
            "⚠️ *نقاط الضعف:*\n"
            "• الإبداع الهجومي يتراجع بغياب زياش\n"
            "• يعاني أمام الفرق ذات التنظيم التكتيكي العالي"
        ),
        "en": (
            "🧠 *Tactical Analysis — Morocco*\n\n"
            "📐 *Formation:* 4-3-3 / 4-1-4-1\n\n"
            "⚙️ *Playing Style:*\n"
            "• Compact defensive block very hard to break\n"
            "• Fast transitions after winning the ball\n"
            "• Mid-block pressing to exhaust opponents\n"
            "• Psychological edge after 2022 semifinal run\n\n"
            "🔑 *Key Players:*\n"
            "• Hakim Ziyech — creativity and killer passes\n"
            "• Youssef En-Nesyri — dangerous striker, strong finisher\n"
            "• Yassine Bono — best African goalkeeper\n\n"
            "⚠️ *Weaknesses:*\n"
            "• Attack loses flair without Ziyech\n"
            "• Can struggle vs high tactical organization"
        ),
    },
}

FUN_FACTS = [
    "⚽ كأس العالم 2026 هو الأكبر في التاريخ: 48 فريق، 104 مباراة، 3 دول مضيفة!\n🌍 The 2026 WC is the biggest ever: 48 teams, 104 matches, 3 host nations!",
    "🏟️ ملعب أزتيكا الوحيد الذي شهد نهائيَّين متتاليين (1970 و1986)!\n🏟️ Azteca is the only stadium to host two finals (1970 & 1986)!",
    "⭐ مبابي (12 هدفاً) يحتاج 4 أهداف فقط ليتفوق على كلوزه (16)!\n⭐ Mbappe (12 goals) needs just 4 more to surpass Klose's all-time record!",
    "🇸🇦 فوز السعودية على الأرجنتين 2022 صنّفه خبراء إحصاء كأكبر مفاجأة رياضية منذ 30 عاماً!\n🇸🇦 Saudi's 2022 win vs Argentina was statistically the biggest sports upset in 30 years!",
    "🇲🇦 المغرب أول منتخب أفريقي وعربي يبلغ نصف نهائي كأس العالم!\n🇲🇦 Morocco — first African & Arab team ever to reach a World Cup semifinal!",
    "💰 جائزة كأس العالم 2026 ستتجاوز المليار دولار — ضعف نسخة 2022!\n💰 2026 prize fund exceeds $1 billion — double the 2022 edition!",
    "🇯🇴 الأردن يشارك لأول مرة في تاريخه — إنجاز تاريخي للكرة العربية!\n🇯🇴 Jordan's first ever World Cup — a historic milestone for Arab football!",
    "📐 فرنسا استخدمت 6 تشكيلات مختلفة في طريقها للقب 2018!\n📐 France used 6 different formations on their way to the 2018 title!",
    "🎯 ألمانيا الوحيدة التي فازت بكأس العالم في ثلاث قارات مختلفة!\n🎯 Germany is the only team to win the World Cup on three different continents!",
    "🧠 متوسط مسافة الجري لكل لاعب في كأس العالم: 11 كيلومتر لكل مباراة!\n🧠 Average distance covered per player at the World Cup: 11 km per match!",
    "🔢 للمرة الأولى في التاريخ 48 منتخباً بدلاً من 32!\n🔢 First time ever: 48 nations qualify instead of 32!",
    "⏱️ إجمالي دقائق اللعب في كأس العالم 2026: 9,880 دقيقة من الإثارة!\n⏱️ Total playing time in WC 2026: 9,880 minutes of football!",
]

# ═══════════════════════════════════════════════════════════════════
#  LANG HELPERS
# ═══════════════════════════════════════════════════════════════════

user_lang = {}

def get_lang(uid):
    db = load_db()
    return db["users"].get(str(uid), {}).get("lang", user_lang.get(uid, "ar"))

def today_str():
    return date.today().strftime("%Y-%m-%d")

# ═══════════════════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════════════════

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
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع | Back", callback_data=target)]])

# ═══════════════════════════════════════════════════════════════════
#  MATCH TEXT BUILDER
# ═══════════════════════════════════════════════════════════════════

def build_matches_text(date_key, lang="ar"):
    matches = MATCHES_BY_DATE.get(date_key, [])
    if not matches:
        return "😴 لا مباريات في هذا اليوم\n😴 No matches scheduled"
    label = "مباريات" if lang == "ar" else "Matches"
    grp_lbl = "المجموعة" if lang == "ar" else "Group"
    lines = [f"⚽ *{label} — {date_key}*\n{'━'*22}"]
    for m in matches:
        lines.append(
            f"\n🆚 *{m['home']}  vs  {m['away']}*\n"
            f"🕐 {m['time']} GMT+1  |  {grp_lbl} {m['group']}\n"
            f"🏟️ {m['stadium']}, {m['city']}"
        )
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════
#  PREDICTIONS DATA
# ═══════════════════════════════════════════════════════════════════

PREDICTIONS = {
    "🇲🇽 Mexico vs 🇿🇦 South Africa": {
        "ar": "🔮 *تحليل المباراة*\n\n🏟️ أزتيكا — أكثر الملاعب سحراً في التاريخ\n📊 *التوقع:* المكسيك 2-0 جنوب أفريقيا\n\n💪 *المكسيك:* الجمهور، السرعة على الأجنحة، خبرة المونديال\n⚠️ *جنوب أفريقيا:* دفاع منظم، لا يخسران شيئاً\n\n🎯 المكسيك تسجل أولاً — احتمال 78%",
        "en": "🔮 *Match Analysis*\n\n🏟️ Azteca — the most iconic WC stadium ever\n📊 *Prediction:* Mexico 2-0 South Africa\n\n💪 *Mexico:* Home crowd, pace on wings, WC experience\n⚠️ *South Africa:* Organized defense, nothing to lose\n\n🎯 Mexico to score first — 78% probability",
    },
    "🇧🇷 Brazil vs 🇲🇦 Morocco": {
        "ar": "🔮 *تحليل المباراة*\n\n📊 *التوقع:* البرازيل 2-1 المغرب\n\n💪 *البرازيل:* فينيسيوس في أفضل حالاته، جيل ذهبي\n⚠️ *المغرب:* نصف نهائي 2022، دفاع عالمي المستوى\n\n🎯 مباراة مفتوحة — أهداف في الشوطين",
        "en": "🔮 *Match Analysis*\n\n📊 *Prediction:* Brazil 2-1 Morocco\n\n💪 *Brazil:* Vinicius at his best, golden generation\n⚠️ *Morocco:* 2022 semifinalists, world-class defense\n\n🎯 Open game — goals expected in both halves",
    },
    "🇫🇷 France vs 🇸🇳 Senegal": {
        "ar": "🔮 *تحليل المباراة*\n\n📊 *التوقع:* فرنسا 2-1 السنغال\n\n💪 *فرنسا:* مبابي + جريزمان = أخطر ثنائي في العالم\n⚠️ *السنغال:* مانيه، روح قتالية، هزموا فرنسا من قبل!\n\n🎯 فرنسا المرشحة للقب — لكن مباراة صعبة",
        "en": "🔮 *Match Analysis*\n\n📊 *Prediction:* France 2-1 Senegal\n\n💪 *France:* Mbappe + Griezmann = world's most dangerous duo\n⚠️ *Senegal:* Mane, fighting spirit, beat France before!\n\n🎯 France are title favorites — but this will be tough",
    },
    "🇦🇷 Argentina vs 🇦🇹 Austria": {
        "ar": "🔮 *تحليل المباراة*\n\n📊 *التوقع:* الأرجنتين 3-0 النمسا\n\n💪 *الأرجنتين:* ميسي يريد التاريخ، كيمياء الفريق استثنائية\n⚠️ *النمسا:* منظمون ومجتهدون لكن الفجوة كبيرة\n\n🎯 ميسي جائع للتاريخ — توقع عرضاً استثنائياً",
        "en": "🔮 *Match Analysis*\n\n📊 *Prediction:* Argentina 3-0 Austria\n\n💪 *Argentina:* Messi wants history, exceptional team chemistry\n⚠️ *Austria:* Organized and hardworking but the gap is huge\n\n🎯 Messi is hungry for history — expect a masterclass",
    },
    "🇩🇿 Algeria vs 🇯🇴 Jordan": {
        "ar": "🔮 *تحليل المباراة*\n\n📊 *التوقع:* الجزائر 2-0 الأردن\n\n💪 *الجزائر:* محرز، خبرة كبيرة، الكرات الثابتة فتاكة\n⚠️ *الأردن:* أول مشاركة، روح قتالية، لا يخسران شيئاً!\n\n🎯 الجزائر بالنقاط — الأردن سيكافح بشرف",
        "en": "🔮 *Match Analysis*\n\n📊 *Prediction:* Algeria 2-0 Jordan\n\n💪 *Algeria:* Mahrez, big experience, deadly set pieces\n⚠️ *Jordan:* First WC ever, fighting spirit, nothing to lose!\n\n🎯 Algeria on points — Jordan will fight with honor",
    },
    "🇸🇦 Saudi Arabia vs 🇮🇷 Iran": {
        "ar": "🔮 *تحليل المباراة*\n\n📊 *التوقع:* السعودية 1-1 إيران\n\n💪 *السعودية:* ذكريات 2022 تمنح ثقة هائلة\n⚠️ *إيران:* مباراة مشحونة، اللاعبون يتجاوزون مستواهم\n\n🎯 مباراة نارية — توقع إيقاعاً عالياً",
        "en": "🔮 *Match Analysis*\n\n📊 *Prediction:* Saudi Arabia 1-1 Iran\n\n💪 *Saudi Arabia:* 2022 memories bring massive confidence\n⚠️ *Iran:* Emotionally charged — players overperform here\n\n🎯 Fiery clash — expect high intensity throughout",
    },
}

# ═══════════════════════════════════════════════════════════════════
#  ARAB TEAMS TEXT
# ═══════════════════════════════════════════════════════════════════

ARAB_TEAMS = {
    "ar": (
        "🌙 *المنتخبات العربية — كأس العالم 2026*\n\n"
        "🇸🇦 *السعودية* — المجموعة E\n إسبانيا 🇪🇸 | بلجيكا 🇧🇪 | إيران 🇮🇷 | ⭐ أبطال 2022 ضد الأرجنتين!\n\n"
        "🇲🇦 *المغرب* — المجموعة G\n البرازيل 🇧🇷 | هايتي 🇭🇹 | أستراليا 🇦🇺 | ⭐ نصف نهائي 2022!\n\n"
        "🇩🇿 *الجزائر* — المجموعة I\n الأرجنتين 🇦🇷 | النمسا 🇦🇹 | الأردن 🇯🇴 | ⭐ مجموعة نار!\n\n"
        "🇹🇳 *تونس* — المجموعة C\n أمريكا 🇺🇸 | باراغواي 🇵🇾 | السويد 🇸🇪 | ⭐ يسعى للدور الثاني!\n\n"
        "🇮🇶 *العراق* — المجموعة F\n فرنسا 🇫🇷 | السنغال 🇸🇳 | النرويج 🇳🇴 | ⭐ عودة تاريخية!\n\n"
        "🇯🇴 *الأردن* — المجموعة I\n الأرجنتين 🇦🇷 | النمسا 🇦🇹 | الجزائر 🇩🇿 | ⭐ أول مشاركة في التاريخ!\n\n"
        "🇶🇦 *قطر* — المجموعة B\n كندا 🇨🇦 | البوسنة 🇧🇦 | سويسرا 🇨🇭 | ⭐ يريد إثبات الذات!"
    ),
    "en": (
        "🌙 *Arab Teams — World Cup 2026*\n\n"
        "🇸🇦 *Saudi Arabia* — Group E\n Spain 🇪🇸 | Belgium 🇧🇪 | Iran 🇮🇷 | ⭐ Heroes of the 2022 Argentina shock!\n\n"
        "🇲🇦 *Morocco* — Group G\n Brazil 🇧🇷 | Haiti 🇭🇹 | Australia 🇦🇺 | ⭐ 2022 semifinalists!\n\n"
        "🇩🇿 *Algeria* — Group I\n Argentina 🇦🇷 | Austria 🇦🇹 | Jordan 🇯🇴 | ⭐ Group of Death!\n\n"
        "🇹🇳 *Tunisia* — Group C\n USA 🇺🇸 | Paraguay 🇵🇾 | Sweden 🇸🇪 | ⭐ Targeting Round of 32!\n\n"
        "🇮🇶 *Iraq* — Group F\n France 🇫🇷 | Senegal 🇸🇳 | Norway 🇳🇴 | ⭐ Historic return!\n\n"
        "🇯🇴 *Jordan* — Group I\n Argentina 🇦🇷 | Austria 🇦🇹 | Algeria 🇩🇿 | ⭐ First ever World Cup!\n\n"
        "🇶🇦 *Qatar* — Group B\n Canada 🇨🇦 | Bosnia 🇧🇦 | Switzerland 🇨🇭 | ⭐ Proving a point!"
    ),
}

STATS_TEXT = {
    "titles": {
        "ar": "🏆 *أكثر المنتخبات تتويجاً*\n\n🥇 🇧🇷 البرازيل — 5\n🥈 🇩🇪 ألمانيا — 4\n🥈 🇮🇹 إيطاليا — 4\n🥉 🇦🇷 الأرجنتين — 3\n4️⃣ 🇫🇷 فرنسا — 2\n4️⃣ 🇺🇾 أوروغواي — 2\n6️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 إنجلترا — 1\n6️⃣ 🇪🇸 إسبانيا — 1",
        "en": "🏆 *Most World Cup Titles*\n\n🥇 🇧🇷 Brazil — 5\n🥈 🇩🇪 Germany — 4\n🥈 🇮🇹 Italy — 4\n🥉 🇦🇷 Argentina — 3\n4️⃣ 🇫🇷 France — 2\n4️⃣ 🇺🇾 Uruguay — 2\n6️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England — 1\n6️⃣ 🇪🇸 Spain — 1",
    },
    "scorers": {
        "ar": "⚽ *هدافو كأس العالم على مر التاريخ*\n\n🥇 🇩🇪 كلوزه — 16 هدف\n🥈 🇧🇷 رونالدو — 15\n🥉 🇩🇪 غيرد مولر — 14\n4️⃣ 🇫🇷 فونتين — 13\n4️⃣ 🇦🇷 ميسي — 13 ⭐\n6️⃣ 🇧🇷 بيليه — 12\n6️⃣ 🇫🇷 مبابي — 12 🔥\n\n🎯 هل سيتصدر مبابي القائمة في 2026؟",
        "en": "⚽ *All-Time World Cup Top Scorers*\n\n🥇 🇩🇪 Klose — 16\n🥈 🇧🇷 Ronaldo — 15\n🥉 🇩🇪 Müller — 14\n4️⃣ 🇫🇷 Fontaine — 13\n4️⃣ 🇦🇷 Messi — 13 ⭐\n6️⃣ 🇧🇷 Pelé — 12\n6️⃣ 🇫🇷 Mbappé — 12 🔥\n\n🎯 Will Mbappé top the list in 2026?",
    },
    "favorites": {
        "ar": "🎯 *المرشحون للقب — 2026*\n\n1️⃣ 🇫🇷 فرنسا — 18%\n2️⃣ 🇧🇷 البرازيل — 15%\n3️⃣ 🇦🇷 الأرجنتين — 14%\n4️⃣ 🇩🇪 ألمانيا — 12%\n5️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 إنجلترا — 11%\n6️⃣ 🇪🇸 إسبانيا — 10%\n7️⃣ 🇵🇹 البرتغال — 8%",
        "en": "🎯 *Title Favorites — 2026*\n\n1️⃣ 🇫🇷 France — 18%\n2️⃣ 🇧🇷 Brazil — 15%\n3️⃣ 🇦🇷 Argentina — 14%\n4️⃣ 🇩🇪 Germany — 12%\n5️⃣ 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England — 11%\n6️⃣ 🇪🇸 Spain — 10%\n7️⃣ 🇵🇹 Portugal — 8%",
    },
    "wc2026": {
        "ar": "📊 *إحصائيات كأس العالم 2026*\n\n🌍 3 دول مضيفة\n⚽ 48 منتخباً\n🎮 104 مباراة\n🏟️ 16 ملعباً\n📅 39 يوماً\n👥 5+ مليون مشجع\n💰 1 مليار دولار جوائز\n📺 5+ مليار مشاهد",
        "en": "📊 *World Cup 2026 Key Stats*\n\n🌍 3 host nations\n⚽ 48 teams\n🎮 104 matches\n🏟️ 16 stadiums\n📅 39 days\n👥 5+ million fans\n💰 $1 billion prize fund\n📺 5+ billion viewers",
    },
}

# ═══════════════════════════════════════════════════════════════════
#  HANDLERS
# ═══════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = register_user(user)
    lang = data.get("lang", "ar")
    name = user.first_name or "Champion"
    wc_start = date(2026, 6, 11)
    days_left = max((wc_start - date.today()).days, 0)
    total_users = get_subscriber_count()

    if lang == "ar":
        countdown = f"⏳ *{days_left} يوم على الانطلاق!*" if days_left > 0 else "🔴 *البطولة انطلقت!*"
        text = (
            f"🌍⚽ *أهلاً {name}!*\n\n"
            f"مرحباً في *بوت كأس العالم 2026 الاحترافي*\n\n"
            f"🏆 11 يونيو — 19 يوليو 2026\n"
            f"🌎 أمريكا 🇺🇸 | المكسيك 🇲🇽 | كندا 🇨🇦\n"
            f"⭐ 48 فريق | 104 مباراة | 16 ملعب\n\n"
            f"{countdown}\n"
            f"👥 {total_users} مشترك معنا الآن\n\n"
            f"اختر ما تريد 👇"
        )
    else:
        countdown = f"⏳ *{days_left} days to kickoff!*" if days_left > 0 else "🔴 *Tournament is LIVE!*"
        text = (
            f"🌍⚽ *Welcome {name}!*\n\n"
            f"*World Cup 2026 Pro Bot*\n\n"
            f"🏆 June 11 — July 19, 2026\n"
            f"🌎 USA 🇺🇸 | Mexico 🇲🇽 | Canada 🇨🇦\n"
            f"⭐ 48 teams | 104 matches | 16 stadiums\n\n"
            f"{countdown}\n"
            f"👥 {total_users} subscribers with us\n\n"
            f"Choose what you need 👇"
        )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard(lang))


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        await update.message.reply_text("⛔ غير مصرح | Unauthorized")
        return
    count = get_subscriber_count()
    db = load_db()
    recent = sorted(db["users"].values(), key=lambda x: x.get("joined",""), reverse=True)[:5]
    recent_text = "\n".join([f"• {u['name']} (@{u['username']}) — {u['joined']}" for u in recent])
    text = (
        f"🛠 *لوحة الإدارة*\n\n"
        f"👥 إجمالي المشتركين: *{count}*\n\n"
        f"🆕 *آخر 5 مشتركين:*\n{recent_text}\n\n"
        f"📢 للإرسال الجماعي: `/broadcast رسالتك هنا`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        await update.message.reply_text("⛔ غير مصرح | Unauthorized")
        return
    if not context.args:
        await update.message.reply_text("⚠️ استخدم: `/broadcast رسالتك`", parse_mode="Markdown")
        return
    message = " ".join(context.args)
    subscribers = get_all_subscribers()
    sent, failed = 0, 0
    status_msg = await update.message.reply_text(f"📢 جاري الإرسال لـ {len(subscribers)} مشترك...")
    for sub in subscribers:
        try:
            await context.bot.send_message(
                chat_id=sub["id"],
                text=f"📢 *إشعار من بوت كأس العالم 2026*\n\n{message}",
                parse_mode="Markdown"
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await status_msg.edit_text(f"✅ أُرسل لـ {sent} مشترك\n❌ فشل: {failed}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data
    lang = get_lang(uid)

    # ── Language switch ──
    if data == "lang_en":
        update_user_lang(uid, "en")
        user_lang[uid] = "en"
        await query.edit_message_text("🌐 *Switched to English!*\nChoose what you need 👇",
                                      parse_mode="Markdown", reply_markup=main_keyboard("en"))
        return
    if data == "lang_ar":
        update_user_lang(uid, "ar")
        user_lang[uid] = "ar"
        await query.edit_message_text("🌐 *تم التبديل للعربية!*\nاختر ما تريد 👇",
                                      parse_mode="Markdown", reply_markup=main_keyboard("ar"))
        return

    # ── Today ──
    if data == "today":
        text = build_matches_text(today_str(), lang)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # ── Tomorrow ──
    elif data == "tomorrow":
        tmr = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        text = build_matches_text(tmr, lang)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # ── Live Matches ──
    elif data == "live":
        await query.edit_message_text("🔴 *جاري جلب المباريات المباشرة...*" if lang == "ar" else "🔴 *Fetching live matches...*",
                                       parse_mode="Markdown")
        live = await fetch_live_matches()
        if live:
            lines = ["🔴 *مباريات الآن | LIVE Now*\n"]
            for m in live:
                lines.append(
                    f"⚡ *{m['home']} {m['home_goal']} — {m['away_goal']} {m['away']}*\n"
                    f"⏱️ {m['minute']}' | {m['status']}\n🏟️ {m['venue']}\n"
                )
            text = "\n".join(lines)
        else:
            text = ("🔴 *لا مباريات مباشرة الآن*\n\nراجع جدول المباريات 👇" if lang == "ar"
                    else "🔴 *No live matches right now*\n\nCheck the schedule below 👇")
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # ── Predictions menu ──
    elif data == "predictions":
        title = "🔮 *اختر المباراة للتحليل:*" if lang == "ar" else "🔮 *Choose a match to analyze:*"
        btns = [[InlineKeyboardButton(m, callback_data=f"pred_{i}")] for i, m in enumerate(PREDICTIONS)]
        btns.append([InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")])
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("pred_"):
        idx = int(data[5:])
        keys = list(PREDICTIONS.keys())
        if idx < len(keys):
            match_name = keys[idx]
            pred = PREDICTIONS[match_name]
            text = f"🔮 *{match_name}*\n\n{pred.get(lang, pred['ar'])}"
        else:
            text = "⚠️ غير متاح"
        await query.edit_message_text(text, parse_mode="Markdown",
                                       reply_markup=back_btn("predictions"))

    # ── Tactical Analysis ──
    elif data == "tactical":
        title = "🧠 *اختر المنتخب للتحليل التكتيكي:*" if lang == "ar" else "🧠 *Choose a team for tactical analysis:*"
        teams = list(TACTICAL_ANALYSIS.keys())
        btns = [[InlineKeyboardButton(t, callback_data=f"tac_{i}")] for i, t in enumerate(teams)]
        btns.append([InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")])
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("tac_"):
        idx = int(data[4:])
        teams = list(TACTICAL_ANALYSIS.keys())
        if idx < len(teams):
            team = teams[idx]
            analysis = TACTICAL_ANALYSIS[team]
            text = analysis.get(lang, analysis["ar"])
        else:
            text = "⚠️ غير متاح"
        await query.edit_message_text(text, parse_mode="Markdown",
                                       reply_markup=back_btn("tactical"))

    # ── Groups ──
    elif data == "groups":
        title = "🏆 *مجموعات كأس العالم 2026*\n\n" if lang == "ar" else "🏆 *World Cup 2026 Groups*\n\n"
        text = title
        for grp, teams in GROUPS.items():
            text += f"*━━ Group {grp} ━━*\n"
            for t in teams:
                text += f"  • {t}\n"
            text += "\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # ── Arab Teams ──
    elif data == "arab_teams":
        text = ARAB_TEAMS.get(lang, ARAB_TEAMS["ar"])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # ── Stats ──
    elif data == "stats":
        if lang == "ar":
            title = "📊 *اختر نوع الإحصائية:*"
            btns = [
                [InlineKeyboardButton("🏆 أكثر المنتخبات تتويجاً", callback_data="st_titles")],
                [InlineKeyboardButton("⚽ هدافو التاريخ", callback_data="st_scorers")],
                [InlineKeyboardButton("🎯 المرشحون للقب", callback_data="st_favorites")],
                [InlineKeyboardButton("📈 أرقام 2026", callback_data="st_wc2026")],
                [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")],
            ]
        else:
            title = "📊 *Choose a stat category:*"
            btns = [
                [InlineKeyboardButton("🏆 Most Titles", callback_data="st_titles")],
                [InlineKeyboardButton("⚽ All-Time Top Scorers", callback_data="st_scorers")],
                [InlineKeyboardButton("🎯 Title Favorites", callback_data="st_favorites")],
                [InlineKeyboardButton("📈 2026 Stats", callback_data="st_wc2026")],
                [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")],
            ]
        await query.edit_message_text(title, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("st_"):
        key = data[3:]
        stat = STATS_TEXT.get(key, {})
        text = stat.get(lang, stat.get("ar", "⚠️ غير متاح"))
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("stats"))

    # ── Fun Fact ──
    elif data == "fact":
        fact = random.choice(FUN_FACTS)
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 أخرى | Another", callback_data="fact")],
            [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")]
        ])
        await query.edit_message_text(f"🌟 *هل تعلم؟ | Did You Know?*\n\n{fact}",
                                       parse_mode="Markdown", reply_markup=btns)

    # ── Back ──
    elif data == "back":
        name = query.from_user.first_name or "Champion"
        wc_start = date(2026, 6, 11)
        days_left = max((wc_start - date.today()).days, 0)
        total = get_subscriber_count()
        if lang == "ar":
            countdown = f"⏳ {days_left} يوم على الانطلاق!" if days_left > 0 else "🔴 البطولة انطلقت!"
            text = f"⚽ *القائمة الرئيسية*\n{countdown}\n👥 {total} مشترك\n\nاختر يا {name} 👇"
        else:
            countdown = f"⏳ {days_left} days to kickoff!" if days_left > 0 else "🔴 Tournament is LIVE!"
            text = f"⚽ *Main Menu*\n{countdown}\n👥 {total} subscribers\n\nChoose, {name} 👇"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard(lang))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid)
    text = "⚽ استخدم الأزرار! أو أرسل /start" if lang == "ar" else "⚽ Use the buttons! Or send /start"
    await update.message.reply_text(text, reply_markup=main_keyboard(lang))


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("⚽ World Cup 2026 Pro Bot v3.0 is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
