#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT TELEGRAM - Assistenza Tecnica Macchinari
Rotondi Group Roma
"""

import logging, sqlite3, os, math
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)

BOT_TOKEN        = os.environ.get("BOT_TOKEN", "")
TECNICI_GROUP_ID = int(os.environ.get("TECNICI_GROUP_ID", "-1001234567890"))
BACKOFFICE_IDS   = [int(x) for x in os.environ.get("BACKOFFICE_IDS", "123456789").split(",")]
NOME_AZIENDA     = "Rotondi Group Roma"
GMAPS_KEY        = os.environ.get("GMAPS_KEY", "")
SEDE             = "Via di Sant'Alessandro 349, Roma, Italia"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
log = logging.getLogger(__name__)
DB_PATH = "assistenza.db"

# ── STATI ───────────────────────────────────────────────────────────────────
(CONDIZIONI, SCEGLI_LINGUA, GDPR, NOME,
 IND_VIA, IND_CIVICO, IND_CAP, IND_CITTA, IND_PROVINCIA,
 TELEFONO, FOTO_TARGHETTA, MARCA, MODELLO, SERIALE,
 PROBLEMA, FOTO_MACCHINA, CONFERMA) = range(17)
REG_TELEFONO = 20

FLAGS = {"it":"🇮🇹","en":"🇬🇧","bn":"🇧🇩","zh":"🇨🇳","ar":"🇸🇦"}

TESTI = {
    "it": {
        "gdpr": (
            "🔒 *INFORMATIVA PRIVACY (GDPR)*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Ai sensi del Reg. UE 2016/679 (GDPR), i Suoi dati personali "
            "saranno trattati da:\n\n"
            "🏢 *Rotondi Group Srl*\n"
            "📍 Via F.lli Rosselli 14/16, 20019 Settimo Milanese (MI)\n"
            "📧 segnalazioni-privacy@rotondigroup.it\n\n"
            "• *Finalità:* gestione richiesta assistenza tecnica\n"
            "• *Conservazione:* max 2 anni\n"
            "• *Diritti:* accesso, rettifica, cancellazione\n\n"
            "Accetta il trattamento dei dati personali?"
        ),
        "gdpr_si":    "✅ Accetto",
        "gdpr_no":    "❌ Non accetto",
        "gdpr_denied":"❌ *Consenso non fornito*\n\nSenza consenso non possiamo procedere.\nScrivi /start per ricominciare.",
        "cond_si":    "✅ Accetto le condizioni",
        "cond_no":    "❌ Non accetto",
        "condizioni": (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔧  *ROTONDI GROUP SRL* — Filiale di Roma\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ *INFORMATIVA SUL SERVIZIO*\n\n"
            "L'assistenza tecnica è un *servizio a pagamento*, anche se il prodotto è *in garanzia*.\n\n"
            "✅ *In garanzia:* parti difettose sostituite senza costo\n\n"
            "💶 *Sempre a carico del cliente:*\n"
            "› Manodopera › Spostamento tecnico › Costo chiamata\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📍 *ZONA DI ROMA* _(dentro il GRA)_\n"
            "› Uscita + 1h lavoro: *€ 80,00 + IVA*\n"
            "› Ore successive: *€ 40,00/h + IVA*\n\n"
            "🗺 *FUORI ROMA* _(Provincia, Lazio, resto d'Italia)_\n"
            "› Km trasferta: *€ 0,70/km + IVA* _(A/R)_\n"
            "› Ore viaggio: *€ 32,00/h + IVA* _(A/R)_\n"
            "› Ore lavoro: *€ 40,00/h + IVA*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "_Pagamento direttamente al tecnico al termine del servizio._\n\n"
            "Accetti queste condizioni e vuoi procedere?"
        ),
        "condizioni_no": "❌ *Servizio non accettato*\n\nScrivi /start per ricominciare.\n\n_Rotondi Group Roma_",
        "nome":           "👤 *DATI PERSONALI*\n\nCome ti chiami?\n_Scrivi nome e cognome_",
        "ind_via":        "📍 *Indirizzo — Via/Piazza*\n\n_Es: Via Roma_",
        "ind_civico":     "🔢 *Numero civico*\n\n_Es: 10 oppure 10/A_",
        "ind_cap":        "📮 *CAP*\n\n_5 cifre — Es: 00100_",
        "ind_citta":      "🏙 *Città*\n\n_Es: Roma_",
        "ind_provincia":  "🗺 *Provincia*\n\n_Sigla 2 lettere — Es: RM_",
        "telefono":       "📞 *Numero di telefono*\n\n_Ti contatteremo su questo numero_",
        "foto_targhetta": "📸 *Foto targhetta macchina*\n\n_Inquadra l'etichetta con marca, modello e seriale_\n\nSe non riesci scrivi *salta*",
        "marca":          "🏭 *Marca della macchina*\n\n_Es: Samsung, LG, Bosch..._",
        "modello":        "🔖 *Modello della macchina*",
        "seriale":        "🔢 *Numero seriale*\n\n_Lo trovi sulla targhetta_",
        "problema":       "🔧 *Descrivi il problema*\n\n_Cosa succede? Da quando?_",
        "foto_macchina":  "📷 *Foto della macchina*\n\nSe non riesci scrivi *salta*",
        "riepilogo": (
            "━━━━━━━━━━━━━━━━━━━━\n📋  *RIEPILOGO RICHIESTA*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "👤  {nome}\n📍  {indirizzo}\n📞  {telefono}\n\n"
            "🏭  *{marca}*  ·  {modello}\n🔢  Seriale: {seriale}\n\n"
            "🔧  _{problema}_\n\n━━━━━━━━━━━━━━━━━━━━\nÈ tutto corretto?"
        ),
        "si":  "✅  Confermo",
        "no":  "✏️  Correggi",
        "registrata": (
            "✅ *Richiesta ricevuta!*\n\n"
            "Un tecnico *Rotondi Group Roma* la contatterà a breve.\n\n"
            "⚠️ Per *annullare* contatti URGENTEMENTE:\n"
            "📞 +39 06 41 40 0514\n\n_Il Team Rotondi Group Roma_"
        ),
        "assegnata": (
            "🎯 *Tecnico assegnato!*\n\n"
            "👨‍🔧  *{tecnico}*\n📞  Ufficio Roma: +39 06 41400617\n"
            "⏰  Arrivo previsto: *{fascia}*\n\n"
            "⚠️ Per annullare: 📞 *+39 06 41 40 0514*\n\n_Il Team Rotondi Group Roma_"
        ),
        "proposta": (
            "📅 *Proposta di appuntamento*\n\n"
            "Il tecnico *{tecnico}* propone:\n\n🗓  *{data_ora}*\n\n"
            "Accetta questa proposta?\n\n"
            "⚠️ _Se rifiuta, la richiesta tornerà disponibile per altri tecnici._"
        ),
        "proposta_accettata": (
            "🎉 *Appuntamento confermato!*\n\n"
            "👨‍🔧  *{tecnico}*\n📞  Ufficio Roma: +39 06 41400617\n"
            "🗓  *{data_ora}*\n\n"
            "⚠️ Per annullare: 📞 *+39 06 41 40 0514*\n\n_Il Team Rotondi Group Roma_"
        ),
        "proposta_rifiutata": "❌ *Proposta rifiutata*\n\nLa sua richiesta è ancora aperta.\n\n_Il Team Rotondi Group Roma_",
        "riassegnazione": "ℹ️ *Aggiornamento*\n\nLa sua richiesta è stata rimessa in circolo.\n\n_Il Team Rotondi Group Roma_",
        "annulla": "❌ Operazione annullata.\n\nScrivi /start per ricominciare.",
        "prev_fuori": (
            "💰 *PREVENTIVO INDICATIVO*\n"
            "────────────────────────\n"
            "📍 *Zona:* Provincia/Lazio/Italia\n"
            "🗺 *Distanza:* {dest_label} — {dur_label}\n\n"
            "{dettaglio}\n\n"
            "💶 *Costo minimo stimato:* €{costo_min:.2f} + IVA\n"
            "────────────────────────\n"
            "_Preventivo indicativo per 1h di lavoro._"
        ),
    },
    "en": {
        "gdpr": "🔒 *PRIVACY NOTICE (GDPR)*\n\nYour personal data will be processed by *Rotondi Group Srl*.\n\nDo you consent?",
        "gdpr_si": "✅ I Accept", "gdpr_no": "❌ I Decline",
        "gdpr_denied": "❌ *Consent not provided*\n\nWrite /start to begin again.",
        "cond_si": "✅ I accept", "cond_no": "❌ I decline",
        "condizioni": (
            "🔧 *ROTONDI GROUP SRL* — Rome Branch\n\n"
            "⚠️ Technical assistance is a *paid service*, even under *warranty*.\n\n"
            "📍 *Rome area (inside GRA):* call-out + 1h: *€ 80.00 + VAT*\n"
            "🗺 *Outside Rome:* € 0.70/km + € 32.00/h travel + € 40.00/h work\n\n"
            "Do you accept?"
        ),
        "condizioni_no": "❌ *Service not accepted*\n\nWrite /start.\n\n_Rotondi Group Roma_",
        "nome": "👤 *PERSONAL DETAILS*\n\nWhat is your full name?",
        "ind_via": "📍 *Street name*\n\n_E.g: Via Roma_",
        "ind_civico": "🔢 *Street number*\n\n_E.g: 10 or 10/A_",
        "ind_cap": "📮 *Postal code*\n\n_5 digits_",
        "ind_citta": "🏙 *City*",
        "ind_provincia": "🗺 *Province code*\n\n_2 letters, e.g: RM_",
        "telefono": "📞 *Phone number*",
        "foto_targhetta": "📸 *Machine label photo*\n\nIf not possible write *skip*",
        "marca": "🏭 *Brand*", "modello": "🔖 *Model*", "seriale": "🔢 *Serial number*",
        "problema": "🔧 *Describe the problem*",
        "foto_macchina": "📷 *Machine photo*\n\nIf not possible write *skip*",
        "riepilogo": "📋 *REQUEST SUMMARY*\n\n👤 {nome}\n📍 {indirizzo}\n📞 {telefono}\n🏭 *{marca}* · {modello}\n🔢 {seriale}\n🔧 _{problema}_\n\nAll correct?",
        "si": "✅ Confirm", "no": "✏️ Correct",
        "registrata": "✅ *Request received!*\n\nTo cancel: 📞 +39 06 41 40 0514\n\n_Rotondi Group Roma Team_",
        "assegnata": "🎯 *Technician assigned!*\n\n👨‍🔧 *{tecnico}*\n⏰ *{fascia}*\n\n⚠️ To cancel: 📞 *+39 06 41 40 0514*",
        "proposta": "📅 *Appointment proposal*\n\nTechnician *{tecnico}* proposes:\n🗓 *{data_ora}*\n\nDo you accept?",
        "proposta_accettata": "🎉 *Confirmed!*\n\n👨‍🔧 *{tecnico}*\n🗓 *{data_ora}*\n\n⚠️ To cancel: 📞 *+39 06 41 40 0514*",
        "proposta_rifiutata": "❌ *Proposal declined*\n\nYour request is still open.",
        "riassegnazione": "ℹ️ *Update*\n\nYour request has been re-opened.",
        "annulla": "❌ Cancelled. Write /start to begin again.",
        "prev_fuori": "💰 *INDICATIVE QUOTE*\n📍 Distance: {dest_label} — {dur_label}\n\n{dettaglio}\n\n💶 Min. cost: €{costo_min:.2f} + VAT",
    },
    "bn": {
        "gdpr": "🔒 *গোপনীয়তা নোটিশ (GDPR)*\n\n*Rotondi Group Srl* আপনার তথ্য প্রক্রিয়া করবে।\n\nআপনি কি সম্মতি দেন?",
        "gdpr_si": "✅ সম্মতি", "gdpr_no": "❌ না",
        "gdpr_denied": "❌ সম্মতি দেওয়া হয়নি\n\n/start লিখুন।",
        "cond_si": "✅ গ্রহণ করছি", "cond_no": "❌ গ্রহণ করছি না",
        "condizioni": "🔧 *ROTONDI GROUP SRL*\n\n⚠️ প্রযুক্তিগত সহায়তা পেইড সার্ভিস।\n\nআপনি কি শর্তগুলি গ্রহণ করেন?",
        "condizioni_no": "❌ সেবা গ্রহণ করা হয়নি\n\n/start লিখুন।",
        "nome": "👤 *নাম*", "ind_via": "📍 *রাস্তা*", "ind_civico": "🔢 *নম্বর*",
        "ind_cap": "📮 *CAP*", "ind_citta": "🏙 *শহর*", "ind_provincia": "🗺 *প্রদেশ কোড*",
        "telefono": "📞 *ফোন*", "foto_targhetta": "📸 *ছবি*\n\nskip লিখুন",
        "marca": "🏭 *ব্র্যান্ড*", "modello": "🔖 *মডেল*", "seriale": "🔢 *সিরিয়াল*",
        "problema": "🔧 *সমস্যা*", "foto_macchina": "📷 *ছবি*\n\nskip লিখুন",
        "riepilogo": "📋 *সারসংক্ষেপ*\n\n👤 {nome}\n📍 {indirizzo}\n📞 {telefono}\n🏭 *{marca}* · {modello}\n🔢 {seriale}\n🔧 _{problema}_",
        "si": "✅ নিশ্চিত", "no": "✏️ সংশোধন",
        "registrata": "✅ *অনুরোধ পাওয়া গেছে!*\n\nবাতিল: 📞 *+39 06 41 40 0514*",
        "assegnata": "🎯 *টেকনিশিয়ান!*\n\n👨‍🔧 *{tecnico}*\n⏰ *{fascia}*",
        "proposta": "📅 *প্রস্তাব*\n\n{tecnico}\n🗓 *{data_ora}*\n\nগ্রহণ করবেন?",
        "proposta_accettata": "🎉 *নিশ্চিত!*\n\n👨‍🔧 *{tecnico}*\n🗓 *{data_ora}*",
        "proposta_rifiutata": "❌ প্রস্তাব প্রত্যাখ্যাত।",
        "riassegnazione": "ℹ️ আপনার অনুরোধ পুনরায় খোলা হয়েছে।",
        "annulla": "❌ বাতিল।\n\n/start লিখুন।",
        "prev_fuori": "💰 *আনুমানিক খরচ*\n📍 {dest_label} — {dur_label}\n💶 সর্বনিম্ন: €{costo_min:.2f} + IVA",
    },
    "zh": {
        "gdpr": "🔒 *隐私通知 (GDPR)*\n\n*Rotondi Group Srl* 将处理您的个人数据。\n\n您是否同意?",
        "gdpr_si": "✅ 我同意", "gdpr_no": "❌ 我拒绝",
        "gdpr_denied": "❌ *未提供同意*\n\n输入 /start 重新开始。",
        "cond_si": "✅ 我接受", "cond_no": "❌ 拒绝",
        "condizioni": "🔧 *ROTONDI GROUP SRL* - 罗马分公司\n\n⚠️ 技术援助是付费服务，即使在保修期内。\n\n您接受吗?",
        "condizioni_no": "❌ *未接受服务*\n\n输入 /start。",
        "nome": "👤 *姓名*", "ind_via": "📍 *街道名称*", "ind_civico": "🔢 *门牌号*",
        "ind_cap": "📮 *邮政编码*", "ind_citta": "🏙 *城市*", "ind_provincia": "🗺 *省份代码*",
        "telefono": "📞 *电话号码*", "foto_targhetta": "📸 *铭牌照片*\n\n如无法拍照写 *skip*",
        "marca": "🏭 *品牌*", "modello": "🔖 *型号*", "seriale": "🔢 *序列号*",
        "problema": "🔧 *描述问题*", "foto_macchina": "📷 *机器照片*\n\n如无法拍照写 *skip*",
        "riepilogo": "📋 *请求摘要*\n\n👤 {nome}\n📍 {indirizzo}\n📞 {telefono}\n🏭 *{marca}* · {modello}\n🔢 {seriale}\n🔧 _{problema}_\n\n一切正确吗?",
        "si": "✅ 确认", "no": "✏️ 更正",
        "registrata": "✅ *请求已收到！*\n\n取消: 📞 *+39 06 41 40 0514*",
        "assegnata": "🎯 *已分配技术人员！*\n\n👨‍🔧 *{tecnico}*\n⏰ *{fascia}*",
        "proposta": "📅 *预约提议*\n\n技术人员 *{tecnico}* 提议:\n🗓 *{data_ora}*\n\n您接受吗?",
        "proposta_accettata": "🎉 *预约已确认！*\n\n👨‍🔧 *{tecnico}*\n🗓 *{data_ora}*",
        "proposta_rifiutata": "❌ 提议已拒绝。",
        "riassegnazione": "ℹ️ 您的请求已重新开放。",
        "annulla": "❌ 已取消。",
        "prev_fuori": "💰 *预估报价*\n📍 {dest_label} — {dur_label}\n💶 预估最低: €{costo_min:.2f} + 增值税",
    },
    "ar": {
        "gdpr": "🔒 *إشعار الخصوصية (GDPR)*\n\nستعالج *Rotondi Group Srl* بياناتك.\n\nهل توافق?",
        "gdpr_si": "✅ أوافق", "gdpr_no": "❌ لا أوافق",
        "gdpr_denied": "❌ *لم تُقدَّم الموافقة*\n\nاكتب /start من جديد.",
        "cond_si": "✅ أقبل", "cond_no": "❌ أرفض",
        "condizioni": "🔧 *ROTONDI GROUP SRL* - فرع روما\n\n⚠️ المساعدة الفنية خدمة مدفوعة حتى في الضمان.\n\nهل تقبل الشروط?",
        "condizioni_no": "❌ *لم تُقبَل الخدمة*\n\nاكتب /start.",
        "nome": "👤 *الاسم*", "ind_via": "📍 *اسم الشارع*", "ind_civico": "🔢 *رقم المبنى*",
        "ind_cap": "📮 *الرمز البريدي*", "ind_citta": "🏙 *المدينة*", "ind_provincia": "🗺 *رمز المحافظة*",
        "telefono": "📞 *رقم الهاتف*", "foto_targhetta": "📸 *صورة اللوحة*\n\nإذا لم تستطع اكتب *skip*",
        "marca": "🏭 *الماركة*", "modello": "🔖 *الموديل*", "seriale": "🔢 *الرقم التسلسلي*",
        "problema": "🔧 *صف المشكلة*", "foto_macchina": "📷 *صورة الجهاز*\n\nإذا لم تستطع اكتب *skip*",
        "riepilogo": "📋 *ملخص الطلب*\n\n👤 {nome}\n📍 {indirizzo}\n📞 {telefono}\n🏭 *{marca}* · {modello}\n🔢 {seriale}\n🔧 _{problema}_\n\nهل كل شيء صحيح?",
        "si": "✅ تأكيد", "no": "✏️ تصحيح",
        "registrata": "✅ *تم استلام طلبك!*\n\nللإلغاء: 📞 *+39 06 41 40 0514*",
        "assegnata": "🎯 *تم تعيين فني!*\n\n👨‍🔧 *{tecnico}*\n⏰ *{fascia}*",
        "proposta": "📅 *اقتراح موعد*\n\nالفني *{tecnico}* يقترح:\n🗓 *{data_ora}*\n\nهل تقبل?",
        "proposta_accettata": "🎉 *تم تأكيد الموعد!*\n\n👨‍🔧 *{tecnico}*\n🗓 *{data_ora}*",
        "proposta_rifiutata": "❌ تم رفض الاقتراح.",
        "riassegnazione": "ℹ️ تم إعادة فتح طلبك.",
        "annulla": "❌ تم الإلغاء.",
        "prev_fuori": "💰 *عرض سعر تقريبي*\n📍 {dest_label} — {dur_label}\n💶 الحد الأدنى: €{costo_min:.2f} + ضريبة",
    },
}


def t(lingua, chiave, **kwargs):
    testo = TESTI.get(lingua, TESTI["it"]).get(chiave, TESTI["it"].get(chiave, ""))
    return testo.format(azienda=NOME_AZIENDA, **kwargs)


def traduci(testo, lingua_src="auto"):
    try:
        if lingua_src == "it": return testo
        return GoogleTranslator(source="auto", target="it").translate(testo) or testo
    except Exception as e:
        log.error(f"Traduzione: {e}"); return testo


# ── DATABASE ─────────────────────────────────────────────────────────────────
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chiamate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER, username TEXT, lingua TEXT,
                nome_cliente TEXT, indirizzo TEXT, telefono TEXT,
                problema_it TEXT, problema_originale TEXT,
                stato TEXT DEFAULT 'aperta',
                tecnico_id INTEGER, tecnico_nome TEXT, fascia_oraria TEXT,
                data_apertura TEXT, data_assegnazione TEXT, msg_id_gruppo INTEGER,
                marca TEXT, modello TEXT, seriale TEXT,
                foto_targhetta_id TEXT, foto_macchina_id TEXT,
                data_ora_proposta TEXT, tecnico_proposta_id INTEGER
            )
        """)
        for col in ["marca TEXT","modello TEXT","seriale TEXT",
                    "foto_targhetta_id TEXT","foto_macchina_id TEXT",
                    "data_ora_proposta TEXT","tecnico_proposta_id INTEGER"]:
            try: conn.execute(f"ALTER TABLE chiamate ADD COLUMN {col}")
            except: pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tecnici (
                telegram_id INTEGER PRIMARY KEY, nome TEXT, telefono TEXT
            )
        """)
        conn.commit()


def get_chiamata(cid):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM chiamate WHERE id=?", (cid,)).fetchone()
    return dict(row) if row else None


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
        cid = cur.lastrowid; conn.commit()
    return cid


def assegna(cid, tecnico_id, tecnico_nome, fascia):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE chiamate SET stato='assegnata', tecnico_id=?, tecnico_nome=?,
            fascia_oraria=?, data_assegnazione=? WHERE id=?
        """, (tecnico_id, tecnico_nome, fascia,
              datetime.now().strftime("%d/%m/%Y %H:%M"), cid))
        conn.commit()


def set_proposta(cid, tecnico_id, tecnico_nome, data_ora):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE chiamate SET stato='in_attesa_conferma',
            tecnico_proposta_id=?, tecnico_nome=?, data_ora_proposta=? WHERE id=?
        """, (tecnico_id, tecnico_nome, data_ora, cid))
        conn.commit()


def reset_proposta(cid):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE chiamate SET stato='aperta',
            tecnico_proposta_id=NULL, tecnico_nome=NULL, data_ora_proposta=NULL WHERE id=?
        """, (cid,))
        conn.commit()


def aggiorna_msg_id(cid, msg_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE chiamate SET msg_id_gruppo=? WHERE id=?", (msg_id, cid))
        conn.commit()


def get_tecnico(tid):
    with sqlite3.connect(DB_PATH) as conn:
        r = conn.execute("SELECT nome, telefono FROM tecnici WHERE telegram_id=?", (tid,)).fetchone()
    return {"nome": r[0], "telefono": r[1] or ""} if r else None


def get_tecnico_nome(tid):
    tc = get_tecnico(tid); return tc["nome"] if tc else None


def registra_tecnico(tid, nome, telefono=None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO tecnici VALUES (?,?,?)", (tid, nome, telefono))
        conn.commit()


def sblocca_chiamata_db(cid):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE chiamate SET stato='aperta', tecnico_id=NULL, tecnico_nome=NULL,
            fascia_oraria=NULL, data_assegnazione=NULL,
            tecnico_proposta_id=NULL, data_ora_proposta=NULL WHERE id=?
        """, (cid,))
        conn.commit()


def lista_chiamate_db(limite=20):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("""
            SELECT id,nome_cliente,indirizzo,stato,tecnico_nome,fascia_oraria,data_apertura,lingua
            FROM chiamate ORDER BY id DESC LIMIT ?
        """, (limite,)).fetchall()


# ── PREVENTIVO ───────────────────────────────────────────────────────────────
def calcola_preventivo_bot(indirizzo_cliente):
    try:
        import requests as rq
        r = rq.get("https://maps.googleapis.com/maps/api/distancematrix/json", params={
            "origins": SEDE, "destinations": indirizzo_cliente,
            "mode": "driving", "key": GMAPS_KEY, "language": "it"
        }, timeout=10)
        data = r.json()
        if data.get("status") != "OK": return None
        el = data["rows"][0]["elements"][0]
        if el.get("status") != "OK": return None
        dist_km = el["distance"]["value"] / 1000
        dur_h   = el["duration"]["value"] / 3600
        if dist_km < 10:
            return {"zona":"inside_gra","dist_km":round(dist_km,1),"dur_h":round(dur_h,1),
                    "costo_min":80.0,"dettaglio":"Uscita + 1h lavoro: *€ 80,00 + IVA*",
                    "dest_label":el["distance"]["text"],"dur_label":el["duration"]["text"]}
        dist_ar=dist_km*2; dur_ar=math.ceil(dur_h*2)
        costo_km=dist_ar*0.70; costo_v=dur_ar*32.0; costo=costo_km+costo_v+40.0
        return {"zona":"outside_gra","dist_km":round(dist_km,1),"dur_h":round(dur_h,1),
                "costo_min":round(costo,2),
                "dettaglio":(f"Km A/R ({dist_ar:.0f}km × €0,70): *€{costo_km:.2f}*\n"
                             f"Viaggio A/R ({dur_ar}h × €32,00): *€{costo_v:.2f}*\n"
                             f"1h lavoro: *€40,00*"),
                "dest_label":el["distance"]["text"],"dur_label":el["duration"]["text"]}
    except Exception as e:
        log.error(f"Maps: {e}"); return None


# ── CONVERSAZIONE CLIENTE ─────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in BACKOFFICE_IDS:
        await update.message.reply_text(
            f"👩‍💼 *Benvenuta nel sistema {NOME_AZIENDA}!*\n\nComandi:\n/lista /aperte /assegnate /storico /statistiche",
            parse_mode="Markdown"); return ConversationHandler.END
    if get_tecnico_nome(user_id):
        await update.message.reply_text(
            f"👨‍🔧 *Bentornato {get_tecnico_nome(user_id)}!*\n\n/chiamate",
            parse_mode="Markdown"); return ConversationHandler.END
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇹 Italiano", callback_data="lang_it"),
         InlineKeyboardButton("🇬🇧 English",  callback_data="lang_en")],
        [InlineKeyboardButton("🇧🇩 বাংলা",    callback_data="lang_bn"),
         InlineKeyboardButton("🇨🇳 中文",      callback_data="lang_zh")],
        [InlineKeyboardButton("🇸🇦 العربية",  callback_data="lang_ar")],
    ])
    await update.message.reply_text(
        f"👋 Benvenuto / Welcome / স্বাগতম / 欢迎 / أهلاً\n\n*{NOME_AZIENDA}*\n\nScegli la lingua:",
        reply_markup=kb, parse_mode="Markdown")
    return SCEGLI_LINGUA


async def scegli_lingua_condizioni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    lingua = query.data.replace("lang_", "")
    context.user_data["lingua"] = lingua
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lingua,"gdpr_si"), callback_data="gdpr_si"),
        InlineKeyboardButton(t(lingua,"gdpr_no"), callback_data="gdpr_no"),
    ]])
    await query.edit_message_text(t(lingua,"gdpr"), reply_markup=kb, parse_mode="Markdown")
    return GDPR


async def gestisci_gdpr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    lingua = context.user_data.get("lingua","it")
    if query.data == "gdpr_no":
        await query.edit_message_text(t(lingua,"gdpr_denied"), parse_mode="Markdown")
        return ConversationHandler.END
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lingua,"cond_si"), callback_data="cond_si"),
        InlineKeyboardButton(t(lingua,"cond_no"), callback_data="cond_no"),
    ]])
    await query.edit_message_text(t(lingua,"condizioni"), reply_markup=kb, parse_mode="Markdown")
    return CONDIZIONI


async def gestisci_condizioni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    lingua = context.user_data.get("lingua","it")
    if query.data == "cond_no":
        await query.edit_message_text(t(lingua,"condizioni_no"), parse_mode="Markdown")
        return ConversationHandler.END
    await query.edit_message_text(f"*{NOME_AZIENDA}*\n\n" + t(lingua,"nome"), parse_mode="Markdown")
    return NOME


async def raccogli_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["nome_orig"] = update.message.text.strip()
    await update.message.reply_text(t(lingua,"ind_via"), parse_mode="Markdown")
    return IND_VIA

async def raccogli_via(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["ind_via"] = update.message.text.strip()
    await update.message.reply_text(t(lingua,"ind_civico"), parse_mode="Markdown")
    return IND_CIVICO

async def raccogli_civico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["ind_civico"] = update.message.text.strip()
    await update.message.reply_text(t(lingua,"ind_cap"), parse_mode="Markdown")
    return IND_CAP

async def raccogli_cap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["ind_cap"] = update.message.text.strip()
    await update.message.reply_text(t(lingua,"ind_citta"), parse_mode="Markdown")
    return IND_CITTA

async def raccogli_citta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["ind_citta"] = update.message.text.strip()
    await update.message.reply_text(t(lingua,"ind_provincia"), parse_mode="Markdown")
    return IND_PROVINCIA

async def raccogli_provincia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["ind_provincia"] = update.message.text.strip().upper()
    indirizzo = (f"{context.user_data.get('ind_via','')}, "
                 f"{context.user_data.get('ind_civico','')}, "
                 f"{context.user_data.get('ind_cap','')} "
                 f"{context.user_data.get('ind_citta','')} "
                 f"({context.user_data['ind_provincia']}), Italia")
    context.user_data["indirizzo"] = indirizzo
    prev = calcola_preventivo_bot(indirizzo)
    if prev and prev["zona"] == "outside_gra":
        context.user_data["preventivo"] = prev
        await update.message.reply_text(
            t(lingua,"prev_fuori", dest_label=prev["dest_label"],
              dur_label=prev["dur_label"], dettaglio=prev["dettaglio"],
              costo_min=prev["costo_min"]), parse_mode="Markdown")
    await update.message.reply_text(t(lingua,"telefono"), parse_mode="Markdown")
    return TELEFONO

async def raccogli_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["telefono"] = update.message.text.strip()
    await update.message.reply_text(t(lingua,"foto_targhetta"), parse_mode="Markdown")
    return FOTO_TARGHETTA

async def raccogli_foto_targhetta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["foto_targhetta_id"] = (
        update.message.photo[-1].file_id if update.message.photo else None)
    await update.message.reply_text(t(lingua,"marca"), parse_mode="Markdown")
    return MARCA

async def raccogli_marca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["marca"] = traduci(update.message.text.strip(), lingua)
    await update.message.reply_text(t(lingua,"modello"), parse_mode="Markdown")
    return MODELLO

async def raccogli_modello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["modello"] = traduci(update.message.text.strip(), lingua)
    await update.message.reply_text(t(lingua,"seriale"), parse_mode="Markdown")
    return SERIALE

async def raccogli_seriale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["seriale"] = update.message.text.strip()
    await update.message.reply_text(t(lingua,"problema"), parse_mode="Markdown")
    return PROBLEMA

async def raccogli_problema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    orig = update.message.text.strip()
    context.user_data["problema_orig"] = orig
    context.user_data["problema_it"]   = traduci(orig, lingua)
    await update.message.reply_text(t(lingua,"foto_macchina"), parse_mode="Markdown")
    return FOTO_MACCHINA

async def raccogli_foto_macchina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    context.user_data["foto_macchina_id"] = (
        update.message.photo[-1].file_id if update.message.photo else None)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lingua,"si"), callback_data="conferma_si"),
        InlineKeyboardButton(t(lingua,"no"), callback_data="conferma_no"),
    ]])
    await update.message.reply_text(
        t(lingua,"riepilogo",
          nome=context.user_data["nome_orig"],
          indirizzo=context.user_data["indirizzo"],
          telefono=context.user_data["telefono"],
          marca=context.user_data.get("marca","-"),
          modello=context.user_data.get("modello","-"),
          seriale=context.user_data.get("seriale","-"),
          problema=context.user_data["problema_orig"]),
        reply_markup=kb, parse_mode="Markdown")
    return CONFERMA


async def conferma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    lingua = context.user_data.get("lingua","it")
    if query.data == "conferma_no":
        await query.edit_message_text(t(lingua,"annulla"), parse_mode="Markdown")
        return ConversationHandler.END
    user    = query.from_user
    nome_it = traduci(context.user_data["nome_orig"], lingua)
    cid     = salva_chiamata(
        user.id, user.username or str(user.id), lingua, nome_it,
        context.user_data["indirizzo"], context.user_data["telefono"],
        context.user_data["problema_it"], context.user_data["problema_orig"],
        context.user_data.get("marca",""), context.user_data.get("modello",""),
        context.user_data.get("seriale",""),
        context.user_data.get("foto_targhetta_id"),
        context.user_data.get("foto_macchina_id"),
    )
    await query.edit_message_text(t(lingua,"registrata"), parse_mode="Markdown")
    flag = FLAGS.get(lingua,"🌍")
    sezione_prob = f"🔧 *Problema (IT):* {context.user_data['problema_it']}"
    if lingua != "it":
        sezione_prob += f"\n🔧 *Originale {flag}:* {context.user_data['problema_orig']}"
    prev = context.user_data.get("preventivo")
    prev_text = (f"\n💰 *Preventivo:* €{prev['costo_min']:.2f} + IVA"
                 f" ({prev['dest_label']} — {prev['dur_label']})" if prev else "")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🕛 Entro le 12:00", callback_data=f"fascia_{cid}_entro12"),
         InlineKeyboardButton("🕕 Entro le 18:00", callback_data=f"fascia_{cid}_entro18")],
        [InlineKeyboardButton("📅 In giornata",    callback_data=f"fascia_{cid}_giornata"),
         InlineKeyboardButton("📆 Entro domani",   callback_data=f"fascia_{cid}_domani")],
        [InlineKeyboardButton("🗓 Da programmare", callback_data=f"programma_{cid}_start")],
    ])
    link_maps = ("https://www.google.com/maps/search/?api=1&query="
                 + context.user_data["indirizzo"].replace(" ","+"))
    testo_gruppo = (
        f"🔔 *NUOVA CHIAMATA #{cid}* {flag}\n{'─'*30}\n"
        f"👤 *Cliente:* {nome_it}\n"
        f"📍 *Indirizzo:* {context.user_data['indirizzo']}\n"
        f"🗺 [Apri su Google Maps]({link_maps})\n"
        f"📞 *Tel:* {context.user_data['telefono']}\n"
        f"🆔 *Telegram:* @{user.username or user.id}\n"
        f"🏷 *Marca:* {context.user_data.get('marca','-')} | *Modello:* {context.user_data.get('modello','-')}\n"
        f"🔢 *Seriale:* {context.user_data.get('seriale','-')}\n"
        f"{sezione_prob}{prev_text}\n{'─'*30}\n"
        f"⏰ Primo tecnico disponibile:"
    )
    msg = await context.bot.send_message(
        chat_id=TECNICI_GROUP_ID, text=testo_gruppo,
        reply_markup=kb, parse_mode="Markdown")
    aggiorna_msg_id(cid, msg.message_id)
    for foto, cap in [
        (context.user_data.get("foto_targhetta_id"), f"📸 Targhetta — Chiamata #{cid}"),
        (context.user_data.get("foto_macchina_id"),  f"📷 Macchina — Chiamata #{cid}"),
    ]:
        if foto:
            try: await context.bot.send_photo(chat_id=TECNICI_GROUP_ID, photo=foto, caption=cap)
            except Exception as e: log.error(f"Foto: {e}")
    for bo_id in BACKOFFICE_IDS:
        try:
            await context.bot.send_message(chat_id=bo_id,
                text=(f"📲 *Nuova richiesta #{cid}* {flag}\n\n"
                      f"👤 {nome_it}\n📍 {context.user_data['indirizzo']}\n"
                      f"📞 {context.user_data['telefono']}\n"
                      f"🏷 {context.user_data.get('marca','-')} — {context.user_data.get('modello','-')}\n"
                      f"🔧 {context.user_data['problema_it']}"
                      + (f"\n🔧 Orig: {context.user_data['problema_orig']}" if lingua!="it" else "")),
                parse_mode="Markdown")
        except Exception as e: log.error(f"BO: {e}")
    return ConversationHandler.END


async def annulla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua","it")
    await update.message.reply_text(t(lingua,"annulla"), parse_mode="Markdown")
    return ConversationHandler.END


# ── FASCIA ORARIA ─────────────────────────────────────────────────────────────
FASCE = {"entro12":"entro le 12:00","entro18":"entro le 18:00",
         "giornata":"in giornata","domani":"entro domani"}

async def gestisci_fascia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parti = query.data.split("_"); cid = int(parti[1]); fascia = FASCE.get(parti[2],parti[2])
    ch = get_chiamata(cid)
    if not ch: await query.answer("⚠️ Chiamata non trovata.", show_alert=True); return
    if ch["stato"] in ("assegnata","in_attesa_conferma"):
        await query.answer("⚠️ Già presa!", show_alert=True); return
    tid    = query.from_user.id
    t_nome = f"{query.from_user.first_name or ''} {query.from_user.last_name or ''}".strip()
    tdb    = get_tecnico(tid)
    nome   = tdb["nome"] if tdb else t_nome
    if not tdb: registra_tecnico(tid, t_nome)
    assegna(cid, tid, nome, fascia)
    await query.edit_message_text(
        f"✅ *CHIAMATA #{cid} — ASSEGNATA*\n{'─'*30}\n"
        f"👤 {ch['nome_cliente']}\n📍 {ch['indirizzo']}\n"
        f"🔧 {ch['problema_it']}\n{'─'*30}\n"
        f"👨‍🔧 {nome} | ⏰ {fascia}", parse_mode="Markdown")
    await query.answer("✅ Assegnata a te!")
    for bo_id in BACKOFFICE_IDS:
        try: await context.bot.send_message(chat_id=bo_id,
            text=f"✅ *Chiamata #{cid} assegnata*\n👤 {ch['nome_cliente']}\n👨‍🔧 {nome}\n⏰ {fascia}",
            parse_mode="Markdown")
        except: pass
    try:
        await context.bot.send_message(chat_id=ch["telegram_id"],
            text=t(ch["lingua"],"assegnata",tecnico=nome,fascia=fascia),
            parse_mode="Markdown")
    except Exception as e: log.error(f"Msg cliente: {e}")


# ── RICHIESTE WEB ─────────────────────────────────────────────────────────────
WEB_DB_PATH = "web_assistenza.db"
FASCE_IT = {"entro12":"Entro le 12:00","entro18":"Entro le 18:00",
            "giornata":"In giornata","domani":"Entro domani","programma":"Da programmare"}

async def gestisci_wfascia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    parti = query.data.split("_"); protocollo = parti[1]; fascia_it = FASCE_IT.get(parti[2],parti[2])
    tid    = query.from_user.id
    t_nome = f"{query.from_user.first_name or ''} {query.from_user.last_name or ''}".strip()
    tdb    = get_tecnico(tid); nome = tdb["nome"] if tdb else t_nome
    if not tdb: registra_tecnico(tid, t_nome)
    try:
        with sqlite3.connect(WEB_DB_PATH) as conn:
            r = conn.execute(
                "SELECT protocollo,nome,indirizzo,telefono,email,marca,modello,problema,stato,lingua"
                " FROM richieste_web WHERE protocollo=?", (protocollo,)).fetchone()
    except Exception as e: log.error(f"Web DB: {e}"); return
    if not r: await query.answer("⚠️ Non trovata.", show_alert=True); return
    if r[8] == "assegnata": await query.answer("⚠️ Già assegnata!", show_alert=True); return
    try:
        with sqlite3.connect(WEB_DB_PATH) as conn:
            conn.execute("UPDATE richieste_web SET stato=?,tecnico=?,fascia=? WHERE protocollo=?",
                         ("assegnata", nome, fascia_it, protocollo)); conn.commit()
    except Exception as e: log.error(f"Web DB update: {e}")
    await query.edit_message_text(
        f"✅ *RICHIESTA WEB {protocollo} — ASSEGNATA*\n"
        f"👤 {r[1]}\n📍 {r[2]}\n🔧 {r[7]}\n👨‍🔧 {nome} | ⏰ {fascia_it}", parse_mode="Markdown")
    for bo_id in BACKOFFICE_IDS:
        try: await context.bot.send_message(chat_id=bo_id,
            text=f"✅ *Web {protocollo} assegnata*\n👤 {r[1]}\n👨‍🔧 {nome}\n⏰ {fascia_it}",
            parse_mode="Markdown")
        except: pass
    email_cliente = r[4]; lingua = r[9] or "it"
    SMTP_U=os.environ.get("SMTP_USER",""); SMTP_P=os.environ.get("SMTP_PASS","")
    SMTP_F=os.environ.get("SMTP_FROM",""); SMTP_H=os.environ.get("SMTP_HOST","smtp.gmail.com")
    SMTP_PO=int(os.environ.get("SMTP_PORT","587"))
    if email_cliente and SMTP_U and SMTP_P:
        import smtplib; from email.mime.text import MIMEText; from email.mime.multipart import MIMEMultipart
        corpo = (f"<p>Gentile <b>{r[1]}</b></p>"
                 f"<p>Protocollo: <b>{protocollo}</b></p>"
                 f"<p>Tecnico: <b>{nome}</b></p><p>Orario: <b>{fascia_it}</b></p>"
                 f"<p>Ufficio Roma: +39 06 41400617</p>")
        try:
            msg_e = MIMEMultipart("alternative")
            msg_e["Subject"] = f"Rotondi Group Roma — Tecnico assegnato #{protocollo}"
            msg_e["From"] = SMTP_F; msg_e["To"] = email_cliente
            msg_e.attach(MIMEText(corpo,"html"))
            with smtplib.SMTP(SMTP_H,SMTP_PO) as s:
                s.starttls(); s.login(SMTP_U,SMTP_P); s.sendmail(SMTP_F,email_cliente,msg_e.as_string())
        except Exception as e: log.error(f"Email: {e}")


# ── DA PROGRAMMARE ────────────────────────────────────────────────────────────
def genera_keyboard_date(cid):
    oggi=datetime.now(); bottoni=[]; riga=[]
    for i in range(7):
        g=oggi+timedelta(
