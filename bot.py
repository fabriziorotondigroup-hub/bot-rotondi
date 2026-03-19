#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT TELEGRAM — Assistenza Tecnica Macchinari
Rotondi Group Roma
"""

import logging, sqlite3, asyncio, os
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)

BOT_TOKEN        = os.environ.get("BOT_TOKEN", "IL_TUO_TOKEN_QUI")
TECNICI_GROUP_ID = int(os.environ.get("TECNICI_GROUP_ID", "-1001234567890"))
BACKOFFICE_IDS   = [int(x) for x in os.environ.get("BACKOFFICE_IDS", "123456789").split(",")]
NOME_AZIENDA     = "Rotondi Group Roma"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

DB_PATH = "assistenza.db"

(SCEGLI_LINGUA, NOME, INDIRIZZO, TELEFONO,
 FOTO_TARGHETTA, MARCA, MODELLO, SERIALE,
 PROBLEMA, FOTO_MACCHINA, CONFERMA) = range(11)

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
            "📋 *INFORMAZIONI SUL SERVIZIO*\n\n"
            "*Zona di Roma:*\n"
            "• Chiamata + 1 ora di lavoro (o frazione): € 80,00 + IVA\n"
            "• Ore successive alla prima: € 40,00/ora + IVA\n\n"
            "*Provincia di Roma e altre regioni*\n"
            "_(Latina, Frosinone, Rieti, Viterbo e resto d'Italia):_\n"
            "• Trasferta: € 0,70/km + IVA _(andata e ritorno)_\n"
            "• Ore di viaggio: € 32,00/ora + IVA _(andata e ritorno)_\n"
            "• Ore di lavoro: € 40,00/ora + IVA _(o frazione d'ora)_\n\n"
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
            "📋 *INFORMAZIONI SUL SERVIZIO*\n\n"
            "*Zona di Roma:*\n"
            "• Chiamata + 1 ora di lavoro (o frazione): € 80,00 + IVA\n"
            "• Ore successive alla prima: € 40,00/ora + IVA\n\n"
            "*Provincia di Roma e altre regioni*\n"
            "_(Latina, Frosinone, Rieti, Viterbo e resto d'Italia):_\n"
            "• Trasferta: € 0,70/km + IVA _(andata e ritorno)_\n"
            "• Ore di viaggio: € 32,00/ora + IVA _(andata e ritorno)_\n"
            "• Ore di lavoro: € 40,00/ora + IVA _(o frazione d'ora)_\n\n"
            "Nota: Il pagamento dovrà essere effettuato direttamente al tecnico al termine del servizio.\n\n"
            "I tecnici che operano con Rotondi Group sono professionisti freelance selezionati e incaricati dalla nostra azienda.\n\n"
            "⚠️ Per annullare contatti URGENTEMENTE il nr. +39 06 41 40 0514.\n"
            "In assenza di disdetta verrà addebitato il costo di uscita.\n\n"
            "_Il Team di Assistenza Tecnica Rotondi Group Roma_"
        ),
        "proposta": (
            "Gentile Cliente,\n"
            "Un tecnico ha proposto un appuntamento per la sua richiesta di assistenza.\n\n"
            "👨‍🔧 *Tecnico:* {tecnico}\n"
            "📅 *Data e ora proposta:* {data_ora}\n\n"
            "Vuole accettare questo appuntamento?"
        ),
        "proposta_accettata": (
            "Gentile Cliente,\n"
            "L'appuntamento è stato confermato!\n\n"
            "👨‍🔧 *Tecnico assegnato:* {tecnico}\n"
            "📞 *Ufficio Roma:* +39 06 41400617\n"
            "📅 *Appuntamento:* {data_ora}\n\n"
            "📋 *INFORMAZIONI SUL SERVIZIO*\n\n"
            "*Zona di Roma:*\n"
            "• Chiamata + 1 ora di lavoro (o frazione): € 80,00 + IVA\n"
            "• Ore successive alla prima: € 40,00/ora + IVA\n\n"
            "*Provincia di Roma e altre regioni*\n"
            "_(Latina, Frosinone, Rieti, Viterbo e resto d'Italia):_\n"
            "• Trasferta: € 0,70/km + IVA _(andata e ritorno)_\n"
            "• Ore di viaggio: € 32,00/ora + IVA _(andata e ritorno)_\n"
            "• Ore di lavoro: € 40,00/ora + IVA _(o frazione d'ora)_\n\n"
            "⚠️ Per annullare contatti URGENTEMENTE il nr. +39 06 41 40 0514.\n\n"
            "_Il Team di Assistenza Tecnica Rotondi Group Roma_"
        ),
        "proposta_rifiutata": (
            "Gentile Cliente,\n"
            "Ha rifiutato la proposta di appuntamento.\n"
            "La sua richiesta è tornata disponibile e un altro tecnico la contatterà presto.\n\n"
            "_Il Team di Assistenza Tecnica Rotondi Group Roma_"
        ),
        "annulla": "❌ Operazione annullata. Scrivi /start per ricominciare.",
        "proposta": (
            "Gentile Cliente,\n"
            "Il tecnico *{tecnico}* ha proposto un intervento per:\n\n"
            "📅 *{data_ora}*\n\n"
            "Accetta questa data e ora?\n\n"
            "⚠️ Se rifiuti, la chiamata tornerà disponibile per altri tecnici."
        ),
        "proposta_accettata": (
            "Gentile Cliente,\n"
            "Perfetto! Ha confermato l'appuntamento.\n\n"
            "👨‍🔧 *Tecnico:* {tecnico}\n"
            "📅 *Data e ora:* {data_ora}\n"
            "📞 *Ufficio Roma:* +39 06 41400617\n\n"
            "📋 *INFORMAZIONI SUL SERVIZIO*\n\n"
            "*Zona di Roma:*\n"
            "• Chiamata + 1 ora di lavoro (o frazione): € 80,00 + IVA\n"
            "• Ore successive alla prima: € 40,00/ora + IVA\n\n"
            "*Provincia di Roma e altre regioni*\n"
            "_(Latina, Frosinone, Rieti, Viterbo e resto d'Italia):_\n"
            "• Trasferta: € 0,70/km + IVA _(andata e ritorno)_\n"
            "• Ore di viaggio: € 32,00/ora + IVA _(andata e ritorno)_\n"
            "• Ore di lavoro: € 40,00/ora + IVA _(o frazione d'ora)_\n\n"
            "⚠️ Per annullare contatti URGENTEMENTE il nr. +39 06 41 40 0514.\n"
            "In assenza di disdetta verrà addebitato il costo di uscita.\n\n"
            "_Il Team di Assistenza Tecnica Rotondi Group Roma_"
        ),
        "proposta_rifiutata": (
            "Gentile Cliente,\n"
            "Ha rifiutato la proposta. La sua richiesta è ancora aperta e un altro tecnico "
            "potrà prenderla in carico a breve.\n\n"
            "_Il Team di Assistenza Tecnica Rotondi Group Roma_"
        ),
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
            "📋 *SERVICE INFORMATION*\n\n"
            "*Rome area:*\n"
            "• Call-out + 1 hour of work (or fraction): € 80.00 + VAT\n"
            "• Additional hours after the first: € 40.00/hour + VAT\n\n"
            "*Province of Rome and other regions*\n"
            "_(Latina, Frosinone, Rieti, Viterbo and rest of Italy):_\n"
            "• Travel: € 0.70/km + VAT _(round trip)_\n"
            "• Travel hours: € 32.00/hour + VAT _(round trip)_\n"
            "• Work hours: € 40.00/hour + VAT _(or fraction)_\n\n"
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
            "📋 *SERVICE INFORMATION*\n\n"
            "*Rome area:*\n"
            "• Call-out + 1 hour of work (or fraction): € 80.00 + VAT\n"
            "• Additional hours after the first: € 40.00/hour + VAT\n\n"
            "*Province of Rome and other regions*\n"
            "_(Latina, Frosinone, Rieti, Viterbo and rest of Italy):_\n"
            "• Travel: € 0.70/km + VAT _(round trip)_\n"
            "• Travel hours: € 32.00/hour + VAT _(round trip)_\n"
            "• Work hours: € 40.00/hour + VAT _(or fraction)_\n\n"
            "⚠️ To cancel contact URGENTLY: +39 06 41 40 0514.\n\n"
            "_The Rotondi Group Roma Technical Assistance Team_"
        ),
        "proposta": (
            "Dear Customer,\n"
            "A technician has proposed an appointment for your assistance request.\n\n"
            "👨‍🔧 *Technician:* {tecnico}\n"
            "📅 *Proposed date and time:* {data_ora}\n\n"
            "Do you want to accept this appointment?"
        ),
        "proposta_accettata": (
            "Dear Customer,\n"
            "Your appointment has been confirmed!\n\n"
            "👨‍🔧 *Assigned technician:* {tecnico}\n"
            "📞 *Rome Office:* +39 06 41400617\n"
            "📅 *Appointment:* {data_ora}\n\n"
            "⚠️ To cancel contact URGENTLY: +39 06 41 40 0514.\n\n"
            "_The Rotondi Group Roma Technical Assistance Team_"
        ),
        "proposta_rifiutata": (
            "Dear Customer,\n"
            "You have declined the appointment proposal.\n"
            "Your request is now available again and another technician will contact you soon.\n\n"
            "_The Rotondi Group Roma Technical Assistance Team_"
        ),
        "annulla": "❌ Cancelled. Write /start to begin again.",
        "proposta": (
            "Dear Customer,\n"
            "Technician *{tecnico}* has proposed an intervention for:\n\n"
            "📅 *{data_ora}*\n\n"
            "Do you accept this date and time?\n\n"
            "⚠️ If you decline, the request will be available for other technicians."
        ),
        "proposta_accettata": (
            "Dear Customer,\n"
            "Great! You have confirmed the appointment.\n\n"
            "👨‍🔧 *Technician:* {tecnico}\n"
            "📅 *Date and time:* {data_ora}\n"
            "📞 *Rome Office:* +39 06 41400617\n\n"
            "⚠️ To cancel contact URGENTLY: +39 06 41 40 0514.\n"
            "Without cancellation, the call-out fee will be charged.\n\n"
            "_The Rotondi Group Roma Technical Assistance Team_"
        ),
        "proposta_rifiutata": (
            "Dear Customer,\n"
            "You have declined the proposal. Your request is still open and another technician "
            "will be able to take it shortly.\n\n"
            "_The Rotondi Group Roma Technical Assistance Team_"
        ),
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
            "📋 *সেবার তথ্য*\n\n"
            "*রোমা শহর:*\n"
            "• আসার চার্জ + ১ ঘণ্টা কাজ: € 80,00 + VAT\n"
            "• প্রথম ঘণ্টার পরে প্রতি ঘণ্টা: € 40,00 + VAT\n\n"
            "*রোমা প্রদেশ ও অন্যান্য অঞ্চল:*\n"
            "• যাতায়াত: € 0,70/কিমি + VAT\n"
            "• ভ্রমণ সময়: € 32,00/ঘণ্টা + VAT\n"
            "• কাজের সময়: € 40,00/ঘণ্টা + VAT\n\n"
            "⚠️ বাতিল করতে জরুরি যোগাযোগ করুন: +39 06 41 40 0514\n\n"
            "_রোটোন্ডি গ্রুপ রোমা টেকনিক্যাল টিম_"
        ),
        "assegnata": (
            "প্রিয় গ্রাহক,\n"
            "আপনার অনুরোধ একজন টেকনিশিয়ানকে দেওয়া হয়েছে।\n\n"
            "👨‍🔧 *টেকনিশিয়ান:* {tecnico}\n"
            "📞 *রোমা অফিস:* +39 06 41400617\n"
            "⏰ *আসার সময়:* {fascia}\n\n"
            "⚠️ বাতিল করতে জরুরি: +39 06 41 40 0514\n\n"
            "_রোটোন্ডি গ্রুপ রোমা টেকনিক্যাল টিম_"
        ),
        "proposta": (
            "প্রিয় গ্রাহক,\n"
            "একজন টেকনিশিয়ান একটি অ্যাপয়েন্টমেন্ট প্রস্তাব করেছেন।\n\n"
            "👨‍🔧 *টেকনিশিয়ান:* {tecnico}\n"
            "📅 *প্রস্তাবিত তারিখ ও সময়:* {data_ora}\n\n"
            "আপনি কি এই অ্যাপয়েন্টমেন্ট গ্রহণ করতে চান?"
        ),
        "proposta_accettata": (
            "প্রিয় গ্রাহক,\n"
            "আপনার অ্যাপয়েন্টমেন্ট নিশ্চিত হয়েছে!\n\n"
            "👨‍🔧 *টেকনিশিয়ান:* {tecnico}\n"
            "📞 *রোমা অফিস:* +39 06 41400617\n"
            "📅 *অ্যাপয়েন্টমেন্ট:* {data_ora}\n\n"
            "⚠️ বাতিল করতে জরুরি: +39 06 41 40 0514\n\n"
            "_রোটোন্ডি গ্রুপ রোমা টেকনিক্যাল টিম_"
        ),
        "proposta_rifiutata": (
            "প্রিয় গ্রাহক,\n"
            "আপনি প্রস্তাব প্রত্যাখ্যান করেছেন। অনুরোধটি আবার উপলব্ধ।\n\n"
            "_রোটোন্ডি গ্রুপ রোমা টেকনিক্যাল টিম_"
        ),
        "annulla": "❌ বাতিল হয়েছে। আবার শুরু করতে /start লিখুন।",
        "proposta": (
            "প্রিয় গ্রাহক,\n"
            "টেকনিশিয়ান *{tecnico}* একটি সময় প্রস্তাব করেছেন:\n\n"
            "📅 *{data_ora}*\n\n"
            "আপনি কি এই তারিখ ও সময় গ্রহণ করবেন?\n\n"
            "⚠️ প্রত্যাখ্যান করলে অনুরোধটি অন্য টেকনিশিয়ানের জন্য উন্মুক্ত থাকবে।"
        ),
        "proposta_accettata": (
            "প্রিয় গ্রাহক,\n"
            "আপনি অ্যাপয়েন্টমেন্ট নিশ্চিত করেছেন।\n\n"
            "👨‍🔧 *টেকনিশিয়ান:* {tecnico}\n"
            "📅 *তারিখ ও সময়:* {data_ora}\n"
            "📞 *রোমা অফিস:* +39 06 41400617\n\n"
            "⚠️ বাতিল করতে জরুরি: +39 06 41 40 0514\n\n"
            "_রোটোন্ডি গ্রুপ রোমা টেকনিক্যাল টিম_"
        ),
        "proposta_rifiutata": (
            "প্রিয় গ্রাহক,\n"
            "আপনি প্রস্তাব প্রত্যাখ্যান করেছেন। আপনার অনুরোধ এখনও খোলা আছে।\n\n"
            "_রোটোন্ডি গ্রুপ রোমা টেকনিক্যাল টিম_"
        ),
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
            "📋 *服务信息*\n\n"
            "*罗马市区:*\n"
            "• 上门费 + 1小时工作: € 80,00 + 增值税\n"
            "• 第一小时后每小时: € 40,00 + 增值税\n\n"
            "*罗马省及其他地区:*\n"
            "• 交通费: € 0,70/公里 + 增值税\n"
            "• 路途时间: € 32,00/小时 + 增值税\n"
            "• 工作时间: € 40,00/小时 + 增值税\n\n"
            "⚠️ 如需取消请紧急联系: +39 06 41 40 0514\n\n"
            "_罗通迪集团罗马技术团队_"
        ),
        "assegnata": (
            "尊敬的客户，\n"
            "您的维修请求已分配给技术人员。\n\n"
            "👨‍🔧 *负责技术人员：* {tecnico}\n"
            "📞 *罗马办公室：* +39 06 41400617\n"
            "⏰ *预计上门时间：* {fascia}\n\n"
            "⚠️ 如需取消请紧急联系: +39 06 41 40 0514\n\n"
            "_罗通迪集团罗马技术团队_"
        ),
        "proposta": (
            "尊敬的客户，\n"
            "技术人员提议了一个预约时间。\n\n"
            "👨‍🔧 *技术人员：* {tecnico}\n"
            "📅 *建议日期和时间：* {data_ora}\n\n"
            "您是否接受此预约？"
        ),
        "proposta_accettata": (
            "尊敬的客户，\n"
            "您的预约已确认！\n\n"
            "👨‍🔧 *技术人员：* {tecnico}\n"
            "📞 *罗马办公室：* +39 06 41400617\n"
            "📅 *预约时间：* {data_ora}\n\n"
            "⚠️ 如需取消请紧急联系: +39 06 41 40 0514\n\n"
            "_罗通迪集团罗马技术团队_"
        ),
        "proposta_rifiutata": (
            "尊敬的客户，\n"
            "您拒绝了预约提议。您的请求重新开放给其他技术人员。\n\n"
            "_罗通迪集团罗马技术团队_"
        ),
        "annulla": "❌ 已取消。写 /start 重新开始。",
        "proposta": (
            "尊敬的客户，\n"
            "技术人员 *{tecnico}* 提议上门时间为：\n\n"
            "📅 *{data_ora}*\n\n"
            "您是否接受此日期和时间？\n\n"
            "⚠️ 如果拒绝，请求将对其他技术人员开放。"
        ),
        "proposta_accettata": (
            "尊敬的客户，\n"
            "您已确认预约。\n\n"
            "👨‍🔧 *技术人员：* {tecnico}\n"
            "📅 *日期和时间：* {data_ora}\n"
            "📞 *罗马办公室：* +39 06 41400617\n\n"
            "⚠️ 如需取消请紧急联系: +39 06 41 40 0514\n\n"
            "_罗通迪集团罗马技术团队_"
        ),
        "proposta_rifiutata": (
            "尊敬的客户，\n"
            "您已拒绝提议。您的请求仍然开放，其他技术人员将很快接手。\n\n"
            "_罗通迪集团罗马技术团队_"
        ),
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
            "📋 *معلومات الخدمة*\n\n"
            "*منطقة روما:*\n"
            "• زيارة + ساعة عمل: € 80,00 + ضريبة\n"
            "• الساعات الإضافية: € 40,00/ساعة + ضريبة\n\n"
            "*مقاطعة روما والمناطق الأخرى:*\n"
            "• تنقل: € 0,70/كم + ضريبة\n"
            "• ساعات السفر: € 32,00/ساعة + ضريبة\n"
            "• ساعات العمل: € 40,00/ساعة + ضريبة\n\n"
            "⚠️ للإلغاء تواصل عاجلاً: +39 06 41 40 0514\n\n"
            "_فريق روتوندي جروب روما للدعم الفني_"
        ),
        "assegnata": (
            "عزيزي العميل،\n"
            "تم تعيين فني لطلبك.\n\n"
            "👨‍🔧 *الفني المعين:* {tecnico}\n"
            "📞 *مكتب روما:* +39 06 41400617\n"
            "⏰ *موعد التدخل:* {fascia}\n\n"
            "⚠️ للإلغاء تواصل عاجلاً: +39 06 41 40 0514\n\n"
            "_فريق روتوندي جروب روما للدعم الفني_"
        ),
        "proposta": (
            "عزيزي العميل،\n"
            "اقترح فني موعداً لطلبك.\n\n"
            "👨‍🔧 *الفني:* {tecnico}\n"
            "📅 *التاريخ والوقت المقترح:* {data_ora}\n\n"
            "هل تقبل هذا الموعد؟"
        ),
        "proposta_accettata": (
            "عزيزي العميل،\n"
            "تم تأكيد موعدك!\n\n"
            "👨‍🔧 *الفني:* {tecnico}\n"
            "📞 *مكتب روما:* +39 06 41400617\n"
            "📅 *الموعد:* {data_ora}\n\n"
            "⚠️ للإلغاء تواصل عاجلاً: +39 06 41 40 0514\n\n"
            "_فريق روتوندي جروب روما للدعم الفني_"
        ),
        "proposta_rifiutata": (
            "عزيزي العميل،\n"
            "لقد رفضت اقتراح الموعد. طلبك متاح مجدداً.\n\n"
            "_فريق روتوندي جروب روما للدعم الفني_"
        ),
        "annulla": "❌ تم الإلغاء. اكتب /start للبدء من جديد.",
        "proposta": (
            "عزيزي العميل،\n"
            "الفني *{tecnico}* اقترح موعداً للتدخل:\n\n"
            "📅 *{data_ora}*\n\n"
            "هل تقبل هذا التاريخ والوقت؟\n\n"
            "⚠️ في حالة الرفض، سيكون الطلب متاحاً لفنيين آخرين."
        ),
        "proposta_accettata": (
            "عزيزي العميل،\n"
            "لقد أكدت الموعد.\n\n"
            "👨‍🔧 *الفني:* {tecnico}\n"
            "📅 *التاريخ والوقت:* {data_ora}\n"
            "📞 *مكتب روما:* +39 06 41400617\n\n"
            "⚠️ للإلغاء تواصل عاجلاً: +39 06 41 40 0514\n\n"
            "_فريق روتوندي جروب روما للدعم الفني_"
        ),
        "proposta_rifiutata": (
            "عزيزي العميل،\n"
            "لقد رفضت الاقتراح. طلبك لا يزال مفتوحاً وسيتولى فني آخر قريباً.\n\n"
            "_فريق روتوندي جروب روما للدعم الفني_"
        ),
    },
}

FLAGS = {"it":"🇮🇹","en":"🇬🇧","bn":"🇧🇩","zh":"🇨🇳","ar":"🇸🇦"}

def t(lingua, chiave, **kwargs):
    testo = TESTI.get(lingua, TESTI["it"]).get(chiave, TESTI["it"].get(chiave, ""))
    return testo.format(azienda=NOME_AZIENDA, **kwargs)

def traduci(testo, lingua_src="auto"):
    try:
        if lingua_src == "it": return testo
        return GoogleTranslator(source="auto", target="it").translate(testo) or testo
    except Exception as e:
        log.error(f"Traduzione: {e}"); return testo

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
                foto_macchina_id   TEXT,
                data_ora_proposta  TEXT,
                tecnico_proposta_id INTEGER
            )
        """)
        for col in ["marca TEXT", "modello TEXT", "seriale TEXT",
                    "foto_targhetta_id TEXT", "foto_macchina_id TEXT",
                    "data_ora_proposta TEXT", "tecnico_proposta_id INTEGER"]:
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

# ── /start ──────────────────────────────────────
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
        [InlineKeyboardButton("🇮🇹 Italiano", callback_data="lang_it"),
         InlineKeyboardButton("🇬🇧 English",  callback_data="lang_en")],
        [InlineKeyboardButton("🇧🇩 বাংলা",    callback_data="lang_bn"),
         InlineKeyboardButton("🇨🇳 中文",      callback_data="lang_zh")],
        [InlineKeyboardButton("🇸🇦 العربية",  callback_data="lang_ar")],
    ])
    await update.message.reply_text(
        f"👋 Benvenuto / Welcome / স্বাগতম / 欢迎 / أهلاً\n\n"
        f"*{NOME_AZIENDA}*\n\n"
        f"Scegli la lingua / Choose language / ভাষা বেছে নিন / 选择语言 / اختر اللغة:",
        reply_markup=keyboard, parse_mode="Markdown"
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

async def raccogli_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    context.user_data["nome"] = context.user_data["nome_orig"] = update.message.text.strip()
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
    context.user_data["foto_targhetta_id"] = update.message.photo[-1].file_id if update.message.photo else None
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
    orig = update.message.text.strip()
    context.user_data["problema_orig"] = orig
    context.user_data["problema_it"] = traduci(orig, lingua)
    await update.message.reply_text(t(lingua, "foto_macchina"), parse_mode="Markdown")
    return FOTO_MACCHINA

async def raccogli_foto_macchina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    context.user_data["foto_macchina_id"] = update.message.photo[-1].file_id if update.message.photo else None
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lingua, "si"), callback_data="conferma_si"),
        InlineKeyboardButton(t(lingua, "no"), callback_data="conferma_no"),
    ]])
    await update.message.reply_text(
        t(lingua, "riepilogo",
          nome=context.user_data["nome_orig"],
          indirizzo=context.user_data["indirizzo"],
          telefono=context.user_data["telefono"],
          marca=context.user_data.get("marca", "-"),
          modello=context.user_data.get("modello", "-"),
          seriale=context.user_data.get("seriale", "-"),
          problema=context.user_data["problema_orig"]),
        reply_markup=keyboard, parse_mode="Markdown"
    )
    return CONFERMA

async def conferma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lingua = context.user_data.get("lingua", "it")
    if query.data == "conferma_no":
        await query.edit_message_text(t(lingua, "annulla"), parse_mode="Markdown")
        return ConversationHandler.END

    user    = query.from_user
    nome_it = traduci(context.user_data["nome_orig"], lingua)
    cid     = salva_chiamata(
        user.id, user.username or str(user.id), lingua, nome_it,
        context.user_data["indirizzo"], context.user_data["telefono"],
        context.user_data["problema_it"], context.user_data["problema_orig"],
        context.user_data.get("marca", ""), context.user_data.get("modello", ""),
        context.user_data.get("seriale", ""),
        context.user_data.get("foto_targhetta_id"),
        context.user_data.get("foto_macchina_id"),
    )
    await query.edit_message_text(t(lingua, "registrata"), parse_mode="Markdown")

    flag = FLAGS.get(lingua, "🌍")
    sezione_problema = f"🔧 *Problema (IT):* {context.user_data['problema_it']}"
    if lingua != "it":
        sezione_problema += f"\n🔧 *Originale {flag}:* {context.user_data['problema_orig']}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🕛 Entro le 12:00", callback_data=f"fascia_{cid}_entro12"),
         InlineKeyboardButton("🕕 Entro le 18:00", callback_data=f"fascia_{cid}_entro18")],
        [InlineKeyboardButton("📅 In giornata",    callback_data=f"fascia_{cid}_giornata"),
         InlineKeyboardButton("📆 Entro domani",   callback_data=f"fascia_{cid}_domani")],
        [InlineKeyboardButton("🗓 Da programmare", callback_data=f"programma_{cid}_start")],
    ])

    indirizzo_maps = context.user_data['indirizzo'].replace(' ', '+') + ",+Roma,+Italia"
    link_maps = f"https://www.google.com/maps/search/?api=1&query={indirizzo_maps}"

    testo_gruppo = (
        f"🔔 *NUOVA CHIAMATA #{cid}* {flag}\n{'─'*30}\n"
        f"👤 *Cliente:* {nome_it}\n"
        f"📍 *Indirizzo:* {context.user_data['indirizzo']}\n"
        f"🗺 [Apri su Google Maps]({link_maps})\n"
        f"📞 *Telefono:* {context.user_data['telefono']}\n"
        f"🆔 *Telegram:* @{user.username or user.id}\n"
        f"🏷 *Marca:* {context.user_data.get('marca', '-')}\n"
        f"📋 *Modello:* {context.user_data.get('modello', '-')}\n"
        f"🔢 *Seriale:* {context.user_data.get('seriale', '-')}\n"
        f"{sezione_problema}\n{'─'*30}\n"
        f"⏰ Primo tecnico disponibile: clicca quando intervieni:"
    )
    msg = await context.bot.send_message(
        chat_id=TECNICI_GROUP_ID, text=testo_gruppo,
        reply_markup=keyboard, parse_mode="Markdown"
    )
    aggiorna_msg_id(cid, msg.message_id)

    for foto, cap in [
        (context.user_data.get("foto_targhetta_id"), f"📸 Foto targhetta — Chiamata #{cid}"),
        (context.user_data.get("foto_macchina_id"),  f"📸 Foto macchina — Chiamata #{cid}"),
    ]:
        if foto:
            try: await context.bot.send_photo(chat_id=TECNICI_GROUP_ID, photo=foto, caption=cap)
            except Exception as e: log.error(f"Foto: {e}")

    for bo_id in BACKOFFICE_IDS:
        try:
            await context.bot.send_message(
                chat_id=bo_id,
                text=(f"📲 *Nuova richiesta #{cid}* {flag}\n\n"
                      f"👤 {nome_it}\n📍 {context.user_data['indirizzo']}\n"
                      f"📞 {context.user_data['telefono']}\n"
                      f"🏷 {context.user_data.get('marca','-')} — {context.user_data.get('modello','-')}\n"
                      f"🔢 Seriale: {context.user_data.get('seriale','-')}\n"
                      f"🔧 {context.user_data['problema_it']}"
                      + (f"\n🔧 Originale: {context.user_data['problema_orig']}" if lingua != "it" else "")),
                parse_mode="Markdown"
            )
        except Exception as e: log.error(f"BO notifica: {e}")

    return ConversationHandler.END

async def annulla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lingua = context.user_data.get("lingua", "it")
    await update.message.reply_text(t(lingua, "annulla"), parse_mode="Markdown")
    return ConversationHandler.END

# ── FASCIA ORARIA ────────────────────────────────
FASCE = {
    "entro12": "entro le 12:00", "entro18": "entro le 18:00",
    "giornata": "in giornata",   "domani":  "entro domani"
}

async def gestisci_fascia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parti = query.data.split("_")
    cid   = int(parti[1])
    fascia = FASCE.get(parti[2], parti[2])

    ch = get_chiamata(cid)
    if not ch:
        await query.answer("⚠️ Chiamata non trovata.", show_alert=True); return
    if ch[9] in ("assegnata", "in_attesa_conferma"):
        await query.answer("⚠️ Chiamata già presa o in attesa conferma!", show_alert=True); return

    tid = query.from_user.id
    t_nome = f"{query.from_user.first_name or ''} {query.from_user.last_name or ''}".strip()
    tecnico_db = get_tecnico(tid)
    nome_finale = tecnico_db["nome"] if tecnico_db else t_nome
    if not tecnico_db: registra_tecnico(tid, t_nome)
    assegna(cid, tid, nome_finale, fascia)

    await query.edit_message_text(
        f"✅ *CHIAMATA #{cid} — ASSEGNATA*\n{'─'*30}\n"
        f"👤 *Cliente:* {ch[4]}\n📍 *Indirizzo:* {ch[5]}\n"
        f"🔧 *Problema:* {ch[7]}\n{'─'*30}\n"
        f"👨‍🔧 *Tecnico:* {nome_finale}\n⏰ *Intervento:* {fascia}",
        parse_mode="Markdown"
    )
    await query.answer("✅ Chiamata assegnata a te!")

    for bo_id in BACKOFFICE_IDS:
        try:
            await context.bot.send_message(
                chat_id=bo_id,
                text=(f"✅ *Chiamata #{cid} assegnata*\n\n"
                      f"👤 {ch[4]}\n👨‍🔧 Tecnico: {nome_finale}\n⏰ {fascia}"),
                parse_mode="Markdown"
            )
        except: pass

    lingua_cliente = ch[3]
    try:
        await context.bot.send_message(
            chat_id=ch[1],
            text=t(lingua_cliente, "assegnata", tecnico=nome_finale, fascia=fascia),
            parse_mode="Markdown"
        )
    except Exception as e: log.error(f"Messaggio cliente: {e}")

# ── DA PROGRAMMARE ───────────────────────────────
def genera_keyboard_date(cid):
    oggi = datetime.now()
    bottoni = []
    riga = []
    for i in range(7):
        giorno = oggi + timedelta(days=i)
        label = giorno.strftime("%a %d/%m")
        data_str = giorno.strftime("%d-%m-%Y")
        riga.append(InlineKeyboardButton(label, callback_data=f"pdata_{cid}_{data_str}"))
        if len(riga) == 2:
            bottoni.append(riga); riga = []
    if riga: bottoni.append(riga)
    bottoni.append([InlineKeyboardButton("❌ Annulla", callback_data=f"pdata_{cid}_annulla")])
    return InlineKeyboardMarkup(bottoni)

def genera_keyboard_ore(cid, data_str):
    ore = ["08:00","09:00","10:00","11:00","12:00","13:00",
           "14:00","15:00","16:00","17:00","18:00","19:00"]
    bottoni = []
    riga = []
    for ora in ore:
        riga.append(InlineKeyboardButton(ora, callback_data=f"pora_{cid}_{data_str}_{ora.replace(':','')}"))
        if len(riga) == 4:
            bottoni.append(riga); riga = []
    if riga: bottoni.append(riga)
    bottoni.append([InlineKeyboardButton("⬅️ Torna alle date", callback_data=f"programma_{cid}_start")])
    return InlineKeyboardMarkup(bottoni)

async def gestisci_programma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parti = query.data.split("_")
    cid   = int(parti[1])

    ch = get_chiamata(cid)
    if not ch:
        await query.answer("⚠️ Chiamata non trovata.", show_alert=True); return
    if ch[9] in ("assegnata",):
        await query.answer("⚠️ Chiamata già assegnata!", show_alert=True); return
    if ch[9] == "in_attesa_conferma":
        await query.answer("⚠️ Già in attesa di conferma cliente!", show_alert=True); return

    await query.edit_message_text(
        f"🗓 *Da programmare — Chiamata #{cid}*\n\n"
        f"👤 *Cliente:* {ch[4]}\n"
        f"Scegli la *data* dell'intervento:",
        reply_markup=genera_keyboard_date(cid),
        parse_mode="Markdown"
    )

async def gestisci_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parti = query.data.split("_")
    cid      = int(parti[1])
    data_str = parti[2]

    if data_str == "annulla":
        ch = get_chiamata(cid)
        if not ch: return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🕛 Entro le 12:00", callback_data=f"fascia_{cid}_entro12"),
             InlineKeyboardButton("🕕 Entro le 18:00", callback_data=f"fascia_{cid}_entro18")],
            [InlineKeyboardButton("📅 In giornata",    callback_data=f"fascia_{cid}_giornata"),
             InlineKeyboardButton("📆 Entro domani",   callback_data=f"fascia_{cid}_domani")],
            [InlineKeyboardButton("🗓 Da programmare", callback_data=f"programma_{cid}_start")],
        ])
        indirizzo_maps = ch[5].replace(' ', '+') + ",+Roma,+Italia"
        link_maps = f"https://www.google.com/maps/search/?api=1&query={indirizzo_maps}"
        await query.edit_message_text(
            f"🔔 *CHIAMATA #{cid}*\n{'─'*30}\n"
            f"👤 *Cliente:* {ch[4]}\n"
            f"📍 *Indirizzo:* {ch[5]}\n"
            f"🗺 [Apri su Google Maps]({link_maps})\n"
            f"📞 *Telefono:* {ch[6]}\n"
            f"🔧 *Problema:* {ch[7]}\n{'─'*30}\n"
            f"⏰ Primo tecnico disponibile: clicca quando intervieni:",
            reply_markup=keyboard, parse_mode="Markdown"
        )
        return

    ch = get_chiamata(cid)
    if not ch: return
    await query.edit_message_text(
        f"🗓 *Da programmare — Chiamata #{cid}*\n\n"
        f"👤 *Cliente:* {ch[4]}\n"
        f"📅 *Data selezionata:* {data_str.replace('-','/')}\n\n"
        f"Scegli l'*ora* dell'intervento:",
        reply_markup=genera_keyboard_ore(cid, data_str),
        parse_mode="Markdown"
    )

async def gestisci_ora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parti    = query.data.split("_")
    cid      = int(parti[1])
    data_str = parti[2]
    ora_str  = parti[3]
    ora_fmt  = f"{ora_str[:2]}:{ora_str[2:]}"
    data_fmt = data_str.replace("-", "/")
    data_ora = f"{data_fmt} alle {ora_fmt}"

    ch = get_chiamata(cid)
    if not ch:
        await query.answer("⚠️ Chiamata non trovata.", show_alert=True); return
    if ch[9] in ("assegnata", "in_attesa_conferma"):
        await query.answer("⚠️ Chiamata non disponibile!", show_alert=True); return

    tid    = query.from_user.id
    t_nome = f"{query.from_user.first_name or ''} {query.from_user.last_name or ''}".strip()
    tecnico_db  = get_tecnico(tid)
    nome_finale = tecnico_db["nome"] if tecnico_db else t_nome
    if not tecnico_db: registra_tecnico(tid, t_nome)

    set_proposta(cid, tid, nome_finale, data_ora)

    await query.edit_message_text(
        f"⏳ *CHIAMATA #{cid} — IN ATTESA CONFERMA CLIENTE*\n{'─'*30}\n"
        f"👤 *Cliente:* {ch[4]}\n"
        f"📍 *Indirizzo:* {ch[5]}\n"
        f"🔧 *Problema:* {ch[7]}\n{'─'*30}\n"
        f"👨‍🔧 *Tecnico:* {nome_finale}\n"
        f"📅 *Proposta:* {data_ora}\n\n"
        f"_In attesa che il cliente accetti o rifiuti..._",
        parse_mode="Markdown"
    )

    lingua_cliente = ch[3]
    keyboard_cliente = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Accetto", callback_data=f"cprop_{cid}_si"),
        InlineKeyboardButton("❌ Rifiuto", callback_data=f"cprop_{cid}_no"),
    ]])
    try:
        await context.bot.send_message(
            chat_id=ch[1],
            text=t(lingua_cliente, "proposta", tecnico=nome_finale, data_ora=data_ora),
            reply_markup=keyboard_cliente,
            parse_mode="Markdown"
        )
    except Exception as e:
        log.error(f"Proposta cliente: {e}")

    for bo_id in BACKOFFICE_IDS:
        try:
            await context.bot.send_message(
                chat_id=bo_id,
                text=(f"⏳ *Chiamata #{cid} in attesa conferma*\n\n"
                      f"👤 {ch[4]}\n👨‍🔧 Tecnico: {nome_finale}\n📅 Proposta: {data_ora}"),
                parse_mode="Markdown"
            )
        except: pass

async def gestisci_conferma_proposta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parti    = query.data.split("_")
    cid      = int(parti[1])
    risposta = parti[2]

    ch = get_chiamata(cid)
    if not ch:
        await query.edit_message_text("⚠️ Chiamata non trovata.", parse_mode="Markdown"); return
    if ch[9] != "in_attesa_conferma":
        await query.edit_message_text("ℹ️ La proposta non è più valida.", parse_mode="Markdown"); return

    lingua_cliente = ch[3]
    data_ora       = ch[21] if len(ch) > 21 else "—"
    nome_tecnico   = ch[11] or "—"
    tecnico_id     = ch[22] if len(ch) > 22 else None

    if risposta == "si":
        assegna(cid, tecnico_id, nome_tecnico, data_ora)
        await query.edit_message_text(
            t(lingua_cliente, "proposta_accettata", tecnico=nome_tecnico, data_ora=data_ora),
            parse_mode="Markdown"
        )
        try:
            await context.bot.send_message(
                chat_id=TECNICI_GROUP_ID,
                text=(f"✅ *CHIAMATA #{cid} CONFERMATA DAL CLIENTE*\n\n"
                      f"👤 {ch[4]}\n📍 {ch[5]}\n"
                      f"👨‍🔧 Tecnico: {nome_tecnico}\n📅 {data_ora}"),
                parse_mode="Markdown"
            )
        except: pass
        for bo_id in BACKOFFICE_IDS:
            try:
                await context.bot.send_message(
                    chat_id=bo_id,
                    text=(f"✅ *Chiamata #{cid} confermata dal cliente*\n\n"
                          f"👤 {ch[4]}\n👨‍🔧 {nome_tecnico}\n📅 {data_ora}"),
                    parse_mode="Markdown"
                )
            except: pass
    else:
        reset_proposta(cid)
        await query.edit_message_text(
            t(lingua_cliente, "proposta_rifiutata"),
            parse_mode="Markdown"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🕛 Entro le 12:00", callback_data=f"fascia_{cid}_entro12"),
             InlineKeyboardButton("🕕 Entro le 18:00", callback_data=f"fascia_{cid}_entro18")],
            [InlineKeyboardButton("📅 In giornata",    callback_data=f"fascia_{cid}_giornata"),
             InlineKeyboardButton("📆 Entro domani",   callback_data=f"fascia_{cid}_domani")],
            [InlineKeyboardButton("🗓 Da programmare", callback_data=f"programma_{cid}_start")],
        ])
        try:
            await context.bot.send_message(
                chat_id=TECNICI_GROUP_ID,
                text=(f"❌ *CHIAMATA #{cid} — PROPOSTA RIFIUTATA DAL CLIENTE*\n\n"
                      f"👤 {ch[4]}\n📍 {ch[5]}\n"
                      f"La chiamata è tornata disponibile per tutti i tecnici!"),
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except: pass
        for bo_id in BACKOFFICE_IDS:
            try:
                await context.bot.send_message(
                    chat_id=bo_id,
                    text=(f"❌ *Chiamata #{cid} — proposta rifiutata*\n\n"
                          f"👤 {ch[4]}\nLa chiamata è tornata libera."),
                    parse_mode="Markdown"
                )
            except: pass

# ── BACK OFFICE ──────────────────────────────────
async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in BACKOFFICE_IDS:
        await update.message.reply_text("⛔ Non autorizzato."); return
    rows = lista_chiamate_db()
    if not rows:
        await update.message.reply_text("📋 Nessuna chiamata."); return
    testo = "📋 *Ultime 20 chiamate:*\n\n"
    for r in rows:
        emoji = "🟡" if r[3] == "aperta" else ("⏳" if r[3] == "in_attesa_conferma" else "✅")
        flag  = FLAGS.get(r[7], "🌍")
        testo += f"{emoji} *#{r[0]}* {flag} — {r[1]}\n📍 {r[2]}\n"
        if r[3] in ("assegnata", "in_attesa_conferma"):
            testo += f"👨‍🔧 {r[4]} — {r[5]}\n"
        testo += f"🕐 {r[6]}\n\n"
    await update.message.reply_text(testo, parse_mode="Markdown")

async def aperte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in BACKOFFICE_IDS:
        await update.message.reply_text("⛔ Non autorizzato."); return
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT id,nome_cliente,indirizzo,data_apertura,lingua,stato
            FROM chiamate WHERE stato IN ('aperta','in_attesa_conferma') ORDER BY id DESC
        """).fetchall()
    if not rows:
        await update.message.reply_text("✅ Nessuna chiamata aperta!"); return
    testo = f"🟡 *Chiamate aperte ({len(rows)}):*\n\n"
    for r in rows:
        emoji = "⏳" if r[5] == "in_attesa_conferma" else "🟡"
        testo += f"{emoji} *#{r[0]}* {FLAGS.get(r[4],'🌍')} — {r[1]}\n📍 {r[2]}\n🕐 {r[3]}\n\n"
    await update.message.reply_text(testo, parse_mode="Markdown")

REG_TELEFONO = 20

async def registrami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nome = f"{user.first_name or ''} {user.last_name or ''}".strip()
    context.user_data["reg_nome"] = nome
    await update.message.reply_text(
        f"👨‍🔧 Ciao *{nome}*!\n\nPer completare la registrazione scrivi il tuo *numero di telefono*:",
        parse_mode="Markdown"
    )
    return REG_TELEFONO

async def registrami_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    nome     = context.user_data.get("reg_nome", user.first_name)
    telefono = update.message.text.strip()
    registra_tecnico(user.id, nome, telefono)
    await update.message.reply_text(
        f"✅ *Registrazione completata!*\n\n👤 Nome: *{nome}*\n📞 Telefono: *{telefono}*\n\n"
        f"Riceverai le notifiche nel gruppo tecnici.\nUsa /chiamate per vedere le tue chiamate.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def mie_chiamate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.effective_user.id
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT id,nome_cliente,indirizzo,problema_it,fascia_oraria,data_assegnazione,stato,data_ora_proposta
            FROM chiamate WHERE tecnico_id=? OR tecnico_proposta_id=? ORDER BY id DESC LIMIT 10
        """, (tid, tid)).fetchall()
    if not rows:
        await update.message.reply_text("📋 Nessuna chiamata assegnata."); return
    testo = "📋 *Le tue ultime chiamate:*\n\n"
    for r in rows:
        if r[6] == "in_attesa_conferma":
            testo += f"⏳ *#{r[0]}* — {r[1]}\n📍 {r[2]}\n🔧 {r[3]}\n📅 Proposta: {r[7]}\n\n"
        else:
            testo += f"✅ *#{r[0]}* — {r[1]}\n📍 {r[2]}\n🔧 {r[3]}\n⏰ {r[4]}\n\n"
    await update.message.reply_text(testo, parse_mode="Markdown")

async def getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    await update.message.reply_text(
        f"🆔 Chat ID: `{chat.id}`\n👤 User ID: `{user.id}`\n📝 Tipo: {chat.type}",
        parse_mode="Markdown"
    )

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
        states={REG_TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, registrami_telefono)]},
        fallbacks=[CommandHandler("annulla", annulla)]
    )

    app.add_handler(conv)
    app.add_handler(conv_registrami)
    app.add_handler(CallbackQueryHandler(gestisci_fascia,            pattern=r"^fascia_"))
    app.add_handler(CallbackQueryHandler(gestisci_programma,         pattern=r"^programma_"))
    app.add_handler(CallbackQueryHandler(gestisci_data,              pattern=r"^pdata_"))
    app.add_handler(CallbackQueryHandler(gestisci_ora,               pattern=r"^pora_"))
    app.add_handler(CallbackQueryHandler(gestisci_conferma_proposta, pattern=r"^cprop_"))
    app.add_handler(CommandHandler("lista",    lista))
    app.add_handler(CommandHandler("aperte",   aperte))
    app.add_handler(CommandHandler("chiamate", mie_chiamate))
    app.add_handler(CommandHandler("getid",    getid))

    log.info("🤖 Bot avviato!")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
