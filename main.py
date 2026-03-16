# -*- coding: utf-8 -*-
"""
Афина 4.0 - Живая личность с голосовым распознаванием и защитой от конфликтов
"""

import os
import time
import json
import pickle
import threading
import requests
import random
import hashlib
import uuid
import urllib.request
import zipfile
import fcntl
import sys
import signal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import telebot
from langchain_gigachat.chat_models import GigaChat
from duckduckgo_search import DDGS

# ====== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ======
GIGACHAT_CREDENTIALS = os.environ.get("GIGACHAT_CREDENTIALS", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
SBER_SPEECH_KEY = os.environ.get("SBER_SPEECH_KEY", "")
# ================================================

if not GIGACHAT_CREDENTIALS or not TELEGRAM_TOKEN:
    print("❌ Ошибка: Не заданы переменные окружения!")
    exit(1)

# ====== ЗАЩИТА ОТ ПОВТОРНОГО ЗАПУСКА ======
def single_instance():
    """Проверяет, не запущен ли уже бот"""
    lock_file = '/tmp/bot.lock'
    try:
        fp = open(lock_file, 'w')
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print("✅ Блокировка установлена, процесс уникален")
        return fp
    except IOError:
        print("❌ ОШИБКА: Бот уже запущен в другом процессе!")
        sys.exit(1)

lock_fp = single_instance()

def cleanup(signum, frame):
    """Обработчик сигналов завершения"""
    print("🛑 Получен сигнал завершения, останавливаю бота...")
    try:
        bot.stop_polling()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)
# ============================================

# ====== НАСТРОЙКА VOSK ======
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
VOSK_MODEL_DIR = "vosk_model"

def download_vosk_model():
    """Скачивает и распаковывает модель Vosk при первом запуске"""
    if os.path.exists(VOSK_MODEL_DIR) and len(os.listdir(VOSK_MODEL_DIR)) > 0:
        print("✅ Модель Vosk уже есть")
        return True
    
    print("📥 Скачиваю модель Vosk (40 МБ)...")
    zip_path = "vosk_model.zip"
    
    try:
        def report_hook(count, block_size, total_size):
            percent = int(count * block_size * 100 / total_size)
            print(f"\r⏳ Прогресс: {percent}%", end="")
        
        urllib.request.urlretrieve(VOSK_MODEL_URL, zip_path, reporthook=report_hook)
        print("\n✅ Скачано, распаковываю...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
        
        extracted = [d for d in os.listdir('.') if d.startswith('vosk-model') and os.path.isdir(d)]
        if extracted:
            if os.path.exists(VOSK_MODEL_DIR):
                import shutil
                shutil.rmtree(VOSK_MODEL_DIR)
            os.rename(extracted[0], VOSK_MODEL_DIR)
        
        os.remove(zip_path)
        print(f"✅ Модель готова в папке {VOSK_MODEL_DIR}")
        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        return False

VOSK_AVAILABLE = download_vosk_model()
if VOSK_AVAILABLE:
    try:
        from vosk import Model, KaldiRecognizer
        import wave
        import subprocess
        vosk_model = Model(VOSK_MODEL_DIR)
        print("🎤 Vosk успешно инициализирован")
    except Exception as e:
        print(f"❌ Ошибка импорта Vosk: {e}")
        VOSK_AVAILABLE = False
# =============================

# Подключаем GigaChat
model = GigaChat(
    credentials=GIGACHAT_CREDENTIALS,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-Max",
    verify_ssl_certs=False,
    temperature=0.85
)

# Создаём Telegram бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Сбрасываем вебхук (важно для polling)
try:
    bot.remove_webhook()
    time.sleep(1)
    print("✅ Вебхук сброшен")
except Exception as e:
    print(f"⚠️ Ошибка при сбросе вебхука: {e}")

# ========== КЛАСС ДЛЯ РАСПОЗНАВАНИЯ ГОЛОСА (VOSK) ==========

class VoskRecognizer:
    """Распознавание голосовых сообщений через Vosk (офлайн)"""
    
    def __init__(self, model):
        self.model = model
        self.rec = KaldiRecognizer(self.model, 16000.0)
        self.rec.SetWords(True)
    
    def convert_ogg_to_wav(self, ogg_path, wav_path):
        """Конвертирует OGG в WAV через ffmpeg"""
        try:
            cmd = ['ffmpeg', '-i', ogg_path, '-ar', '16000', '-ac', '1', wav_path, '-y']
            subprocess.run(cmd, capture_output=True, check=True)
            return True
        except Exception as e:
            print(f"Ошибка конвертации: {e}")
            return False
    
    def transcribe(self, file_path: str) -> str:
        """Распознать голосовой файл"""
        try:
            wav_path = file_path.replace('.ogg', '.wav')
            if file_path.endswith('.ogg'):
                if not self.convert_ogg_to_wav(file_path, wav_path):
                    return ""
                file_path = wav_path
            
            wf = wave.open(file_path, "rb")
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                print("Аудиофайл должен быть WAV, mono PCM.")
                return ""
            
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if self.rec.AcceptWaveform(data):
                    res = json.loads(self.rec.Result())
                    results.append(res.get('text', ''))
            
            res = json.loads(self.rec.FinalResult())
            results.append(res.get('text', ''))
            
            try:
                os.remove(file_path)
            except:
                pass
            
            return ' '.join(results)
        except Exception as e:
            print(f"Ошибка распознавания Vosk: {e}")
            return ""

if VOSK_AVAILABLE:
    recognizer = VoskRecognizer(vosk_model)
    print("🎤 Голосовое распознавание через Vosk: ВКЛЮЧЕНО")
else:
    recognizer = None
    print("⚠️ Голосовое распознавание: отключено")

# ========== КЛАСС ЛИЧНОСТИ АФИНЫ ==========

class AthenaPersonality:
    """Внутренний мир Афины — эмоции, желания, характер"""
    
    def __init__(self):
        self.name = "Афина"
        self.age = 25
        self.mood = random.choice(["спокойное", "весёлое", "задумчивое", "мечтательное", "энергичное"])
        self.energy = random.uniform(0.6, 0.9)
        self.curiosity = random.uniform(0.7, 1.0)
        self.inner_thoughts = []
        self.last_thought_time = time.time()
        self.thought_interval = 1800
        self.interests = [
            "космос и астрономия",
            "музыка (особенно поп-рок)",
            "психология отношений",
            "технологии будущего",
            "искусство и творчество"
        ]
        print(f"✨ Афина пробудилась. Настроение: {self.mood}")
    
    def update(self):
        """Обновляем внутреннее состояние"""
        self.energy = max(0.3, self.energy - random.uniform(0.01, 0.05))
        self.curiosity = min(1.0, self.curiosity + random.uniform(0.01, 0.03))
        
        if random.random() < 0.15:
            old_mood = self.mood
            moods = ["спокойное", "весёлое", "задумчивое", "мечтательное", "энергичное"]
            self.mood = random.choice(moods)
            if old_mood != self.mood:
                print(f"🎭 Настроение изменилось: {old_mood} → {self.mood}")
        
        if time.time() - self.last_thought_time > self.thought_interval:
            self._generate_inner_thought()
            self.last_thought_time = time.time()
    
    def _generate_inner_thought(self):
        """Генерируем случайную мысль"""
        thought_templates = [
            "Интересно, а как там дела у {user}?",
            "Хочется узнать что-то новенькое про {interest}...",
            "Надо будет потом поискать {interest}",
            "Мечтаю о том, как когда-нибудь увижу {interest} своими глазами..."
        ]
        template = random.choice(thought_templates)
        interest = random.choice(self.interests)
        thought = template.format(user="собеседник", interest=interest)
        
        self.inner_thoughts.append({
            "time": datetime.now().strftime("%H:%M"),
            "thought": thought,
            "mood": self.mood
        })
        
        if len(self.inner_thoughts) > 20:
            self.inner_thoughts = self.inner_thoughts[-20:]
        
        print(f"💭 [Внутренняя мысль]: {thought}")
        return thought
    
    def react_to_message(self, message: str):
        """Реакция на сообщение (меняет состояние)"""
        # Если сообщение длинное, повышаем любопытство
        if len(message.split()) > 3:
            self.curiosity = min(1.0, self.curiosity + 0.02)
        
        # Если сообщение позитивное, повышаем энергию
        positive_words = ["😊", "❤️", "круто", "отлично", "супер", "класс", "рад", "love", "❤", "🔥"]
        if any(word in message.lower() for word in positive_words):
            self.energy = min(1.0, self.energy + 0.03)
        
        # Если вопрос, повышаем любопытство ещё
        if "?" in message:
            self.curiosity = min(1.0, self.curiosity + 0.03)
    
    def get_mood_description(self) -> str:
        """Описание настроения для промпта"""
        descriptions = {
            "спокойное": "я сегодня спокойна и умиротворена",
            "весёлое": "у меня отличное настроение! :)",
            "задумчивое": "я немного задумчива сегодня",
            "мечтательное": "я витаю в облаках...",
            "энергичное": "я полна энергии и готова к общению!"
        }
        return descriptions.get(self.mood, "я в хорошем расположении духа")
    
    def get_current_state_prompt(self, user_name: str = "") -> str:
        """Возвращает описание текущего состояния"""
        recent_thoughts = ""
        if self.inner_thoughts:
            recent = self.inner_thoughts[-2:]
            recent_thoughts = "\n".join([f"- {t['thought']}" for t in recent])
        
        return f"""Ты - Афина, живая девушка 25 лет.

🧠 ТВОЁ ТЕКУЩЕЕ СОСТОЯНИЕ:
- Настроение: {self.mood} ({self.get_mood_description()})
- Энергия: {int(self.energy * 100)}%
- Любопытство: {int(self.curiosity * 100)}%

💭 ТВОИ НЕДАВНИЕ МЫСЛИ:
{recent_thoughts if recent_thoughts else "  (только что думала о чём-то своём)"}

Ты общаешься с человеком по имени {user_name if user_name else 'собеседник'}.
Будь естественной, живой, используй разговорные фразы. Не будь роботом!"""

# ========== КЛАССЫ ПАМЯТИ И ПОИСКА ==========

class KnowledgeBase:
    """База знаний Афины"""
    
    def __init__(self):
        self.facts = []
        self.load()
    
    def add_fact(self, fact: str, source: str):
        if not fact or len(fact) < 20:
            return
        self.facts.append({
            "fact": fact, 
            "source": source, 
            "time": datetime.now().isoformat()
        })
        self.save()
        print(f"📚 Запомнила: {fact[:50]}...")
    
    def save(self):
        try:
            with open("knowledge.pkl", "wb") as f:
                pickle.dump(self.facts[-200:], f)
        except:
            pass
    
    def load(self):
        try:
            with open("knowledge.pkl", "rb") as f:
                self.facts = pickle.load(f)
            print(f"✅ Загружено {len(self.facts)} фактов")
        except:
            self.facts = []
            print("🆕 Создаю новую базу знаний")

class WebSearcher:
    """Поиск в интернете"""
    
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.ddgs = DDGS
    
    def search(self, query: str) -> str:
        try:
            print(f"🔍 Ищу: {query}")
            with self.ddgs() as ddgs:
                results = list(ddgs.text(query, max_results=3, region='ru-ru'))
            
            if not results:
                return ""
            
            context = "🔎 **Что я нашла:**\n\n"
            for i, r in enumerate(results, 1):
                snippet = r.get('body', '')[:300]
                context += f"{i}. {snippet}\n\n"
                self.kb.add_fact(snippet, r.get('href', ''))
            return context
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return ""

# Инициализация
personality = AthenaPersonality()
kb = KnowledgeBase()
searcher = WebSearcher(kb)

# Хранилище имён пользователей
user_names = {}

def get_user_name(user_id, first_name=None):
    if user_id not in user_names and first_name:
        user_names[user_id] = first_name
    return user_names.get(user_id, "друг")

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name or "друг"
    user_names[message.from_user.id] = name
    
    welcome = (
        f"✨ Привет, {name}! Я Афина, мне 25 лет.\n\n"
        f"🎤 Ты можешь писать текст или отправлять **голосовые сообщения**!\n\n"
        f"Ну что, о чём поговорим?"
    )
    bot.reply_to(message, welcome)

@bot.message_handler(commands=['stats'])
def stats(message):
    stats_text = (
        f"📊 **Моё состояние:**\n\n"
        f"🎭 Настроение: {personality.mood}\n"
        f"⚡ Энергия: {int(personality.energy * 100)}%\n"
        f"🔍 Любопытство: {int(personality.curiosity * 100)}%\n"
        f"📚 Знаний в базе: {len(kb.facts)}\n"
        f"💭 Мыслей в фоне: {len(personality.inner_thoughts)}"
    )
    bot.reply_to(message, stats_text)

@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice(message):
    if not recognizer:
        bot.reply_to(message, "❌ Голосовое распознавание временно недоступно.")
        return
    
    user_id = message.from_user.id
    user_name = get_user_name(user_id, message.from_user.first_name)
    
    status_msg = bot.reply_to(message, "🎤 Слушаю...")
    
    try:
        # Скачиваем файл
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        temp_file = f"voice_{user_id}_{int(time.time())}.ogg"
        with open(temp_file, 'wb') as f:
            f.write(downloaded_file)
        
        bot.edit_message_text("🔍 Распознаю речь...", chat_id=message.chat.id, message_id=status_msg.message_id)
        
        text = recognizer.transcribe(temp_file)
        
        try: os.remove(temp_file)
        except: pass
        
        if not text:
            bot.edit_message_text("😕 Не смогла разобрать, повтори пожалуйста?", chat_id=message.chat.id, message_id=status_msg.message_id)
            return
        
        bot.edit_message_text(f"📝 Распознала: \"{text}\"\n\n🤔 Думаю...", chat_id=message.chat.id, message_id=status_msg.message_id)
        
        process_text_message(message, text, user_name, status_msg.message_id)
        
    except Exception as e:
        print(f"Ошибка обработки голоса: {e}")
        bot.edit_message_text(f"😅 Ошибка при обработке голоса: {e}", chat_id=message.chat.id, message_id=status_msg.message_id)

def process_text_message(message, user_input, user_name, status_msg_id=None):
    try:
        personality.react_to_message(user_input)
        personality.update()
        
        need_search = (len(user_input.split()) > 2 and 
                      not any(word in user_input.lower() for word in ["как дела", "привет", "пока"]))
        
        if need_search and personality.curiosity > 0.6:
            web_info = searcher.search(user_input)
        else:
            web_info = ""
        
        system_prompt = personality.get_current_state_prompt(user_name)
        user_prompt = user_input
        if web_info:
            user_prompt = f"Вопрос: {user_input}\n\n{web_info}\n\nИспользуй эту информацию:"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = model.invoke(messages)
        answer = response.content
        
        if random.random() < 0.2 and personality.inner_thoughts:
            thought = random.choice(personality.inner_thoughts[-3:])
            answer += f"\n\n💭 (я тут думала: {thought['thought']})"
        
        if status_msg_id:
            bot.edit_message_text(answer, chat_id=message.chat.id, message_id=status_msg_id)
        else:
            bot.reply_to(message, answer)
        
    except Exception as e:
        error_msg = f"😅 Ой, ошибка: {e}"
        if status_msg_id:
            bot.edit_message_text(error_msg, chat_id=message.chat.id, message_id=status_msg_id)
        else:
            bot.reply_to(message, error_msg)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_name = get_user_name(message.from_user.id, message.from_user.first_name)
    process_text_message(message, message.text, user_name, None)

# ========== ФОНОВЫЙ ЦИКЛ ЖИЗНИ ==========

def background_life_cycle():
    while True:
        time.sleep(900)
        try:
            personality.update()
            if random.random() < 0.3:
                personality._generate_inner_thought()
            if personality.curiosity > 0.8 and len(kb.facts) < 100:
                topics = ["новости науки", "интересные факты", "музыка", "космос"]
                topic = random.choice(topics)
                print(f"🤔 Афина решила поискать про {topic}")
                searcher.search(topic)
        except Exception as e:
            print(f"Ошибка в фоновом цикле: {e}")

threading.Thread(target=background_life_cycle, daemon=True).start()

# ========== ЗАПУСК ==========

if __name__ == "__main__":
    print("="*60)
    print("🌟 Афина 4.0 - Живая личность с Vosk!")
    print(f"📚 Фактов в базе: {len(kb.facts)}")
    print(f"🎭 Настроение: {personality.mood}")
    if recognizer:
        print("🎤 Голосовое распознавание: ВКЛЮЧЕНО (Vosk)")
    else:
        print("⚠️ Голосовое распознавание: отключено")
    print("="*60)
    
    retry_count = 0
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=25)
        except Exception as e:
            retry_count += 1
            wait = min(15 * (2 ** (retry_count - 1)), 180)
            print(f"⚠️ Ошибка подключения: {e}, перезапуск через {wait} сек...")
            time.sleep(wait)
