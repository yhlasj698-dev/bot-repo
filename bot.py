# -*- coding: utf-8 -*-
"""
Multi-tool Telegram bot.
Required environment variable: BOT_TOKEN
Optional: OCR_SPACE_API_KEY, YTDLP_COOKIES_FILE
Run: python bot.py
"""
import os
import re
import io
import time
import uuid
import html
import socket
import string
import secrets
import sqlite3
import asyncio
import threading
import datetime
import tempfile
from urllib.parse import quote, urlparse

import telebot
from telebot import types
import requests
import qrcode
import yt_dlp
import edge_tts
from PIL import Image
from bs4 import BeautifulSoup

# ---------------- CONFIG ----------------
TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML", threaded=True)
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "Mozilla/5.0 (compatible; MultiToolBot/1.0)"})
DB_PATH = os.getenv("DB_PATH", "bot.db")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", os.path.join(tempfile.gettempdir(), "multitool_bot"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

db_lock = threading.RLock()
state_lock = threading.RLock()
conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=30000")
with db_lock:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(chat_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'tk');
    CREATE TABLE IF NOT EXISTS todos(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT, done INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT, remind_at TEXT, sent INTEGER DEFAULT 0);
    """)
    conn.commit()

url_cache = {}
user_state = {}

# ---------------- LANGUAGES ----------------
LANGS = {
    "tk": "🇹🇲 Türkmen", "ru": "🇷🇺 Русский", "en": "🇬🇧 English",
    "tr": "🇹🇷 Türkçe", "de": "🇩🇪 Deutsch"
}
# Missing translations fall back to Turkmen.
T = {
"tk": {
"menu":"🤖 <b>Esasy Menýu</b>\n\nHaýsy bölümi saýlaýarsyňyz?",
"cat_w":"🌤 Howa & Täzelikler","desc_w":"<b>🌤 Howa & Täzelikler</b>\nHowa, zilzila we IT täzelikleri.",
"cat_os":"🕵️ OSINT & Howpsuzlyk","desc_os":"<b>🕵️ OSINT & Howpsuzlyk</b>\nIP, ulanyjy ady, parol we surat gözlegi.",
"cat_md":"📥 Media & Guralar","desc_md":"<b>📥 Media & Guralar</b>\nWideo/aýdym ýüklemek, TTS, QR, PDF.",
"cat_ai":"🤖 AI & Dil","desc_ai":"<b>🤖 AI & Dil</b>\nAI çat, surat döretmek, terjime we OCR.",
"cat_pt":"🧰 Amaly Gurallar","desc_pt":"<b>🧰 Amaly Gurallar</b>\nBirlik öwürmek, saýt barlamak, kino gözlemek.",
"cat_fun":"🎮 Oýun & Gözleg","desc_fun":"<b>🎮 Oýun & Gözleg</b>\nAýdym, kitap gözlegi we kiber oýny.",
"cat_ps":"📝 Şahsy","desc_ps":"<b>📝 Şahsy</b>\nÝazgylar we ýatlatmalar.",
"btn_weather":"🌤 Howa","btn_quake":"🌍 Zilzila","btn_news":"📰 Täzelikler",
"btn_ip":"🌐 IP/Domen","btn_user":"🕵️ Ulanyjy","btn_pass":"🔐 Parol","btn_scrape":"🕸 Saýtdan maglumat","btn_face":"📸 Surat gözlegi",
"btn_dl":"📥 Ýükle","btn_tts":"🗣 Ses (TTS)","btn_qr":"📱 QR döret","btn_qrread":"📷 QR oka","btn_pdf":"📄 Suratlary PDF",
"btn_ai":"🤖 AI çat","btn_img":"🎨 Surat döret","btn_tr":"🌐 Terjime","btn_ocr":"📸 OCR",
"btn_conv":"📏 Birlik öwür","btn_site":"📶 Saýt barla","btn_movie":"🎬 Kino/serial",
"btn_music":"🎵 Aýdym gözle","btn_book":"📚 Kitap gözle","btn_quiz":"🎮 Kiber oýun",
"btn_todo":"📝 Ýazgylar","btn_remind":"⏰ Ýatlatma","back":"⬅️ Yza","stop_ai":"🛑 AI-ny bes et",
"btn_vid":"🎬 Wideo (HQ)","btn_aud":"🎵 Aýdym (MP3)",
"ask_city":"🏙 Şäher adyny ýazyň:","ask_ip":"🌐 IP ýa-da domen ýazyň:","ask_user":"👤 Ulanyjy adyny ýazyň:","ask_pass":"🔐 Parol uzynlygyny ýazyň (8-64):",
"ask_dl":"📥 TikTok, YouTube ýa-da Instagram salgysyny iberiň:","ask_face":"📸 Surat iberiň. Surat internetde wagtlaýyn ýerleşdirilip, tersine gözleg baglanyşyklary dörediler.",
"ask_tts":"🗣 Seslendirmek üçin tekst iberiň:","ask_qr":"📱 QR üçin tekst/link iberiň:","ask_qrread":"📷 QR kodly suraty iberiň:","ask_pdf":"📄 PDF üçin suratlary iberiň. Soňra /done_pdf ýazyň.",
"ask_ai":"🤖 <b>AI çat açyk.</b>\nSoragyňyzy ýazyň. Çykmak üçin /stop.",
"ask_img":"🎨 Surat üçin prompt iberiň (iňlisçe has gowy netije berýär):","ask_tr":"🌐 Terjime üçin tekst iberiň. Mysal: <code>en ru Hello</code> ýa-da diňe tekst.",
"ask_ocr":"📸 Tekstli suraty iberiň:","ask_conv":"📏 Mysal: <code>10 km to miles</code>","ask_site":"📶 Saýtyň salgysyny iberiň:","ask_movie":"🎬 Kino ýa-da serial adyny ýazyň:",
"ask_scrape":"🕸 Maglumat çekmek üçin URL iberiň:","ask_music":"🎵 Aýdymyň ýa-da aýdymçynyň adyny ýazyň:","ask_book":"📚 Kitabyň adyny ýazyň:",
"ask_todo":"📝 Ýazgyňyzy iberiň:","ask_remind":"⏰ Format: <code>10m Suw içmeli</code> (m=minut, h=sagat, d= gün)",
"load":"⏳ Garaşyň...","notfound":"❌ Tapylmady!","err":"❌ Ýalňyşlyk: {e}","ask_format":"Nähili görnüşde ýüklemeli?","dl_wait":"⏳ Ýüklenýär...","dl_err":"❌ Ýüklemek başartmady."
},
"ru": {
"menu":"🤖 <b>Главное меню</b>\n\nВыберите раздел:","cat_w":"🌤 Погода и новости","desc_w":"<b>🌤 Погода и новости</b>",
"cat_os":"🕵️ OSINT и безопасность","desc_os":"<b>🕵️ OSINT и безопасность</b>","cat_md":"📥 Медиа и инструменты","desc_md":"<b>📥 Медиа и инструменты</b>",
"cat_ai":"🤖 ИИ и язык","desc_ai":"<b>🤖 ИИ и язык</b>","cat_pt":"🧰 Полезные инструменты","desc_pt":"<b>🧰 Полезные инструменты</b>",
"cat_fun":"🎮 Игры и поиск","desc_fun":"<b>🎮 Игры и поиск</b>","cat_ps":"📝 Личное","desc_ps":"<b>📝 Личное</b>",
"btn_weather":"🌤 Погода","btn_quake":"🌍 Землетрясения","btn_news":"📰 Новости","btn_ip":"🌐 IP/Домен","btn_user":"🕵️ Юзернейм","btn_pass":"🔐 Пароль","btn_scrape":"🕸 Парсинг","btn_face":"📸 Поиск по фото",
"btn_dl":"📥 Скачать","btn_tts":"🗣 Озвучка","btn_qr":"📱 Создать QR","btn_qrread":"📷 Читать QR","btn_pdf":"📄 Фото в PDF","btn_ai":"🤖 ИИ чат","btn_img":"🎨 Создать фото","btn_tr":"🌐 Перевод","btn_ocr":"📸 OCR",
"btn_conv":"📏 Конвертер","btn_site":"📶 Проверка сайта","btn_movie":"🎬 Кино/сериал","btn_music":"🎵 Поиск музыки","btn_book":"📚 Поиск книг","btn_quiz":"🎮 Кибер-игра",
"btn_todo":"📝 Заметки","btn_remind":"⏰ Напоминание","back":"⬅️ Назад","stop_ai":"🛑 Выйти из ИИ","btn_vid":"🎬 Видео (HQ)","btn_aud":"🎵 Аудио (MP3)",
"ask_city":"🏙 Название города:","ask_ip":"🌐 IP или домен:","ask_user":"👤 Имя пользователя:","ask_pass":"🔐 Длина пароля (8-64):","ask_dl":"📥 Отправьте ссылку TikTok/YouTube/Instagram:",
"ask_face":"📸 Отправьте фото для обратного поиска изображений:","ask_tts":"🗣 Текст для озвучки:","ask_qr":"📱 Текст/ссылка для QR:","ask_qrread":"📷 Фото с QR-кодом:","ask_pdf":"📄 Отправьте фото для PDF, затем /done_pdf.",
"ask_ai":"🤖 <b>ИИ-чат включён.</b>\nДля выхода /stop.","ask_img":"🎨 Опишите изображение:","ask_tr":"🌐 Текст для перевода. Формат: <code>en ru Hello</code> или просто текст.",
"ask_ocr":"📸 Отправьте фото с текстом:","ask_conv":"📏 Например: <code>10 km to miles</code>","ask_site":"📶 Адрес сайта:","ask_movie":"🎬 Название фильма/сериала:","ask_scrape":"🕸 URL сайта:","ask_music":"🎵 Название песни или исполнителя:","ask_book":"📚 Название книги:","ask_todo":"📝 Заметка:","ask_remind":"⏰ Формат: <code>10m Вода</code>",
"load":"⏳ Загрузка...","notfound":"❌ Не найдено!","err":"❌ Ошибка: {e}","ask_format":"Выберите формат:","dl_wait":"⏳ Скачивание...","dl_err":"❌ Не удалось скачать."
},
"en": {
"menu":"🤖 <b>Main menu</b>\n\nChoose a category:","cat_w":"🌤 Weather & News","desc_w":"<b>🌤 Weather & News</b>","cat_os":"🕵️ OSINT & Security","desc_os":"<b>🕵️ OSINT & Security</b>",
"cat_md":"📥 Media & Tools","desc_md":"<b>📥 Media & Tools</b>","cat_ai":"🤖 AI & Language","desc_ai":"<b>🤖 AI & Language</b>","cat_pt":"🧰 Practical tools","desc_pt":"<b>🧰 Practical tools</b>",
"cat_fun":"🎮 Games & Search","desc_fun":"<b>🎮 Games & Search</b>","cat_ps":"📝 Personal","desc_ps":"<b>📝 Personal</b>",
"btn_weather":"🌤 Weather","btn_quake":"🌍 Earthquakes","btn_news":"📰 News","btn_ip":"🌐 IP/Domain","btn_user":"🕵️ Username","btn_pass":"🔐 Password","btn_scrape":"🕸 Web scraper","btn_face":"📸 Reverse image search",
"btn_dl":"📥 Download","btn_tts":"🗣 Text to speech","btn_qr":"📱 Create QR","btn_qrread":"📷 Read QR","btn_pdf":"📄 Images to PDF","btn_ai":"🤖 AI chat","btn_img":"🎨 Generate image","btn_tr":"🌐 Translate","btn_ocr":"📸 OCR",
"btn_conv":"📏 Converter","btn_site":"📶 Site check","btn_movie":"🎬 Movie/series","btn_music":"🎵 Music search","btn_book":"📚 Book search","btn_quiz":"🎮 Cyber quiz","btn_todo":"📝 Notes","btn_remind":"⏰ Reminder",
"back":"⬅️ Back","stop_ai":"🛑 Stop AI","btn_vid":"🎬 Video (HQ)","btn_aud":"🎵 Audio (MP3)",
"ask_city":"🏙 City name:","ask_ip":"🌐 IP or domain:","ask_user":"👤 Username:","ask_pass":"🔐 Password length (8-64):","ask_dl":"📥 Send a TikTok, YouTube or Instagram URL:",
"ask_face":"📸 Send an image for reverse image search:","ask_tts":"🗣 Text to speak:","ask_qr":"📱 Text/link for QR:","ask_qrread":"📷 Send an image containing a QR code:","ask_pdf":"📄 Send images, then use /done_pdf.",
"ask_ai":"🤖 <b>AI chat is enabled.</b>\nUse /stop to exit.","ask_img":"🎨 Describe the image:","ask_tr":"🌐 Text to translate. Format: <code>en ru Hello</code> or plain text.",
"ask_ocr":"📸 Send an image containing text:","ask_conv":"📏 Example: <code>10 km to miles</code>","ask_site":"📶 Website URL:","ask_movie":"🎬 Movie/series title:","ask_scrape":"🕸 Website URL:","ask_music":"🎵 Song or artist name:","ask_book":"📚 Book title:","ask_todo":"📝 Your note:","ask_remind":"⏰ Format: <code>10m Drink water</code>",
"load":"⏳ Loading...","notfound":"❌ Not found!","err":"❌ Error: {e}","ask_format":"Choose download format:","dl_wait":"⏳ Downloading...","dl_err":"❌ Download failed."
},
"tr": {
"menu":"🤖 <b>Ana Menü</b>\n\nBir kategori seçin:","cat_w":"🌤 Hava & Haberler","desc_w":"<b>🌤 Hava & Haberler</b>","cat_os":"🕵️ OSINT & Güvenlik","desc_os":"<b>🕵️ OSINT & Güvenlik</b>",
"cat_md":"📥 Medya & Araçlar","desc_md":"<b>📥 Medya & Araçlar</b>","cat_ai":"🤖 AI & Dil","desc_ai":"<b>🤖 AI & Dil</b>","cat_pt":"🧰 Pratik Araçlar","desc_pt":"<b>🧰 Pratik Araçlar</b>","cat_fun":"🎮 Oyun & Arama","desc_fun":"<b>🎮 Oyun & Arama</b>","cat_ps":"📝 Kişisel","desc_ps":"<b>📝 Kişisel</b>",
"btn_weather":"🌤 Hava","btn_quake":"🌍 Deprem","btn_news":"📰 Haberler","btn_ip":"🌐 IP/Domain","btn_user":"🕵️ Kullanıcı","btn_pass":"🔐 Şifre","btn_scrape":"🕸 Site tarama","btn_face":"📸 Görsel arama",
"btn_dl":"📥 İndir","btn_tts":"🗣 Seslendir","btn_qr":"📱 QR oluştur","btn_qrread":"📷 QR oku","btn_pdf":"📄 PDF","btn_ai":"🤖 AI sohbet","btn_img":"🎨 Görsel oluştur","btn_tr":"🌐 Çeviri","btn_ocr":"📸 OCR",
"btn_conv":"📏 Dönüştür","btn_site":"📶 Site kontrol","btn_movie":"🎬 Film/Dizi","btn_music":"🎵 Müzik ara","btn_book":"📚 Kitap ara","btn_quiz":"🎮 Siber oyun","btn_todo":"📝 Notlar","btn_remind":"⏰ Hatırlatıcı",
"back":"⬅️ Geri","stop_ai":"🛑 AI çıkış","btn_vid":"🎬 Video (HQ)","btn_aud":"🎵 Ses (MP3)",
"ask_city":"🏙 Şehir:","ask_ip":"🌐 IP veya domain:","ask_user":"👤 Kullanıcı adı:","ask_pass":"🔐 Şifre uzunluğu:","ask_dl":"📥 TikTok/YouTube/Instagram URL gönderin:","ask_face":"📸 Tersine görsel arama için fotoğraf gönderin:",
"ask_tts":"🗣 Metin:","ask_qr":"📱 QR metni/linki:","ask_qrread":"📷 QR fotoğrafı:","ask_pdf":"📄 Fotoğrafları gönderin, sonra /done_pdf.","ask_ai":"🤖 <b>AI sohbet açık.</b>\nÇıkmak için /stop.","ask_img":"🎨 Görseli açıklayın:","ask_tr":"🌐 Çevrilecek metin:","ask_ocr":"📸 Metin içeren fotoğraf:","ask_conv":"📏 Örnek: <code>10 km to miles</code>","ask_site":"📶 Site adresi:","ask_movie":"🎬 Film/dizi adı:","ask_scrape":"🕸 Site URL:","ask_music":"🎵 Şarkı veya sanatçı:","ask_book":"📚 Kitap adı:","ask_todo":"📝 Not:","ask_remind":"⏰ Format: <code>10m Su iç</code>",
"load":"⏳ Yükleniyor...","notfound":"❌ Bulunamadı!","err":"❌ Hata: {e}","ask_format":"İndirme biçimini seçin:","dl_wait":"⏳ İndiriliyor...","dl_err":"❌ İndirme başarısız."
},
"de": {
"menu":"🤖 <b>Hauptmenü</b>\n\nKategorie auswählen:","cat_w":"🌤 Wetter & Nachrichten","desc_w":"<b>🌤 Wetter & Nachrichten</b>","cat_os":"🕵️ OSINT & Sicherheit","desc_os":"<b>🕵️ OSINT & Sicherheit</b>","cat_md":"📥 Medien & Tools","desc_md":"<b>📥 Medien & Tools</b>","cat_ai":"🤖 KI & Sprache","desc_ai":"<b>🤖 KI & Sprache</b>","cat_pt":"🧰 Werkzeuge","desc_pt":"<b>🧰 Werkzeuge</b>","cat_fun":"🎮 Spiele & Suche","desc_fun":"<b>🎮 Spiele & Suche</b>","cat_ps":"📝 Persönlich","desc_ps":"<b>📝 Persönlich</b>",
"btn_weather":"🌤 Wetter","btn_quake":"🌍 Erdbeben","btn_news":"📰 Nachrichten","btn_ip":"🌐 IP/Domain","btn_user":"🕵️ Benutzername","btn_pass":"🔐 Passwort","btn_scrape":"🕸 Website-Analyse","btn_face":"📸 Bildersuche","btn_dl":"📥 Herunterladen","btn_tts":"🗣 Vorlesen","btn_qr":"📱 QR erstellen","btn_qrread":"📷 QR lesen","btn_pdf":"📄 Bilder zu PDF","btn_ai":"🤖 KI-Chat","btn_img":"🎨 Bild erstellen","btn_tr":"🌐 Übersetzen","btn_ocr":"📸 OCR","btn_conv":"📏 Umrechner","btn_site":"📶 Website prüfen","btn_movie":"🎬 Film/Serie","btn_music":"🎵 Musik suchen","btn_book":"📚 Bücher suchen","btn_quiz":"🎮 Cyber-Quiz","btn_todo":"📝 Notizen","btn_remind":"⏰ Erinnerung","back":"⬅️ Zurück","stop_ai":"🛑 KI beenden","btn_vid":"🎬 Video (HQ)","btn_aud":"🎵 Audio (MP3)",
"ask_city":"🏙 Stadt:","ask_ip":"🌐 IP oder Domain:","ask_user":"👤 Benutzername:","ask_pass":"🔐 Passwortlänge:","ask_dl":"📥 TikTok/YouTube/Instagram-URL senden:","ask_face":"📸 Bild für Rückwärtssuche senden:","ask_tts":"🗣 Text:","ask_qr":"📱 QR-Text/Link:","ask_qrread":"📷 QR-Bild senden:","ask_pdf":"📄 Bilder senden, danach /done_pdf.","ask_ai":"🤖 <b>KI-Chat aktiviert.</b>\nZum Beenden /stop.","ask_img":"🎨 Bild beschreiben:","ask_tr":"🌐 Text zum Übersetzen:","ask_ocr":"📸 Bild mit Text senden:","ask_conv":"📏 Beispiel: <code>10 km to miles</code>","ask_site":"📶 Website-Adresse:","ask_movie":"🎬 Film-/Serientitel:","ask_scrape":"🕸 Website-URL:","ask_music":"🎵 Lied oder Künstler:","ask_book":"📚 Buchtitel:","ask_todo":"📝 Notiz:","ask_remind":"⏰ Format: <code>10m Wasser trinken</code>",
"load":"⏳ Lädt...","notfound":"❌ Nicht gefunden!","err":"❌ Fehler: {e}","ask_format":"Format auswählen:","dl_wait":"⏳ Wird heruntergeladen...","dl_err":"❌ Download fehlgeschlagen."
}
}

def tr(cid, key):
    lang = get_lang(cid)
    return T.get(lang, T["tk"]).get(key, T["tk"].get(key, "⚠️"))

def get_lang(cid):
    with db_lock:
        row = conn.execute("SELECT lang FROM users WHERE chat_id=?", (cid,)).fetchone()
    return row[0] if row else "tk"

def set_lang(cid, lang):
    if lang not in LANGS:
        return
    with db_lock:
        conn.execute("INSERT INTO users(chat_id,lang) VALUES(?,?) ON CONFLICT(chat_id) DO UPDATE SET lang=excluded.lang", (cid, lang))
        conn.commit()

def set_state(cid, value):
    with state_lock:
        user_state[cid] = value

def pop_state(cid):
    with state_lock:
        return user_state.pop(cid, None)

def get_state(cid):
    with state_lock:
        return user_state.get(cid)

def safe_html(value):
    return html.escape(str(value or ""), quote=True)

# ---------------- KEYBOARDS ----------------
def main_kb(cid):
    kb = types.InlineKeyboardMarkup(row_width=1)
    cats = ["w", "os", "md", "ai", "pt", "fun", "ps"]
    for cat in cats:
        kb.add(types.InlineKeyboardButton(tr(cid, "cat_" + cat), callback_data="cat_" + cat))
    kb.add(types.InlineKeyboardButton("🌐 Hacker Tools (Web)", url="https://cyber-alltool.netlify.app/"))
    kb.add(types.InlineKeyboardButton("🌍 Dil / Language", callback_data="lang_menu"))
    return kb

def cat_kb(cid, cat):
    groups = {
        "w":["weather","quake","news"],
        "os":["ip","user","pass","scrape","face"],
        "md":["dl","tts","qr","qrread","pdf"],
        "ai":["ai","img","tr","ocr"],
        "pt":["conv","site","movie"],
        "fun":["music","book","quiz"],
        "ps":["todo","remind"]
    }
    kb = types.InlineKeyboardMarkup(row_width=2)
    for action in groups.get(cat, []):
        kb.add(types.InlineKeyboardButton(tr(cid, "btn_" + action), callback_data="act_" + action))
    kb.add(types.InlineKeyboardButton(tr(cid, "back"), callback_data="menu"))
    return kb

def lang_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    for code, name in LANGS.items():
        kb.add(types.InlineKeyboardButton(name, callback_data="lang_" + code))
    return kb

def stop_ai_kb(cid):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(tr(cid, "stop_ai"), callback_data="menu"))
    return kb

def dl_format_kb(cid, url):
    short_id = uuid.uuid4().hex[:12]
    with state_lock:
        url_cache[short_id] = (url, time.time())
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(tr(cid, "btn_vid"), callback_data="dl_vid_" + short_id),
        types.InlineKeyboardButton(tr(cid, "btn_aud"), callback_data="dl_aud_" + short_id)
    )
    return kb

# ---------------- URL / MEDIA ----------------
ALLOWED_HOSTS = ("tiktok.com", "youtube.com", "youtu.be", "instagram.com")

def normalize_media_url(value):
    value = value.strip()
    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if not any(host == d or host.endswith("." + d) for d in ALLOWED_HOSTS):
        raise ValueError("Diňe TikTok, YouTube we Instagram salgylary goldanylýar.")
    return value

def f_download(url, cid, mode="audio"):
    """Download media to a unique temp directory and return the real output path."""
    workdir = tempfile.mkdtemp(prefix=f"dl_{cid}_", dir=DOWNLOAD_DIR)
    try:
        url = normalize_media_url(url)
        outtmpl = os.path.join(workdir, "%(id)s.%(ext)s")
        opts = {
            "quiet": True, "no_warnings": True, "noplaylist": True,
            "outtmpl": outtmpl, "restrictfilenames": True,
            "retries": 3, "fragment_retries": 3, "socket_timeout": 30,
            "ignoreerrors": False, "overwrites": True,
        }
        cookie_file = os.getenv("YTDLP_COOKIES_FILE", "").strip()
        if cookie_file and os.path.isfile(cookie_file):
            opts["cookiefile"] = cookie_file
        # Prefer a single-file MP4 for video to avoid mandatory FFmpeg merging.
        if mode == "audio":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            opts["format"] = "best[ext=mp4][height<=1080]/best[height<=1080]/best"
            opts["merge_output_format"] = "mp4"
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise RuntimeError("Wideo barada maglumat tapylmady.")
            if info.get("entries"):
                info = next((x for x in info["entries"] if x), None)
            if not info:
                raise RuntimeError("Media tapylmady.")
            requested = info.get("requested_downloads") or []
            candidates = []
            if mode == "audio":
                candidates += [os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"]
            else:
                candidates += [ydl.prepare_filename(info)]
                if info.get("_filename"):
                    candidates.append(info["_filename"])
            for item in requested:
                fp = item.get("filepath")
                if fp:
                    candidates.append(fp)
            candidates += [
                os.path.join(workdir, n) for n in os.listdir(workdir)
                if not n.endswith((".part", ".ytdl", ".temp"))
            ]
            file_path = next((p for p in candidates if p and os.path.isfile(p)), None)
            if not file_path:
                raise RuntimeError("Ýüklenen faýl tapylmady. FFmpeg gurnalanlygyny barlaň.")
            size = os.path.getsize(file_path)
            if size > 49 * 1024 * 1024:
                raise RuntimeError(f"Faýl uly ({size / 1024 / 1024:.1f} MB). Telegram bot API çägi takmynan 50 MB.")
            return {"file": file_path, "title": info.get("title") or "Download", "mode": mode, "workdir": workdir}
    except Exception as exc:
        # Keep no partial files after a failed download.
        try:
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)
        except Exception:
            pass
        return {"error": str(exc)[:900]}

def f_music_search(query, cid):
    query = query.strip()
    if not query:
        return {"error": "Aýdym adyny ýazyň."}
    try:
        search_opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "socket_timeout": 25}
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            data = ydl.extract_info("ytsearch1:" + query, download=False)
        entries = (data or {}).get("entries") or []
        if not entries:
            return {"error": "Aýdym tapylmady."}
        item = entries[0]
        video_url = item.get("webpage_url") or item.get("url")
        if video_url and not str(video_url).startswith("http"):
            video_url = "https://www.youtube.com/watch?v=" + str(item.get("id", video_url))
        if not video_url:
            return {"error": "Aýdymyň salgysy tapylmady."}
        result = f_download(video_url, cid, "audio")
        if not result.get("error"):
            result["title"] = item.get("title") or result.get("title")
        return result
    except Exception as exc:
        return {"error": str(exc)[:700]}

# ---------------- FEATURE FUNCTIONS ----------------
def f_weather(city):
    try:
        g = HTTP.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name":city,"count":1,"language":"en"}, timeout=12).json()
        if not g.get("results"):
            return None
        p = g["results"][0]
        w = HTTP.get("https://api.open-meteo.com/v1/forecast",
            params={"latitude":p["latitude"],"longitude":p["longitude"],
                    "hourly":"temperature_2m,relative_humidity_2m,precipitation_probability",
                    "forecast_hours":12,"timezone":"auto"}, timeout=12).json()
        hourly = w.get("hourly", {})
        out = [f"📍 <b>{safe_html(p['name'])}, {safe_html(p.get('country',''))}</b>\n⏰ Indiki 12 sagat\n"]
        for i, stamp in enumerate(hourly.get("time", [])[:12]):
            temp = hourly.get("temperature_2m", [])[i]
            hum = hourly.get("relative_humidity_2m", [])[i]
            rain = hourly.get("precipitation_probability", [])[i]
            icon = "☀️" if rain < 20 else "🌦" if rain < 60 else "⛈"
            out.append(f"{icon} <code>{stamp.split('T')[-1]}</code>  <b>{temp}°C</b>  💧{hum}%")
        return "\n".join(out)
    except Exception as e:
        return f"❌ {safe_html(e)}"

def f_ip(query):
    try:
        try:
            ip = socket.gethostbyname(query.strip())
        except OSError:
            ip = query.strip()
        r = HTTP.get(f"http://ip-api.com/json/{quote(ip)}",
                     params={"fields":"status,country,city,isp,org,query"}, timeout=12).json()
        if r.get("status") != "success":
            return None
        return (f"🌐 <b>{safe_html(r.get('query'))}</b>\n"
                f"🏳️ {safe_html(r.get('country','—'))}\n"
                f"🏙 {safe_html(r.get('city','—'))}\n"
                f"📡 {safe_html(r.get('isp','—'))}")
    except Exception as e:
        return f"❌ {safe_html(e)}"

def f_username(username):
    username = re.sub(r"[^a-zA-Z0-9_.-]", "", username).strip(".")
    if not username:
        return "❌ Ulanyjy ady nädogry."
    sites = {
        "GitHub":f"https://github.com/{username}", "Reddit":f"https://www.reddit.com/user/{username}",
        "Telegram":f"https://t.me/{username}", "Instagram":f"https://www.instagram.com/{username}/",
        "TikTok":f"https://www.tiktok.com/@{username}", "X":f"https://x.com/{username}",
        "Pinterest":f"https://www.pinterest.com/{username}/", "Twitch":f"https://www.twitch.tv/{username}",
        "YouTube":f"https://youtube.com/@{username}", "Steam":f"https://steamcommunity.com/id/{username}",
        "VK":f"https://vk.com/{username}", "Dribbble":f"https://dribbble.com/{username}"
    }
    found = []
    for name, url in sites.items():
        try:
            response = HTTP.get(url, timeout=7, allow_redirects=True)
            if response.status_code == 200 and "page not found" not in response.text[:4000].lower():
                found.append(f'🟢 <a href="{url}">{safe_html(name)}</a>')
        except requests.RequestException:
            pass
    return f"🕵️ <b>@{safe_html(username)}</b>\n\n" + ("\n".join(found) if found else "❌ Açyk profil tapylmady ýa-da saýtlaryň barlagy çäklendirildi.")

def f_scrape(url):
    try:
        url = normalize_http_url(url)
        r = HTTP.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else "Ady ýok"
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        paragraphs = [p for p in paragraphs if len(p) > 30]
        body = "\n\n".join(paragraphs[:4])
        return f"🕸 <b>{safe_html(title)}</b>\n\n{safe_html(body[:2500])}" if body else f"🕸 <b>{safe_html(title)}</b>\n\nTekst tapylmady."
    except Exception as e:
        return f"❌ {safe_html(e)}"

def normalize_http_url(url):
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("URL nädogry.")
    return url

def f_face_search(img_bytes):
    """Uploads an image temporarily and returns reverse-image-search links, not identity recognition."""
    try:
        response = requests.post("https://0x0.st", files={"file":("image.jpg", img_bytes, "image/jpeg")}, timeout=25)
        response.raise_for_status()
        image_url = response.text.strip()
        if not image_url.startswith("https://"):
            raise RuntimeError("Surat hyzmat tarapyndan kabul edilmedi.")
        encoded = quote(image_url, safe="")
        return (
            "✅ <b>Surat wagtlaýyn ýüklendi.</b>\n"
            "Bu hyzmat adamyň kimdigini anyklamaýar. Diňe suratyň internetdäki meňzeş nusgalaryny gözlemek üçin:\n\n"
            f'🔎 <a href="https://lens.google.com/uploadbyurl?url={encoded}">Google Lens</a>\n'
            f'🔎 <a href="https://yandex.com/images/search?rpt=imageview&url={encoded}">Yandex Images</a>\n'
            f'🔎 <a href="https://www.bing.com/images/search?view=detailv2&iss=sbiupload&q=imgurl:{encoded}">Bing Images</a>\n'
            f'🔎 <a href="https://tineye.com/search?url={encoded}">TinEye</a>\n\n'
            "⚠️ Surat üçün üçünji tarap hyzmatynyň gizlinlik düzgünlerini göz öňünde tutuň."
        )
    except Exception as e:
        return f"❌ {safe_html(e)}"

def f_pass(length=16):
    length = max(8, min(int(length), 64))
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def f_qr(text):
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf

def f_qr_read(img_bytes):
    try:
        r = HTTP.post("https://api.qrserver.com/v1/read-qr-code/",
                      files={"file":("qr.png", img_bytes, "image/png")}, timeout=15).json()
        data = r[0]["symbol"][0].get("data") if r and r[0].get("symbol") else None
        return f"📱 <b>QR maglumaty:</b>\n\n<code>{safe_html(data)}</code>" if data else "❌ QR kod tapylmady."
    except Exception as e:
        return f"❌ {safe_html(e)}"

def f_ocr(img_bytes):
    try:
        api_key = os.getenv("OCR_SPACE_API_KEY", "helloworld")
        response = HTTP.post("https://api.ocr.space/parse/image",
            files={"filename":("image.jpg", img_bytes, "image/jpeg")},
            data={"apikey":api_key,"language":"eng","isOverlayRequired":False}, timeout=30).json()
        if response.get("IsErroredOnProcessing"):
            return "❌ OCR işläp bilmedi. OCR_SPACE_API_KEY sazlamasyny barlaň."
        parsed = "\n".join(x.get("ParsedText","") for x in response.get("ParsedResults", []))
        return f"📸 <b>Suratdan tekst:</b>\n\n<code>{safe_html(parsed[:3500])}</code>" if parsed.strip() else "❌ Tekst tapylmady."
    except Exception as e:
        return f"❌ {safe_html(e)}"

def f_img2pdf(images):
    try:
        pages = [Image.open(io.BytesIO(data)).convert("RGB") for data in images]
        if not pages:
            return None
        buf = io.BytesIO()
        pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
        buf.seek(0)
        return buf
    except Exception:
        return None

def f_translate(text):
    try:
        parts = text.split(maxsplit=2)
        src, target, query = "autodetect", "ru", text
        if len(parts) == 3 and re.fullmatch(r"[a-zA-Z-]{2,12}", parts[0]) and re.fullmatch(r"[a-zA-Z-]{2,12}", parts[1]):
            src, target, query = parts
        data = HTTP.get("https://api.mymemory.translated.net/get",
            params={"q":query,"langpair":f"{src}|{target}"}, timeout=20).json()
        translated = data.get("responseData",{}).get("translatedText","")
        return f"🌐 <b>{safe_html(src)} → {safe_html(target)}</b>\n\n{safe_html(translated or 'Terjime tapylmady.')}"
    except Exception as e:
        return f"❌ {safe_html(e)}"

def f_convert(text):
    try:
        match = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s+([a-zA-Z]+)\s+(?:to|->)\s+([a-zA-Z]+)\s*$", text.lower())
        if not match:
            return "❌ Format: <code>10 km to miles</code>"
        val, u1, u2 = float(match.group(1)), match.group(2), match.group(3)
        pairs = {
            ("km","miles"):lambda x:x*0.621371, ("miles","km"):lambda x:x/0.621371,
            ("kg","lbs"):lambda x:x*2.20462, ("lbs","kg"):lambda x:x/2.20462,
            ("c","f"):lambda x:x*9/5+32, ("f","c"):lambda x:(x-32)*5/9,
            ("m","ft"):lambda x:x*3.28084, ("ft","m"):lambda x:x/3.28084,
            ("cm","in"):lambda x:x/2.54, ("in","cm"):lambda x:x*2.54,
            ("l","gal"):lambda x:x*0.264172, ("gal","l"):lambda x:x/0.264172
        }
        fn = pairs.get((u1,u2))
        if not fn:
            return "❌ Bu birlik jübüti goldanylmaýar."
        return f"📏 <b>Netije:</b> {val:g} {u1} = <b>{fn(val):.4f} {u2}</b>"
    except Exception:
        return "❌ Format nädogry."

def f_sitecheck(url):
    try:
        url = normalize_http_url(url)
        r = HTTP.get(url, timeout=15, allow_redirects=True)
        return f"📶 <b>Saýt barlagy</b>\n\n{'🟢' if r.ok else '🟠'} <code>{safe_html(url)}</code>\nStatus: <b>{r.status_code}</b>"
    except Exception as e:
        return f"🔴 Saýt açylmady: {safe_html(e)}"

def f_ai(prompt):
    try:
        r = HTTP.get("https://text.pollinations.ai/" + quote(prompt, safe=""), timeout=60)
        if r.status_code == 200:
            return "🤖 <b>AI jogaby:</b>\n\n" + safe_html(r.text[:3800])
        return f"❌ AI jogap bermedi (HTTP {r.status_code})."
    except Exception as e:
        return f"❌ {safe_html(e)}"

def f_image_gen(prompt):
    try:
        url = "https://image.pollinations.ai/prompt/" + quote(prompt, safe="") + "?width=1024&height=1024&nologo=true"
        r = HTTP.get(url, timeout=90)
        return io.BytesIO(r.content) if r.status_code == 200 and r.content else None
    except Exception:
        return None

def f_movie(query):
    try:
        data = HTTP.get("https://search.imdbot.workers.dev/",
                        params={"q":query}, timeout=20).json()
        items = data.get("description") or []
        if not items:
            return None
        item = items[0]
        title = safe_html(item.get("#TITLE","—"))
        year = safe_html(item.get("#YEAR","—"))
        rank = safe_html(item.get("#RANK","—"))
        imdb_id = safe_html(item.get("#IMDB_ID",""))
        caption = f"🎬 <b>{title}</b> ({year})\n\n⭐ Reýting: {rank}\n🔗 <a href='https://www.imdb.com/title/{imdb_id}/'>IMDb</a>"
        return caption, item.get("#IMG_POSTER","")
    except Exception:
        return None

def f_earthquake():
    try:
        data = HTTP.get("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson", timeout=15).json()
        features = data.get("features",[])[:8]
        if not features:
            return "🌍 Soňky 24 sagatda möhüm zilzila ýok."
        out = ["🌍 <b>Soňky möhüm zilzilalar (24 sagat)</b>\n"]
        for item in features:
            p = item["properties"]
            mag = p.get("mag") or 0
            stamp = datetime.datetime.fromtimestamp(p["time"]/1000).strftime("%m-%d %H:%M")
            out.append(f"{'🔴' if mag>=6 else '🟠' if mag>=5 else '🟡'} <b>M{mag}</b> · {safe_html(p.get('place','—'))} · <i>{stamp}</i>")
        return "\n".join(out)
    except Exception as e:
        return f"❌ {safe_html(e)}"

def f_news():
    try:
        ids = HTTP.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=12).json()
        out = ["📰 <b>Iň täze tehnologiýa täzelikleri</b>\n"]
        for story_id in ids[:6]:
            item = HTTP.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=8).json()
            if item and item.get("title"):
                title = safe_html(item["title"])
                url = item.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
                out.append(f'🔹 <a href="{safe_html(url)}">{title}</a>')
        return "\n".join(out)
    except Exception:
        return "❌ Täzelikleri alyp bolmady."

def f_book_search(query):
    try:
        data = HTTP.get("https://openlibrary.org/search.json",
                        params={"q":query,"limit":4}, timeout=20).json()
        docs = data.get("docs",[])
        if not docs:
            return None
        out = [f"📚 <b>{safe_html(query)} boýunça netijeler:</b>\n"]
        for doc in docs:
            title = safe_html(doc.get("title","Näbelli"))
            authors = doc.get("author_name") or ["Näbelli"]
            author = safe_html(authors[0])
            key = safe_html(doc.get("key",""))
            out.append(f"📖 <b>{title}</b>\n✍️ {author}\n🔗 <a href='https://openlibrary.org{key}'>Maglumat</a>\n")
        return "\n".join(out)
    except Exception:
        return None

quiz_data = [
    {"q":"Haýsy parol iň howpsuz?","opts":["12345678","admin","P@ssw0rd!2024","qwerty"],"ans":2},
    {"q":"SQL näme üçin ulanylýar?","opts":["Surat döretmek","Maglumat bazasy","Wideo görkezmek","Ses ýazmak"],"ans":1},
    {"q":"XSS hüjümi nämä gönükdirilen?","opts":["Serwere","Ulanyjynyň brauzerine","Tor kabeline","Wi-Fi routerine"],"ans":1}
]

def quiz_kb(index):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for i, option in enumerate(quiz_data[index]["opts"]):
        kb.add(types.InlineKeyboardButton(option, callback_data=f"quiz_{index}_{i}"))
    return kb

def generate_tts(text, voice):
    async def _run():
        path = os.path.join(tempfile.gettempdir(), f"tts_{uuid.uuid4().hex}.mp3")
        await edge_tts.Communicate(text, voice).save(path)
        return path
    try:
        return asyncio.run(_run())
    except RuntimeError:
        # Works even if called from a thread with an already-running event loop.
        result = {}
        def runner():
            try:
                result["path"] = asyncio.run(_run())
            except Exception as exc:
                result["error"] = exc
        thread = threading.Thread(target=runner)
        thread.start()
        thread.join()
        return result.get("path")

def f_tts(text, lang):
    voices = {
        "tk":"tr-TR-EmelNeural", "ru":"ru-RU-SvetlanaNeural",
        "en":"en-US-AriaNeural", "tr":"tr-TR-EmelNeural", "de":"de-DE-KatjaNeural"
    }
    return generate_tts(text, voices.get(lang, voices["en"]))

# ---------------- TODO / REMINDERS ----------------
def f_todo_list(cid):
    with db_lock:
        rows = conn.execute("SELECT id,text,done FROM todos WHERE chat_id=? ORDER BY done,id", (cid,)).fetchall()
    if not rows:
        return "📝 Ýazgy ýok."
    lines = ["📝 <b>Ýazgylaryňyz:</b>\n"]
    for rid, text, done in rows[:30]:
        lines.append(f"{'✅' if done else '⬜'} <code>#{rid}</code> — {safe_html(text[:250])}")
    lines.append("\n<i>/done ID · /del ID</i>")
    return "\n".join(lines)

def f_add_reminder(cid, text):
    match = re.match(r"^(\d+)([mhd])\s+(.+)$", text.strip(), re.I)
    if not match:
        return "❌ Format: <code>10m Suw içmeli</code>"
    value, unit, task = int(match.group(1)), match.group(2).lower(), match.group(3).strip()
    if value < 1 or value > 525600 or not task:
        return "❌ Wagt ýa-da tekst nädogry."
    delta = datetime.timedelta(minutes=value) if unit=="m" else datetime.timedelta(hours=value) if unit=="h" else datetime.timedelta(days=value)
    remind_at = (datetime.datetime.now() + delta).strftime("%Y-%m-%d %H:%M:%S")
    with db_lock:
        conn.execute("INSERT INTO reminders(chat_id,text,remind_at) VALUES(?,?,?)", (cid,task,remind_at))
        conn.commit()
    return f"✅ Ýatlatma goýuldy!\n⏰ {remind_at}\n📝 {safe_html(task)}"

def reminder_worker():
    while True:
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with db_lock:
                due = conn.execute("SELECT id,chat_id,text FROM reminders WHERE remind_at<=? AND sent=0", (now,)).fetchall()
                for rid, cid, text in due:
                    conn.execute("UPDATE reminders SET sent=1 WHERE id=?", (rid,))
                conn.commit()
            for rid, cid, text in due:
                try:
                    bot.send_message(cid, f"🔔 <b>ÝATLATMA!</b>\n\n{safe_html(text)}")
                except Exception:
                    pass
        except Exception as e:
            print("Reminder worker:", e)
        time.sleep(20)

# ---------------- HANDLERS ----------------
@bot.message_handler(commands=["start","menu"])
def cmd_start(message):
    cid = message.chat.id
    if message.text and message.text.split()[0] == "/start":
        bot.send_message(cid, f"👋 <b>Salam, {safe_html(message.from_user.first_name)}!</b>\n\n🌍 <b>Dil saýlaň:</b>", reply_markup=lang_kb())
    else:
        bot.send_message(cid, tr(cid,"menu"), reply_markup=main_kb(cid))

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    cid = message.chat.id
    pop_state(cid)
    bot.reply_to(message, "🛑 AI/iş tertibi ýapyldy. Esasy menýu:", reply_markup=main_kb(cid))

@bot.message_handler(commands=["done_pdf"])
def cmd_done_pdf(message):
    cid = message.chat.id
    state = get_state(cid)
    if not isinstance(state, dict) or state.get("type") != "pdf":
        return bot.reply_to(message, "❌ Ilki PDF bölümini saýlaň.")
    images = state.get("images", [])
    if not images:
        return bot.reply_to(message, "❌ Surat ibermediňiz.")
    bot.send_chat_action(cid, "upload_document")
    pdf = f_img2pdf(images)
    if not pdf:
        return bot.reply_to(message, "❌ PDF döredip bolmady.")
    bot.send_document(cid, pdf, visible_file_name="photos.pdf")
    pop_state(cid)

@bot.message_handler(commands=["done"])
def cmd_done(message):
    try:
        rid = int(message.text.split(maxsplit=1)[1])
        with db_lock:
            cur = conn.execute("UPDATE todos SET done=1 WHERE id=? AND chat_id=?", (rid,message.chat.id))
            conn.commit()
        bot.reply_to(message, f"✅ #{rid} tamamlandy." if cur.rowcount else "❌ Şeýle ýazgy tapylmady.")
    except Exception:
        bot.reply_to(message, "❌ Format: /done 1")

@bot.message_handler(commands=["del"])
def cmd_del(message):
    try:
        rid = int(message.text.split(maxsplit=1)[1])
        with db_lock:
            cur = conn.execute("DELETE FROM todos WHERE id=? AND chat_id=?", (rid,message.chat.id))
            conn.commit()
        bot.reply_to(message, f"🗑 #{rid} pozuldy." if cur.rowcount else "❌ Şeýle ýazgy tapylmady.")
    except Exception:
        bot.reply_to(message, "❌ Format: /del 1")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    cid = call.message.chat.id if call.message else call.from_user.id
    data = call.data or ""
    if data.startswith("quiz_"):
        try:
            _, qi, ai = data.split("_")
            qi, ai = int(qi), int(ai)
            if qi < 0 or qi >= len(quiz_data) or ai < 0 or ai >= len(quiz_data[qi]["opts"]):
                return
            correct = ai == quiz_data[qi]["ans"]
            bot.answer_callback_query(call.id, "✅ Dogry!" if correct else "❌ Nädogry!", show_alert=True)
            if correct and qi + 1 < len(quiz_data):
                bot.send_message(cid, f"🎮 <b>Sorag {qi+2}:</b>\n\n{quiz_data[qi+1]['q']}", reply_markup=quiz_kb(qi+1))
            elif correct:
                bot.send_message(cid, "🏆 Ähli soraglar tamamlandy!")
        except Exception:
            pass
        return

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    if data.startswith(("dl_vid_", "dl_aud_")):
        mode = "video" if data.startswith("dl_vid_") else "audio"
        key = data.split("_", 2)[2]
        with state_lock:
            cached = url_cache.get(key)
        if not cached or time.time() - cached[1] > 1800:
            with state_lock:
                url_cache.pop(key, None)
            return bot.answer_callback_query(call.id, "❌ Salgynyň möhleti geçdi. Täzeden iberiň.", show_alert=True)
        url = cached[0]
        try:
            bot.edit_message_text(tr(cid,"dl_wait"), cid, call.message.message_id)
        except Exception:
            pass
        bot.send_chat_action(cid, "upload_video" if mode=="video" else "record_audio")
        result = f_download(url, cid, mode)
        if result.get("error"):
            try:
                bot.edit_message_text(f"{tr(cid,'dl_err')}\n\n<code>{safe_html(result['error'][:700])}</code>", cid, call.message.message_id)
            except Exception:
                bot.send_message(cid, f"{tr(cid,'dl_err')}\n\n<code>{safe_html(result['error'][:700])}</code>")
            with state_lock:
                url_cache.pop(key, None)
            return
        path = result["file"]
        try:
            with open(path, "rb") as stream:
                caption = safe_html(result.get("title","Download"))[:900]
                if mode == "video":
                    bot.send_video(cid, stream, caption=caption, supports_streaming=True, timeout=120)
                else:
                    bot.send_audio(cid, stream, title=result.get("title","Audio")[:200], timeout=120)
            bot.delete_message(cid, call.message.message_id)
        except Exception as exc:
            bot.send_message(cid, f"❌ Telegram faýly iberip bilmedi: <code>{safe_html(exc)}</code>")
        finally:
            import shutil
            shutil.rmtree(result.get("workdir",""), ignore_errors=True)
            with state_lock:
                url_cache.pop(key, None)
        return

    if data == "lang_menu":
        bot.edit_message_text("🌍 <b>Dil saýlaň:</b>", cid, call.message.message_id, reply_markup=lang_kb())
        return
    if data.startswith("lang_"):
        lang = data.split("_",1)[1]
        if lang not in LANGS:
            return
        set_lang(cid, lang)
        bot.edit_message_text(f"✅ {LANGS[lang]}", cid, call.message.message_id)
        bot.send_message(cid, tr(cid,"menu"), reply_markup=main_kb(cid))
        return
    if data == "menu":
        pop_state(cid)
        bot.edit_message_text(tr(cid,"menu"), cid, call.message.message_id, reply_markup=main_kb(cid))
        return
    if data.startswith("cat_"):
        cat = data.split("_",1)[1]
        if cat not in ("w","os","md","ai","pt","fun","ps"):
            return
        bot.edit_message_text(tr(cid,"desc_"+cat), cid, call.message.message_id, reply_markup=cat_kb(cid,cat))
        return
    if data.startswith("act_"):
        act = data.split("_",1)[1]
        if act == "quake":
            bot.send_message(cid, f_earthquake()); return
        if act == "news":
            bot.send_message(cid, f_news(), disable_web_page_preview=True); return
        if act == "ai":
            set_state(cid,"ai")
            bot.send_message(cid,tr(cid,"ask_ai"),reply_markup=stop_ai_kb(cid)); return
        if act == "pdf":
            set_state(cid,{"type":"pdf","images":[]})
            bot.send_message(cid,tr(cid,"ask_pdf")); return
        if act == "quiz":
            bot.send_message(cid,f"🎮 <b>Sorag 1:</b>\n\n{quiz_data[0]['q']}",reply_markup=quiz_kb(0)); return
        ask_keys = {
            "weather":"ask_city","ip":"ask_ip","user":"ask_user","pass":"ask_pass","dl":"ask_dl",
            "tts":"ask_tts","qr":"ask_qr","qrread":"ask_qrread","ocr":"ask_ocr","img":"ask_img",
            "tr":"ask_tr","conv":"ask_conv","site":"ask_site","movie":"ask_movie","scrape":"ask_scrape",
            "todo":"ask_todo","remind":"ask_remind","music":"ask_music","book":"ask_book","face":"ask_face"
        }
        if act in ask_keys:
            set_state(cid,act)
            bot.send_message(cid,tr(cid,ask_keys[act]))
        return

@bot.message_handler(content_types=["text","photo"])
def on_message(message):
    cid = message.chat.id
    state = get_state(cid)

    if message.content_type == "photo":
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            image_bytes = bot.download_file(file_info.file_path)
        except Exception as exc:
            return bot.reply_to(message, f"❌ Surat alyp bolmady: {safe_html(exc)}")
        if isinstance(state,dict) and state.get("type")=="pdf":
            state["images"].append(image_bytes)
            return bot.reply_to(message,f"✅ Surat goşuldy! Jemi: {len(state['images'])}\n/done_pdf ýazyň.")
        if state == "face":
            pop_state(cid)
            bot.send_chat_action(cid,"typing")
            msg = bot.reply_to(message,"⏳ Surat işlenýär...")
            result = f_face_search(image_bytes)
            return bot.edit_message_text(result,cid,msg.message_id,disable_web_page_preview=True)
        if state == "qrread":
            pop_state(cid)
            return bot.reply_to(message,f_qr_read(image_bytes))
        if state == "ocr":
            pop_state(cid)
            bot.send_chat_action(cid,"typing")
            return bot.reply_to(message,f_ocr(image_bytes))
        return bot.reply_to(message,"📷 Surat kabul edildi. Ilki menýudan degişli bölümi saýlaň.")

    if not message.text:
        return
    text = message.text.strip()
    if not text:
        return

    if state == "ai":
        bot.send_chat_action(cid,"typing")
        return bot.reply_to(message,f_ai(text),disable_web_page_preview=True)

    if state == "weather":
        pop_state(cid); return bot.reply_to(message,f_weather(text) or tr(cid,"notfound"))
    if state == "ip":
        pop_state(cid); return bot.reply_to(message,f_ip(text) or tr(cid,"notfound"))
    if state == "user":
        pop_state(cid); return bot.reply_to(message,f_username(text),disable_web_page_preview=True)
    if state == "pass":
        pop_state(cid)
        length = int(text) if text.isdigit() else 16
        return bot.reply_to(message,f"🔐 <code>{f_pass(length)}</code>")
    if state == "scrape":
        pop_state(cid); bot.send_chat_action(cid,"typing"); return bot.reply_to(message,f_scrape(text),disable_web_page_preview=True)
    if state == "dl":
        pop_state(cid)
        try:
            url = normalize_media_url(text)
            return bot.reply_to(message,tr(cid,"ask_format"),reply_markup=dl_format_kb(cid,url))
        except Exception as exc:
            return bot.reply_to(message,f"❌ {safe_html(exc)}")
    if state == "music":
        pop_state(cid); bot.send_chat_action(cid,"record_audio")
        status = bot.reply_to(message,tr(cid,"load"))
        result = f_music_search(text,cid)
        if result.get("error"):
            return bot.edit_message_text(f"❌ Aýdym ýükläp bolmady:\n<code>{safe_html(result['error'][:700])}</code>",cid,status.message_id)
        path = result["file"]
        try:
            with open(path,"rb") as stream:
                bot.send_audio(cid,stream,title=result.get("title","Audio")[:200],timeout=120)
            bot.delete_message(cid,status.message_id)
        except Exception as exc:
            bot.edit_message_text(f"❌ Iberip bolmady: {safe_html(exc)}",cid,status.message_id)
        finally:
            import shutil
            shutil.rmtree(result.get("workdir",""),ignore_errors=True)
        return
    if state == "book":
        pop_state(cid); bot.send_chat_action(cid,"typing")
        return bot.reply_to(message,f_book_search(text) or tr(cid,"notfound"),disable_web_page_preview=True)
    if state == "tts":
        pop_state(cid); bot.send_chat_action(cid,"record_voice")
        path = f_tts(text,get_lang(cid))
        if path and os.path.isfile(path):
            try:
                with open(path,"rb") as stream: bot.send_voice(cid,stream,timeout=90)
            finally:
                try: os.remove(path)
                except OSError: pass
        else:
            bot.reply_to(message,"❌ Ses döredip bolmady.")
        return
    if state == "qr":
        pop_state(cid)
        return bot.send_photo(cid,f_qr(text),caption=f"📱 <code>{safe_html(text[:300])}</code>")
    if state == "tr":
        pop_state(cid); bot.send_chat_action(cid,"typing"); return bot.reply_to(message,f_translate(text))
    if state == "conv":
        pop_state(cid); return bot.reply_to(message,f_convert(text))
    if state == "site":
        pop_state(cid); bot.send_chat_action(cid,"typing"); return bot.reply_to(message,f_sitecheck(text),disable_web_page_preview=True)
    if state == "img":
        pop_state(cid); bot.send_chat_action(cid,"upload_photo")
        status = bot.reply_to(message,tr(cid,"load"))
        image = f_image_gen(text)
        if image:
            bot.delete_message(cid,status.message_id)
            return bot.send_photo(cid,image,caption=f"🎨 <b>Prompt:</b> {safe_html(text[:700])}")
        return bot.edit_message_text("❌ Surat döredip bolmady.",cid,status.message_id)
    if state == "movie":
        pop_state(cid); bot.send_chat_action(cid,"typing")
        result = f_movie(text)
        if not result:
            return bot.reply_to(message,tr(cid,"notfound"))
        caption, poster = result
        if poster:
            try:
                return bot.send_photo(cid,poster,caption=caption)
            except Exception:
                pass
        return bot.reply_to(message,caption,disable_web_page_preview=True)
    if state == "todo":
        pop_state(cid)
        with db_lock:
            conn.execute("INSERT INTO todos(chat_id,text) VALUES(?,?)",(cid,text[:1000]))
            conn.commit()
        return bot.reply_to(message,"✅ Goşuldy!\n\n"+f_todo_list(cid))
    if state == "remind":
        pop_state(cid); return bot.reply_to(message,f_add_reminder(cid,text))

    # Automatic media URL detection in any normal chat.
    if re.match(r"^(https?://)?(www\.)?(m\.)?(vt\.)?(tiktok\.com|youtube\.com|youtu\.be|instagram\.com)/",text,re.I):
        try:
            url = normalize_media_url(text)
            return bot.reply_to(message,tr(cid,"ask_format"),reply_markup=dl_format_kb(cid,url))
        except Exception:
            pass

    bot.send_chat_action(cid,"typing")
    return bot.reply_to(message,f_ai(text)+"\n\n<i>Menýu: /menu</i>",disable_web_page_preview=True)

# ---------------- START ----------------
def main():
    print("Bot started.")
    threading.Thread(target=reminder_worker,daemon=True).start()
    # One active polling process is required. Running two copies causes Telegram 409 Conflict.
    while True:
        try:
            bot.infinity_polling(
                timeout=25,
                long_polling_timeout=20,
                allowed_updates=["message","callback_query"],
                skip_pending=True
            )
        except KeyboardInterrupt:
            print("Bot stopped.")
            break
        except Exception as exc:
            print("Polling error:", repr(exc))
            time.sleep(7)

if __name__ == "__main__":
    main()
