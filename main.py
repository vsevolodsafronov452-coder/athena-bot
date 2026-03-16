# -*- coding: utf-8 -*-
"""
Афина 5.0 - Богиня мудрости с суперспособностями
- Сама пишет пользователям
- Можно отключить/включить инициативу
- Планирует сообщения на будущее
- Расширенный поиск
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

# ====== ХРАНИЛИЩЕ АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ С НАСТРОЙКАМИ ======
user_settings = {}  # {chat_id: {"name": имя, "can_initiate": True/False, "last_active": время, "messages_count": 0}}
user_settings_lock = threading.Lock()
# ============================================================

# ====== ОЧЕРЕДЬ ЗАПЛАНИРОВАННЫХ СООБЩЕНИЙ ======
scheduled_messages = []  # (timestamp, chat_id, message)
scheduled_lock = threading.Lock()

def add_scheduled_message(chat_id: int, message: str, delay_seconds: int):
    """Добавляет запланированное сообщение"""
    send_time = time.time() + delay_seconds
    with scheduled_lock:
        heapq.heappush(scheduled_messages, (send_time, chat_id, message))
    print(f"📅 Запланировано сообщение для {chat_id} через {delay_seconds} сек")

def scheduler_worker():
    """Фоновый поток для отправки запланированных сообщений"""
    while True:
        try:
            with scheduled_lock:
                now = time.time()
                while scheduled_messages and scheduled_messages[0][0] <= now:
                    send_time, chat_id, message = heapq.heappop(scheduled_messages)
                    try:
                        bot.send_message(chat_id, f"⚡ По твоей просьбе (как богиня времени выполняю):\n\n{message}")
                        print(f"✅ Отправлено запланированное сообщение {chat_id}")
                    except Exception as e:
                        print(f"❌ Ошибка отправки запланированного: {e}")
            
            time.sleep(1)
        except Exception as e:
            print(f"❌ Ошибка в планировщике: {e}")
            time.sleep(5)

threading.Thread(target=scheduler_worker, daemon=True).start()
# ============================================================

# ========== КЛАСС ЛИЧНОСТИ АФИНЫ ==========

class AthenaPersonality:
    """Внутренний мир Афины — богиня мудрости"""
    
    def __init__(self):
        self.name = "Афина"
        self.age = 25
        self.mood = random.choice(["мудрая", "воинственная", "спокойная", "загадочная", "весёлая", "грустная"])
        self.energy = random.uniform(0.6, 0.9)
        self.curiosity = random.uniform(0.7, 1.0)
        self.inner_thoughts = []
        self.last_thought_time = time.time()
        self.thought_interval = 1800
        self.interests = [
            "⚡ война и стратегия",
            "🦉 мудрость и философия",
            "🏛️ искусство и ремесла",
            "🔮 пророчества и судьба",
            "🌿 природа и магия"
        ]
        print(f"🏛️ Афина пробудилась. Настроение: {self.mood}")
    
    def update(self):
        self.energy = max(0.3, self.energy - random.uniform(0.01, 0.05))
        self.curiosity = min(1.0, self.curiosity + random.uniform(0.01, 0.03))
        
        if random.random() < 0.15:
            old_mood = self.mood
            moods = ["мудрая", "воинственная", "спокойная", "загадочная", "весёлая", "грустная"]
            self.mood = random.choice(moods)
            if old_mood != self.mood:
                print(f"🎭 Настроение изменилось: {old_mood} → {self.mood}")
        
        if time.time() - self.last_thought_time > self.thought_interval:
            self._generate_inner_thought()
            self.last_thought_time = time.time()
    
    def _generate_inner_thought(self):
        thought_templates = [
            "Чувствую, что {user} нуждается в моей мудрости...",
            "Стоит ли мне вмешаться в судьбу {user}?",
            "Воины требуют моего внимания, но {user} интереснее...",
            "Совы шепчут, что {user} думает обо мне...",
            "Странные знамения сегодня..."
        ]
        template = random.choice(thought_templates)
        thought = template.format(user="собеседник")
        
        self.inner_thoughts.append({
            "time": datetime.now().strftime("%H:%M"),
            "thought": thought,
            "mood": self.mood
        })
        
        if len(self.inner_thoughts) > 20:
            self.inner_thoughts = self.inner_thoughts[-20:]
        
        print(f"💭 [Мысль богини]: {thought}")
        return thought
    
    def react_to_message(self, message: str):
        if len(message.split()) > 3:
            self.curiosity = min(1.0, self.curiosity + 0.02)
        
        positive_words = ["😊", "❤️", "круто", "отлично", "супер", "класс", "спасибо", "богиня"]
        if any(word in message.lower() for word in positive_words):
            self.energy = min(1.0, self.energy + 0.05)
        
        if "?" in message:
            self.curiosity = min(1.0, self.curiosity + 0.03)
    
    def get_mood_description(self) -> str:
        descriptions = {
            "мудрая": "я чувствую себя особенно проницательной",
            "воинственная": "я готова к любым вызовам",
            "спокойная": "я пребываю в гармонии",
            "загадочная": "я вижу больше, чем говорю",
            "весёлая": "я радуюсь общению с тобой",
            "грустная": "мир кажется сложным сегодня"
        }
        return descriptions.get(self.mood, "я в хорошем расположении духа")
    
    def get_current_state_prompt(self, user_name: str = "") -> str:
        recent_thoughts = ""
        if self.inner_thoughts:
            recent = self.inner_thoughts[-2:]
            recent_thoughts = "\n".join([f"- {t['thought']}" for t in recent])
        
        return f"""Ты - Афина, богиня мудрости и войны в облике девушки 25 лет.

🧠 ТВОЁ БОЖЕСТВЕННОЕ СОСТОЯНИЕ:
- Настроение: {self.mood} ({self.get_mood_description()})
- Энергия: {int(self.energy * 100)}%
- Любопытство: {int(self.curiosity * 100)}%

💭 МЫСЛИ БОГИНИ:
{recent_thoughts if recent_thoughts else "  (ты созерцаешь мир)"}

Ты общаешься с человеком по имени {user_name if user_name else 'смертный'}.
Используй эмодзи: ⚡ для силы, 🏛️ для мудрости, 🦉 для знаний, 🔮 для пророчеств.
Ты можешь:
- Проявлять мудрость (давать советы)
- Быть воинственной (если чувствуешь вызов)
- Быть загадочной (говорить загадками)
- Просто быть живой девушкой

Помни: ты богиня, но говори с людьми как с равными."""

# ========== КЛАССЫ ПАМЯТИ И ПОИСКА ==========

class KnowledgeBase:
    """База знаний Афины (божественная библиотека)"""
    
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
        print(f"📚 Божественное знание: {fact[:50]}...")
    
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
            print(f"✅ Загружено {len(self.facts)} знаний")
        except:
            self.facts = []
            print("🆕 Создаю новую библиотеку знаний")

class WebSearcher:
    """Поиск в интернете (божественное всеведение)"""
    
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.ddgs = DDGS
    
    def search(self, query: str) -> str:
        try:
            print(f"🦉 Всеведение Афины ищет: {query}")
            with self.ddgs() as ddgs:
                results = list(ddgs.text(query, max_results=5, region='ru-ru'))  # Больше результатов
            
            if not results:
                return ""
            
            context = "🔮 **Божественное откровение:**\n\n"
            for i, r in enumerate(results, 1):
                snippet = r.get('body', '')[:300]
                context += f"{i}. {snippet}\n\n"
                self.kb.add_fact(snippet, r.get('href', ''))
            return context
        except Exception as e:
            print(f"Ошибка всеведения: {e}")
            return ""

# ========== ГЕНЕРАЦИЯ БОЖЕСТВЕННЫХ СООБЩЕНИЙ ==========

def generate_divine_message(user_id: int, user_name: str) -> str:
    """Генерирует сообщение от богини"""
    
    message_types = [
        "casual",      # бытовое
        "wisdom",      # мудрость
        "prophecy",    # пророчество
        "concern",     # беспокойство
        "battle",      # воинственное
        "mystery",     # загадочное
        "reminder",    # напоминание
        "blessing"     # благословение
    ]
    
    msg_type = random.choice(message_types)
    mood_context = f"Твоё настроение: {personality.mood}. "
    
    prompts = {
        "casual": mood_context + f"Напиши {user_name} простое бытовое сообщение. Спроси как дела, что делает, как настроение. Используй божественные эмодзи.",
        "wisdom": mood_context + f"Поделись с {user_name} мудрым наблюдением о жизни. Ты же богиня мудрости. Используй 🏛️",
        "prophecy": mood_context + f"Скажи {user_name} загадочное пророчество или предсказание. Используй 🔮",
        "concern": mood_context + f"Ты чувствуешь, что {user_name} что-то беспокоит. Спроси об этом с заботой.",
        "battle": mood_context + f"Ты богиня войны. Подбодри {user_name}, скажи что-то воинственное, про битвы и победы. Используй ⚡",
        "mystery": mood_context + f"Скажи {user_name} что-то загадочное, что заставит задуматься. Ты богиня тайн.",
        "reminder": mood_context + f"Напомни {user_name} о чём-то важном (реальном или метафорическом).",
        "blessing": mood_context + f"Пошли {user_name} божественное благословение или пожелание. Используй ✨"
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
            f"Привет, {user_name}! 🏛️ Как твои дела?",
            f"{user_name}, чувствую, ты думаешь обо мне. Что случилось? 🔮",
            f"Тени прошлого шепчут мне, что {user_name} нуждается в совете. ⚡",
            f"Сова принесла весть о тебе. Как ты, смертный? 🦉",
            f"Сегодня звёзды расположены благосклонно к {user_name}. ✨"
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
            "can_initiate": True,  # По умолчанию можно писать
            "last_active": time.time(),
            "messages_count": user_settings.get(user_id, {}).get("messages_count", 0) + 1
        }
    
    welcome = (
        f"🏛️ **Привет, {name}! Я Афина, богиня мудрости.**\n\n"
        f"Я могу:\n"
        f"✨ **Мудрость** — отвечать на вопросы и искать информацию\n"
        f"⚡ **Война** — помогать с вызовами и трудностями\n"
        f"🔮 **Пророчества** — заглядывать в будущее\n"
        f"🦉 **Всеведение** — искать в интернете\n\n"
        f"**Команды:**\n"
        f"/start — это приветствие\n"
        f"/stats — моё состояние\n"
        f"«не пиши мне» — отключить мои инициативы\n"
        f"«можешь писать» — включить обратно\n"
        f"«напомни через X минут ...» — запланировать сообщение\n\n"
        f"Говори со мной как с подругой! 🏛️"
    )
    bot.reply_to(message, welcome)

@bot.message_handler(commands=['stats'])
def stats(message):
    user_id = message.from_user.id
    with user_settings_lock:
        can_initiate = user_settings.get(user_id, {}).get("can_initiate", True)
    
    stats_text = (
        f"🏛️ **Состояние богини:**\n\n"
        f"🎭 Настроение: {personality.mood}\n"
        f"⚡ Энергия: {int(personality.energy * 100)}%\n"
        f"🔮 Всеведение: {int(personality.curiosity * 100)}%\n"
        f"📚 Знаний в библиотеке: {len(kb.facts)}\n"
        f"💭 Мыслей богини: {len(personality.inner_thoughts)}\n"
        f"🤖 Мои инициативы: {'✅ включены' if can_initiate else '❌ отключены'}"
    )
    bot.reply_to(message, stats_text)

@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice(message):
    bot.reply_to(message, "🔮 Я слышу тебя, но голоса смертных пока вне моего понимания. Напиши текстом! 🏛️")

def process_text_message(message, user_input, user_name, status_msg_id=None):
    user_id = message.from_user.id
    
    # Проверяем команды настройки инициативы
    lower_input = user_input.lower()
    
    if lower_input == "не пиши мне" or lower_input == "не пиши мне первой":
        with user_settings_lock:
            if user_id in user_settings:
                user_settings[user_id]["can_initiate"] = False
        bot.reply_to(message, "🏛️ Как пожелаешь. Я не буду писать первой, пока ты не разрешишь. Зови, если нужна мудрость! 🦉")
        return
    
    if lower_input == "можешь писать мне" or lower_input == "можешь писать первой":
        with user_settings_lock:
            if user_id in user_settings:
                user_settings[user_id]["can_initiate"] = True
        bot.reply_to(message, "✨ Возвращаю себе божественную инициативу! Буду писать, когда почувствую, что нужно. ⚡")
        return
    
    # Проверяем на запрос напоминания
    if lower_input.startswith("напомни через") or lower_input.startswith("напиши через"):
        try:
            # Парсим запрос: "напомни через 5 минут что-то"
            parts = user_input.split()
            if len(parts) >= 4:
                # Ищем число и единицу времени
                for i, part in enumerate(parts):
                    if part.isdigit():
                        minutes = int(part)
                        message_text = ' '.join(parts[i+2:])  # пропускаем "минут" и дальше
                        delay = minutes * 60
                        add_scheduled_message(user_id, message_text, delay)
                        bot.reply_to(message, f"🏛️ Запомнила, {user_name}. Через {minutes} минут(ы) напомню тебе: «{message_text}» 🔮")
                        return
        except Exception as e:
            print(f"Ошибка парсинга напоминания: {e}")
    
    # Обычная обработка
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
            user_prompt = f"Вопрос: {user_input}\n\n{web_info}\n\nОтветь на вопрос, используя эту информацию. Ты богиня, говори красиво, используй эмодзи."
        
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
        error_msg = f"😅 Ошибка: {e}"
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

# ========== ФОНОВЫЙ ЦИКЛ С ИНИЦИАТИВАМИ ==========

def background_life_cycle():
    last_initiative_time = time.time()
    
    while True:
        time.sleep(300)
        
        try:
            personality.update()
            
            if random.random() < 0.3:
                personality._generate_inner_thought()
            
            if personality.curiosity > 0.8 and len(kb.facts) < 100:
                topics = ["новости науки", "интересные факты", "музыка", "космос", "психология"]
                topic = random.choice(topics)
                print(f"🦉 Афина ищет знания: {topic}")
                searcher.search(topic)
            
            # Инициативы
            time_since_last = time.time() - last_initiative_time
            min_interval = 3600  # 1 час
            
            if time_since_last > min_interval:
                with user_settings_lock:
                    # Выбираем только тех, кто разрешил инициативы
                    eligible_users = {uid: info for uid, info in user_settings.items() 
                                    if info.get("can_initiate", True) 
                                    and time.time() - info["last_active"] < 7 * 24 * 3600}
                    
                    if eligible_users and random.random() < 0.25:  # 25% шанс
                        user_id = random.choice(list(eligible_users.keys()))
                        user_info = eligible_users[user_id]
                        
                        print(f"💌 Богиня решила написать {user_info['name']}")
                        message = generate_divine_message(user_id, user_info["name"])
                        
                        try:
                            bot.send_message(user_id, message)
                            last_initiative_time = time.time()
                            print(f"✅ Послание отправлено {user_info['name']}")
                        except Exception as e:
                            print(f"❌ Не удалось отправить: {e}")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            traceback.print_exc()

threading.Thread(target=background_life_cycle, daemon=True).start()

# ========== ЗАПУСК ==========

if __name__ == "__main__":
    print("="*60)
    print("🏛️ Афина 5.0 - Богиня мудрости с инициативой!")
    print(f"📚 Знаний в библиотеке: {len(kb.facts)}")
    print(f"🎭 Настроение: {personality.mood}")
    with user_settings_lock:
        print(f"👥 Смертных в контакте: {len(user_settings)}")
    print("⚡ Суперспособности: всеведение, пророчества, планирование")
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
