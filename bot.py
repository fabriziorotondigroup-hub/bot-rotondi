#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT TELEGRAM — Assistenza Tecnica Macchinari
Rotondi Group Roma
"""

import logging, sqlite3, asyncio, os
from datetime import datetime
from deep_translator import GoogleTranslator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)

# ══════════════════════════════════════════════════════════════
#  CONFIGURAZIONE — legge dalle variabili ambiente (Railway)
# ══════════════════════════════════════════════════════════════

BOT_TOKEN        = os.environ.get("BOT_TOKEN", "IL_TUO_TOKEN_QUI")
TECNICI_GROUP_ID = int(os.environ.get("TECNICI_GROUP_ID", "-1001234567890"))
BACKOFFICE_IDS   = [int(x) for x in os.environ.get("BACKOFFICE_IDS", "123456789").split(",")]
NOME_AZIENDA     = "Rotondi Group Roma"

# ══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

DB_PATH = "assistenza.db"

# ─────────────────────────────────────────────
# STATI CONVERSAZIONE
# ─────────────────────────────────────────────
(SCEGLI_LINGUA, NOME, INDIRIZZO, TELEFONO,
 FOTO_TARGHETTA, MARCA, MODELLO, SERIALE,
 PROBLEMA, FOTO_MACCHINA, CONFERMA) = range(11)

# ─────────────────────────────────────────────
# MESSAGGI MULTILINGUA
# ─────────────────────────────────────────────
TESTI = {
    "it": {
        "nome":           "👤 Scrivi il tuo *nome e cognome*:",
        "indirizzo":      "📍 Scrivi il tuo *indirizzo completo* (via, numero civico e città):",
        "telefono":       "📞 Scrivi il tuo *numero di telefono*:",
        "foto_targhetta": "📸 Fai una *foto alla targhetta della macchina* e inviala (oppure scrivi 'salta'):",
        "marca":          "🏷 Dimmi la *marca della macchina*:",
        "modello":        "📋 Dimmi il *modello della macchina*:",
        "seriale":        "🔢 Dimmi il *numero seriale* della macchina:",
        "problema":       "🔧 Descrivi il *problema della macchina*:",
        "foto_macchina":  "📸 Fai una *foto alla macchina* e inviala (oppure scrivi 'salta'):",
        "riepilogo":      "📋 *Riepilogo:*\n\n👤 {nome}\n📍 {indirizzo}\n📞 {telefono}\n🏷 {marca} — {modello}\n🔢 Seriale: {seriale}\n🔧 {problema}\n\nÈ tutto corretto?",
        "si":             "✅ Sì, confermo",
        "no":             "❌ No, ricomincio",
        "registrata": (
            "Gentile Cliente,\n"
            "Grazie per aver contattato il nostro servizio di assistenza tecnica. "
            "La sua richiesta è stata ricevuta e un nostro tecnico sarà disponibile a breve.\n\n"
            "📋 *INFORMAZIONI SUL SERVIZIO*\n"
            "• Chiamata + 1 ora di lavoro (o frazione): € 80,00 + IVA\n"
            "• Ore successive alla prima: € 40,00/ora + IVA\n\n"
            "⚠️ *ANNULLAMENTO CHIAMATA*\n"
            "Per annullare contatti URGENTEMENTE il nr. +39 06 41 40 0514.\n"
            "In assenza di disdetta verrà addebitato il costo di uscita.\n\n"
            "_Il Team di Assistenza Tecnica Rotondi Group Roma_"
        ),
        "assegnata": (
            "Gentile Cliente,\n"
            "La informiamo che la sua richiesta di assistenza è stata assegnata.\n\n"
            "👨‍🔧 *Tecnico assegnato:* {tecnico}\n"
            "📞 *Ufficio Roma:* +39 06 41400617\n"
            "⏰ *Intervento previsto:* {fascia}\n\n"
            "📋 *INFORMAZIONI SUL SERVIZIO*\n"
            "• Chiamata + 1 Ora di lavoro (o frazione): € 80,00 + IVA\n"
            "• Ore successive alla prima: € 40,00/ora + IVA\n\n"
            "Nota: Il pagamento dell'intervento dovrà essere effettuato direttamente al tecnico al termine del servizio.\n\n"
            "I tecnici che operano con Rotondi Group sono professionisti freelance selezionati e incaricati dalla nostra azienda per l'assistenza e la riparazione dei nostri macchinari.\n\n"
            "⚠️ Per annullare contatti URGENTEMENTE il nr. +39 06 41 40 0514.\n"
            "In assenza di disdetta verrà addebitato il costo di uscita.\n\n"
            "_Il Team di Assistenza Tecnica Rotondi Group Roma_"
        ),
        "annulla": "❌ Operazione annullata. Scrivi /start per ricominciare.",
    },
    "en": {
        "nome":           "👤 Write your *full name*:",
        "indirizzo":      "📍 Write your *full address* (street, number and city):",
        "telefono":       "📞 Write your *phone number*:",
        "foto_targhetta": "📸 Take a *photo of the machine's label* and send it (or write 'skip'):",
        "marca":          "🏷 Tell me the *brand of the machine*:",
        "modello":        "📋 Tell me the *model of the machine*:",
        "seriale":        "🔢 Tell me the *serial number* of the machine:",
        "problema":       "🔧 Describe the *problem with the machine*:",
        "foto_macchina":  "📸 Take a *photo of the machine* and send it (or write 'skip'):",
        "riepilogo":      "📋 *Summary:*\n\n👤 {nome}\n📍 {indirizzo}\n📞 {telefono}\n🏷 {marca} — {modello}\n🔢 Serial: {seriale}\n🔧 {problema}\n\nIs everything correct?",
        "si":             "✅ Yes, confirm",
        "no":             "❌ No, start over",
        "registrata": (
            "Dear Customer,\n"
            "Thank you for contacting our technical assistance service. "
            "Your request has been received and one of our technicians will be available shortly.\n\n"
            "📋 *SERVICE INFORMATION*\n"
            "• Call-out + 1 hour of work (or fraction): € 80.00 + VAT\n"
            "• Additional hours after the first: € 40.00/hour + VAT\n\n"
            "⚠️ *CANCELLATION*\n"
            "To cancel contact URGENTLY: +39 06 41 40 0514.\n"
            "Without cancellation, the call-out fee will be charged.\n\n"
            "_The Rotondi Group Roma Technical Assistance Team_"
        ),
        "assegnata": (
            "Dear Customer,\n"
            "Your assistance request has been assigned.\n\n"
            "👨‍🔧 *Assigned technician:* {tecnico}\n"
            "📞 *Rome Office:* +39 06 41400617\n"
            "⏰ *Scheduled intervention:* {fascia}\n\n"
            "📋 *SERVICE INFORMATION*\n"
            "• Call-out + 1 hour of work (or fraction): € 80.00 + VAT\n"
            "• Additional hours: € 40.00/hour + VAT\n\n"
            "Note: Payment must be made directly to the technician at the end of the service.\n\n"
            "Our technicians are freelance professionals selected by Rotondi Group.\n\n"
            "⚠️ To cancel contact URGENTLY: +39 06 41 40 0514.\n"
            "Without cancellation, the call-out fee will be charged.\n\n"
            "_The Rotondi Group Roma Technical Assistance Team_"
        ),
        "annulla": "❌ Cancelled. Write /start to begin again.",
    },
    "bn": {
        "nome":           "👤 আপনার *পুরো নাম* লিখুন:",
        "indirizzo":      "📍 আপনার *সম্পূর্ণ ঠিকানা* লিখুন (রাস্তা, নম্বর এবং শহর):",
        "telefono":       "📞 আপনার *ফোন নম্বর* লিখুন:",
        "foto_targhetta": "📸 মেশিনের *তারিখফলকের ছবি* পাঠান (অথবা 'skip' লিখুন):",
        "marca":          "🏷 মেশিনের *ব্র্যান্ড* বলুন:",
        "modello":        "📋 মেশিনের *মডেল* বলুন:",
        "seriale":        "🔢 মেশিনের *সিরিয়াল নম্বর* বলুন:",
        "problema":       "🔧 মেশিনের *সমস্যা* বর্ণনা করুন:",
        "foto_macchina":  "📸 মেশিনের *ছবি* পাঠান (অথবা 'skip' লিখুন):",
        "riepilogo":      "📋 *সারসংক্ষেপ:*\n\n👤 {nome}\n📍 {indirizzo}\n📞 {telefono}\n🏷 {marca} — {modello}\n🔢 সিরিয়াল: {seriale}\n🔧 {problema}\n\nসব ঠিক আছে?",
        "si":             "✅ হ্যাঁ, নিশ্চিত",
        "no":             "❌ না, আবার শুরু",
        "registrata": (
            "প্রিয় গ্রাহক,\n"
            "আমাদের প্রযুক্তিগত সহায়তা সেবায় যোগাযোগ করার জন্য ধন্যবাদ।\n\n"
            "📋 *সেবার তথ্য*\n"
            "• আসার চার্জ + ১ ঘণ্টা কাজ: € 80,00 + VAT\n"
            "• প্রথম ঘণ্টার পরে প্রতি ঘণ্টা: € 40,00 + VAT\n\n"
            "⚠️ বাতিল করতে জরুরি যোগাযোগ করুন: +39 06 41 40 0514\n"
            "বাতিল না করলে আসার চার্জ প্রযোজ্য হবে।\n\n"
            "_রোটোন্ডি গ্রুপ রোমা টেকনিক্যাল টিম_"
        ),
        "assegnata": (
            "প্রিয় গ্রাহক,\n"
            "আপনার অনুরোধ একজন টেকনিশিয়ানকে দেওয়া হয়েছে।\n\n"
            "👨‍🔧 *টেকনিশিয়ান:* {tecnico}\n"
            "📞 *রোমা অফিস:* +39 06 41400617\n"
            "⏰ *আসার সময়:* {fascia}\n\n"
            "📋 *সেবার খরচ*\n"
            "• আসার চার্জ + ১ ঘণ্টা: € 80,00 + VAT\n"
            "• অতিরিক্ত ঘণ্টা: € 40,00 + VAT\n\n"
            "⚠️ বাতিল করতে জরুরি: +39 06 41 40 0514\n\n"
            "_রোটোন্ডি গ্রুপ রোমা টেকনিক্যাল টিম_"
        ),
        "annulla": "❌ বাতিল হয়েছে। আবার শুরু করতে /start লিখুন।",
    },
    "zh": {
        "nome":           "👤 请写您的*姓名*：",
        "indirizzo":      "📍 请写您的*完整地址*（街道、门牌号和城市）：",
        "telefono":       "📞 请写您的*电话号码*：",
        "foto_targhetta": "📸 请拍*机器铭牌照片*发送（或写'跳过'）：",
        "marca":          "🏷 请告诉我*机器品牌*：",
        "modello":        "📋 请告诉我*机器型号*：",
        "seriale":        "🔢 请告诉我*序列号*：",
        "problema":       "🔧 请描述*机器的问题*：",
        "foto_macchina":  "📸 请拍*机器照片*发送（或写'跳过'）：",
        "riepilogo":      "📋 *摘要：*\n\n👤 {nome}\n📍 {indirizzo}\n📞 {telefono}\n🏷 {marca} — {modello}\n🔢 序列号: {seriale}\n🔧 {problema}\n\n一切正确吗？",
        "si":             "✅ 是，确认",
        "no":             "❌ 否，重新开始",
        "registrata": (
            "尊敬的客户，\n"
            "感谢您联系我们的技术援助服务。\n\n"
            "📋 *服务信息*\n"
            "• 上门费 + 1小时工作: € 80,00 + 增值税\n"
            "• 第一小时后每小时: € 40,00 + 增值税\n\n"
            "⚠️ 如需取消请紧急联系: +39 06 41 40 0514\n"
            "未取消将收取上门费。\n\n"
            "_罗通迪集团罗马技术团队_"
        ),
        "assegnata": (
            "尊敬的客户，\n"
            "您的维修请求已分配给技术人员。\n\n"
            "👨‍🔧 *负责技术人员：* {tecnico}\n"
            "📞 *罗马办公室：* +39 06 41400617\n"
            "⏰ *预计上门时间：* {fascia}\n\n"
            "📋 *服务费用*\n"
            "• 上门费 + 1小时: € 80,00 + 增值税\n"
            "• 额外每小时: € 40,00 + 增值税\n\n"
            "⚠️ 如需取消请紧急联系: +39 06 41 40 0514\n\n"
            "_罗通迪集团罗马技术团队_"
        ),
        "annulla": "❌ 已取消。写 /start 重新开始。",
    },
    "ar": {
        "nome":           "👤 اكتب *اسمك الكامل*:",
        "indirizzo":      "📍 اكتب *عنوانك الكامل* (الشارع والرقم والمدينة):",
        "telefono":       "📞 اكتب *رقم هاتفك*:",
        "foto_targhetta": "📸 أرسل *صورة لوحة الجهاز* (أو اكتب 'تخطي'):",
        "marca":          "🏷 أخبرني *ماركة الجهاز*:",
        "modello":        "📋 أخبرني *موديل الجهاز*:",
        "seriale":        "🔢 أخبرني *الرقم التسلسلي* للجهاز:",
        "problema":       "🔧 صف *مشكلة الجهاز*:",
        "foto_macchina":  "📸 أرسل *صورة الجهاز* (أو اكتب 'تخطي'):",
        "riepilogo":      "📋 *الملخص:*\n\n👤 {nome}\n📍 {indirizzo}\n📞 {telefono}\n🏷 {marca} — {modello}\n🔢 الرقم التسلسلي: {seriale}\n🔧 {problema}\n\nهل كل شيء صحيح؟",
        "si":             "✅ نعم، تأكيد",
        "no":             "❌ لا، ابدأ من جديد",
        "registrata": (
            "عزيزي العميل،\n"
            "شكراً لتواصلك مع خدمة الدعم الفني لدينا.\n\n"
            "📋 *معلومات الخدمة*\n"
            "• زيارة + ساعة عمل: € 80,00 + ضريبة\n"
            "• الساعات الإضافية: € 40,00/ساعة + ضريبة\n\n"
            "⚠️ للإلغاء تواصل عاجلاً: +39 06 41 40 0514\n"
            "في حالة عدم الإلغاء سيتم احتساب رسوم الزيارة.\n\n"
            "_فريق روتوندي جروب روما للدعم الفني_"
        ),
        "assegnata": (
            "عزيزي العميل،\n"
            "تم تعيين فني لطلبك.\n\n"
            "👨‍🔧 *الفني المعين:* {tecnico}\n"
            "📞 *مكتب روما:* +39 06 41400617\n"
            "⏰ *موعد التدخل:* {fascia}\n\n"
            "📋 *تكاليف الخدمة*\n"
            "• زيارة + ساعة عمل: € 80,00 + ضريبة\n"
            "• ساعات إضافية: € 40,00/ساعة + ضريبة\n\n"
            "⚠️ للإلغاء تواصل عاجلاً: +39 06 41 40 0514\n\n"
            "_فريق روتوندي جروب روما للدعم الفني_"
        ),
        "annulla": "❌ تم الإلغاء. اكتب /start للبدء من جديد.",
    },
}

FLAGS = {"it":"🇮🇹","en":"🇬🇧","bn":"🇧🇩","zh":"🇨🇳","ar":"🇸🇦"}

def t(lingua, chiave, **kwargs):
    testo = TESTI.get(lingua, TESTI["it"]).get(chiave, "")
    return testo.format(azienda=NOME_AZIENDA, **kwargs)

def traduci(testo, lingua_src="auto"):
    try:
        if lingua_src == "it": return testo
        return GoogleTranslator(source="auto", target="it").translate(testo) or testo
    except Exception as e:
        log.error(f"Traduzione: {e}"); return testo

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chiamate (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id        INTEGER,
                username           TEXT,
                lingua             TEXT,
                nome_cliente       TEXT,
                indirizzo          TEXT,
                telefono           TEXT,
                problema_it        TEXT,
                problema_originale TEXT,
                stato              TEXT DEFAULT 'aperta',
                tecnico_id         INTEGER,
                tecnico_nome       TEXT,
                fascia_oraria      TEXT,
                data_apertura      TEXT,
                data_assegnazione  TEXT,
                msg_id_gruppo      INTEGER,
                marca              TEXT,
                modello            TEXT,
                seriale            TEXT,
                foto_targhetta_id  TEXT,
                foto_macchina_id   TEXT
            )
        """)
        # Aggiungi colonne nuove se non esistono (per DB esistenti)
        for col in ["marca TEXT", "modello TEXT", "seriale TEXT",
                    "foto_targhetta_id TEXT", "foto_macchina_id TEXT"]:
            try:
                conn.execute(f"ALTER TABLE chiamate ADD COLUMN {col}")
            except: pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tecnici (
                telegram_id INTEGER PRIMARY KEY,
                nome        TEXT,
                telefono    TEXT
            )
        """)
        conn.commit()

def salva_chiamata(tg_id, username, lingua, nome, indirizzo, telefono,
                   prob_it, prob_orig, marca, modello, seriale,
                   foto_targhetta_id, foto_macchina_id):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("""
            INSERT INTO chiamate
            (telegram_id,username,lingua,nome_cliente,indirizzo,telefono,
             problema_it,problema_originale,data_apertura,
             marca,modello,seriale,foto_targhetta_id,foto_macchina_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (tg_id, username, lingua, nome, indirizzo, telefono,
              prob_it, prob_orig, datetime.now().strftime("%d/%m/%Y %H:%M"),
              marca, modello, seriale, foto_targhetta_id, foto_macchina_id))
        cid = cur.lastrowid
        conn.commit()
    return cid

def assegna(cid, tecnico_id, tecnico_nome, fascia):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE chiamate SET stato='assegnata', tecnico_id=?, tecnico_nome=?,
            fascia_oraria=?, data_assegnazione=? WHERE id=?
        """, (tecnico_id, tecnico_nome, fascia,
              datetime.now().strftime("%d/%m/%Y %H:%M"), cid))
        conn.commit()

def get_chiamata(cid):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("SELECT * FROM chiamate WHERE id=?", (cid,)).fetchone()

def aggiorna_msg_id(cid, msg_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE chiamate SET msg_id_gruppo=? WHERE id=?", (msg_id, cid))
        conn.commit()

def get_tecnico(tid):
    with sqlite3.connect(DB_PATH) as conn:
        r = conn.execute("SELECT nome, telefono FROM tecnici WHERE telegram_id=?", (tid,)).fetchone()
    return {"nome": r[0], "telefono": r[1] or ""} if r else None

def get_tecnico_nome(tid):
    t = get_tecnico(tid)
    return t["nome"] if t else None

def registra_tecnico(tid, nome, telefono=None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO tecnici VALUES (?,?,?)", (tid, nome, telefono))
        conn.commit()

def lista_chiamate_db(limite=20):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("""
            SELECT id,nome_cliente,indirizzo,stato,tecnico_nome,fascia_oraria,data_apertura,lingua
            FROM chiamate ORDER BY id DESC LIMIT ?
        """, (limite,)).fetchall()

# ─────────────────────────────────────────────
# /start — CLIENTE
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in BACKOFFICE_IDS:
        await update.message.reply_text(
            f"👩‍💼 *Benvenuta nel sistema {NOME_AZIENDA}!*\n\n"
            "Comandi disponibili:\n"
            "/lista — vedi le ultime chiamate\n"
            "/aperte — vedi solo le chiamate aperte",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    nome_tg = get_tecnico_nome(user_id)
    if nome_tg:
        await update.message.reply_text(
            f"👨‍🔧 *Bentornato {nome_tg}!*\n\n"
            "/chiamate — le tue chiamate assegnate",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇮🇹 Italiano", callback_data="lang_it"),
            InlineKeyboardButton("🇬🇧 English",  callback_data="lang_en"),
        ],
        [
            InlineKeyboardButton("🇧🇩 বাংলা",    callback_data="lang_bn"),
            InlineKeyboardButton("🇨🇳 中文",      callback_data="lang_zh"),
        ],
        [
            InlineKeyboardButton("🇸🇦 العربية",  callback_data="lang_ar"),
        ],
    ])
    await update.message.reply_text(
        f"👋 Benvenuto / Welcome / স্বাগতম / 欢迎 / أهلاً\n\n"
        f"*{NOME_AZIENDA}*\n\n"
        f"Scegli la lingua / Choose language / ভাষা বেছে নিন / 选择语言 / اختر اللغة:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return SCEGLI_LINGUA

async def scegli_lingua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lingua = query.data.replace("lang_", "")
    context.user_data["lingua"] = lingua
    await query.edit_message_text(
        f"{FLAGS[lingua]} *{NOME_AZIENDA}*\n\n" + t(lingua, "nome"),
        parse_mode="Markdown"
    )
    return NOME

# ─────────────────────────────────────────────
# RACCOLTA DATI CLIENTE
# ─────────────────────────────────────────────
async def raccogli_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    context.user_data["nome"]      = update.message.text.strip()
    context.user_data["nome_orig"] = update.message.text.strip()
    await update.message.reply_text(t(lingua, "indirizzo"), parse_mode="Markdown")
    return INDIRIZZO

async def raccogli_indirizzo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    context.user_data["indirizzo"] = traduci(update.message.text.strip(), lingua)
    await update.message.reply_text(t(lingua, "telefono"), parse_mode="Markdown")
    return TELEFONO

async def raccogli_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    context.user_data["telefono"] = update.message.text.strip()
    await update.message.reply_text(t(lingua, "foto_targhetta"), parse_mode="Markdown")
    return FOTO_TARGHETTA

async def raccogli_foto_targhetta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    if update.message.photo:
        context.user_data["foto_targhetta_id"] = update.message.photo[-1].file_id
    else:
        context.user_data["foto_targhetta_id"] = None
    await update.message.reply_text(t(lingua, "marca"), parse_mode="Markdown")
    return MARCA

async def raccogli_marca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    context.user_data["marca"] = traduci(update.message.text.strip(), lingua)
    await update.message.reply_text(t(lingua, "modello"), parse_mode="Markdown")
    return MODELLO

async def raccogli_modello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    context.user_data["modello"] = traduci(update.message.text.strip(), lingua)
    await update.message.reply_text(t(lingua, "seriale"), parse_mode="Markdown")
    return SERIALE

async def raccogli_seriale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    context.user_data["seriale"] = update.message.text.strip()
    await update.message.reply_text(t(lingua, "problema"), parse_mode="Markdown")
    return PROBLEMA

async def raccogli_problema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    orig   = update.message.text.strip()
    trad   = traduci(orig, lingua)
    context.user_data["problema_orig"] = orig
    context.user_data["problema_it"]   = trad
    await update.message.reply_text(t(lingua, "foto_macchina"), parse_mode="Markdown")
    return FOTO_MACCHINA

async def raccogli_foto_macchina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    if update.message.photo:
        context.user_data["foto_macchina_id"] = update.message.photo[-1].file_id
    else:
        context.user_data["foto_macchina_id"] = None

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lingua, "si"), callback_data="conferma_si"),
        InlineKeyboardButton(t(lingua, "no"), callback_data="conferma_no"),
    ]])
    await update.message.reply_text(
        t(lingua, "riepilogo",
          nome      = context.user_data["nome_orig"],
          indirizzo = context.user_data["indirizzo"],
          telefono  = context.user_data["telefono"],
          marca     = context.user_data.get("marca", "-"),
          modello   = context.user_data.get("modello", "-"),
          seriale   = context.user_data.get("seriale", "-"),
          problema  = context.user_data["problema_orig"]),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return CONFERMA

async def conferma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()
    lingua = context.user_data.get("lingua", "it")

    if query.data == "conferma_no":
        await query.edit_message_text(t(lingua, "annulla"), parse_mode="Markdown")
        return ConversationHandler.END

    user    = query.from_user
    nome_it = traduci(context.user_data["nome_orig"], lingua)
    cid     = salva_chiamata(
        user.id,
        user.username or str(user.id),
        lingua,
        nome_it,
        context.user_data["indirizzo"],
        context.user_data["telefono"],
        context.user_data["problema_it"],
        context.user_data["problema_orig"],
        context.user_data.get("marca", ""),
        context.user_data.get("modello", ""),
        context.user_data.get("seriale", ""),
        context.user_data.get("foto_targhetta_id"),
        context.user_data.get("foto_macchina_id"),
    )

    await query.edit_message_text(t(lingua, "registrata"), parse_mode="Markdown")

    # Notifica tecnici
    flag = FLAGS.get(lingua, "🌍")
    sezione_problema = f"🔧 *Problema (IT):* {context.user_data['problema_it']}"
    if lingua != "it":
        sezione_problema += f"\n🔧 *Originale {flag}:* {context.user_data['problema_orig']}"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🕛 Entro le 12:00", callback_data=f"fascia_{cid}_entro12"),
            InlineKeyboardButton("🕕 Entro le 18:00", callback_data=f"fascia_{cid}_entro18"),
        ],
        [
            InlineKeyboardButton("📅 In giornata",    callback_data=f"fascia_{cid}_giornata"),
            InlineKeyboardButton("📆 Entro domani",   callback_data=f"fascia_{cid}_domani"),
        ]
    ])

    indirizzo_maps = context.user_data['indirizzo'].replace(' ', '+') + ",+Roma,+Italia"
    link_maps = f"https://www.google.com/maps/search/?api=1&query={indirizzo_maps}"

    testo_gruppo = (
        f"🔔 *NUOVA CHIAMATA #{cid}* {flag}\n"
        f"{'─'*30}\n"
        f"👤 *Cliente:* {nome_it}\n"
        f"📍 *Indirizzo:* {context.user_data['indirizzo']}\n"
        f"🗺 [Apri su Google Maps]({link_maps})\n"
        f"📞 *Telefono:* {context.user_data['telefono']}\n"
        f"🆔 *Telegram:* @{user.username or user.id}\n"
        f"🏷 *Marca:* {context.user_data.get('marca', '-')}\n"
        f"📋 *Modello:* {context.user_data.get('modello', '-')}\n"
        f"🔢 *Seriale:* {context.user_data.get('seriale', '-')}\n"
        f"{sezione_problema}\n"
        f"{'─'*30}\n"
        f"⏰ Primo tecnico disponibile: clicca quando intervieni:"
    )

    msg = await context.bot.send_message(
        chat_id=TECNICI_GROUP_ID,
        text=testo_gruppo,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    aggiorna_msg_id(cid, msg.message_id)

    # Invia foto targhetta al gruppo se presente
    if context.user_data.get("foto_targhetta_id"):
        try:
            await context.bot.send_photo(
                chat_id=TECNICI_GROUP_ID,
                photo=context.user_data["foto_targhetta_id"],
                caption=f"📸 Foto targhetta — Chiamata #{cid}"
            )
        except Exception as e:
            log.error(f"Foto targhetta: {e}")

    # Invia foto macchina al gruppo se presente
    if context.user_data.get("foto_macchina_id"):
        try:
            await context.bot.send_photo(
                chat_id=TECNICI_GROUP_ID,
                photo=context.user_data["foto_macchina_id"],
                caption=f"📸 Foto macchina — Chiamata #{cid}"
            )
        except Exception as e:
            log.error(f"Foto macchina: {e}")

    # Notifica back office
    for bo_id in BACKOFFICE_IDS:
        try:
            await context.bot.send_message(
                chat_id=bo_id,
                text=(
                    f"📲 *Nuova richiesta #{cid}* {flag}\n\n"
                    f"👤 {nome_it}\n"
                    f"📍 {context.user_data['indirizzo']}\n"
                    f"📞 {context.user_data['telefono']}\n"
                    f"🏷 {context.user_data.get('marca','-')} — {context.user_data.get('modello','-')}\n"
                    f"🔢 Seriale: {context.user_data.get('seriale','-')}\n"
                    f"🔧 {context.user_data['problema_it']}"
                    + (f"\n🔧 Originale: {context.user_data['problema_orig']}" if lingua != "it" else "")
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            log.error(f"BO notifica: {e}")

    return ConversationHandler.END

async def annulla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    await update.message.reply_text(t(lingua, "annulla"), parse_mode="Markdown")
    return ConversationHandler.END

# ─────────────────────────────────────────────
# TECNICO CLICCA TASTO FASCIA ORARIA
# ─────────────────────────────────────────────
FASCE = {
    "entro12":  "entro le 12:00",
    "entro18":  "entro le 18:00",
    "giornata": "in giornata",
    "domani":   "entro domani"
}

async def gestisci_fascia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    parti  = query.data.split("_")
    cid    = int(parti[1])
    fascia = FASCE.get(parti[2], parti[2])

    ch = get_chiamata(cid)
    if not ch:
        await query.answer("⚠️ Chiamata non trovata.", show_alert=True); return
    if ch[9] == "assegnata":
        await query.answer("⚠️ Già assegnata a un altro tecnico!", show_alert=True); return

    tid    = query.from_user.id
    t_nome = f"{query.from_user.first_name or ''} {query.from_user.last_name or ''}".strip()
    tecnico_db  = get_tecnico(tid)
    nome_finale = tecnico_db["nome"] if tecnico_db else t_nome
    if not tecnico_db:
        registra_tecnico(tid, t_nome)
    assegna(cid, tid, nome_finale, fascia)

    await query.edit_message_text(
        f"✅ *CHIAMATA #{cid} — ASSEGNATA*\n"
        f"{'─'*30}\n"
        f"👤 *Cliente:* {ch[4]}\n"
        f"📍 *Indirizzo:* {ch[5]}\n"
        f"🔧 *Problema:* {ch[7]}\n"
        f"{'─'*30}\n"
        f"👨‍🔧 *Tecnico:* {nome_finale}\n"
        f"⏰ *Intervento:* {fascia}",
        parse_mode="Markdown"
    )
    await query.answer("✅ Chiamata assegnata a te!")

    # Notifica back office
    for bo_id in BACKOFFICE_IDS:
        try:
            await context.bot.send_message(
                chat_id=bo_id,
                text=(
                    f"✅ *Chiamata #{cid} assegnata*\n\n"
                    f"👤 {ch[4]}\n"
                    f"👨‍🔧 Tecnico: {nome_finale}\n"
                    f"⏰ {fascia}"
                ),
                parse_mode="Markdown"
            )
        except: pass

    # Messaggio al cliente nella sua lingua
    lingua_cliente = ch[3]
    try:
        await context.bot.send_message(
            chat_id=ch[1],
            text=t(lingua_cliente, "assegnata",
                   tecnico=nome_finale,
                   fascia=fascia),
            parse_mode="Markdown"
        )
    except Exception as e:
        log.error(f"Messaggio cliente: {e}")

# ─────────────────────────────────────────────
# COMANDI BACK OFFICE
# ─────────────────────────────────────────────
async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in BACKOFFICE_IDS:
        await update.message.reply_text("⛔ Non autorizzato."); return
    rows = lista_chiamate_db()
    if not rows:
        await update.message.reply_text("📋 Nessuna chiamata."); return
    testo = "📋 *Ultime 20 chiamate:*\n\n"
    for r in rows:
        emoji = "🟡" if r[3] == "aperta" else "✅"
        flag  = FLAGS.get(r[7], "🌍")
        testo += f"{emoji} *#{r[0]}* {flag} — {r[1]}\n📍 {r[2]}\n"
        if r[3] == "assegnata":
            testo += f"👨‍🔧 {r[4]} — {r[5]}\n"
        testo += f"🕐 {r[6]}\n\n"
    await update.message.reply_text(testo, parse_mode="Markdown")

async def aperte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in BACKOFFICE_IDS:
        await update.message.reply_text("⛔ Non autorizzato."); return
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT id,nome_cliente,indirizzo,data_apertura,lingua
            FROM chiamate WHERE stato='aperta' ORDER BY id DESC
        """).fetchall()
    if not rows:
        await update.message.reply_text("✅ Nessuna chiamata aperta!"); return
    testo = f"🟡 *Chiamate aperte ({len(rows)}):*\n\n"
    for r in rows:
        testo += f"*#{r[0]}* {FLAGS.get(r[4],'🌍')} — {r[1]}\n📍 {r[2]}\n🕐 {r[3]}\n\n"
    await update.message.reply_text(testo, parse_mode="Markdown")

# ─────────────────────────────────────────────
# COMANDO TECNICO — /registrami
# ─────────────────────────────────────────────
REG_TELEFONO = 20

async def registrami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nome = f"{user.first_name or ''} {user.last_name or ''}".strip()
    context.user_data["reg_nome"] = nome
    await update.message.reply_text(
        f"👨‍🔧 Ciao *{nome}*!\n\n"
        f"Per completare la registrazione scrivi il tuo *numero di telefono*:",
        parse_mode="Markdown"
    )
    return REG_TELEFONO

async def registrami_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    nome     = context.user_data.get("reg_nome", update.effective_user.first_name)
    telefono = update.message.text.strip()
    registra_tecnico(user.id, nome, telefono)
    await update.message.reply_text(
        f"✅ *Registrazione completata!*\n\n"
        f"👤 Nome: *{nome}*\n"
        f"📞 Telefono: *{telefono}*\n\n"
        f"Riceverai le notifiche nel gruppo tecnici.\n"
        f"Usa /chiamate per vedere le tue chiamate assegnate.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def mie_chiamate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT id,nome_cliente,indirizzo,problema_it,fascia_oraria,data_assegnazione
            FROM chiamate WHERE tecnico_id=? ORDER BY id DESC LIMIT 10
        """, (tid,)).fetchall()
    if not rows:
        await update.message.reply_text("📋 Nessuna chiamata assegnata."); return
    testo = "📋 *Le tue ultime chiamate:*\n\n"
    for r in rows:
        testo += f"✅ *#{r[0]}* — {r[1]}\n📍 {r[2]}\n🔧 {r[3]}\n⏰ {r[4]}\n\n"
    await update.message.reply_text(testo, parse_mode="Markdown")

# ─────────────────────────────────────────────
# COMANDO /getid — per trovare ID gruppo
# ─────────────────────────────────────────────
async def getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    await update.message.reply_text(
        f"🆔 Chat ID: `{chat.id}`\n"
        f"👤 User ID: `{user.id}`\n"
        f"📝 Tipo: {chat.type}",
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SCEGLI_LINGUA:  [CallbackQueryHandler(scegli_lingua, pattern="^lang_")],
            NOME:           [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_nome)],
            INDIRIZZO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_indirizzo)],
            TELEFONO:       [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_telefono)],
            FOTO_TARGHETTA: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, raccogli_foto_targhetta)],
            MARCA:          [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_marca)],
            MODELLO:        [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_modello)],
            SERIALE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_seriale)],
            PROBLEMA:       [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_problema)],
            FOTO_MACCHINA:  [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, raccogli_foto_macchina)],
            CONFERMA:       [CallbackQueryHandler(conferma, pattern="^conferma_")],
        },
        fallbacks=[CommandHandler("annulla", annulla)]
    )

    conv_registrami = ConversationHandler(
        entry_points=[CommandHandler("registrami", registrami)],
        states={
            REG_TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, registrami_telefono)],
        },
        fallbacks=[CommandHandler("annulla", annulla)]
    )

    app.add_handler(conv)
    app.add_handler(conv_registrami)
    app.add_handler(CallbackQueryHandler(gestisci_fascia, pattern=r"^fascia_"))
    app.add_handler(CommandHandler("lista",    lista))
    app.add_handler(CommandHandler("aperte",   aperte))
    app.add_handler(CommandHandler("chiamate", mie_chiamate))
    app.add_handler(CommandHandler("getid",    getid))

    log.info("🤖 Bot avviato!")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
