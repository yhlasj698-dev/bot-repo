# -*- coding: utf-8 -*-
import telebot
from telebot import types
import requests, sqlite3, qrcode, io, datetime, threading, time, re, socket, secrets, string, os, asyncio, uuid
import edge_tts
import yt_dlp
from PIL import Image 
from bs4 import BeautifulSoup

# ---------- TOKEN ----------
TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

url_cache = {}

# ---------- BAZA ----------
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users(chat_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'tk')")
c.execute("CREATE TABLE IF NOT EXISTS todos(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT, done INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, text TEXT, remind_at TEXT, sent INTEGER DEFAULT 0)")
conn.commit()

def get_lang(cid):
    c.execute("SELECT lang FROM users WHERE chat_id=?", (cid,))
    r = c.fetchone()
    return r[0] if r else 'tk'

def set_lang(cid, lang):
    c.execute("INSERT OR REPLACE INTO users(chat_id, lang) VALUES(?,?)", (cid, lang))
    conn.commit()

# ---------- DILLER ----------
LANGS = {'tk':'🇹🇲 Türkmen','ru':'🇷🇺 Русский','en':'🇬🇧 English','tr':'🇹🇷 Türkçe','de':'🇩🇪 Deutsch'}

T = {
'tk': {
 'menu': "🤖 <b>Esasy Menýu</b>\n\nHaýsy bölümi saýlaýarsyňyz?",
 'cat_w': "🌤 Howa & Täzelikler", 'desc_w': "<b>🌤 Howa & Täzelikler</b>\n\nHowa maglumaty, zilzilalar we IT täzelikleri.",
 'cat_os': "🕵️ OSINT & Howpsuzlyk", 'desc_os': "<b>🕵️ OSINT & Howpsuzlyk</b>\n\nIP barlag, ulanyjy gözleg, parol we <b>suratdan adam gözlemek</b>.",
 'cat_md': "📥 Media & Guralar", 'desc_md': "<b>📥 Media & Guralar</b>\n\nWideo/Aýdym ýükle, Janly Ses, QR kod, Suratdan PDF.",
 'cat_ai': "🤖 AI & Dil", 'desc_ai': "<b>🤖 AI & Dil</b>\n\nAI çat, Surat dörediji, terjime we OCR.",
 'cat_pt': "🧰 Amaly Gurallar", 'desc_pt': "<b>🧰 Amaly Gurallar</b>\n\nBirlik öwüriji, Saýt barlagy, Kino gözleg.",
 'cat_fun': "🎮 Oýun & Gözleg", 'desc_fun': "<b>🎮 Oýun & Gözleg</b>\n\nAýdym gözle, Kitap gözle we Kiberhowpsuzlyk oýny.",
 'cat_ps': "📝 Şahsy", 'desc_ps': "<b>📝 Şahsy</b>\n\nÝazgylary saklamak we wagtlaýyn ýatlatmalar.",
 
 'btn_weather': "🌤 Howa", 'btn_quake': "🌍 Zilzila", 'btn_news': "📰 Täzelikler",
 'btn_ip': "🌐 IP/Domen", 'btn_user': "🕵️ Ulanyjy", 'btn_pass': "🔐 Parol", 'btn_scrape': "🕸 Saýtdan Maglumat",
 'btn_face': "📸 Suratdan Gözle",
 'btn_dl': "📥 Ýükle", 'btn_tts': "🗣 Ses (TTS)", 'btn_qr': "📱 QR Döret", 'btn_qrread': "📷 QR Oka", 'btn_pdf': "📄 Suratdan PDF",
 'btn_ai': "🤖 AI Çat", 'btn_img': "🎨 Surat Döret", 'btn_tr': "🌐 Terjime", 'btn_ocr': "📸 OCR",
 'btn_conv': "📏 Birlik Öwür", 'btn_site': "📶 Saýt Barla", 'btn_movie': "🎬 Kino/Serial",
 'btn_music': "🎵 Aýdym Gözle", 'btn_book': "📚 Kitap Gözle", 'btn_quiz': "🎮 Kiber Oýny",
 'btn_todo': "📝 Ýazgylar", 'btn_remind': "⏰ Ýatlatma", 'back': "⬅️ Yza", 'stop_ai': "🛑 AI-ny Bes Et",
 'btn_vid': "🎬 Wideo (HQ)", 'btn_aud': "🎵 Aýdym (MP3)",
 
 'ask_city': "🏙 Şäher adyny ýazyň:", 'ask_ip': "🌐 IP ýa-da domen ýazyň:",
 'ask_user': "👤 Ulanyjy adyny ýazyň:", 'ask_pass': "🔐 Parol uzynlygyny ýazyň (meselem: 16):",
 'ask_dl': "📥 Wideo ýa-da aýdym salgysyny (URL) iberiň (TikTok, YT, IG):",
 'ask_face': "📸 Adamyň suratyny iberiň (ýüzi doly we anyk görünýän bolmaly):",
 'ask_tts': "🗣 Seslendirmek üçin tekst iberiň:", 'ask_qr': "📱 QR üçin tekst/link iberiň:",
 'ask_qrread': "📷 Içinde QR kod bar suraty iberiň:", 'ask_pdf': "📄 PDF ýasamak üçin suratlary iberiň.\nDoly bolansoň /done_pdf ýazyň.",
 'ask_ai': "🤖 <b>AI Çat açyldy!</b>\n\nIslendik soragyňyzy ýazyp bilersiňiz.\nÇykmak üçin <code>/stop</code> ýazyň.",
 'ask_img': "🎨 <b>Surat Dörediji</b>\n\nNähili surat döretmek isleýärsiňiz? Iňlis dilinde ýazyň:",
 'ask_tr': "🌐 Terjime üçin tekst iberiň.\nFormat: <code>text</code> ýa-da <code>en ru text</code>",
 'ask_ocr': "📸 Içinde tekst bar suraty iberiň (OCR):",
 'ask_conv': "📏 Format: <code>san birlik -> birlik</code>\nMeselem: <code>10 km to miles</code>",
 'ask_site': "📶 Barlamak üçin saýtyň adresini iberiň:",
 'ask_movie': "🎬 Gözlemek üçin kino ýa-da serial adyny ýazyň:",
 'ask_scrape': "🕸 Maglumatyny çekmek isleýän saýtyňyzyň salgysyny (URL) iberiň:",
 'ask_music': "🎵 Gözlemek üçin aýdymyň ýa-da aýdymçynyň adyny ýazyň:",
 'ask_book': "📚 Gözlemek üçin kitabyň adyny ýazyň:",
 'ask_todo': "📝 Ýazgyňyzy iberiň:", 'ask_remind': "⏰ Format: <code>wagt tekst</code>\nMeselem: <code>10m Suw içmeli</code>",
 'load': "⏳ Biraz garaşyň...", 'notfound': "❌ Tapylmady!", 'err': "❌ Ýalňyşlyk: {e}",
 'ask_format': "Nähili görnüşde ýüklemek isleýärsiňiz?",
 'dl_wait': "⏳ Ýüklenýär... (Ulylygyna bagly, biraz garaşyň)", 'dl_err': "❌ Ýüklemek başartmady (TikTok ýapyk bolmagy mümkin ýa-da 50MB-dan uly)."
},
'ru': {
 'menu': "🤖 <b>Главное меню</b>\n\nВыберите раздел:", 'cat_w': "🌤 Погода и Новости", 'desc_w': "<b>🌤 Погода и Новости</b>",
 'cat_os': "🕵️ OSINT и Безопасность", 'desc_os': "<b>🕵️ OSINT и Безопасность</b>\n\nIP, юзернейм, пароль и <b>поиск по фото</b>.",
 'cat_md': "📥 Медиа и Инструменты", 'desc_md': "<b>📥 Медиа и Инструменты</b>",
 'cat_ai': "🤖 ИИ и Язык", 'desc_ai': "<b>🤖 ИИ и Язык</b>",
 'cat_pt': "🧰 Полезные инструменты", 'desc_pt': "<b>🧰 Полезные инструменты</b>",
 'cat_fun': "🎮 Игры и Поиск", 'desc_fun': "<b>🎮 Игры и Поиск</b>\n\nПоиск музыки, книг и игра.",
 'cat_ps': "📝 Личное", 'desc_ps': "<b>📝 Личное</b>",
 'btn_weather': "🌤 Погода", 'btn_quake': "🌍 Землетрясения", 'btn_news': "📰 Новости", 'btn_ip': "🌐 IP/Домен", 'btn_user': "🕵️ Юзернейм", 'btn_pass': "🔐 Пароль", 'btn_scrape': "🕸 Парсинг сайта",
 'btn_face': "📸 Поиск по фото",
 'btn_dl': "📥 Скачать", 'btn_tts': "🗣 Озвучка", 'btn_qr': "📱 QR Создать", 'btn_qrread': "📷 QR Читать", 'btn_pdf': "📄 Фото в PDF",
 'btn_ai': "🤖 ИИ Чат", 'btn_img': "🎨 Создать фото", 'btn_tr': "🌐 Перевод", 'btn_ocr': "📸 OCR",
 'btn_conv': "📏 Конвертер", 'btn_site': "📶 Проверка сайта", 'btn_movie': "🎬 Кино/Сериал",
 'btn_music': "🎵 Поиск Музыки", 'btn_book': "📚 Поиск Книг", 'btn_quiz': "🎮 Кибер Игра",
 'btn_todo': "📝 Заметки", 'btn_remind': "⏰ Напоминание", 'back': "⬅️ Назад", 'stop_ai': "🛑 Выйти из ИИ",
 'btn_vid': "🎬 Видео (HQ)", 'btn_aud': "🎵 Аудио (MP3)",
 'ask_city': "🏙 Название города:", 'ask_ip': "🌐 IP или домен:", 'ask_user': "👤 Юзернейм:", 'ask_pass': "🔐 Длина пароля:", 'ask_dl': "📥 Отправьте ссылку (URL):",
 'ask_face': "📸 Отправьте фото человека (лицо должно быть четким):",
 'ask_tts': "🗣 Текст для озвучки:", 'ask_qr': "📱 Текст/ссылка для QR:", 'ask_qrread': "📷 Отправьте фото с QR-кодом:", 'ask_pdf': "📄 Отправьте фото для PDF.\nЗатем /done_pdf.",
 'ask_ai': "🤖 <b>ИИ Чат включен!</b>\n\nЗадайте вопрос.\nДля выхода <code>/stop</code>.", 'ask_img': "🎨 <b>Генератор картинок</b>\n\nОпишите картинку на английском:",
 'ask_tr': "🌐 Текст для перевода:", 'ask_ocr': "📸 Отправьте фото с текстом:", 
 'ask_conv': "📏 Формат: <code>число единица -> единица</code>", 'ask_site': "📶 Отправьте адрес сайта:", 
 'ask_movie': "🎬 Введите название фильма:", 'ask_scrape': "🕸 Отправьте URL сайта для парсинга:",
 'ask_music': "🎵 Введите название песни или исполнителя:", 'ask_book': "📚 Введите название книги:",
 'ask_todo': "📝 Заметка:", 'ask_remind': "⏰ Формат: <code>время текст</code>",
 'load': "⏳ Загрузка...", 'notfound': "❌ Не найдено!", 'err': "❌ Ошибка: {e}",
 'ask_format': "В каком формате скачать?", 'dl_wait': "⏳ Скачивание...", 'dl_err': "❌ Не удалось скачать."
},
'en': {
 'menu': "🤖 <b>Main Menu</b>\n\nSelect a category:", 'cat_w': "🌤 Weather & News", 'desc_w': "<b>🌤 Weather & News</b>",
 'cat_os': "🕵️ OSINT & Security", 'desc_os': "<b>🕵️ OSINT & Security</b>\n\nIP, username, password and <b>photo search</b>.",
 'cat_md': "📥 Media & Tools", 'desc_md': "<b>📥 Media & Tools</b>",
 'cat_ai': "🤖 AI & Language", 'desc_ai': "<b>🤖 AI & Language</b>",
 'cat_pt': "🧰 Practical Tools", 'desc_pt': "<b>🧰 Practical Tools</b>",
 'cat_fun': "🎮 Games & Search", 'desc_fun': "<b>🎮 Games & Search</b>\n\nMusic search, Book search and Cyber Quiz.",
 'cat_ps': "📝 Personal", 'desc_ps': "<b>📝 Personal</b>",
 'btn_weather': "🌤 Weather", 'btn_quake': "🌍 Earthquakes", 'btn_news': "📰 News", 'btn_ip': "🌐 IP/Domain", 'btn_user': "🕵️ Username", 'btn_pass': "🔐 Password", 'btn_scrape': "🕸 Web Scraper",
 'btn_face': "📸 Photo Search",
 'btn_dl': "📥 Download", 'btn_tts': "🗣 TTS", 'btn_qr': "📱 Create QR", 'btn_qrread': "📷 Read QR", 'btn_pdf': "📄 Image to PDF",
 'btn_ai': "🤖 AI Chat", 'btn_img': "🎨 Gen Image", 'btn_tr': "🌐 Translate", 'btn_ocr': "📸 OCR",
 'btn_conv': "📏 Converter", 'btn_site': "📶 Site Check", 'btn_movie': "🎬 Movie/Series",
 'btn_music': "🎵 Music Search", 'btn_book': "📚 Book Search", 'btn_quiz': "🎮 Cyber Quiz",
 'btn_todo': "📝 Notes", 'btn_remind': "⏰ Reminder", 'back': "⬅️ Back", 'stop_ai': "🛑 Exit AI",
 'btn_vid': "🎬 Video (HQ)", 'btn_aud': "🎵 Audio (MP3)",
 'ask_city': "🏙 City name:", 'ask_ip': "🌐 IP or domain:", 'ask_user': "👤 Username:", 'ask_pass': "🔐 Password length:", 'ask_dl': "📥 Send URL:",
 'ask_face': "📸 Send a photo of the person (face must be clear):",
 'ask_tts': "🗣 Text for TTS:", 'ask_qr': "📱 Text/link for QR:", 'ask_qrread': "📷 Send QR photo:", 'ask_pdf': "📄 Send images for PDF.\nThen /done_pdf.",
 'ask_ai': "🤖 <b>AI Chat is ON!</b>", 'ask_img': "🎨 <b>Image Generator</b>",
 'ask_tr': "🌐 Text to translate:", 'ask_ocr': "📸 Send a photo with text:", 
 'ask_conv': "📏 Format: <code>number unit -> unit</code>", 'ask_site': "📶 Send website:", 
 'ask_movie': "🎬 Enter movie name:", 'ask_scrape': "🕸 Send website URL to scrape:",
 'ask_music': "🎵 Enter song or artist name:", 'ask_book': "📚 Enter book name:",
 'ask_todo': "📝 Note:", 'ask_remind': "⏰ Format: <code>time text</code>",
 'load': "⏳ Loading...", 'notfound': "❌ Not found!", 'err': "❌ Error: {e}",
 'ask_format': "Choose format to download:", 'dl_wait': "⏳ Downloading...", 'dl_err': "❌ Download failed."
},
'tr': {
 'menu': "🤖 <b>Ana Menü</b>", 'cat_w': "🌤 Hava & Haberler", 'desc_w': "<b>🌤 Hava & Haberler</b>",
 'cat_os': "🕵️ OSINT & Güvenlik", 'desc_os': "<b>🕵️ OSINT & Güvenlik</b>\n\nIP, kullanıcı adı, şifre ve <b>fotoğraf arama</b>.",
 'cat_md': "📥 Medya & Araçlar", 'desc_md': "<b>📥 Medya & Araçlar</b>",
 'cat_ai': "🤖 AI & Dil", 'desc_ai': "<b>🤖 AI & Dil</b>",
 'cat_pt': "🧰 Pratik Araçlar", 'desc_pt': "<b>🧰 Pratik Araçlar</b>",
 'cat_fun': "🎮 Oyun & Arama", 'desc_fun': "<b>🎮 Oyun & Arama</b>\n\nMüzik arama, Kitap arama ve Siber Oyun.",
 'cat_ps': "📝 Kişisel", 'desc_ps': "<b>📝 Kişisel</b>",
 'btn_weather': "🌤 Hava", 'btn_quake': "🌍 Depremler", 'btn_news': "📰 Haberler", 'btn_ip': "🌐 IP", 'btn_user': "🕵️ Kullanıcı", 'btn_pass': "🔐 Şifre", 'btn_scrape': "🕸 Kazıma",
 'btn_face': "📸 Fotoğraftan Ara",
 'btn_dl': "📥 İndir", 'btn_tts': "🗣 Seslendir", 'btn_qr': "📱 QR Oluştur", 'btn_qrread': "📷 QR Oku", 'btn_pdf': "📄 PDF",
 'btn_ai': "🤖 AI Sohbet", 'btn_img': "🎨 Resim Oluştur", 'btn_tr': "🌐 Çeviri", 'btn_ocr': "📸 OCR",
 'btn_conv': "📏 Çevir", 'btn_site': "📶 Site Kontrol", 'btn_movie': "🎬 Film/Dizi",
 'btn_music': "🎵 Müzik Ara", 'btn_book': "📚 Kitap Ara", 'btn_quiz': "🎮 Siber Oyun",
 'btn_todo': "📝 Notlar", 'btn_remind': "⏰ Hatırlatıcı", 'back': "⬅️ Geri", 'stop_ai': "🛑 Çık",
 'btn_vid': "🎬 Video (HQ)", 'btn_aud': "🎵 Ses (MP3)",
 'ask_city': "🏙 Şehir:", 'ask_ip': "🌐 IP/Domain:", 'ask_user': "👤 Kullanıcı:", 'ask_pass': "🔐 Uzunluk:", 'ask_dl': "📥 URL:",
 'ask_face': "📸 Kişinin fotoğrafını gönderin (yüz net olmalı):",
 'ask_tts': "🗣 Metin:", 'ask_qr': "📱 Metin/Link:", 'ask_qrread': "📷 QR Fotoğrafı:", 'ask_pdf': "📄 Resimleri gönderin.\nSonra /done_pdf.",
 'ask_ai': "🤖 <b>AI AÇIK!</b>", 'ask_img': "🎨 <b>Resim Oluşturucu</b>",
 'ask_tr': "🌐 Metin:", 'ask_ocr': "📸 Fotoğraf:", 'ask_conv': "📏 Format:", 'ask_site': "📶 Site:", 
 'ask_movie': "🎬 Film:", 'ask_scrape': "🕸 URL:", 
 'ask_music': "🎵 Şarkı veya sanatçı adı:", 'ask_book': "📚 Kitap adı:",
 'ask_todo': "📝 Not:", 'ask_remind': "⏰ Format:",
 'load': "⏳ Yükleniyor...", 'notfound': "❌ Bulunamadı!", 'err': "❌ Hata: {e}",
 'ask_format': "Hangi formatta indirilsin?", 'dl_wait': "⏳ İndiriliyor...", 'dl_err': "❌ İndirilemedi."
},
'de': {
 'menu': "🤖 <b>Hauptmenü</b>", 'cat_w': "🌤 Wetter", 'desc_w': "<b>🌤 Wetter</b>",
 'cat_os': "🕵️ OSINT", 'desc_os': "<b>🕵️ OSINT</b>\n\nIP, Benutzername, Passwort und <b>Fotosuche</b>.",
 'cat_md': "📥 Medien", 'desc_md': "<b>📥 Medien</b>",
 'cat_ai': "🤖 KI", 'desc_ai': "<b>🤖 KI</b>",
 'cat_pt': "🧰 Tools", 'desc_pt': "<b>🧰 Tools</b>",
 'cat_fun': "🎮 Spiele", 'desc_fun': "<b>🎮 Spiele</b>\n\nMusiksuche, Buchsuche und Cyber-Quiz.",
 'cat_ps': "📝 Notizen", 'desc_ps': "<b>📝 Notizen</b>",
 'btn_weather': "🌤 Wetter", 'btn_quake': "🌍 Erdbeben", 'btn_news': "📰 News", 'btn_ip': "🌐 IP", 'btn_user': "🕵️ Benutzer", 'btn_pass': "🔐 Passwort", 'btn_scrape': "🕸 Scraper",
 'btn_face': "📸 Fotosuche",
 'btn_dl': "📥 Download", 'btn_tts': "🗣 TTS", 'btn_qr': "📱 QR", 'btn_qrread': "📷 QR lesen", 'btn_pdf': "📄 PDF",
 'btn_ai': "🤖 Chat", 'btn_img': "🎨 Bild", 'btn_tr': "🌐 Übersetzen", 'btn_ocr': "📸 OCR",
 'btn_conv': "📏 Umrechner", 'btn_site': "📶 Check", 'btn_movie': "🎬 Film",
 'btn_music': "🎵 Musiksuche", 'btn_book': "📚 Buchsuche", 'btn_quiz': "🎮 Cyber Quiz",
 'btn_todo': "📝 Notizen", 'btn_remind': "⏰ Erinnerung", 'back': "⬅️ Zurück", 'stop_ai': "🛑 KI beenden",
 'btn_vid': "🎬 Video (HQ)", 'btn_aud': "🎵 Audio (MP3)",
 'ask_city': "🏙 Stadt:", 'ask_ip': "🌐 IP:", 'ask_user': "👤 Benutzer:", 'ask_pass': "🔐 Länge:", 'ask_dl': "📥 URL:",
 'ask_face': "📸 Senden Sie ein Foto (Gesicht klar):",
 'ask_tts': "🗣 Text:", 'ask_qr': "📱 Text:", 'ask_qrread': "📷 QR Foto:", 'ask_pdf': "📄 Bilder senden.\nDann /done_pdf.",
 'ask_ai': "🤖 <b>KI AN!</b>", 'ask_img': "🎨 <b>Bildgenerator</b>",
 'ask_tr': "🌐 Text:", 'ask_ocr': "📸 Foto:", 'ask_conv': "📏 Format:", 'ask_site': "📶 Website:", 
 'ask_movie': "🎬 Film:", 'ask_scrape': "🕸 URL:", 
 'ask_music': "🎵 Lied oder Künstler:", 'ask_book': "📚 Buchname:",
 'ask_todo': "📝 Notiz:", 'ask_remind': "⏰ Format:",
 'load': "⏳ Laden...", 'notfound': "❌ Nicht gefunden!", 'err': "❌ Fehler: {e}",
 'ask_format': "Format wählen:", 'dl_wait': "⏳ Wird heruntergeladen...", 'dl_err': "❌ Fehlgeschlagen."
},
}

def tr(cid, key):
    return T.get(get_lang(cid), T['tk']).get(key, "⚠️")

# ---------- KLAWIATURALAR ----------
def main_kb(cid):
    kb = types.InlineKeyboardMarkup(row_width=1)
    SITE_URL = "https://cyber-alltool.netlify.app/"
    kb.add(
        types.InlineKeyboardButton(tr(cid,'cat_w'), callback_data="cat_w"),
        types.InlineKeyboardButton(tr(cid,'cat_os'), callback_data="cat_os"),
        types.InlineKeyboardButton(tr(cid,'cat_md'), callback_data="cat_md"),
        types.InlineKeyboardButton(tr(cid,'cat_ai'), callback_data="cat_ai"),
        types.InlineKeyboardButton(tr(cid,'cat_pt'), callback_data="cat_pt"),
        types.InlineKeyboardButton(tr(cid,'cat_fun'), callback_data="cat_fun"),
        types.InlineKeyboardButton(tr(cid,'cat_ps'), callback_data="cat_ps"),
        types.InlineKeyboardButton("🌐 Hacker Tools (Web)", url=SITE_URL),
        types.InlineKeyboardButton("🌍 Dil / Language", callback_data="lang_menu")
    )
    return kb

def cat_kb(cid, cat):
    kb = types.InlineKeyboardMarkup(row_width=2)
    if cat == 'w':
        kb.add(types.InlineKeyboardButton(tr(cid,'btn_weather'), callback_data="act_weather"),
               types.InlineKeyboardButton(tr(cid,'btn_quake'), callback_data="act_quake"),
               types.InlineKeyboardButton(tr(cid,'btn_news'), callback_data="act_news"))
    elif cat == 'os':
        kb.add(types.InlineKeyboardButton(tr(cid,'btn_ip'), callback_data="act_ip"),
               types.InlineKeyboardButton(tr(cid,'btn_user'), callback_data="act_user"),
               types.InlineKeyboardButton(tr(cid,'btn_pass'), callback_data="act_pass"),
               types.InlineKeyboardButton(tr(cid,'btn_scrape'), callback_data="act_scrape"),
               types.InlineKeyboardButton(tr(cid,'btn_face'), callback_data="act_face"))
    elif cat == 'md':
        kb.add(types.InlineKeyboardButton(tr(cid,'btn_dl'), callback_data="act_dl"),
               types.InlineKeyboardButton(tr(cid,'btn_tts'), callback_data="act_tts"),
               types.InlineKeyboardButton(tr(cid,'btn_qr'), callback_data="act_qr"),
               types.InlineKeyboardButton(tr(cid,'btn_qrread'), callback_data="act_qrread"),
               types.InlineKeyboardButton(tr(cid,'btn_pdf'), callback_data="act_pdf"))
    elif cat == 'ai':
        kb.add(types.InlineKeyboardButton(tr(cid,'btn_ai'), callback_data="act_ai"),
               types.InlineKeyboardButton(tr(cid,'btn_img'), callback_data="act_img"),
               types.InlineKeyboardButton(tr(cid,'btn_tr'), callback_data="act_tr"),
               types.InlineKeyboardButton(tr(cid,'btn_ocr'), callback_data="act_ocr"))
    elif cat == 'pt':
        kb.add(types.InlineKeyboardButton(tr(cid,'btn_conv'), callback_data="act_conv"),
               types.InlineKeyboardButton(tr(cid,'btn_site'), callback_data="act_site"),
               types.InlineKeyboardButton(tr(cid,'btn_movie'), callback_data="act_movie"))
    elif cat == 'fun':
        kb.add(types.InlineKeyboardButton(tr(cid,'btn_music'), callback_data="act_music"),
               types.InlineKeyboardButton(tr(cid,'btn_book'), callback_data="act_book"),
               types.InlineKeyboardButton(tr(cid,'btn_quiz'), callback_data="act_quiz"))
    elif cat == 'ps':
        kb.add(types.InlineKeyboardButton(tr(cid,'btn_todo'), callback_data="act_todo"),
               types.InlineKeyboardButton(tr(cid,'btn_remind'), callback_data="act_remind"))
    kb.add(types.InlineKeyboardButton(tr(cid,'back'), callback_data="menu"))
    return kb

def lang_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    for code, name in LANGS.items():
        kb.add(types.InlineKeyboardButton(name, callback_data=f"lang_{code}"))
    return kb

def stop_ai_kb(cid):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(tr(cid,'stop_ai'), callback_data="menu"))
    return kb

def dl_format_kb(cid, url):
    kb = types.InlineKeyboardMarkup(row_width=2)
    short_id = uuid.uuid4().hex[:10] 
    url_cache[short_id] = url
    kb.add(types.InlineKeyboardButton(tr(cid,'btn_vid'), callback_data=f"dl_vid_{short_id}"),
           types.InlineKeyboardButton(tr(cid,'btn_aud'), callback_data=f"dl_aud_{short_id}"))
    return kb

# ---------- FEATURE FUNKSIÝALAR ----------
def f_scrape(url):
    if not url.startswith('http'): url = 'https://' + url
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.title.string if soup.title else "Ady ýok"
        paragraphs = [p.text.strip() for p in soup.find_all('p') if len(p.text.strip()) > 30]
        text = "\n\n".join(paragraphs[:3]) 
        return f"🕸 <b>Saýt:</b> {title}\n\n{text[:1500]}..." if text else "❌ Tekst tapylmady."
    except Exception as e: return f"❌ {e}"

def f_weather(city):
    try:
        g = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name":city,"count":1,"language":"en"}, timeout=10).json()
        if not g.get("results"): return None
        p = g["results"][0]
        w = requests.get("https://api.open-meteo.com/v1/forecast", params={"latitude":p["latitude"],"longitude":p["longitude"],"hourly":"temperature_2m,relative_humidity_2m,precipitation_probability","forecast_hours":12,"timezone":"auto"}, timeout=10).json()
        out = [f"📍 <b>{p['name']}, {p.get('country','')}</b>\n⏰ <i>Indiki 12 sagat</i> 🌡\n"]
        for i in range(12):
            t = w["hourly"]["time"][i].split("T")[1]
            temp, hum, rain = w["hourly"]["temperature_2m"][i], w["hourly"]["relative_humidity_2m"][i], w["hourly"]["precipitation_probability"][i]
            out.append(f"{'☀️' if rain<20 else '🌦' if rain<60 else '⛈'} <code>{t}</code> — <b>{temp}°C</b> 💧{hum}%")
        return "\n".join(out)
    except Exception as e: return f"❌ {e}"

def f_ip(q):
    try:
        try: ip = socket.gethostbyname(q)
        except: ip = q
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,isp,org,query", timeout=10).json()
        if r.get("status") != "success": return None
        return f"🌐 <b>{r.get('query')}</b>\n🏳️ <b>{r.get('country','—')}</b>\n🏙 <b>{r.get('city','—')}</b>\n📡 <b>{r.get('isp','—')}</b>"
    except Exception as e: return f"❌ {e}"

def f_username(u):
    u = re.sub(r'[^a-zA-Z0-9_.\-]', '', u)
    # Top 15 sites for username search
    sites = {
        "GitHub":f"https://github.com/{u}", "Reddit":f"https://www.reddit.com/user/{u}",
        "Telegram":f"https://t.me/{u}", "Instagram":f"https://www.instagram.com/{u}/",
        "TikTok":f"https://www.tiktok.com/@{u}", "Twitter/X":f"https://x.com/{u}",
        "Pinterest":f"https://www.pinterest.com/{u}/", "Twitch":f"https://www.twitch.tv/{u}",
        "YouTube":f"https://youtube.com/@{u}", "Steam":f"https://steamcommunity.com/id/{u}",
        "Spotify":f"https://open.spotify.com/user/{u}", "VK":f"https://vk.com/{u}",
        "Facebook":f"https://www.facebook.com/{u}", "Flickr":f"https://www.flickr.com/people/{u}",
        "Dribbble":f"https://dribbble.com/{u}"
    }
    found, notf = [], []
    for name, url in sites.items():
        try:
            r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=6, allow_redirects=True)
            if r.status_code == 200 and "not found" not in r.text.lower()[:3000] and "404" not in r.text.lower()[:500]: found.append(f"🟢 <a href='{url}'>{name}</a>")
            else: notf.append(name)
        except: notf.append(name)
    s = f"🕵️ <b>@{u}</b>\n\n"
    if found: s += "✅ <b>Bar:</b>\n" + "\n".join(found) + "\n\n"
    if notf:  s += "🔴 <b>Ýok:</b> " + ", ".join(notf)
    return s

# TÄZE: Suratdan adam gözlemek (Mugt API: 0x0.st arkaly)
def f_face_search(img_bytes):
    try:
        # 1. Suraty gizlin we mugt ýükleýän saýta iberýäris
        files = {'file': ('image.jpg', img_bytes)}
        r = requests.post('https://0x0.st', files=files, timeout=15)
        if r.status_code != 200:
            return "❌ Suraty gözleg üçin ýükläp bolmady (0x0.st ýapyk)."
        
        img_url = r.text.strip()
        
        # 2. Gözleg linklerini taýýarlaýarys
        out = [
            "✅ <b>Surat üstünlikli ýüklendi!</b>\n",
            "Aşakdaky baglanyşyklara basyp, şol adamyň beýleki profillerini we suratlaryny gözläp bilersiňiz:\n",
            f"🔍 <a href='https://lens.google.com/uploadbyurl?url={img_url}'>Google Lens (Iň güýçli)</a>",
            f"🔍 <a href='https://yandex.com/images/search?rpt=imageview&url={img_url}'>Yandex Surat Gözlegi</a>",
            f"🔍 <a href='https://www.bing.com/images/search?view=detailv2&iss=sbiupload&q=imgurl:{img_url}'>Bing Tersine Gözleg</a>",
            f"🔍 <a href='https://tineye.com/search?url={img_url}'>TinEye</a>",
            "\n<i>Bellik: Bu usul arkaly adamyň VK, TikTok, Instagram ýaly açyk profillerini tapyp bilersiňiz.</i>"
        ]
        return "\n".join(out)
    except Exception as e:
        return f"❌ Ýalňyşlyk: {e}"

def f_pass(l=16):
    return ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*") for _ in range(min(max(l, 8), 64)))

def f_qr(text):
    img = qrcode.make(text); buf = io.BytesIO(); img.save(buf, "PNG"); buf.seek(0); return buf

def f_qr_read(img_bytes):
    try:
        r = requests.post("https://api.qrserver.com/v1/read-qr-code/", files={'file': ('qr.png', img_bytes)}, timeout=10).json()
        data = r[0]['symbol'][0]['data']
        return f"📱 <b>QR Maglumaty:</b>\n\n<code>{data}</code>" if data else "❌ QR kod tapylmady."
    except: return "❌ Okap bolmady."

def f_ocr(img_bytes):
    try:
        r = requests.post("https://api.ocr.space/parse/image", files={'filename': img_bytes}, data={'apikey': 'helloworld', 'language': 'eng'}, timeout=20).json()
        if r.get('IsErroredOnProcessing'): return "❌ Tekst okap bolmady."
        res = r.get('ParsedResults', [{}])[0].get('ParsedText', '')
        return f"📸 <b>Suratdan Tekst:</b>\n\n<code>{res}</code>" if res.strip() else "❌ Suratda tekst tapylmady."
    except Exception as e: return f"❌ {e}"

def f_img2pdf(images_list):
    try:
        pil_images = [Image.open(io.BytesIO(img_bytes)).convert("RGB") for img_bytes in images_list]
        if not pil_images: return None
        pdf_buffer = io.BytesIO()
        pil_images[0].save(pdf_buffer, format="PDF", save_all=True, append_images=pil_images[1:])
        pdf_buffer.seek(0)
        return pdf_buffer
    except: return None

def f_translate(text):
    try:
        parts = text.split(maxsplit=2)
        src, tgt, q = "Autodetect", "ru", text
        if len(parts) >= 3 and len(parts[0])==2 and len(parts[1])==2: src, tgt, q = parts[0], parts[1], parts[2]
        r = requests.get("https://api.mymemory.translated.net/get", params={"q":q,"langpair":f"{src}|{tgt}"}, timeout=15).json()
        return f"🌐 <b>{src} → {tgt}</b>\n\n📝 <i>Asyl:</i>\n{text}\n\n✨ <b>Terjime:</b>\n{r.get('responseData',{}).get('translatedText','—')}"
    except Exception as e: return f"❌ {e}"

def f_convert(text):
    try:
        text = text.lower().replace("->", " ").replace("to", " ").split()
        val, u1, u2 = float(text[0]), text[1], text[2]
        res = val
        if u1 in ["km"] and u2 in ["miles", "mil"]: res = val * 0.621371
        elif u1 in ["miles", "mil"] and u2 in ["km"]: res = val / 0.621371
        elif u1 in ["kg", "kilo"] and u2 in ["lbs", "pound"]: res = val * 2.20462
        elif u1 in ["lbs", "pound"] and u2 in ["kg", "kilo"]: res = val / 2.20462
        elif u1 in ["c"] and u2 in ["f"]: res = (val * 9/5) + 32
        elif u1 in ["f"] and u2 in ["c"]: res = (val - 32) * 5/9
        else: return "❌ Bu birlikleri tanaamok."
        return f"📏 <b>Netije:</b>\n{val} {u1.upper()} = <b>{round(res, 4)} {u2.upper()}</b>"
    except: return "❌ Format nädogry."

def f_sitecheck(url):
    if not url.startswith('http'): url = 'https://' + url
    try:
        r = requests.get(url, timeout=10)
        em = "🟢" if r.status_code == 200 else "🟠"
        return f"📶 <b>Saýt Barlagy</b>\n\n{em} <b>{url}</b>\nStatus: <b>{r.status_code}</b>"
    except Exception as e: return f"🔴 <b>{url}</b> açylýanok."

def f_ai(prompt):
    try:
        r = requests.get(f"https://text.pollinations.ai/{requests.utils.quote(prompt)}", timeout=30)
        return f"🤖 <b>AI Jogaby:</b>\n\n{r.text}" if r.status_code == 200 else "❌ AI jogap berip bilmedi."
    except Exception as e: return f"❌ {e}"

def f_image_gen(prompt):
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1024&height=1024&nologo=true"
        r = requests.get(url, timeout=40)
        if r.status_code == 200: return io.BytesIO(r.content)
        return None
    except: return None

def f_movie(query):
    try:
        r = requests.get(f"https://search.imdbot.workers.dev/?q={requests.utils.quote(query)}", timeout=15).json()
        if not r.get("description"): return None
        item = r["description"][0]
        return f"🎬 <b>{item.get('#TITLE', '—')}</b> ({item.get('#YEAR', '—')})\n\n⭐ <b>Reýting:</b> {item.get('#RANK', '—')}\n🔗 <a href='https://www.imdb.com/title/{item.get('#IMDB_ID', '')}/'>IMDb sahypasy</a>", item.get("#IMG_POSTER", "")
    except: return None

def f_earthquake():
    try:
        r = requests.get("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson", timeout=10).json()
        feats = r.get("features", [])[:8]
        if not feats: return "🌍 Soňky 24 sagatda möhüm zilzila ýok ✅"
        out = ["🌍 <b>Soňky möhüm zilzilalar (24s)</b>\n"]
        for f in feats:
            p = f["properties"]; mag = p["mag"]; t = datetime.datetime.fromtimestamp(p["time"]/1000).strftime("%m-%d %H:%M")
            out.append(f"{'🔴' if mag and mag>=6 else '🟠' if mag and mag>=5 else '🟡'} <b>M{mag}</b> — {p['place']} <i>({t})</i>")
        return "\n".join(out)
    except Exception as e: return f"❌ {e}"

def f_news():
    try:
        r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10).json()
        out = ["📰 <b>Iň soňky tehnologiýa täzelikleri</b>\n"]
        for tid in r[:5]:
            item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{tid}.json", timeout=5).json()
            if item and 'title' in item: out.append(f"🔹 <a href='{item.get('url', '')}'>{item['title']}</a>")
        return "\n".join(out)
    except: return "❌ Täzelikleri alyp bolmady."

def f_todo_list(cid):
    c.execute("SELECT id,text,done FROM todos WHERE chat_id=? ORDER BY done,id", (cid,))
    rows = c.fetchall()
    if not rows: return "📝 Boş."
    out = ["📝 <b>Ýazgylaryňyz:</b>\n"] + [f"{'✅' if d else '⬜'} <code>#{rid}</code> — {txt}" for rid,txt,d in rows]
    return "\n".join(out) + "\n\n<i>/done ID · /del ID</i>"

# TIKTOK 100% DÜZEDILEN FUNKSIÝA
def f_download(url, cid, mode='audio'):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'impersonate': 'chrome', # TikTok üçin iň möhüm setir
            'outtmpl': f'./{cid}_dl_%(id)s.%(ext)s',
            'noplaylist': True,
            'extractor_args': {'tiktok': {'webpage_video_data': ['1']}} # TikTok-a goşmaça maglumat ibermek üçin
        }
        
        if mode == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        else:
            # TikTok üçin iň gowy format
            ydl_opts['format'] = 'best[ext=mp4]/best' 

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info: return {'error': "Maglumat alyp bolmady."}
            
            file_path = ydl.prepare_filename(info)
            if mode == 'audio':
                for ext in ['.webm', '.m4a', '.mp4']:
                    if file_path.endswith(ext):
                        file_path = file_path.replace(ext, '.mp3')
                        break
            
            if not os.path.exists(file_path):
                return {'error': "Faýl göçürip alynmady."}

            return {'file': file_path, 'title': info.get('title', 'Faýl'), 'mode': mode}
    except Exception as e: 
        return {'error': str(e)}

def f_music_search(query, cid):
    try:
        search_opts = {'quiet': True, 'default_search': 'ytsearch1', 'impersonate': 'chrome', 'noplaylist': True}
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if not info or 'entries' not in info or not info['entries']: return None
            video_url = info['entries'][0]['webpage_url']
            title = info['entries'][0]['title']
        res = f_download(video_url, cid, 'audio')
        if res and not res.get('error'): res['title'] = title; return res
        return {'error': 'Ýüklemek başartmady.'}
    except: return {'error': 'Gözleg ýalňyşlygy.'}

def f_book_search(query):
    try:
        r = requests.get(f"https://openlibrary.org/search.json?q={requests.utils.quote(query)}&limit=3", timeout=15).json()
        docs = r.get('docs', [])
        if not docs: return None
        out = [f"📚 <b>'{query}' boýunça netijeler:</b>\n"]
        for doc in docs:
            out.append(f"📖 <b>{doc.get('title', 'Näbelli')}</b>\n✍️ {doc.get('author_name', ['Näbelli'])[0]}\n🔗 <a href='https://openlibrary.org{doc.get('key', '')}'>Maglumat</a>\n")
        return "\n".join(out)
    except: return None

quiz_data = [
    {"q": "Haýsy parol iň howpsuz?", "opts": ["12345678", "admin", "P@ssw0rd!2024", "qwerty"], "ans": 2},
    {"q": "SQL näme üçin ulanylýar?", "opts": ["Surat döretmek", "Maglumat bazasy", "Wideo görkezmek", "Ses ýazmak"], "ans": 1},
    {"q": "XSS hüjümi nämä gönükdirilen?", "opts": ["Serwere", "Ulanyjynyň brauzerine", "Tor toryna", "Wi-Fi-yna"], "ans": 1}
]
def get_quiz_kb(q_idx):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for i, opt in enumerate(quiz_data[q_idx]['opts']): kb.add(types.InlineKeyboardButton(opt, callback_data=f"quiz_{q_idx}_{i}"))
    return kb

async def generate_tts_async(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    file_path = f"tts_{int(time.time())}.mp3"
    await communicate.save(file_path)
    return file_path

def f_tts(text, lang):
    voices = {'tk': "tr-TR-EmelNeural", 'ru': "ru-RU-SvetlanaNeural", 'en': "en-US-AriaNeural", 'tr': "tr-TR-EmelNeural", 'de': "de-DE-KatjaNeural"}
    try: return asyncio.run(generate_tts_async(text, voices.get(lang, "en-US-AriaNeural")))
    except: return None

def f_add_reminder(cid, text):
    m = re.match(r'^(\d+)([mhd])\s+(.+)$', text.strip())
    if not m: return "❌ Format nädogry."
    val, unit, task = int(m.group(1)), m.group(2), m.group(3)
    delta = datetime.timedelta(minutes=val) if unit == 'm' else datetime.timedelta(hours=val) if unit == 'h' else datetime.timedelta(days=val)
    remind_at = (datetime.datetime.now() + delta).strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO reminders(chat_id,text,remind_at) VALUES(?,?,?)", (cid, task, remind_at))
    conn.commit()
    return f"✅ Ýatlatma goýuldy!\n⏰ Wagt: {remind_at}\n📝 Tekst: {task}"

def reminder_worker():
    while True:
        try:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("SELECT id,chat_id,text FROM reminders WHERE remind_at<=? AND sent=0", (now,))
            for rid, cid, txt in c.fetchall():
                try: bot.send_message(cid, f"🔔 <b>ÝATLATMA!</b>\n\n{txt}")
                except: pass
                c.execute("UPDATE reminders SET sent=1 WHERE id=?", (rid,))
            conn.commit()
        except: pass
        time.sleep(30)
threading.Thread(target=reminder_worker, daemon=True).start()

# ---------- HANDLERS ----------
@bot.message_handler(commands=['start', 'menu'])
def cmd_start(m):
    if m.text == '/start':
        bot.send_message(m.chat.id, f"👋 <b>Salam, {m.from_user.first_name}!</b>\n\n🌍 <b>Dil saýlaň:</b>", reply_markup=lang_kb())
    else:
        bot.send_message(m.chat.id, tr(m.chat.id, 'menu'), reply_markup=main_kb(m.chat.id))

@bot.message_handler(commands=['stop'])
def cmd_stop(m):
    cid = m.chat.id
    if cid in user_state and user_state[cid] == 'ai':
        del user_state[cid]
        bot.reply_to(m, "🛑 AI Çat ýapyldy. Esasy menýu:", reply_markup=main_kb(cid))
    else: bot.reply_to(m, "Esasy menýu:", reply_markup=main_kb(cid))

@bot.message_handler(commands=['done_pdf'])
def cmd_done_pdf(m):
    cid = m.chat.id
    if cid in user_state and isinstance(user_state[cid], dict) and user_state[cid].get('type') == 'pdf':
        images = user_state[cid]['images']
        if not images: return bot.reply_to(m, "❌ Hiç hili surat ibermediňiz.")
        bot.send_chat_action(cid, 'upload_document')
        pdf_buf = f_img2pdf(images)
        if pdf_buf: bot.send_document(cid, pdf_buf, visible_file_name="photos.pdf"); del user_state[cid]
        else: bot.reply_to(m, "❌ PDF ýasap bolmady.")
    else: bot.reply_to(m, "❌ Ilki bilen PDF bölümini saýlaň.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    cid = call.message.chat.id
    data = call.data
    
    if data.startswith("quiz_"):
        parts = data.split("_")
        q_idx, ans_idx = int(parts[1]), int(parts[2])
        if ans_idx == quiz_data[q_idx]['ans']: bot.answer_callback_query(call.id, "✅ Dogry jogap!", show_alert=True)
        else: bot.answer_callback_query(call.id, "❌ Ýalňyş! Täzeden synanyşyň.", show_alert=True)
        return

    if data.startswith("dl_vid_") or data.startswith("dl_aud_"):
        mode = 'video' if data.startswith("dl_vid_") else 'audio'
        short_id = data.replace("dl_vid_", "").replace("dl_aud_", "")
        url = url_cache.get(short_id)
        
        if not url: return bot.answer_callback_query(call.id, "❌ URL-iň wagty geçdi. Täzeden iberiň.")
            
        bot.edit_message_text(tr(cid, 'dl_wait'), cid, call.message.message_id)
        bot.send_chat_action(cid, 'upload_video' if mode == 'video' else 'record_audio')
        
        res = f_download(url, cid, mode)
        if res.get('error'):
            bot.edit_message_text(f"{tr(cid, 'dl_err')}\n\n<code>{res['error'][:100]}</code>", cid, call.message.message_id)
        else:
            try:
                file_size = os.path.getsize(res['file']) / (1024 * 1024)
                if file_size > 50:
                    bot.edit_message_text(f"❌ Faýl gaty uly ({file_size:.1f} MB). Telegram boty 50MB-dan uly faýl iberip bilmeýär.", cid, call.message.message_id)
                else:
                    with open(res['file'], 'rb') as f:
                        if mode == 'video': bot.send_video(cid, f, caption=res['title'], supports_streaming=True)
                        else: bot.send_audio(cid, f, title=res['title'])
                    bot.delete_message(cid, call.message.message_id)
            except Exception as e:
                bot.edit_message_text(f"❌ Iberip bolmady: {e}", cid, call.message.message_id)
            finally:
                if res.get('file') and os.path.exists(res['file']): os.remove(res['file'])
                if short_id in url_cache: del url_cache[short_id]
        return
        
    if data.startswith("lang_"):
        set_lang(cid, data.split("_")[1])
        bot.edit_message_text(f"✅ {LANGS[data.split('_')[1]]}", cid, call.message.message_id)
        bot.send_message(cid, tr(cid, 'menu'), reply_markup=main_kb(cid))
        return
    if data == "menu":
        user_state.pop(cid, None) 
        bot.edit_message_text(tr(cid, 'menu'), cid, call.message.message_id, reply_markup=main_kb(cid))
        return
    if data.startswith("cat_"):
        cat = data.split("_")[1]
        bot.edit_message_text(tr(cid, f'desc_{cat}'), cid, call.message.message_id, reply_markup=cat_kb(cid, cat))
        return
    if data.startswith("act_"):
        act = data.replace("act_", "")
        if act == "quake": bot.send_chat_action(cid, 'typing'); bot.send_message(cid, f_earthquake())
        elif act == "news": bot.send_chat_action(cid, 'typing'); bot.send_message(cid, f_news())
        elif act == "ai":
            user_state[cid] = 'ai'
            bot.send_message(cid, tr(cid, 'ask_ai'), reply_markup=stop_ai_kb(cid))
        elif act == "pdf":
            user_state[cid] = {'type': 'pdf', 'images': []}
            bot.send_message(cid, tr(cid, 'ask_pdf'))
        elif act == "quiz":
            bot.send_message(cid, f"🎮 <b>Kiberhowpsuzlyk Soragy 1:</b>\n\n{quiz_data[0]['q']}", reply_markup=get_quiz_kb(0))
        else:
            user_state[cid] = act
            ask_map = {'weather':'ask_city','ip':'ask_ip','user':'ask_user','pass':'ask_pass','dl':'ask_dl','tts':'ask_tts','qr':'ask_qr','qrread':'ask_qrread','ocr':'ask_ocr','img':'ask_img','tr':'ask_tr','conv':'ask_conv','site':'ask_site','movie':'ask_movie','scrape':'ask_scrape','todo':'ask_todo','remind':'ask_remind', 'music':'ask_music', 'book':'ask_book', 'face':'ask_face'}
            bot.send_message(cid, tr(cid, ask_map.get(act, 'load')))

@bot.message_handler(commands=['done'])
def cmd_done(m):
    try: rid = int(m.text.split()[1]); c.execute("UPDATE todos SET done=1 WHERE id=? AND chat_id=?", (rid, m.chat.id)); conn.commit(); bot.reply_to(m, f"✅ #{rid} belgilendi")
    except: bot.reply_to(m, "❌ Format: /done 1")

@bot.message_handler(commands=['del'])
def cmd_del(m):
    try: rid = int(m.text.split()[1]); c.execute("DELETE FROM todos WHERE id=? AND chat_id=?", (rid, m.chat.id)); conn.commit(); bot.reply_to(m, f"🗑 #{rid} pozuldy")
    except: bot.reply_to(m, "❌ Format: /del 1")

user_state = {}

@bot.message_handler(content_types=['text', 'photo'])
def on_text(m):
    cid = m.chat.id
    st = user_state.get(cid)
    
    if m.content_type == 'photo':
        downloaded_file = bot.download_file(bot.get_file(m.photo[-1].file_id).file_path)
        if isinstance(st, dict) and st.get('type') == 'pdf':
            st['images'].append(downloaded_file)
            return bot.reply_to(m, f"✅ Surat goşuldy! (Jemi: {len(st['images'])})\nDowam ediň ýa-da /done_pdf ýazyň.")
        if st == 'face':
            user_state.pop(cid, None); bot.send_chat_action(cid, 'typing')
            msg = bot.reply_to(m, "⏳ Surat gözleg ulgamyna ýüklenýär...")
            res = f_face_search(downloaded_file)
            bot.edit_message_text(res, cid, msg.message_id, disable_web_page_preview=True)
            return
        if st == 'qrread': user_state.pop(cid, None); return bot.reply_to(m, f_qr_read(downloaded_file))
        if st == 'ocr': user_state.pop(cid, None); bot.send_chat_action(cid, 'typing'); return bot.reply_to(m, f_ocr(downloaded_file))

    if not m.text: return
    txt = m.text.strip()
    
    if st == 'ai': bot.send_chat_action(cid, 'typing'); return bot.reply_to(m, f_ai(txt))
    elif st == 'weather': user_state.pop(cid, None); bot.reply_to(m, f_weather(txt) or tr(cid,'notfound'))
    elif st == 'ip': user_state.pop(cid, None); bot.reply_to(m, f_ip(txt) or tr(cid,'notfound'))
    elif st == 'user': user_state.pop(cid, None); bot.reply_to(m, f_username(txt), disable_web_page_preview=True)
    elif st == 'pass': user_state.pop(cid, None); bot.reply_to(m, f"🔐 <code>{f_pass(int(txt) if txt.isdigit() else 16)}</code>")
    elif st == 'scrape': user_state.pop(cid, None); bot.send_chat_action(cid, 'typing'); bot.reply_to(m, f_scrape(txt))
    elif st == 'dl':
        user_state.pop(cid, None)
        bot.reply_to(m, tr(cid, 'ask_format'), reply_markup=dl_format_kb(cid, txt))
    elif st == 'music':
        user_state.pop(cid, None); bot.send_chat_action(cid, 'record_audio')
        msg = bot.reply_to(m, tr(cid, 'load'))
        res = f_music_search(txt, cid)
        if res and not res.get('error'):
            try:
                with open(res['file'], 'rb') as f: bot.send_audio(cid, f, title=res['title'])
                bot.delete_message(cid, msg.message_id)
            except Exception as e: bot.edit_message_text(f"❌ {e}", cid, msg.message_id)
            finally:
                if os.path.exists(res.get('file', '')): os.remove(res['file'])
        else: bot.edit_message_text(f"❌ Aýdym tapylmady.", cid, msg.message_id)
    elif st == 'book':
        user_state.pop(cid, None); bot.send_chat_action(cid, 'typing')
        res = f_book_search(txt)
        bot.reply_to(m, res if res else tr(cid,'notfound'), disable_web_page_preview=True)
    elif st == 'tts':
        user_state.pop(cid, None); bot.send_chat_action(cid,'record_voice')
        path = f_tts(txt, get_lang(cid))
        if path and os.path.exists(path):
            with open(path, 'rb') as f: bot.send_voice(cid, f)
            os.remove(path)
        else: bot.reply_to(m, "❌ Ses döredip bolmady.")
    elif st == 'qr': user_state.pop(cid, None); bot.send_photo(cid, f_qr(txt), caption=f"📱 <code>{txt[:100]}</code>")
    elif st == 'tr': user_state.pop(cid, None); bot.send_chat_action(cid,'typing'); bot.reply_to(m, f_translate(txt))
    elif st == 'conv': user_state.pop(cid, None); bot.reply_to(m, f_convert(txt))
    elif st == 'site': user_state.pop(cid, None); bot.send_chat_action(cid,'typing'); bot.reply_to(m, f_sitecheck(txt))
    elif st == 'img':
        user_state.pop(cid, None); bot.send_chat_action(cid, 'upload_photo')
        msg = bot.reply_to(m, tr(cid, 'load'))
        img_buf = f_image_gen(txt)
        if img_buf: bot.delete_message(cid, msg.message_id); bot.send_photo(cid, img_buf, caption=f"🎨 <b>Prompt:</b> {txt}")
        else: bot.edit_message_text("❌ Surat döredip bolmady.", cid, msg.message_id)
    elif st == 'movie':
        user_state.pop(cid, None); bot.send_chat_action(cid, 'typing')
        res = f_movie(txt)
        if res:
            cap, img = res
            if img:
                try: bot.send_photo(cid, img, caption=cap)
                except: bot.reply_to(m, cap)
            else: bot.reply_to(m, cap)
        else: bot.reply_to(m, tr(cid,'notfound'))
    elif st == 'todo':
        user_state.pop(cid, None); c.execute("INSERT INTO todos(chat_id,text) VALUES(?,?)", (cid, txt)); conn.commit()
        bot.reply_to(m, f"✅ Goşuldy!\n\n{f_todo_list(cid)}")
    elif st == 'remind': user_state.pop(cid, None); bot.reply_to(m, f_add_reminder(cid, txt))
    else: bot.send_chat_action(cid, 'typing'); bot.reply_to(m, f_ai(txt) + "\n\n<i>(Göni AI ýazýarsyňyz. Menýu üçin /menu ýazyň)</i>")

# ---------- BOTY DURMAGYNYŇ ÖŇÜNI ALMAK (409 FIX) ----------
if __name__ == '__main__':
    print("🤖 Bot işledi... (Doly wersiýa + Täze OSINT we TikTok düzedişleri)")
    
    try:
        bot.remove_webhook()
        time.sleep(2)
    except Exception as e:
        print(f"Webhook pozmakda ýalňyşlyk: {e}")

    while True:
        try: 
            bot.infinity_polling(timeout=10, long_polling_timeout=5, allowed_updates=['message', 'callback_query'])
        except Exception as e: 
            print(f"⚠️ Baglanyşyk ýalňyşlygy (409 Restart): {e}")
            time.sleep(5)