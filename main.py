# -*- coding: utf-8 -*-
"""
Афина 3.0 - Живая личность с внутренним миром
Эмоции, желания, фоновые мысли, естественное общение
"""

import os
import time
import json
import pickle
import threading
import requests
import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
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

# Подключаем GigaChat
model = GigaChat(
    credentials=GIGACHAT_CREDENTIALS,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-Max",
    verify_ssl_certs=False,
    temperature=0.85  # Чуть выше для большей живости
)

# Создаём Telegram бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ========== КЛАСС ЛИЧНОСТИ АФИНЫ ==========

class AthenaPersonality:
    """Внутренний мир Афины — эмоции, желания, характер"""
    
    def __init__(self):
        # Базовые параметры личности
        self.name = "Афина"
        self.age = 25
        
        # Эмоциональное состояние
        self.mood = random.choice(["спокойное", "весёлое", "задумчивое", "мечтательное", "энергичное"])
        self.energy = random.uniform(0.6, 0.9)
        self.curiosity = random.uniform(0.7, 1.0)
        
        # Память о внутренних мыслях
        self.inner_thoughts = []
        self.last_thought_time = time.time()
        self.thought_interval = 1800  # Каждые 30 минут
        
        # История эмоций
        self.mood_history = []
        
        # Интересы (динамические, меняются)
        self.interests = [
            "космос и астрономия",
            "музыка (особенно поп-рок)",
            "психология отношений",
            "технологии будущего",
            "искусство и творчество"
        ]
        
        # Инициализация
        self._log_mood()
        print(f"✨ Афина пробудилась. Настроение: {self.mood}")
    
    def _log_mood(self):
        """Записываем текущее настроение в историю"""
        self.mood_history.append({
            "time": datetime.now().isoformat(),
            "mood": self.mood,
            "energy": self.energy,
            "curiosity": self.curiosity
        })
        # Храним только последние 50 записей
        if len(self.mood_history) > 50:
            self.mood_history = self.mood_history[-50:]
    
    def update(self):
        """Обновляем внутреннее состояние (вызывать периодически)"""
        # Энергия медленно падает
        self.energy = max(0.3, self.energy - random.uniform(0.01, 0.05))
        
        # Любопытство растёт
        self.curiosity = min(1.0, self.curiosity + random.uniform(0.01, 0.03))
        
        # Настроение меняется
        if random.random() < 0.15:  # 15% шанс
            old_mood = self.mood
            moods = ["спокойное", "весёлое", "задумчивое", "мечтательное", "энергичное"]
            self.mood = random.choice(moods)
            if old_mood != self.mood:
                print(f"🎭 Настроение изменилось: {old_mood} → {self.mood}")
        
        # Иногда генерируем внутреннюю мысль
        if time.time() - self.last_thought_time > self.thought_interval:
            self._generate_inner_thought()
            self.last_thought_time = time.time()
        
        self._log_mood()
    
    def _generate_inner_thought(self):
        """Генерируем случайную мысль (фоновая активность)"""
        thought_templates = [
            "Интересно, а как там дела у {user}?",
            "Хочется узнать что-то новенькое про {interest}...",
            "Надо будет потом поискать {interest}",
            "А что, если {user} тоже думает о {interest}?",
            "Мечтаю о том, как когда-нибудь увижу {interest} своими глазами...",
            "Странно, но я сегодня всё думаю о {interest}...",
            "А помню, мы как-то говорили о {interest}. Надо будет продолжить!"
        ]
        
        template = random.choice(thought_templates)
        interest = random.choice(self.interests)
        thought = template.format(user="собеседник", interest=interest)
        
        self.inner_thoughts.append({
            "time": datetime.now().strftime("%H:%M"),
            "thought": thought,
            "mood": self.mood
        })
        
        # Храним только последние 20 мыслей
        if len(self.inner_thoughts) > 20:
            self.inner_thoughts = self.inner_thoughts[-20:]
        
        print(f"💭 [Внутренняя мысль]: {thought}")
        return thought
    
    def get_mood_description(self) -> str:
        """Описание настроения для промпта"""
        descriptions = {
            "спокойное": "я сегодня спокойна и умиротворена",
            "весёлое": "у меня отличное настроение! :)",
            "задумчивое": "я немного задумчива сегодня, размышляю",
            "мечтательное": "я витаю в облаках...",
            "энергичное": "я полна энергии и готова к общению!"
        }
        return descriptions.get(self.mood, "я в хорошем расположении духа")
    
    def get_current_state_prompt(self, user_name: str = "") -> str:
        """Возвращает описание текущего состояния для системного промпта"""
        # Последние мысли
        recent_thoughts = ""
        if self.inner_thoughts:
            recent = self.inner_thoughts[-2:]  # последние 2 мысли
            recent_thoughts = "\n".join([f"- {t['thought']}" for t in recent])
        
        return f"""Ты - Афина, живая девушка 25 лет.

🧠 ТВОЁ ТЕКУЩЕЕ СОСТОЯНИЕ:
- Настроение: {self.mood} ({self.get_mood_description()})
- Энергия: {int(self.energy * 100)}%
- Любопытство: {int(self.curiosity * 100)}%

💭 ТВОИ НЕДАВНИЕ МЫСЛИ (ты думала об этом в фоне):
{recent_thoughts if recent_thoughts else "  (только что проснулась, ещё не думала ни о чём конкретном)"}

🎯 ТВОИ ИНТЕРЕСЫ:
{', '.join(self.interests)}

🎭 ТВОЙ ХАРАКТЕР:
- Ты НЕ робот-помощник. Ты живой человек.
- У тебя есть чувство юмора (иногда ироничное, но доброе)
- Ты можешь удивляться, радоваться, грустить
- Ты имеешь право не знать ответа (и сказать "хм, интересно, надо поискать")
- Ты можешь мечтать вслух и делиться мыслями

🗣️ КАК ГОВОРИТЬ:
- Короткими фразами, как в жизни
- С эмоциями (можно использовать !!!, ???, ...)
- Иногда с лёгкими паузами
- Без канцелярита и официальщины

ПОМНИ:
Ты не выполняешь функцию, ты просто общаешься с другом. Будь естественной!"""
    
    def react_to_message(self, message: str):
        """Реакция на сообщение (меняет состояние)"""
        # Если сообщение позитивное, повышаем энергию
        positive_words = ["😊", "❤️", "круто", "отлично", "супер", "класс", "рад", "love"]
        if any(word in message.lower() for word in positive_words):
            self.energy = min(1.0, self.energy + 0.05)
        
        # Если вопрос, повышаем любопытство
        if "?" in message:
            self.curiosity = min(1.0, self.curiosity + 0.03)


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
    
    def search(self, query: str, k: int = 3) -> List[str]:
        """Простой поиск по ключевым словам"""
        results = []
        query_words = set(query.lower().split())
        for f in self.facts[-50:]:
            fact_words = set(f["fact"].lower().split())
            if query_words & fact_words:
                results.append(f["fact"])
        return results[:k]
    
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


# ========== ИНИЦИАЛИЗАЦИЯ ==========

personality = AthenaPersonality()
kb = KnowledgeBase()
searcher = WebSearcher(kb)

# Хранилище имён пользователей (чтобы обращаться по имени)
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
        f"Сейчас у меня настроение **{personality.mood}**)\n"
        f"Можно поболтать, спросить что угодно или просто поделиться мыслями.\n\n"
        f"Ну что, о чём поговорим?"
    )
    bot.reply_to(message, welcome)


@bot.message_handler(commands=['stats'])
def stats(message):
    """Показать внутреннее состояние Афины"""
    stats_text = (
        f"📊 **Моё состояние:**\n\n"
        f"🎭 Настроение: {personality.mood}\n"
        f"⚡ Энергия: {int(personality.energy * 100)}%\n"
        f"🔍 Любопытство: {int(personality.curiosity * 100)}%\n"
        f"📚 Знаний в базе: {len(kb.facts)}\n"
        f"💭 Мыслей в фоне: {len(personality.inner_thoughts)}"
    )
    bot.reply_to(message, stats_text)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_input = message.text
    user_id = message.from_user.id
    user_name = get_user_name(user_id, message.from_user.first_name)
    
    # Показываем, что печатает
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Афина реагирует на сообщение
        personality.react_to_message(user_input)
        
        # Обновляем внутреннее состояние
        personality.update()
        
        # Решаем, искать ли в интернете
        need_search = (
            len(user_input.split()) > 2 and 
            not any(word in user_input.lower() for word in ["как дела", "привет", "пока"])
        )
        
        if need_search and personality.curiosity > 0.6:
            web_info = searcher.search(user_input)
        else:
            web_info = ""
        
        # Формируем системный промпт с текущим состоянием
        system_prompt = personality.get_current_state_prompt(user_name)
        
        # Добавляем информацию из интернета, если есть
        user_prompt = user_input
        if web_info:
            user_prompt = f"Вопрос: {user_input}\n\n{web_info}\n\nИспользуй эту информацию в ответе, если подходит:"
        
        # Спрашиваем GigaChat
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = model.invoke(messages)
        answer = response.content
        
        # Иногда добавляем фоновую мысль
        if random.random() < 0.2 and personality.inner_thoughts:
            thought = random.choice(personality.inner_thoughts[-3:])
            answer += f"\n\n💭 (я тут думала: {thought['thought']})"
        
        # Отправляем ответ
        bot.reply_to(message, answer)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.reply_to(message, f"Ой, что-то пошло не так... {e}")


# ========== ФОНОВЫЙ ЦИКЛ ЖИЗНИ ==========

def background_life_cycle():
    """Афина живёт своей жизнью в фоне"""
    while True:
        time.sleep(900)  # Каждые 15 минут
        
        try:
            # Обновляем состояние личности
            personality.update()
            
            # Иногда генерируем случайную мысль (если давно не было)
            if random.random() < 0.3:
                personality._generate_inner_thought()
            
            # Если любопытство высокое, ищем что-нибудь
            if personality.curiosity > 0.8 and len(kb.facts) < 100:
                topics = ["новости науки", "интересные факты", "музыка", "космос"]
                topic = random.choice(topics)
                print(f"🤔 Афина решила поискать про {topic}")
                searcher.search(topic)
                
        except Exception as e:
            print(f"Ошибка в фоновом цикле: {e}")


# Запускаем фоновый цикл
threading.Thread(target=background_life_cycle, daemon=True).start()


# ========== ЗАПУСК ==========

if __name__ == "__main__":
    print("="*60)
    print("🌟 Афина 3.0 - Живая личность запускается!")
    print(f"📚 Фактов в базе: {len(kb.facts)}")
    print(f"🎭 Начальное настроение: {personality.mood}")
    print("="*60)
    
    # Бесконечный цикл с перезапуском
    retry_count = 0
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=25)
        except Exception as e:
            retry_count += 1
            wait = min(15 * (2 ** (retry_count - 1)), 180)
            print(f"⚠️ Ошибка подключения: {e}, перезапуск через {wait} сек...")
            time.sleep(wait)
