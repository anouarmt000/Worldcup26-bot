#!/usr/bin/env python3
"""
⚽ World Cup 2026 Pro Bot — Version 8.5 PURE STATIC EDITION
✅ بدون أي اعتماد على API خارجي — كل البيانات ثابتة أو يديرها الأدمن
✅ 🔮 ميزة جديدة: محاكي المباريات (Match Simulator) — تقارير عشوائية فورية
✅ 🏆 الترتيب + ⚽ الهدافون: روابط غوغل مباشرة (محدّثة دائماً)
✅ 📊 النتائج: يُضيفها الأدمن يدوياً عبر /result
✅ نظام مشتركين كامل + بث جماعي + ملخص يومي
"""

import os, logging, random, json, asyncio
from datetime import date, timedelta, datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN    = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

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
#  HELPERS
# ═══════════════════════════════════════════════════════

def today_str():
    return date.today().strftime("%Y-%m-%d")

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
#  RESULTS — يُديرها الأدمن يدوياً عبر /result (بدون أي API)
# ═══════════════════════════════════════════════════════

STATIC_RESULTS = [
    # الشكل: date, home, away, hg, ag, group, done
    # ── يُضاف هنا تلقائياً عبر أمر /result بعد كل مباراة ──
]

async def get_recent_results() -> list:
    """نتائج ثابتة 100% — يضيفها الأدمن عبر /result، بدون أي استدعاء خارجي"""
    results = []
    for r in STATIC_RESULTS:
        if r.get("done"):
            results.append({
                "date": r["date"],
                "home": r["home"],
                "away": r["away"],
                "home_goal": r["hg"],
                "away_goal": r["ag"],
                "group": r["group"],
            })
    results.sort(key=lambda x: x["date"], reverse=True)
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

# ═══════════════════════════════════════════════════════
#  🔮 محاكي المباريات — Match Simulator (Pure Random, No API)
# ═══════════════════════════════════════════════════════

SIM_TEAMS = [
    {"flag":"🇲🇦","ar":"المغرب","en":"Morocco","p_ar":["حكيمي","إبراهيم دياز","ياسين بونو","أمرابط"],"p_en":["Hakimi","Díaz","yassin bono","Amrabat"]},
    {"flag":"🇦🇷","ar":"الأرجنتين","en":"Argentina","p_ar":["ميسي","خوليان ألفاريز","ماك أليستر","دي باول"],"p_en":["Messi","Julián Álvarez","Mac Allister","De Paul"]},
    {"flag":"🇧🇷","ar":"البرازيل","en":"Brazil","p_ar":["فينيسيوس","رودريغو","أندريك","رافينيا"],"p_en":["Vinícius","Rodrygo","Endrick","Raphinha"]},
    {"flag":"🇫🇷","ar":"فرنسا","en":"France","p_ar":["مبابي","جريزمان","تشواميني","ديمبيلي"],"p_en":["Mbappé","Griezmann","Tchouaméni","Dembélé"]},
    {"flag":"🇪🇸","ar":"إسبانيا","en":"Spain","p_ar":["لامين يامال","رودري","بيدري","أوياربيدي"],"p_en":["Lamine Yamal","Rodri","Pedri","Oyarzabal"]},
    {"flag":"🇵🇹","ar":"البرتغال","en":"Portugal","p_ar":["رونالدو","برناردو سيلفا","رافاييل لياو","روبن نيفيش"],"p_en":["Ronaldo","Bernardo Silva","Rafael Leão","Rúben Neves"]},
    {"flag":"🇩🇪","ar":"ألمانيا","en":"Germany","p_ar":["موسيالا","فيرتز","هافرتز","فولكروغ"],"p_en":["Musiala","Wirtz","Havertz","Füllkrug"]},
    {"flag":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","ar":"إنجلترا","en":"England","p_ar":["بيلينغهام","ساكا","فودن","كين"],"p_en":["Bellingham","Saka","Foden","Kane"]},
]

def build_simulator_text(lang="ar") -> str:
    """تقرير مباراة تخيلي 100% — فريقان عشوائيان من كبار المنتخبات."""
    t1, t2 = random.sample(SIM_TEAMS, 2)
    g1, g2 = random.randint(0, 4), random.randint(0, 4)
    poss1 = random.randint(38, 62)
    poss2 = 100 - poss1
    pk = "p_ar" if lang == "ar" else "p_en"
    sep = "، " if lang == "ar" else ", "
    s1 = sep.join(random.choice(t1[pk]) for _ in range(g1)) if g1 else "—"
    s2 = sep.join(random.choice(t2[pk]) for _ in range(g2)) if g2 else "—"
    motm_team = t1 if g1 >= g2 else t2
    motm = random.choice(motm_team[pk])

    if lang == "ar":
        return (
            f"🔮 *محاكي المباريات*\n{'━'*22}\n\n"
            f"🆚 *{t1['flag']} {t1['ar']}  —  {t2['flag']} {t2['ar']}*\n\n"
            f"📊 *النتيجة النهائية:* {g1} — {g2}\n\n"
            f"⚽ *هدافو {t1['ar']}:* {s1}\n"
            f"⚽ *هدافو {t2['ar']}:* {s2}\n\n"
            f"⭐ *رجل المباراة:* {motm}\n"
            f"📈 *الاستحواذ:* {t1['ar']} {poss1}% — {poss2}% {t2['ar']}\n\n"
            f"_تقرير تخيلي عشوائي للترفيه فقط ⚽🔮_"
        )
    return (
        f"🔮 *Match Simulator*\n{'━'*22}\n\n"
        f"🆚 *{t1['flag']} {t1['en']}  —  {t2['flag']} {t2['en']}*\n\n"
        f"📊 *Final Score:* {g1} — {g2}\n\n"
        f"⚽ *{t1['en']} Scorers:* {s1}\n"
        f"⚽ *{t2['en']} Scorers:* {s2}\n\n"
        f"⭐ *Man of the Match:* {motm}\n"
        f"📈 *Possession:* {t1['en']} {poss1}% — {poss2}% {t2['en']}\n\n"
        f"_Random simulated report, for fun only ⚽🔮_"
    )

# ═══════════════════════════════════════════════════════
#  TACTICAL ANALYSIS
# ═══════════════════════════════════════════════════════

TACTICAL_ANALYSIS = {
    "🇲🇦 Morocco": {
        "ar": "🧠 *المغرب 🇲🇦*\n📐 4-3-3 | 👨‍💼 محمد وهبي\n🎯 الأسلوب: ضغط عالٍ منظم + خروج سريع من الخلف\n\n🔑 *النجوم:*\n• أشرف حكيمي (PSG) — القائد، أفضل لاعب أفريقي 2025\n• إبراهيم دياز (ريال مدريد) — 5 أهداف في 5 مباريات AFCON!\n• يوسف النصيري — قاتل مرمى البرتغال 2022\n• ياسين بونو (الهلال) — حارس عالمي\n\n⚙️ *القوة:* ضغط جماعي + انتقالات سريعة + كرات ثابتة\n⚠️ *الضعف:* مدرب جديد = غموض تكتيكي",
        "en": "🧠 *Morocco 🇲🇦*\n📐 4-3-3 | 👨‍💼 Mohamed Ouahbi\n🎯 Style: organized high press + quick build-up from the back\n\n🔑 *Stars:*\n• Achraf Hakimi (PSG) — captain, Africa best 2025\n• Brahim Díaz (Real Madrid) — 5 goals in 5 AFCON games!\n• Youssef En-Nesyri — ended Portugal 2022\n• Yassine Bono (Al-Hilal) — world-class goalkeeper\n\n⚙️ *Strength:* collective press + fast transitions + set pieces\n⚠️ *Weakness:* new coach = tactical uncertainty",
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
        "ar": "🧠 *فرنسا 🇫🇷*\n📐 4-2-3-1 | 👨‍💼 ديشامب\n🎯 الأسلوب: دفاع متكتل + ارتدادات سريعة عبر مبابي\n\n🔑 *النجوم:*\n• مبابي — 12 هدفاً في المونديال، الأخطر في العالم\n• جريزمان — رؤية وإبداع استثنائيان\n• تشيامني — رئة الوسط\n• ديمبيلي — مراوغة وتمريرات قاتلة\n\n⚙️ *القوة:* دفاع عميق + انتقال متفجر عبر مبابي\n⚠️ *الضعف:* اعتماد زائد على مبابي",
        "en": "🧠 *France 🇫🇷*\n📐 4-2-3-1 | 👨‍💼 Deschamps\n🎯 Style: compact block + fast counters through Mbappé\n\n🔑 *Stars:*\n• Mbappé — 12 WC goals, world's most dangerous\n• Griezmann — exceptional vision and creativity\n• Tchouaméni — midfield engine\n• Dembélé — dribbling and killer passes\n\n⚙️ *Strength:* deep block + explosive counter through Mbappé\n⚠️ *Weakness:* over-reliance on Mbappé",
    },
    "🇦🇷 Argentina": {
        "ar": "🧠 *الأرجنتين 🇦🇷*\n📐 4-4-2 | 👨‍💼 سكالوني\n🎯 الأسلوب: استحواذ منظم + ضغط جماعي (Scaloneta)\n\n🔑 *النجوم:*\n• ميسي (38 سنة!) — رسمياً في المونديال\n• خوليان ألفاريز — حركة بلا توقف\n• ماك أليستر (ليفربول) — عقل الوسط\n• دي باول (إنتر ميامي) — رئة الفريق\n\n⚙️ *القوة:* Scaloni Press + ميسي بحرية مطلقة\n⚠️ *الضعف:* ميسي في الـ38 — هل لا يزال في قمته؟",
        "en": "🧠 *Argentina 🇦🇷*\n📐 4-4-2 | 👨‍💼 Scaloni\n🎯 Style: structured possession + collective press (Scaloneta)\n\n🔑 *Stars:*\n• Messi (38!) — officially in the squad\n• Julián Álvarez — relentless movement\n• Mac Allister (Liverpool) — midfield brain\n• De Paul (Inter Miami) — the engine\n\n⚙️ *Strength:* relentless Scaloni Press + Messi total freedom\n⚠️ *Weakness:* Messi at 38 — still at peak level?",
    },
    "🇧🇷 Brazil": {
        "ar": "🧠 *البرازيل 🇧🇷*\n📐 4-2-3-1 | 👨‍💼 دوريفال جونيور\n🎯 الأسلوب: كرة هجومية تقنية + جناحان خطيران\n\n🔑 *النجوم:*\n• فينيسيوس جونيور — أفضل لاعب في العالم 2024\n• روديغو — أهداف في المباريات الكبيرة\n• أندريك — 18 سنة، المستقبل الآن!\n• كاسيميرو — العمق الدفاعي\n\n⚙️ *القوة:* ارتكاز + انتقالات متفجرة\n⚠️ *الضعف:* دفاع ضعيف أمام الكرات العرضية",
        "en": "🧠 *Brazil 🇧🇷*\n📐 4-2-3-1 | 👨‍💼 Dorival Júnior\n🎯 Style: technical attacking football + lethal wingers\n\n🔑 *Stars:*\n• Vinícius Jr — Best Player in the World 2024\n• Rodrygo — big-game goals\n• Endrick — 18 years old, the future is NOW!\n• Casemiro — defensive cover\n\n⚙️ *Strength:* possession + explosive transitions\n⚠️ *Weakness:* defense weak to aerial balls",
    },
    "🇪🇸 Spain": {
        "ar": "🧠 *إسبانيا 🇪🇸*\n📐 4-3-3 | 👨‍💼 لويس دي لا فوينتي\n🎯 الأسلوب: تيكي تاكا حديث + استحواذ خانق\n\n🔑 *النجوم:*\n• لامين يامال (برشلونة) — أصغر نجم عالمي، مهارات استثنائية\n• رودري (مان سيتي) — أفضل لاعب أوروبا 2024\n• بيدري (برشلونة) — تمرير ورؤية\n• أوياربيدي (ريال سوسيداد) — حسم أمام المرمى\n\n⚙️ *القوة:* استحواذ خانق + جناحان رهيبان\n⚠️ *الضعف:* عمق هجومي محدود + مجموعة H صعبة",
        "en": "🧠 *Spain 🇪🇸*\n📐 4-3-3 | 👨‍💼 Luis de la Fuente\n🎯 Style: modern tiki-taka + suffocating possession\n\n🔑 *Stars:*\n• Lamine Yamal (Barcelona) — youngest global star, elite skills\n• Rodri (Man City) — Europe's Player of 2024\n• Pedri (Barcelona) — passing and vision\n• Oyarzabal (Real Sociedad) — clinical finisher\n\n⚙️ *Strength:* suffocating possession + lethal wingers\n⚠️ *Weakness:* limited attacking depth + tough Group H",
    },
    "🇵🇹 Portugal": {
        "ar": "🧠 *البرتغال 🇵🇹*\n📐 4-3-3 | 👨‍💼 روبرتو مارتينيز\n🎯 الأسلوب: هجوم سريع عبر الأطراف + ضغط مرتفع\n\n🔑 *النجوم:*\n• كريستيانو رونالدو (41) — 6 مونديالات، أسطورة لا تشيخ\n• برناردو سيلفا (مان سيتي) — ذكاء تكتيكي\n• رافاييل لياو (ميلان) — سرعة وحسم\n• روبن نيفيش — استقرار الوسط\n\n⚙️ *القوة:* خبرة كبيرة + توازن هجومي\n⚠️ *الضعف:* اعتماد على عمر رونالدو + مجموعة K",
        "en": "🧠 *Portugal 🇵🇹*\n📐 4-3-3 | 👨‍💼 Roberto Martínez\n🎯 Style: fast wide attacks + high press\n\n🔑 *Stars:*\n• Cristiano Ronaldo (41) — 6th World Cup, ageless legend\n• Bernardo Silva (Man City) — tactical intelligence\n• Rafael Leão (Milan) — pace and finishing\n• Rúben Neves — midfield stability\n\n⚙️ *Strength:* huge experience + attacking balance\n⚠️ *Weakness:* reliance on Ronaldo's age + Group K",
    },
    "🇩🇪 Germany": {
        "ar": "🧠 *ألمانيا 🇩🇪*\n📐 4-2-3-1 | 👨‍💼 يوليان ناغلسمان\n🎯 الأسلوب: ضغط مرتفع + انتقال سريع للهجوم\n\n🔑 *النجوم:*\n• جمال موسيالا (بايرن) — إبداع وتمرير قاتل\n• فلوريان فيرتز (ليفركوزن) — صانع ألعاب العام\n• كاي هافرتز (أرسنال) — تنوع هجومي\n• نيكلاس فولكروغ — هداف الفرص الصعبة\n\n⚙️ *القوة:* عمق الصفوف + لياقة عالية\n⚠️ *الضعف:* دفاع متوسط العمر + مجموعة E مع ساحل العاج",
        "en": "🧠 *Germany 🇩🇪*\n📐 4-2-3-1 | 👨‍💼 Julian Nagelsmann\n🎯 Style: high press + rapid transitions\n\n🔑 *Stars:*\n• Jamal Musiala (Bayern) — creativity and killer passes\n• Florian Wirtz (Leverkusen) — playmaker of the year\n• Kai Havertz (Arsenal) — attacking versatility\n• Niclas Füllkrug — clinical poacher\n\n⚙️ *Strength:* squad depth + high fitness levels\n⚠️ *Weakness:* aging defense + Group E with Ivory Coast",
    },
    "🇮🇹 Italy": {
        "ar": "🧠 *إيطاليا 🇮🇹*\n📐 3-5-2 | 👨‍💼 لوتشيانو سباليتي\n🎯 الأسلوب: تنظيم دفاعي صلب + ارتداد سريع\n\n🔑 *النجوم:*\n• نيكولو بارينيا — صانع ألعاب الجيل الجديد\n• فيديريكو كييزا — سرعة وحسم\n• جانلويجي دوناروما — حارس عالمي\n• ساندرو توناللي — قوة الوسط\n\n⚙️ *القوة:* تنظيم دفاعي + خبرة البطولات الكبرى\n⚠️ *الضعف:* قلة الفعالية الهجومية",
        "en": "🧠 *Italy 🇮🇹*\n📐 3-5-2 | 👨‍💼 Luciano Spalletti\n🎯 Style: solid defensive structure + fast counters\n\n🔑 *Stars:*\n• Nicolò Barella — next-gen playmaker\n• Federico Chiesa — pace and finishing\n• Gianluigi Donnarumma — world-class goalkeeper\n• Sandro Tonali — midfield power\n\n⚙️ *Strength:* defensive organization + big-tournament experience\n⚠️ *Weakness:* lack of attacking efficiency",
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
    "fastest_goal": {
        "ar": "⏱️ *أسرع هدف في تاريخ المونديال*\n\n🥇 🇹🇷 هاكان شكر — 10.8 ثانية!\n📅 أمام كوريا الجنوبية 🇰🇷 — 2002\n🥈 🇸🇮 فالتر زينغا (خصم) — 14.8 ثانية، إيطاليا 1990\n🥉 🇪🇨 برنال — 23.8 ثانية، 2006",
        "en": "⏱️ *Fastest Goals in WC History*\n\n🥇 🇹🇷 Hakan Şükür — 10.8 sec!\n📅 vs South Korea 🇰🇷 — 2002\n🥈 1990 — 14.8 sec (Italy opener)\n🥉 🇪🇨 Bernal — 23.8 sec, 2006",
    },
    "top_assists": {
        "ar": "🎯 *الأكثر صناعة للأهداف*\n\n🥇 🇩🇪 توماس مولر — أعلى مساهمات تهديفية (أهداف+تمريرات)\n🥈 🇧🇷 بيليه — صانع كلاسيكي لعصره\n🥉 🇩🇪 مسعود أوزيل — 2010-2014\n⭐ مبابي وغريزمان يتنافسان على الصدارة 2026!",
        "en": "🎯 *Most Goal Contributions*\n\n🥇 🇩🇪 Thomas Müller — most combined goals+assists ever\n🥈 🇧🇷 Pelé — classic playmaker of his era\n🥉 🇩🇪 Mesut Özil — 2010-2014\n⭐ Mbappé & Griezmann chase the top spot in 2026!",
    },
    "stadiums_2026": {
        "ar": "🏟️ *أكبر ملاعب 2026*\n\n🥇 إستاد أزتيكا (مكسيكو سيتي) — ~87,000\n🥈 ميتلايف (نيويورك/نيوجيرسي) — ~82,500 🏆 يحتضن النهائي\n🥉 إيه تي آند تي (دالاس) — ~80,000\n4️⃣ جيلت (فيلادلفيا) — ~69,000",
        "en": "🏟️ *Biggest Stadiums 2026*\n\n🥇 Estadio Azteca (Mexico City) — ~87,000\n🥈 MetLife Stadium (NY/NJ) — ~82,500 🏆 hosts the Final\n🥉 AT&T Stadium (Dallas) — ~80,000\n4️⃣ Lincoln Financial Field (Philly) — ~69,000",
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
    "⏱️ أسرع هدف في التاريخ: هاكان شكر سجّل في 10.8 ثانية فقط (2002)!\n⏱️ Fastest goal ever: Hakan Şükür scored in just 10.8 seconds (2002)!",
    "🌍 أول مونديال تستضيفه 3 دول معاً: أمريكا، المكسيك، وكندا!\n🌍 First World Cup ever co-hosted by 3 nations: USA, Mexico & Canada!",
    "🇲🇽 المكسيك أول دولة تستضيف كأس العالم 3 مرات (1970، 1986، 2026)!\n🇲🇽 Mexico becomes the first country to host the World Cup 3 times (1970, 1986, 2026)!",
    "👶 أصغر هداف في تاريخ المونديال: بيليه بعمر 17 عاماً فقط (1958)!\n👶 Youngest WC scorer ever: Pelé, just 17 years old (1958)!",
    "💥 أكبر فوز في تاريخ المونديال: المجر 10-1 السلفادور (1982)!\n💥 Biggest win in WC history: Hungary 10-1 El Salvador (1982)!",
]

# ═══════════════════════════════════════════════════════
#  TEXT BUILDERS
# ═══════════════════════════════════════════════════════

def build_matches_text(date_key, lang="ar") -> str:
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
        if lang == "ar":
            return ("⏳ لا نتائج مُضافة بعد.\n\n"
                    "🔍 تابع كل النتائج الحية مباشرة على غوغل 👇")
        return ("⏳ No results added yet.\n\n"
                "🔍 Follow all live results directly on Google 👇")
    label = "نتائج المباريات" if lang == "ar" else "Match Results"
    grp_lbl = "المجموعة" if lang == "ar" else "Group"
    lines = [f"📊 *{label}*\n{'━'*22}"]
    by_date = {}
    for r in results:
        by_date.setdefault(r["date"], []).append(r)
    for d in sorted(by_date.keys(), reverse=True)[:7]:
        lines.append(f"\n📅 *{d}*")
        for m in by_date[d]:
            hg = m.get("home_goal", 0)
            ag = m.get("away_goal", 0)
            # تحديد الفائز بالنتيجة
            if hg > ag:
                home_icon, away_icon = "🏆", ""
            elif ag > hg:
                home_icon, away_icon = "", "🏆"
            else:
                home_icon = away_icon = "🤝"
            lines.append(
                f"⚽ {m['home']}{home_icon} *{hg} — {ag}* {away_icon}{m['away']}\n"
                f"   {grp_lbl}: {m['group']}"
            )
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════

def main_keyboard(lang="ar"):
    if lang == "ar":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 مباريات اليوم", callback_data="today"),
             InlineKeyboardButton("📊 النتائج", callback_data="results")],
            [InlineKeyboardButton("🔮 محاكي المباريات", callback_data="simulator"),
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
            [InlineKeyboardButton("🔮 Match Simulator", callback_data="simulator"),
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

    done_results = len([r for r in STATIC_RESULTS if r.get("done")])
    status_info = (
        f"\n\n📊 *الحالة:*\n"
        f"• نتائج مُضافة: {done_results}\n"
        f"• 🏆 الترتيب + ⚽ الهدافون: Google Links ✅\n"
        f"• ⚙️ بدون أي API خارجي ✅"
    )

    await update.message.reply_text(
        f"🛠 *لوحة الإدارة*\n\n👥 المشتركون: *{count}*\n\n🆕 *آخر 5:*\n{recent_text}"
        f"{status_info}\n\n"
        f"📢 `/broadcast رسالتك`\n"
        f"📰 `/daily` ملخص يومي\n"
        f"⚽ `/result` إضافة نتيجة مباراة\n"
        f"📋 `/results_list` عرض النتائج المضافة",
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
            lines.append(f"• {m['home']} vs {m['away']} 🕐{m['time']} GMT")
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


async def result_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر الأدمين لإضافة نتيجة مباراة يدوياً
    الصيغة: /result تاريخ فريق1 نتيجة1 نتيجة2 فريق2 مجموعة
    مثال: /result 2026-06-11 Mexico 2 0 "South Africa" A
    """
    if update.effective_user.id != ADMIN_ID:
        return

    args = context.args
    if not args or len(args) < 6:
        await update.message.reply_text(
            "📝 *الصيغة:*\n`/result YYYY-MM-DD الفريق1 هدف1 هدف2 الفريق2 المجموعة`\n\n"
            "*مثال:*\n`/result 2026-06-11 Mexico 2 0 SouthAfrica A`\n\n"
            "أو أرسل `/results_list` لرؤية النتائج الحالية",
            parse_mode="Markdown"
        )
        return

    try:
        match_date = args[0]
        home = args[1].replace("_", " ")
        hg = int(args[2])
        ag = int(args[3])
        away = args[4].replace("_", " ")
        group = args[5].upper()

        # أضف للقائمة الثابتة
        STATIC_RESULTS.append({
            "date": match_date,
            "home": home,
            "away": away,
            "hg": hg,
            "ag": ag,
            "group": group,
            "done": True
        })

        await update.message.reply_text(
            f"✅ *تمت إضافة النتيجة:*\n\n"
            f"⚽ *{home} {hg} — {ag} {away}*\n"
            f"📅 {match_date} | المجموعة {group}",
            parse_mode="Markdown"
        )
        logger.info(f"✅ Result added: {home} {hg}-{ag} {away} ({match_date})")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}\nتأكد من الصيغة الصحيحة")


async def results_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة النتائج المضافة للأدمين"""
    if update.effective_user.id != ADMIN_ID:
        return
    done = [r for r in STATIC_RESULTS if r.get("done")]
    if not done:
        await update.message.reply_text("📋 لا توجد نتائج مضافة بعد\nاستخدم `/result` لإضافة نتيجة", parse_mode="Markdown")
        return
    lines = ["📋 *النتائج المضافة:*\n"]
    for r in done:
        lines.append(f"• {r['home']} *{r['hg']}—{r['ag']}* {r['away']} | {r['date']} | G{r['group']}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


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
        text = build_matches_text(today_str(), lang)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # Results
    elif data == "results":
        results = await get_recent_results()
        text = build_results_text(results, lang)
        if not results:
            q = "نتائج كاس العالم 2026 اليوم" if lang == "ar" else "World Cup 2026 results today"
            url = "https://www.google.com/search?q=" + q.replace(" ", "+")
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 النتائج على غوغل | Google", url=url)],
                [InlineKeyboardButton("🔙 القائمة الرئيسية | Main Menu", callback_data="back")],
            ])
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
        else:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # Match Simulator
    elif data == "simulator":
        text = build_simulator_text(lang)
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 محاكاة جديدة | New Simulation", callback_data="simulator")],
            [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")]
        ])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=btns)

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
                [InlineKeyboardButton("⏱️ أسرع هدف", callback_data="st_fastest_goal")],
                [InlineKeyboardButton("🎯 الأكثر صناعة", callback_data="st_top_assists")],
                [InlineKeyboardButton("🏟️ أكبر الملاعب 2026", callback_data="st_stadiums_2026")],
                [InlineKeyboardButton("🔙 رجوع | Back", callback_data="back")],
            ]
        else:
            title = "📈 *Choose a stat category:*"
            btns = [
                [InlineKeyboardButton("🏆 Most Titles", callback_data="st_titles")],
                [InlineKeyboardButton("⚽ All-Time Scorers", callback_data="st_history_scorers")],
                [InlineKeyboardButton("🎯 Title Favorites", callback_data="st_favorites")],
                [InlineKeyboardButton("📊 2026 Stats", callback_data="st_records")],
                [InlineKeyboardButton("⏱️ Fastest Goal", callback_data="st_fastest_goal")],
                [InlineKeyboardButton("🎯 Most Assists", callback_data="st_top_assists")],
                [InlineKeyboardButton("🏟️ Biggest Stadiums 2026", callback_data="st_stadiums_2026")],
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
            [InlineKeyboardButton("🔵 LiveTV مباشر", url="https://www.google.com/search?q=كورة+لايف)],
            [InlineKeyboardButton("🟣 كورة ستار | Kora Star", url="https://koora-online.live")],
            [InlineKeyboardButton("🟡 بين سبورت | beIN Sport", url="https://www.beinsports.com/ar")],
            [InlineKeyboardButton("⚫ Sport365", url="https://sport365.live")],
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
#  MAIN
# ═══════════════════════════════════════════════════════

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler("result", result_cmd))
    app.add_handler(CommandHandler("results_list", results_list_cmd))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("⚽ World Cup 2026 Pro Bot v8.5 — Pure Static Edition — LIVE!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
