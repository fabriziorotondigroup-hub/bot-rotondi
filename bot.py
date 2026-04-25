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
        g=oggi+timedelta(days=i)
        riga.append(InlineKeyboardButton(g.strftime("%a %d/%m"),
            callback_data=f"pdata_{cid}_{g.strftime('%d-%m-%Y')}"))
        if len(riga)==2: bottoni.append(riga); riga=[]
    if riga: bottoni.append(riga)
    bottoni.append([InlineKeyboardButton("❌ Annulla", callback_data=f"pdata_{cid}_annulla")])
    return InlineKeyboardMarkup(bottoni)

def genera_keyboard_ore(cid, data_str):
    ore=["08:00","09:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00","19:00"]
    bottoni=[]; riga=[]
    for ora in ore:
        riga.append(InlineKeyboardButton(ora,
            callback_data=f"pora_{cid}_{data_str}_{ora.replace(':','')}"))
        if len(riga)==4: bottoni.append(riga); riga=[]
    if riga: bottoni.append(riga)
    bottoni.append([InlineKeyboardButton("⬅️ Torna alle date", callback_data=f"programma_{cid}_start")])
    return InlineKeyboardMarkup(bottoni)

def _keyboard_fascia(cid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕛 Entro le 12:00", callback_data=f"fascia_{cid}_entro12"),
         InlineKeyboardButton("🕕 Entro le 18:00", callback_data=f"fascia_{cid}_entro18")],
        [InlineKeyboardButton("📅 In giornata",    callback_data=f"fascia_{cid}_giornata"),
         InlineKeyboardButton("📆 Entro domani",   callback_data=f"fascia_{cid}_domani")],
        [InlineKeyboardButton("🗓 Da programmare", callback_data=f"programma_{cid}_start")],
    ])

async def gestisci_programma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    cid = int(query.data.split("_")[1]); ch = get_chiamata(cid)
    if not ch: return
    if ch["stato"] == "assegnata": await query.answer("⚠️ Già assegnata!", show_alert=True); return
    if ch["stato"] == "in_attesa_conferma": await query.answer("⚠️ In attesa conferma!", show_alert=True); return
    await query.edit_message_text(
        f"🗓 *Da programmare #{cid}*\n\n👤 {ch['nome_cliente']}\nScegli la *data*:",
        reply_markup=genera_keyboard_date(cid), parse_mode="Markdown")

async def gestisci_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    parti=query.data.split("_"); cid=int(parti[1]); data_str=parti[2]
    if data_str == "annulla":
        ch=get_chiamata(cid)
        if not ch: return
        link_maps="https://www.google.com/maps/search/?api=1&query="+ch["indirizzo"].replace(" ","+")
        await query.edit_message_text(
            f"🔔 *CHIAMATA #{cid}*\n👤 {ch['nome_cliente']}\n📍 {ch['indirizzo']}\n"
            f"🗺 [Google Maps]({link_maps})\n📞 {ch['telefono']}\n🔧 {ch['problema_it']}\n\n⏰ Primo tecnico:",
            reply_markup=_keyboard_fascia(cid), parse_mode="Markdown"); return
    ch=get_chiamata(cid)
    if not ch: return
    await query.edit_message_text(
        f"🗓 *Da programmare #{cid}*\n👤 {ch['nome_cliente']}\n📅 Data: {data_str.replace('-','/')}\n\nScegli l'*ora*:",
        reply_markup=genera_keyboard_ore(cid, data_str), parse_mode="Markdown")

async def gestisci_ora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    parti=query.data.split("_"); cid=int(parti[1]); data_str=parti[2]; ora_str=parti[3]
    data_ora=f"{data_str.replace('-','/')} alle {ora_str[:2]}:{ora_str[2:]}"
    ch=get_chiamata(cid)
    if not ch: return
    if ch["stato"] in ("assegnata","in_attesa_conferma"):
        await query.answer("⚠️ Non disponibile!", show_alert=True); return
    tid=query.from_user.id
    t_nome=f"{query.from_user.first_name or ''} {query.from_user.last_name or ''}".strip()
    tdb=get_tecnico(tid); nome=tdb["nome"] if tdb else t_nome
    if not tdb: registra_tecnico(tid, t_nome)
    set_proposta(cid, tid, nome, data_ora)
    await query.edit_message_text(
        f"⏳ *CHIAMATA #{cid} — IN ATTESA CONFERMA*\n"
        f"👤 {ch['nome_cliente']}\n👨‍🔧 {nome}\n📅 Proposta: {data_ora}\n\n_In attesa..._",
        parse_mode="Markdown")
    kb_c = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Accetto", callback_data=f"cprop_{cid}_si"),
        InlineKeyboardButton("❌ Rifiuto", callback_data=f"cprop_{cid}_no"),
    ]])
    try:
        await context.bot.send_message(chat_id=ch["telegram_id"],
            text=t(ch["lingua"],"proposta",tecnico=nome,data_ora=data_ora),
            reply_markup=kb_c, parse_mode="Markdown")
    except Exception as e: log.error(f"Proposta cliente: {e}")
    for bo_id in BACKOFFICE_IDS:
        try: await context.bot.send_message(chat_id=bo_id,
            text=f"⏳ *Chiamata #{cid} in attesa*\n👤 {ch['nome_cliente']}\n👨‍🔧 {nome}\n📅 {data_ora}",
            parse_mode="Markdown")
        except: pass

async def gestisci_conferma_proposta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    parti=query.data.split("_"); cid=int(parti[1]); risposta=parti[2]
    ch=get_chiamata(cid)
    if not ch: await query.edit_message_text("⚠️ Chiamata non trovata."); return
    if ch["stato"] != "in_attesa_conferma": await query.edit_message_text("ℹ️ Proposta non più valida."); return
    lingua=ch["lingua"]; data_ora=ch.get("data_ora_proposta") or "—"
    nome_tecnico=ch.get("tecnico_nome") or "—"; tecnico_id=ch.get("tecnico_proposta_id")
    if risposta == "si":
        assegna(cid, tecnico_id, nome_tecnico, data_ora)
        await query.edit_message_text(
            t(lingua,"proposta_accettata",tecnico=nome_tecnico,data_ora=data_ora), parse_mode="Markdown")
        try: await context.bot.send_message(chat_id=TECNICI_GROUP_ID,
            text=f"✅ *CHIAMATA #{cid} CONFERMATA*\n👤 {ch['nome_cliente']}\n👨‍🔧 {nome_tecnico}\n📅 {data_ora}",
            parse_mode="Markdown")
        except: pass
        for bo_id in BACKOFFICE_IDS:
            try: await context.bot.send_message(chat_id=bo_id,
                text=f"✅ *Chiamata #{cid} confermata*\n👤 {ch['nome_cliente']}\n👨‍🔧 {nome_tecnico}\n📅 {data_ora}",
                parse_mode="Markdown")
            except: pass
    else:
        reset_proposta(cid)
        await query.edit_message_text(t(lingua,"proposta_rifiutata"), parse_mode="Markdown")
        try: await context.bot.send_message(chat_id=TECNICI_GROUP_ID,
            text=f"❌ *CHIAMATA #{cid} — PROPOSTA RIFIUTATA*\n👤 {ch['nome_cliente']}\nTornata disponibile!",
            reply_markup=_keyboard_fascia(cid), parse_mode="Markdown")
        except: pass
        for bo_id in BACKOFFICE_IDS:
            try: await context.bot.send_message(chat_id=bo_id,
                text=f"❌ *Chiamata #{cid} proposta rifiutata*\n👤 {ch['nome_cliente']}",
                parse_mode="Markdown")
            except: pass


# ── BACK OFFICE ───────────────────────────────────────────────────────────────
async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in BACKOFFICE_IDS:
        await update.message.reply_text("⛔ Non autorizzato."); return
    rows = lista_chiamate_db()
    if not rows: await update.message.reply_text("📋 Nessuna chiamata."); return
    for r in rows:
        emoji = "🟡" if r[3]=="aperta" else ("⏳" if r[3]=="in_attesa_conferma" else "✅")
        flag  = FLAGS.get(r[7],"🌍")
        testo = f"{emoji} *#{r[0]}* {flag} — {r[1]}\n📍 {r[2]}\n"
        if r[3] in ("assegnata","in_attesa_conferma"): testo += f"👨‍🔧 {r[4]} | {r[5]}\n"
        testo += f"🕐 {r[6]}"
        if r[3] in ("assegnata","in_attesa_conferma"):
            await update.message.reply_text(testo, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔓 Sblocca", callback_data=f"sblocca_{r[0]}")]]))
        else: await update.message.reply_text(testo, parse_mode="Markdown")

async def aperte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in BACKOFFICE_IDS:
        await update.message.reply_text("⛔ Non autorizzato."); return
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""SELECT id,nome_cliente,indirizzo,data_apertura,lingua,stato,tecnico_nome
            FROM chiamate WHERE stato IN ('aperta','in_attesa_conferma') ORDER BY id DESC""").fetchall()
    if not rows: await update.message.reply_text("✅ Nessuna chiamata aperta!"); return
    await update.message.reply_text(f"🟡 *Chiamate aperte: {len(rows)}*", parse_mode="Markdown")
    for r in rows:
        emoji = "⏳" if r[5]=="in_attesa_conferma" else "🟡"
        testo = f"{emoji} *#{r[0]}* {FLAGS.get(r[4],'🌍')} — {r[1]}\n📍 {r[2]}\n🕐 {r[3]}"
        if r[5]=="in_attesa_conferma" and r[6]: testo += f"\n⏳ In attesa da: {r[6]}"
        await update.message.reply_text(testo, parse_mode="Markdown")

async def assegnate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in BACKOFFICE_IDS:
        await update.message.reply_text("⛔ Non autorizzato."); return
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""SELECT id,nome_cliente,indirizzo,data_apertura,lingua,stato,
            tecnico_nome,fascia_oraria,data_ora_proposta
            FROM chiamate WHERE stato IN ('assegnata','in_attesa_conferma') ORDER BY id DESC LIMIT 20""").fetchall()
    if not rows: await update.message.reply_text("📋 Nessuna!"); return
    await update.message.reply_text(f"✅ *Assegnate: {len(rows)}*", parse_mode="Markdown")
    for r in rows:
        emoji = "⏳" if r[5]=="in_attesa_conferma" else "✅"
        orario = r[8] if r[5]=="in_attesa_conferma" else r[7]
        testo = (f"{emoji} *#{r[0]}* {FLAGS.get(r[4],'🌍')} — {r[1]}\n"
                 f"📍 {r[2]}\n👨‍🔧 {r[6] or '—'}\n⏰ {orario or '—'}\n🕐 {r[3]}")
        await update.message.reply_text(testo, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔓 Sblocca e rimetti in circolo",
                callback_data=f"sblocca_{r[0]}")]]))

async def gestisci_sblocco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.from_user.id not in BACKOFFICE_IDS:
        await query.answer("⛔ Non autorizzato.", show_alert=True); return
    cid = int(query.data.split("_")[1]); ch = get_chiamata(cid)
    if not ch: await query.answer("⚠️ Non trovata.", show_alert=True); return
    if ch["stato"] == "aperta": await query.answer("ℹ️ Già libera.", show_alert=True); return
    tecnico_prec_id = ch.get("tecnico_id")
    sblocca_chiamata_db(cid)
    await query.edit_message_text(
        f"🔓 *CHIAMATA #{cid} — SBLOCCATA*\n👤 {ch['nome_cliente']}\n📍 {ch['indirizzo']}\n_Rimessa in circolo_",
        parse_mode="Markdown")
    link_maps="https://www.google.com/maps/search/?api=1&query="+ch["indirizzo"].replace(" ","+")
    flag=FLAGS.get(ch["lingua"],"🌍")
    try: await context.bot.send_message(chat_id=TECNICI_GROUP_ID,
        text=(f"🔔 *RIASSEGNAZIONE #{cid}* {flag}\n👤 {ch['nome_cliente']}\n📍 {ch['indirizzo']}\n"
              f"🗺 [Google Maps]({link_maps})\n📞 {ch['telefono']}\n🔧 {ch['problema_it']}\n\n"
              f"⚠️ _Rimessa in circolo dal back office_\n⏰ Clicca per assegnarti:"),
        reply_markup=_keyboard_fascia(cid), parse_mode="Markdown")
    except Exception as e: log.error(f"Sblocco: {e}")
    if tecnico_prec_id:
        try: await context.bot.send_message(chat_id=tecnico_prec_id,
            text=f"ℹ️ *Chiamata #{cid} rimessa in circolo*\n\nLa chiamata di {ch['nome_cliente']} è stata rimessa.\n\n_Rotondi Group Roma_",
            parse_mode="Markdown")
        except: pass
    try: await context.bot.send_message(chat_id=ch["telegram_id"],
        text=t(ch["lingua"],"riassegnazione"), parse_mode="Markdown")
    except Exception as e: log.error(f"Notifica cliente: {e}")

async def storico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in BACKOFFICE_IDS:
        await update.message.reply_text("⛔ Non autorizzato."); return
    now=datetime.now()
    mesi=["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]
    anno=now.year; bottoni=[]; riga=[]
    for i,m in enumerate(mesi,1):
        riga.append(InlineKeyboardButton(f"{m} {anno}", callback_data=f"storico_{i:02d}_{anno}"))
        if len(riga)==3: bottoni.append(riga); riga=[]
    if riga: bottoni.append(riga)
    bottoni.append([InlineKeyboardButton(f"📅 Anno {anno-1}", callback_data=f"storico_00_{anno-1}")])
    await update.message.reply_text("📊 *Storico chiamate*\n\nScegli il mese:",
        reply_markup=InlineKeyboardMarkup(bottoni), parse_mode="Markdown")

async def gestisci_storico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer()
    if query.from_user.id not in BACKOFFICE_IDS: return
    parti=query.data.split("_")
    await _invia_storico(query.message, context, int(parti[1]), int(parti[2]))

async def _invia_storico(msg, context, mese, anno):
    with sqlite3.connect(DB_PATH) as conn:
        if mese==0:
            rows=conn.execute("""SELECT id,nome_cliente,indirizzo,stato,tecnico_nome,fascia_oraria,
                data_apertura,lingua,marca,modello,problema_it
                FROM chiamate WHERE data_apertura LIKE ? ORDER BY id DESC""", (f"%/{anno}%",)).fetchall()
            periodo=f"Anno {anno}"
        else:
            rows=conn.execute("""SELECT id,nome_cliente,indirizzo,stato,tecnico_nome,fascia_oraria,
                data_apertura,lingua,marca,modello,problema_it
                FROM chiamate WHERE data_apertura LIKE ? ORDER BY id DESC""", (f"%/{mese:02d}/{anno}%",)).fetchall()
            mesi_it=["","Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
                     "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
            periodo=f"{mesi_it[mese]} {anno}"
    if not rows:
        await msg.reply_text(f"📊 *{periodo}*\n\n_Nessuna chiamata trovata._", parse_mode="Markdown"); return
    totale=len(rows); ass=sum(1 for r in rows if r[3]=="assegnata")
    ape=sum(1 for r in rows if r[3]=="aperta"); att=sum(1 for r in rows if r[3]=="in_attesa_conferma")
    tc={}
    for r in rows:
        if r[4]: tc[r[4]]=tc.get(r[4],0)+1
    ries=(f"📊 *STORICO — {periodo}*\n{'━'*28}\n\n"
          f"📈 Totale: *{totale}* | ✅ {ass} | 🟡 {ape} | ⏳ {att}\n\n")
    if tc:
        ries+="*Per tecnico:*\n"
        for nome,count in sorted(tc.items(),key=lambda x:-x[1]):
            ries+=f"  👨‍🔧 {nome}: {count}\n"
    await msg.reply_text(ries, parse_mode="Markdown")
    for i in range(0,len(rows),10):
        testo=""
        for r in rows[i:i+10]:
            emoji="✅" if r[3]=="assegnata" else ("⏳" if r[3]=="in_attesa_conferma" else "🟡")
            testo+=(f"{emoji} *#{r[0]}* {FLAGS.get(r[7],'🌍')} — {r[1]}\n"
                    f"📍 {r[2]}\n🕐 {r[6]}")
            if r[4]: testo+=f"\n👨‍🔧 {r[4]}"+(f" | {r[5]}" if r[5] else "")
            testo+=f"\n🔧 _{(r[10] or '')[:60]}_\n\n"
        await msg.reply_text(testo, parse_mode="Markdown")

async def statistiche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in BACKOFFICE_IDS:
        await update.message.reply_text("⛔ Non autorizzato."); return
    now=datetime.now()
    mese_like="%/"+now.strftime('%m/%Y')+"%"; anno_like=f"%/{now.year}%"
    with sqlite3.connect(DB_PATH) as conn:
        tot=conn.execute("SELECT COUNT(*) FROM chiamate").fetchone()[0]
        ass=conn.execute("SELECT COUNT(*) FROM chiamate WHERE stato='assegnata'").fetchone()[0]
        ape=conn.execute("SELECT COUNT(*) FROM chiamate WHERE stato='aperta'").fetchone()[0]
        att=conn.execute("SELECT COUNT(*) FROM chiamate WHERE stato='in_attesa_conferma'").fetchone()[0]
        m_tot=conn.execute("SELECT COUNT(*) FROM chiamate WHERE data_apertura LIKE ?",(mese_like,)).fetchone()[0]
        m_ass=conn.execute("SELECT COUNT(*) FROM chiamate WHERE stato='assegnata' AND data_apertura LIKE ?",(mese_like,)).fetchone()[0]
        a_tot=conn.execute("SELECT COUNT(*) FROM chiamate WHERE data_apertura LIKE ?",(anno_like,)).fetchone()[0]
        tc_rows=conn.execute("""SELECT tecnico_nome,COUNT(*) FROM chiamate
            WHERE tecnico_nome IS NOT NULL AND tecnico_nome!=''
            GROUP BY tecnico_nome ORDER BY COUNT(*) DESC""").fetchall()
        lg_rows=conn.execute("SELECT lingua,COUNT(*) FROM chiamate GROUP BY lingua ORDER BY COUNT(*) DESC").fetchall()
        ultima=conn.execute("SELECT nome_cliente,data_apertura FROM chiamate ORDER BY id DESC LIMIT 1").fetchone()
    msg1=(f"📊 *STATISTICHE*\n{'━'*30}\n\n"
          f"📅 *{now.strftime('%B %Y')}:* {m_tot} ricevute, {m_ass} assegnate\n"
          f"📆 *Anno {now.year}:* {a_tot} chiamate\n\n"
          f"🗂 *Storico:* {tot} totali | ✅{ass} | 🟡{ape} | ⏳{att}")
    if ultima: msg1+=f"\n🕐 Ultima: {ultima[0]} — {ultima[1]}"
    await update.message.reply_text(msg1, parse_mode="Markdown")
    if tc_rows:
        medaglie=["🥇","🥈","🥉"]
        msg2=f"👨‍🔧 *CLASSIFICA TECNICI*\n{'━'*30}\n\n"
        for i,(nome,cnt) in enumerate(tc_rows):
            msg2+=f"{medaglie[i] if i<3 else str(i+1)+'.'} *{nome}*: *{cnt}* chiamate\n"
        await update.message.reply_text(msg2, parse_mode="Markdown")
    if lg_rows:
        LINGUE_NOMI={"it":"🇮🇹 IT","en":"🇬🇧 EN","bn":"🇧🇩 BD","zh":"🇨🇳 CN","ar":"🇸🇦 SA"}
        tot_ling=sum(r[1] for r in lg_rows)
        msg3=f"🌍 *LINGUE CLIENTI*\n{'━'*30}\n\n"
        for lingua,cnt in lg_rows:
            perc=int(cnt/tot_ling*100) if tot_ling else 0
            msg3+=f"{LINGUE_NOMI.get(lingua,lingua)}: *{cnt}* ({perc}%)\n"
        await update.message.reply_text(msg3, parse_mode="Markdown")

async def registrami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user=update.effective_user; nome=f"{user.first_name or ''} {user.last_name or ''}".strip()
    context.user_data["reg_nome"]=nome
    await update.message.reply_text(f"👨‍🔧 Ciao *{nome}*!\n\nScrivi il tuo *numero di telefono*:", parse_mode="Markdown")
    return REG_TELEFONO

async def registrami_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user=update.effective_user; nome=context.user_data.get("reg_nome",user.first_name)
    telefono=update.message.text.strip(); registra_tecnico(user.id,nome,telefono)
    await update.message.reply_text(
        f"✅ *Registrazione completata!*\n\n👤 *{nome}*\n📞 *{telefono}*\n\nUsa /chiamate per le tue chiamate.",
        parse_mode="Markdown")
    return ConversationHandler.END

async def mie_chiamate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid=update.effective_user.id
    with sqlite3.connect(DB_PATH) as conn:
        rows=conn.execute("""SELECT id,nome_cliente,indirizzo,problema_it,fascia_oraria,
            data_assegnazione,stato,data_ora_proposta
            FROM chiamate WHERE tecnico_id=? OR tecnico_proposta_id=?
            ORDER BY id DESC LIMIT 10""", (tid,tid)).fetchall()
    if not rows: await update.message.reply_text("📋 Nessuna chiamata assegnata."); return
    testo="📋 *Le tue ultime chiamate:*\n\n"
    for r in rows:
        if r[6]=="in_attesa_conferma": testo+=f"⏳ *#{r[0]}* — {r[1]}\n📍 {r[2]}\n📅 Proposta: {r[7]}\n\n"
        else: testo+=f"✅ *#{r[0]}* — {r[1]}\n📍 {r[2]}\n⏰ {r[4]}\n\n"
    await update.message.reply_text(testo, parse_mode="Markdown")

async def getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat=update.effective_chat; user=update.effective_user
    await update.message.reply_text(f"ID Chat: {chat.id}\nID User: {user.id}\nTipo: {chat.type}")


# ── HEALTH SERVER ─────────────────────────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'OK')
    def log_message(self, format, *args): pass

def avvia_http():
    HTTPServer(('0.0.0.0', int(os.environ.get('PORT',8080))), HealthHandler).serve_forever()


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SCEGLI_LINGUA:  [CallbackQueryHandler(scegli_lingua_condizioni, pattern="^lang_")],
            GDPR:           [CallbackQueryHandler(gestisci_gdpr,            pattern="^gdpr_")],
            CONDIZIONI:     [CallbackQueryHandler(gestisci_condizioni,      pattern="^cond_")],
            NOME:           [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_nome)],
            IND_VIA:        [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_via)],
            IND_CIVICO:     [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_civico)],
            IND_CAP:        [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_cap)],
            IND_CITTA:      [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_citta)],
            IND_PROVINCIA:  [MessageHandler(filters.TEXT & ~filters.COMMAND, raccogli_provincia)],
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
    conv_reg = ConversationHandler(
        entry_points=[CommandHandler("registrami", registrami)],
        states={REG_TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, registrami_telefono)]},
        fallbacks=[CommandHandler("annulla", annulla)]
    )

    app.add_handler(conv)
    app.add_handler(conv_reg)
    app.add_handler(CallbackQueryHandler(gestisci_fascia,            pattern=r"^fascia_"))
    app.add_handler(CallbackQueryHandler(gestisci_wfascia,           pattern=r"^wfascia_"))
    app.add_handler(CallbackQueryHandler(gestisci_programma,         pattern=r"^programma_"))
    app.add_handler(CallbackQueryHandler(gestisci_data,              pattern=r"^pdata_"))
    app.add_handler(CallbackQueryHandler(gestisci_ora,               pattern=r"^pora_"))
    app.add_handler(CallbackQueryHandler(gestisci_conferma_proposta, pattern=r"^cprop_"))
    app.add_handler(CommandHandler("lista",       lista))
    app.add_handler(CommandHandler("aperte",      aperte))
    app.add_handler(CommandHandler("assegnate",   assegnate))
    app.add_handler(CommandHandler("chiamate",    mie_chiamate))
    app.add_handler(CommandHandler("getid",       getid))
    app.add_handler(CommandHandler("storico",     storico))
    app.add_handler(CommandHandler("statistiche", statistiche))
    app.add_handler(CallbackQueryHandler(gestisci_storico, pattern=r"^storico_"))
    app.add_handler(CallbackQueryHandler(gestisci_sblocco, pattern=r"^sblocca_"))

    log.info("🤖 Bot avviato!")
    Thread(target=avvia_http, daemon=True).start()
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
