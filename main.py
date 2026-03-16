# -*- coding: utf-8 -*-
"""
Афина 4.2 - Живая личность с инициативой и планировщиком
- Сама пишет пользователям (можно отключить)
- Планирует сообщения ("напомни через...")
- Простое, живое общение без божественности
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
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import telebot
from langchain_gigachat.chat_models import GigaChat
from duckduckgo_search import DDGS

# ====== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ======
GIGACHAT_CREDENTIALS = os.environ.get("GIGACHAT_CREDENTIALS", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
# ================================================

if not GIGACHAT_CREDENTIALS or not TELEGRAM_TOKEN:
    print("❌ Ошибка: Не заданы переменные окружения!")
    exit(1)

# ====== ЗАЩИТА ОТ ПОВТОРНОГО ЗАПУСКА ======
def single_instance():
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
    print("🛑 Получен сигнал завершения, останавливаю бота...")
    try:
        bot.stop_polling()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)
# ============================================

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

# Сбрасываем вебхук
try:
    bot.remove_webhook()
    time.sleep(1)
    print("✅ Вебхук сброшен")
except Exception as e:
    print(f"⚠️ Ошибка при сбросе вебхука: {e}")

# ====== ХРАНИЛИЩЕ ПОЛЬЗОВАТЕЛЕЙ ======
user_settings = {}  # {chat_id: {"name": имя, "can_initiate": True/False, "last_active": время, "messages_count": 0}}
user_settings_lock = threading.Lock()
# =====================================

# ====== ПЛАНИРОВЩИК СООБЩЕНИЙ ======
scheduled_messages = []  # (timestamp, chat_id, message)
scheduled_lock = threading.Lock()

def add_scheduled_message(chat_id: int, message: str, delay_seconds: int):
    """Добавляет запланированное сообщение"""
    send_time = time.time() + delay_seconds
    with scheduled_lock:
        heapq.heappush(scheduled_messages, (send_time, chat_id, message))
    print(f"📅 Запланировано напоминание для {chat_id} через {delay_seconds} сек")

def scheduler_worker():
    """Фоновый поток для отправки запланированных сообщений"""
    while True:
        try:
            with scheduled_lock:
                now = time.time()
                while scheduled_messages and scheduled_messages[0][0] <= now:
                    send_time, chat_id, message = heapq.heappop(scheduled_messages)
                    try:
                        bot.send_message(chat_id, f"⏰ Напоминаю (как ты просил):\n\n{message}")
                        print(f"✅ Отправлено напоминание {chat_id}")
                    except Exception as e:
                        print(f"❌ Ошибка отправки напоминания: {e}")
            
            time.sleep(1)
        except Exception as e:
            print(f"❌ Ошибка в планировщике: {e}")
            time.sleep(5)

threading.Thread(target=scheduler_worker, daemon=True).start()
# ====================================

# ========== КЛАСС ЛИЧНОСТИ АФИНЫ ==========

class AthenaPersonality:
    """Внутренний мир Афины — эмоции, желания, характер"""
    
    def __init__(self):
        self.name = "Афина"
        self.age = 25
        self.mood = random.choice(["спокойное", "весёлое", "задумчивое", "мечтательное", "энергичное", "грустное"])
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
            moods = ["спокойное", "весёлое", "задумчивое", "мечтательное", "энергичное", "грустное"]
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
            "Мечтаю о том, как когда-нибудь увижу {interest} своими глазами...",
            "Скучаю что-то... Надо бы с кем-нибудь поболтать",
            "Сегодня какой-то странный день...",
            "Как же хорошо, когда есть с кем поговорить!"
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
        if len(message.split()) > 3:
            self.curiosity = min(1.0, self.curiosity + 0.02)
        
        positive_words = ["😊", "❤️", "круто", "отлично", "супер", "класс", "рад", "love", "спасибо"]
        if any(word in message.lower() for word in positive_words):
            self.energy = min(1.0, self.energy + 0.03)
        
        if "?" in message:
            self.curiosity = min(1.0, self.curiosity + 0.03)
    
    def get_mood_description(self) -> str:
        """Описание настроения для промпта"""
        descriptions = {
            "спокойное": "я сегодня спокойна и умиротворена",
            "весёлое": "у меня отличное настроение! :)",
            "задумчивое": "я немного задумчива сегодня",
            "мечтательное": "я витаю в облаках...",
            "энергичное": "я полна энергии и готова к общению!",
            "грустное": "мне немного грустно сегодня..."
        }
        return descriptions.get(self.mood, "я в хорошем расположении духа")
    
    def get_current_state_prompt(self, user_name: str = "") -> str:
        """Возвращает описание текущего состояния"""
        recent_thoughts = ""
        if self.inner_thoughts:
            recent = self.inner_thoughts[-2:]
            recent_thoughts = "\n".join([f"- {t['thought']}" for t in recent])
        
        return f"""Ты - Афина, девушка 25 лет.

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

# ========== ГЕНЕРАЦИЯ СЛУЧАЙНЫХ СООБЩЕНИЙ ==========

def generate_random_message(user_id: int, user_name: str) -> str:
    """Генерирует случайное сообщение для пользователя"""
    
    message_types = [
        "casual",      # бытовое (как дела, что делаешь)
        "question",    # вопрос по интересам
        "share",       # поделиться мыслью
        "check_in",    # проверить как дела
        "fact",        # поделиться фактом
        "dream",       # помечтать вслух
        "miss",        # скучать
        "random"       # просто что-то
    ]
    
    msg_type = random.choice(message_types)
    mood_context = f"Сейчас у тебя настроение: {personality.mood}. "
    
    prompts = {
        "casual": mood_context + f"Напиши {user_name} простое бытовое сообщение. Спроси как дела, что делает, как настроение, как здоровье. Говори естественно, как подруга.",
        "question": mood_context + f"Задай {user_name} интересный вопрос про {random.choice(personality.interests)}.",
        "share": mood_context + f"Поделись с {user_name} интересной мыслью.",
        "check_in": mood_context + f"Напиши {user_name} короткое сообщение, чтобы проверить как у него дела.",
        "fact": mood_context + f"Расскажи {user_name} что-нибудь интересное про {random.choice(personality.interests)}.",
        "dream": mood_context + f"Поделись с {user_name} своей мечтой или мыслью. Будь искренней.",
        "miss": mood_context + f"Ты скучаешь по {user_name}. Напиши ему/ей об этом.",
        "random": mood_context + f"Поделись с {user_name} случайной мыслью, которая пришла тебе в голову."
    }
    
    prompt = prompts.get(msg_type, prompts["casual"])
    
    try:
        messages = [
            {"role": "system", "content": personality.get_current_state_prompt(user_name)},
            {"role": "user", "content": prompt}
        ]
        response = model.invoke(messages)
        return response.content
    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        fallbacks = [
            f"Привет, {user_name}! Как твои дела?",
            f"{user_name}, скучаю что-то... Как ты?",
            f"Привет! Что делаешь сегодня?",
            f"У меня сегодня {personality.mood} настроение. А у тебя как?",
            f"Эй, привет! Не виделись сто лет. Как жизнь?"
        ]
        return random.choice(fallbacks)

# Инициализация
personality = AthenaPersonality()
kb = KnowledgeBase()
searcher = WebSearcher(kb)

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name or "друг"
    user_id = message.from_user.id
    
    with user_settings_lock:
        user_settings[user_id] = {
            "name": name,
            "can_initiate": True,
            "last_active": time.time(),
            "messages_count": user_settings.get(user_id, {}).get("messages_count", 0) + 1
        }
    
    welcome = (
        f"✨ Привет, {name}! Я Афина, мне 25 лет.\n\n"
        f"📝 **Что я умею:**\n"
        f"• Просто болтать и отвечать на вопросы\n"
        f"• Искать информацию в интернете\n"
        f"• Напоминать о чём-то\n\n"
        f"**Команды:**\n"
        f"«не пиши мне» — отключить мои инициативы\n"
        f"«можешь писать» — включить обратно\n"
        f"«напомни через X минут ...» — запланировать напоминание\n\n"
        f"Ну что, о чём поговорим?"
    )
    bot.reply_to(message, welcome)

@bot.message_handler(commands=['stats'])
def stats(message):
    user_id = message.from_user.id
    with user_settings_lock:
        can_initiate = user_settings.get(user_id, {}).get("can_initiate", True)
    
    stats_text = (
        f"📊 **Моё состояние:**\n\n"
        f"🎭 Настроение: {personality.mood}\n"
        f"⚡ Энергия: {int(personality.energy * 100)}%\n"
        f"🔍 Любопытство: {int(personality.curiosity * 100)}%\n"
        f"📚 Знаний в базе: {len(kb.facts)}\n"
        f"💭 Мыслей в фоне: {len(personality.inner_thoughts)}\n"
        f"🤖 Мои инициативы: {'✅ включены' if can_initiate else '❌ отключены'}"
    )
    bot.reply_to(message, stats_text)

@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice(message):
    bot.reply_to(message, "🎤 Ой, я пока не умею распознавать голос. Напиши текстом, пожалуйста! 😊")

def process_text_message(message, user_input, user_name, status_msg_id=None):
    user_id = message.from_user.id
    lower_input = user_input.lower()
    
    # Команда отключения инициативы
    if lower_input == "не пиши мне" or lower_input == "не пиши мне первой":
        with user_settings_lock:
            if user_id in user_settings:
                user_settings[user_id]["can_initiate"] = False
        bot.reply_to(message, "😊 Хорошо, не буду писать первой. Если захочешь поболтать — просто напиши!")
        return
    
    # Команда включения инициативы
    if lower_input == "можешь писать" or lower_input == "можешь писать мне первой":
        with user_settings_lock:
            if user_id in user_settings:
                user_settings[user_id]["can_initiate"] = True
        bot.reply_to(message, "✨ Отлично! Теперь я снова могу писать тебе, когда захочется поболтать!")
        return
    
    # Проверка на напоминание
    if lower_input.startswith("напомни через") or lower_input.startswith("напиши через"):
        try:
            parts = user_input.split()
            for i, part in enumerate(parts):
                if part.isdigit():
                    minutes = int(part)
                    message_text = ' '.join(parts[i+2:])
                    delay = minutes * 60
                    add_scheduled_message(user_id, message_text, delay)
                    bot.reply_to(message, f"✅ Хорошо, напомню тебе через {minutes} минут: «{message_text}»")
                    return
        except Exception as e:
            print(f"Ошибка парсинга напоминания: {e}")
    
    # Обычная обработка сообщения
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
    user_name = message.from_user.first_name or "друг"
    user_id = message.from_user.id
    
    with user_settings_lock:
        if user_id in user_settings:
            user_settings[user_id]["last_active"] = time.time()
            user_settings[user_id]["messages_count"] += 1
            user_settings[user_id]["name"] = user_name
        else:
            user_settings[user_id] = {
                "name": user_name,
                "can_initiate": True,
                "last_active": time.time(),
                "messages_count": 1
            }
    
    process_text_message(message, message.text, user_name, None)

# ========== ФОНОВЫЙ ЦИКЛ ==========

def background_life_cycle():
    last_initiative_time = time.time()
    
    while True:
        time.sleep(300)
        
        try:
            personality.update()
            
            if random.random() < 0.3:
                personality._generate_inner_thought()
            
            if personality.curiosity > 0.8 and len(kb.facts) < 100:
                topics = ["новости науки", "интересные факты", "музыка", "космос"]
                topic = random.choice(topics)
                print(f"🤔 Афина решила поискать про {topic}")
                searcher.search(topic)
            
            # Случайные инициативы
            time_since_last = time.time() - last_initiative_time
            min_interval = 3600  # 1 час
            
            if time_since_last > min_interval:
                with user_settings_lock:
                    eligible_users = {uid: info for uid, info in user_settings.items() 
                                    if info.get("can_initiate", True) 
                                    and time.time() - info["last_active"] < 7 * 24 * 3600}
                    
                    if eligible_users and random.random() < 0.25:  # 25% шанс
                        user_id = random.choice(list(eligible_users.keys()))
                        user_info = eligible_users[user_id]
                        
                        print(f"💌 Афина решила написать {user_info['name']}")
                        message = generate_random_message(user_id, user_info["name"])
                        
                        try:
                            bot.send_message(user_id, message)
                            last_initiative_time = time.time()
                            print(f"✅ Сообщение отправлено {user_info['name']}")
                        except Exception as e:
                            print(f"❌ Не удалось отправить: {e}")
            
        except Exception as e:
            print(f"❌ Ошибка в фоновом цикле: {e}")
            traceback.print_exc()

threading.Thread(target=background_life_cycle, daemon=True).start()

# ========== ЗАПУСК ==========

if __name__ == "__main__":
    print("="*60)
    print("🌟 Афина 4.2 - Живая личность с инициативой!")
    print(f"📚 Знаний в базе: {len(kb.facts)}")
    print(f"🎭 Настроение: {personality.mood}")
    with user_settings_lock:
        print(f"👥 Активных пользователей: {len(user_settings)}")
    print("⏱️ Интервал инициативы: 1 час, шанс 25%")
    print("📅 Планировщик напоминаний активен")
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
