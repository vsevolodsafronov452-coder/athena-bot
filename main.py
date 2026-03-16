# -*- coding: utf-8 -*-
"""
Афина — простая живая девчонка, 25 лет
Болтает, ищет в интернете, напоминает, иногда пишет сама
"""

import os
import time
import json
import pickle
import threading
import requests
import random
import hashlib
import fcntl
import sys
import signal
import traceback
import heapq
from datetime import datetime
from typing import List, Dict
import telebot
from langchain_gigachat.chat_models import GigaChat
from duckduckgo_search import DDGS

# ====== НАСТРОЙКИ ======
GIGACHAT_CREDENTIALS = os.environ.get("GIGACHAT_CREDENTIALS", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
if not GIGACHAT_CREDENTIALS or not TELEGRAM_TOKEN:
    print("❌ Ошибка: Не заданы переменные окружения!")
    exit(1)

# ====== ЗАЩИТА ОТ ПОВТОРНОГО ЗАПУСКА ======
def single_instance():
    lock_file = '/tmp/bot.lock'
    try:
        fp = open(lock_file, 'w')
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print("✅ Блокировка установлена")
        return fp
    except IOError:
        print("❌ Бот уже запущен!")
        sys.exit(1)

lock_fp = single_instance()

def cleanup(signum, frame):
    print("🛑 Останавливаю бота...")
    try:
        bot.stop_polling()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)
# =========================

# Подключаем GigaChat
model = GigaChat(
    credentials=GIGACHAT_CREDENTIALS,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-Max",
    verify_ssl_certs=False,
    temperature=0.85
)

# Создаём бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Сбрасываем вебхук
try:
    bot.remove_webhook()
    time.sleep(1)
    print("✅ Вебхук сброшен")
except Exception as e:
    print(f"⚠️ Ошибка: {e}")

# ====== ПОЛЬЗОВАТЕЛИ ======
user_settings = {}  # {chat_id: {"name": имя, "can_initiate": True/False, "last_active": время}}
user_settings_lock = threading.Lock()
# =========================

# ====== ПЛАНИРОВЩИК ======
scheduled_messages = []  # (timestamp, chat_id, message)
scheduled_lock = threading.Lock()

def add_scheduled_message(chat_id: int, message: str, delay_seconds: int):
    send_time = time.time() + delay_seconds
    with scheduled_lock:
        heapq.heappush(scheduled_messages, (send_time, chat_id, message))
    print(f"📅 Напоминание через {delay_seconds} сек")

def scheduler_worker():
    while True:
        try:
            with scheduled_lock:
                now = time.time()
                while scheduled_messages and scheduled_messages[0][0] <= now:
                    send_time, chat_id, msg = heapq.heappop(scheduled_messages)
                    try:
                        bot.send_message(chat_id, f"⏰ Напоминаю:\n\n{msg}")
                    except:
                        pass
            time.sleep(1)
        except:
            time.sleep(5)

threading.Thread(target=scheduler_worker, daemon=True).start()
# =========================

# ========== ЛИЧНОСТЬ ==========
class AthenaPersonality:
    def __init__(self):
        self.name = "Афина"
        self.age = 25
        self.mood = random.choice(["спокойное", "весёлое", "задумчивое", "мечтательное", "энергичное", "грустное"])
        self.energy = random.uniform(0.6, 0.9)
        self.curiosity = random.uniform(0.7, 1.0)
        self.inner_thoughts = []
        self.last_thought_time = time.time()
        self.thought_interval = 1800
        self.interests = ["космос", "музыка", "психология", "технологии", "искусство"]
        print(f"✨ Привет, я Афина. Настроение: {self.mood}")
    
    def update(self):
        self.energy = max(0.3, self.energy - random.uniform(0.01, 0.05))
        self.curiosity = min(1.0, self.curiosity + random.uniform(0.01, 0.03))
        if random.random() < 0.15:
            old = self.mood
            moods = ["спокойное", "весёлое", "задумчивое", "мечтательное", "энергичное", "грустное"]
            self.mood = random.choice(moods)
            if old != self.mood:
                print(f"🎭 Настроение: {old} → {self.mood}")
        if time.time() - self.last_thought_time > self.thought_interval:
            self._generate_thought()
            self.last_thought_time = time.time()
    
    def _generate_thought(self):
        t = random.choice([
            "Интересно, как там {user}?",
            "Надо бы почитать про {interest}...",
            "Скучно что-то...",
            "Хочется поболтать с {user}",
            "Какой сегодня день странный..."
        ])
        thought = t.format(user="собеседник", interest=random.choice(self.interests))
        self.inner_thoughts.append({"time": datetime.now().strftime("%H:%M"), "thought": thought})
        if len(self.inner_thoughts) > 20:
            self.inner_thoughts = self.inner_thoughts[-20:]
        print(f"💭 Мысль: {thought}")
    
    def react_to_message(self, msg: str):
        if len(msg.split()) > 3:
            self.curiosity = min(1.0, self.curiosity + 0.02)
        if any(w in msg.lower() for w in ["😊", "❤️", "круто", "спасибо"]):
            self.energy = min(1.0, self.energy + 0.03)
        if "?" in msg:
            self.curiosity = min(1.0, self.curiosity + 0.03)
    
    def get_prompt(self, user_name=""):
        thoughts = ""
        if self.inner_thoughts:
            thoughts = "\n".join([f"- {t['thought']}" for t in self.inner_thoughts[-2:]])
        return f"""Ты - Афина, девушка 25 лет.

Сейчас твоё состояние:
- Настроение: {self.mood}
- Энергия: {int(self.energy * 100)}%
- Любопытство: {int(self.curiosity * 100)}%

Недавние мысли:
{thoughts if thoughts else "  (ничего особенного)"}

Ты разговариваешь с {user_name if user_name else 'собеседником'}.
Будь простой, живой, естественной. Говори как обычная девушка."""
# ===============================

# ========== ПАМЯТЬ И ПОИСК ==========
class KnowledgeBase:
    def __init__(self):
        self.facts = []
        self.load()
    def add_fact(self, fact, source):
        if not fact or len(fact) < 20: return
        self.facts.append({"fact": fact, "source": source, "time": datetime.now().isoformat()})
        self.save()
        print(f"📚 Запомнила: {fact[:50]}...")
    def save(self):
        try:
            with open("knowledge.pkl", "wb") as f:
                pickle.dump(self.facts[-200:], f)
        except: pass
    def load(self):
        try:
            with open("knowledge.pkl", "rb") as f:
                self.facts = pickle.load(f)
            print(f"✅ Загружено {len(self.facts)} фактов")
        except:
            self.facts = []
            print("🆕 Новая база знаний")

class WebSearcher:
    def __init__(self, kb):
        self.kb = kb
        self.ddgs = DDGS
    def search(self, query):
        try:
            print(f"🔍 Ищу: {query}")
            with self.ddgs() as ddgs:
                results = list(ddgs.text(query, max_results=3, region='ru-ru'))
            if not results:
                return ""
            context = "🔎 Нашла:\n\n"
            for i, r in enumerate(results, 1):
                snippet = r.get('body', '')[:300]
                context += f"{i}. {snippet}\n\n"
                self.kb.add_fact(snippet, r.get('href', ''))
            return context
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return ""
# ====================================

# ========== ГЕНЕРАЦИЯ СООБЩЕНИЙ ==========
def generate_message_for(user_id, user_name):
    types = ["casual", "question", "share", "check_in", "miss"]
    t = random.choice(types)
    
    prompts = {
        "casual": f"Напиши {user_name} простое сообщение. Спроси как дела, что делает.",
        "question": f"Задай {user_name} интересный вопрос.",
        "share": f"Поделись с {user_name} чем-то, что тебя волнует.",
        "check_in": f"Напиши {user_name} коротко, проверить как у него дела.",
        "miss": f"Ты скучаешь по {user_name}. Напиши об этом."
    }
    
    try:
        messages = [
            {"role": "system", "content": personality.get_prompt(user_name)},
            {"role": "user", "content": prompts[t]}
        ]
        response = model.invoke(messages)
        return response.content
    except:
        return f"Привет, {user_name}! Как твои дела?"
# ======================================

# Инициализация
personality = AthenaPersonality()
kb = KnowledgeBase()
searcher = WebSearcher(kb)

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name or "друг"
    uid = message.from_user.id
    with user_settings_lock:
        user_settings[uid] = {
            "name": name,
            "can_initiate": True,
            "last_active": time.time()
        }
    bot.reply_to(message, 
        f"✨ Привет, {name}! Я Афина, 25 лет.\n\n"
        "📝 Просто болтай со мной\n"
        "🔍 «не пиши мне» — отключить мои сообщения\n"
        "🔍 «можешь писать» — включить обратно\n"
        "⏰ «напомни через X минут ...»\n\n"
        "Ну что, о чём поговорим?")

@bot.message_handler(commands=['stats'])
def stats(message):
    uid = message.from_user.id
    with user_settings_lock:
        can = user_settings.get(uid, {}).get("can_initiate", True)
    bot.reply_to(message,
        f"📊 Моё состояние:\n"
        f"🎭 Настроение: {personality.mood}\n"
        f"⚡ Энергия: {int(personality.energy*100)}%\n"
        f"📚 Фактов: {len(kb.facts)}\n"
        f"💭 Мыслей: {len(personality.inner_thoughts)}\n"
        f"🤖 Писать первой: {'да' if can else 'нет'}")

@bot.message_handler(content_types=['voice', 'audio'])
def voice(message):
    bot.reply_to(message, "🎤 Голос пока не понимаю, напиши текстом :)")

def handle_message_text(message, user_input, user_name, status_msg_id=None):
    uid = message.from_user.id
    lower = user_input.lower()
    
    if lower in ["не пиши мне", "не пиши мне первой"]:
        with user_settings_lock:
            if uid in user_settings:
                user_settings[uid]["can_initiate"] = False
        bot.reply_to(message, "😊 Ок, не буду писать первой")
        return
    
    if lower in ["можешь писать", "можешь писать первой"]:
        with user_settings_lock:
            if uid in user_settings:
                user_settings[uid]["can_initiate"] = True
        bot.reply_to(message, "✨ Ок, буду писать, когда захочется")
        return
    
    if lower.startswith("напомни через") or lower.startswith("напиши через"):
        try:
            parts = user_input.split()
            for i, p in enumerate(parts):
                if p.isdigit():
                    mins = int(p)
                    txt = ' '.join(parts[i+2:])
                    add_scheduled_message(uid, txt, mins*60)
                    bot.reply_to(message, f"✅ Напомню через {mins} мин: «{txt}»")
                    return
        except:
            pass
    
    try:
        personality.react_to_message(user_input)
        personality.update()
        
        need_search = len(user_input.split())>2 and not any(w in lower for w in ["как дела","привет"])
        web_info = searcher.search(user_input) if need_search and personality.curiosity>0.6 else ""
        
        prompt = user_input
        if web_info:
            prompt = f"Вопрос: {user_input}\n\n{web_info}\n\nИспользуй эту информацию:"
        
        messages = [
            {"role": "system", "content": personality.get_prompt(user_name)},
            {"role": "user", "content": prompt}
        ]
        response = model.invoke(messages)
        answer = response.content
        
        if status_msg_id:
            bot.edit_message_text(answer, chat_id=message.chat.id, message_id=status_msg_id)
        else:
            bot.reply_to(message, answer)
        
    except Exception as e:
        err = f"😅 Ошибка: {e}"
        if status_msg_id:
            bot.edit_message_text(err, chat_id=message.chat.id, message_id=status_msg_id)
        else:
            bot.reply_to(message, err)

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    name = message.from_user.first_name or "друг"
    uid = message.from_user.id
    with user_settings_lock:
        if uid in user_settings:
            user_settings[uid]["last_active"] = time.time()
            user_settings[uid]["name"] = name
        else:
            user_settings[uid] = {"name": name, "can_initiate": True, "last_active": time.time()}
    handle_message_text(message, message.text, name, None)

# ========== ФОН ==========
def background_loop():
    last_init = time.time()
    while True:
        time.sleep(300)
        try:
            personality.update()
            if random.random()<0.3:
                personality._generate_thought()
            
            # Поиск знаний
            if personality.curiosity>0.8 and len(kb.facts)<100:
                topic = random.choice(["новости", "интересные факты", "музыка", "космос"])
                searcher.search(topic)
            
            # Случайные инициативы
            if time.time()-last_init > 3600:  # 1 час
                with user_settings_lock:
                    eligible = {uid:inf for uid,inf in user_settings.items() 
                              if inf.get("can_initiate",True) 
                              and time.time()-inf["last_active"] < 7*24*3600}
                if eligible and random.random()<0.25:  # 25%
                    uid = random.choice(list(eligible.keys()))
                    name = eligible[uid]["name"]
                    msg = generate_message_for(uid, name)
                    try:
                        bot.send_message(uid, msg)
                        last_init = time.time()
                        print(f"💌 Написала {name}")
                    except:
                        pass
        except:
            traceback.print_exc()

threading.Thread(target=background_loop, daemon=True).start()

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("="*50)
    print("🌟 Афина — простая девчонка 25 лет")
    print(f"📚 Знаний: {len(kb.facts)}")
    print(f"🎭 Настроение: {personality.mood}")
    print("⏱️ Пишет сама: раз в час с шансом 25%")
    print("📅 Напоминания работают")
    print("="*50)
    
    retry = 0
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=25)
        except Exception as e:
            retry += 1
            wait = min(15 * (2**(retry-1)), 180)
            print(f"⚠️ Ошибка: {e}, перезапуск через {wait} сек")
            time.sleep(wait)
