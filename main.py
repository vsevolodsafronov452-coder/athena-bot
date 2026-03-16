# -*- coding: utf-8 -*-
"""
Афина 5.0 - Живая личность с генерацией изображений (Nano Banana/Gemini)
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
import base64
from datetime import datetime
from typing import List, Dict, Optional
import telebot
from langchain_gigachat.chat_models import GigaChat
from duckduckgo_search import DDGS
import google.generativeai as genai

# ====== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ======
GIGACHAT_CREDENTIALS = os.environ.get("GIGACHAT_CREDENTIALS", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")  # Ключ для Gemini/Nano Banana
# ================================================

if not GIGACHAT_CREDENTIALS or not TELEGRAM_TOKEN:
    print("❌ Ошибка: Не заданы переменные окружения!")
    exit(1)

# Настраиваем Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini API настроен")
else:
    print("⚠️ Gemini API не настроен (генерация изображений отключена)")

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

# ========== ФУНКЦИЯ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ ==========
def generate_image(prompt: str) -> Optional[bytes]:
    """Генерирует изображение через Gemini API"""
    if not GEMINI_API_KEY:
        print("❌ Gemini API не настроен")
        return None
    
    try:
        print(f"🎨 Генерирую изображение по запросу: {prompt}")
        
        # Используем модель Nano Banana (Gemini 3.1 Flash Image Preview)
        # В зависимости от версии API название может отличаться
        image_model = genai.GenerativeModel("gemini-3.1-flash-image-preview")
        
        response = image_model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1"  # Можно настроить
        )
        
        if response.generated_images and len(response.generated_images) > 0:
            image_data = response.generated_images[0].image_bytes
            print(f"✅ Изображение сгенерировано, размер: {len(image_data)} байт")
            return image_data
        else:
            print("❌ Не удалось получить изображение")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка генерации изображения: {e}")
        traceback.print_exc()
        return None

# Альтернативный вариант через прямой HTTP запрос (если библиотека не поддерживает generate_images)
def generate_image_http(prompt: str) -> Optional[bytes]:
    """Генерирует изображение через прямой HTTP запрос к Gemini API"""
    if not GEMINI_API_KEY:
        return None
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:predict?key={GEMINI_API_KEY}"
        
        payload = {
            "prompt": prompt,
            "number_of_images": 1,
            "aspect_ratio": "1:1"
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if "predictions" in data and len(data["predictions"]) > 0:
                # Изображение приходит в base64
                image_base64 = data["predictions"][0]["image"]["data"]
                image_bytes = base64.b64decode(image_base64)
                print(f"✅ Изображение сгенерировано (HTTP), размер: {len(image_bytes)} байт")
                return image_bytes
        else:
            print(f"❌ Ошибка HTTP: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка HTTP генерации: {e}")
        return None
# ===================================================

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
            "искусство и творчество",
            "нейросети и AI арт"
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
            "Мечтаю о том, как когда-нибудь увижу {interest} своими глазами...",
            "Может нарисовать что-нибудь через нейросеть?"
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
        
        positive_words = ["😊", "❤️", "круто", "отлично", "супер", "класс", "рад", "love", "❤", "🔥"]
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
        self.generated_images = []  # История генераций
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
    
    def add_image_generation(self, prompt: str, success: bool):
        """Запоминает историю генерации изображений"""
        self.generated_images.append({
            "prompt": prompt,
            "success": success,
            "time": datetime.now().isoformat()
        })
        if len(self.generated_images) > 50:
            self.generated_images = self.generated_images[-50:]
        self.save()
    
    def save(self):
        try:
            data = {
                "facts": self.facts[-200:],
                "generated_images": self.generated_images
            }
            with open("knowledge.pkl", "wb") as f:
                pickle.dump(data, f)
        except:
            pass
    
    def load(self):
        try:
            with open("knowledge.pkl", "rb") as f:
                data = pickle.load(f)
                self.facts = data.get("facts", [])
                self.generated_images = data.get("generated_images", [])
            print(f"✅ Загружено {len(self.facts)} фактов, {len(self.generated_images)} генераций")
        except:
            self.facts = []
            self.generated_images = []
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
        f"📝 Просто пиши мне текстом — я отвечу с удовольствием!\n"
        f"🎨 Также я умею генерировать изображения через **/image [описание]**\n\n"
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
        f"🖼️ Сгенерировано картинок: {len(kb.generated_images)}\n"
        f"💭 Мыслей в фоне: {len(personality.inner_thoughts)}"
    )
    bot.reply_to(message, stats_text)

@bot.message_handler(commands=['image'])
def handle_image_command(message):
    """Обработка команды /image для генерации изображений"""
    if not GEMINI_API_KEY:
        bot.reply_to(message, "❌ Генерация изображений отключена (не настроен API ключ)")
        return
    
    # Получаем текст после команды
    prompt = message.text.replace('/image', '', 1).strip()
    
    if not prompt:
        bot.reply_to(message, "🎨 Напиши, что именно нарисовать. Например: `/image кот в космосе`")
        return
    
    user_name = get_user_name(message.from_user.id, message.from_user.first_name)
    status_msg = bot.reply_to(message, f"🎨 Рисую: \"{prompt}\"\n⏳ Это может занять 10-20 секунд...")
    
    try:
        # Пробуем сначала через библиотеку
        image_data = generate_image(prompt)
        
        # Если не получилось, пробуем через HTTP
        if not image_data:
            print("⚠️ Библиотека не сработала, пробую HTTP...")
            image_data = generate_image_http(prompt)
        
        if image_data:
            # Сохраняем в историю
            kb.add_image_generation(prompt, True)
            
            # Отправляем изображение
            bot.send_photo(
                message.chat.id,
                image_data,
                caption=f"🎨 По запросу: \"{prompt}\"",
                reply_to_message_id=message.message_id
            )
            
            # Удаляем статусное сообщение
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            kb.add_image_generation(prompt, False)
            bot.edit_message_text(
                "😕 Не смогла сгенерировать изображение. Попробуй другой запрос или проверь API ключ.",
                chat_id=message.chat.id,
                message_id=status_msg.message_id
            )
            
    except Exception as e:
        print(f"❌ Ошибка в обработчике /image: {e}")
        traceback.print_exc()
        bot.edit_message_text(
            f"😅 Ошибка: {e}",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )

@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice(message):
    bot.reply_to(message, "🎤 Ой, я пока не умею распознавать голос. Напиши текстом, пожалуйста! 😊")

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
                topics = ["новости науки", "интересные факты", "музыка", "космос", "AI арт"]
                topic = random.choice(topics)
                print(f"🤔 Афина решила поискать про {topic}")
                searcher.search(topic)
        except Exception as e:
            print(f"❌ Ошибка в фоновом цикле: {e}")
            traceback.print_exc()

threading.Thread(target=background_life_cycle, daemon=True).start()

# ========== ЗАПУСК ==========

if __name__ == "__main__":
    print("="*60)
    print("🌟 Афина 5.0 - Живая личность с генерацией изображений!")
    print(f"📚 Фактов в базе: {len(kb.facts)}")
    print(f"🎭 Настроение: {personality.mood}")
    if GEMINI_API_KEY:
        print("🎨 Генерация изображений: ВКЛЮЧЕНО")
    else:
        print("⚠️ Генерация изображений: отключено (нет GEMINI_API_KEY)")
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
