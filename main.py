# -*- coding: utf-8 -*-
"""
Афина 4.0 - Живая личность с голосовым распознаванием
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
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import telebot
from langchain_gigachat.chat_models import GigaChat
from duckduckgo_search import DDGS

# ====== НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ======
GIGACHAT_CREDENTIALS = os.environ.get("GIGACHAT_CREDENTIALS", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
SBER_SPEECH_KEY = os.environ.get("SBER_SPEECH_KEY", "")  # Ключ для SaluteSpeech
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
    temperature=0.85
)

# Создаём Telegram бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ========== КЛАСС ДЛЯ РАСПОЗНАВАНИЯ ГОЛОСА ==========

class SpeechRecognizer:
    """Распознавание голосовых сообщений через Sber SmartSpeech"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.auth_token = None
        self.token_expires = 0
        
    def _get_auth_token(self):
        """Получение токена авторизации для SmartSpeech"""
        if self.auth_token and time.time() < self.token_expires:
            return self.auth_token
            
        try:
            # Авторизация через OAuth 2.0 [citation:7]
            auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            headers = {
                "Authorization": f"Basic {self.api_key}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {"scope": "SALUTE_SPEECH_PERS"}
            
            response = requests.post(auth_url, headers=headers, data=data, timeout=10)
            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data["access_token"]
                self.token_expires = time.time() + token_data["expires_in"] - 60
                return self.auth_token
            else:
                print(f"Ошибка авторизации SmartSpeech: {response.text}")
                return None
        except Exception as e:
            print(f"Ошибка получения токена: {e}")
            return None
    
    def transcribe(self, file_path: str) -> str:
        """Распознать голосовой файл"""
        token = self._get_auth_token()
        if not token:
            return ""
            
        try:
            url = "https://smartspeech.sber.ru/v1/speech:recognize"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "audio/ogg"
            }
            
            with open(file_path, "rb") as f:
                audio_data = f.read()
            
            response = requests.post(
                url, 
                headers=headers, 
                data=audio_data,
                params={"language": "ru-RU"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Парсим ответ (формат зависит от версии API)
                if "result" in result:
                    return result["result"][0]["text"]
                else:
                    return result.get("text", "")
            else:
                print(f"Ошибка распознавания: {response.text}")
                return ""
        except Exception as e:
            print(f"Ошибка при распознавании: {e}")
            return ""


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
            "Мечтаю о том, как когда-нибудь увижу {interest} своими глазами...",
            "Странно, но я сегодня всё думаю о {interest}..."
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

# Инициализируем распознавание голоса (если есть ключ)
if SBER_SPEECH_KEY:
    recognizer = SpeechRecognizer(SBER_SPEECH_KEY)
    print("🎤 Распознавание голоса включено")
else:
    recognizer = None
    print("⚠️ Распознавание голоса отключено (нет ключа)")

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
        f"Сейчас у меня настроение **{personality.mood}**)\n"
        f"🎤 Ты можешь писать текст или отправлять **голосовые сообщения**!\n\n"
        f"Ну что, о чём поговорим?"
    )
    bot.reply_to(message, welcome)


@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice(message):
    """Обработка голосовых сообщений"""
    user_id = message.from_user.id
    user_name = get_user_name(user_id, message.from_user.first_name)
    
    # Показываем, что обрабатываем
    bot.send_chat_action(message.chat.id, 'typing')
    status_msg = bot.reply_to(message, "🎤 Слушаю...")
    
    try:
        if not recognizer:
            bot.edit_message_text(
                "❌ Распознавание голоса не настроено. Добавь SBER_SPEECH_KEY в переменные окружения.",
                chat_id=message.chat.id,
                message_id=status_msg.message_id
            )
            return
        
        # Получаем файл голосового сообщения
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Сохраняем временно
        temp_file = f"voice_{user_id}_{int(time.time())}.ogg"
        with open(temp_file, 'wb') as f:
            f.write(downloaded_file)
        
        # Распознаём речь
        bot.edit_message_text(
            "🔍 Распознаю речь...",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )
        
        text = recognizer.transcribe(temp_file)
        
        # Удаляем временный файл
        try:
            os.remove(temp_file)
        except:
            pass
        
        if not text:
            bot.edit_message_text(
                "😕 Не смогла разобрать, повтори пожалуйста?",
                chat_id=message.chat.id,
                message_id=status_msg.message_id
            )
            return
        
        # Показываем распознанный текст
        bot.edit_message_text(
            f"📝 Распознала: \"{text}\"\n\n🤔 Думаю...",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )
        
        # Обрабатываем как обычное сообщение
        process_text_message(message, text, user_name, status_msg.message_id)
        
    except Exception as e:
        print(f"Ошибка обработки голоса: {e}")
        bot.edit_message_text(
            f"😅 Ошибка при обработке голоса: {e}",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )


def process_text_message(message, user_input, user_name, status_msg_id=None):
    """Обработка текстового сообщения"""
    try:
        # Обновляем состояние Афины
        personality.react_to_message(user_input)
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
        
        # Формируем системный промпт
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
        
        # Добавляем фоновую мысль
        if random.random() < 0.2 and personality.inner_thoughts:
            thought = random.choice(personality.inner_thoughts[-3:])
            answer += f"\n\n💭 (я тут думала: {thought['thought']})"
        
        # Отправляем ответ
        if status_msg_id:
            bot.edit_message_text(
                answer,
                chat_id=message.chat.id,
                message_id=status_msg_id
            )
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
    """Обработка текстовых сообщений"""
    user_name = get_user_name(message.from_user.id, message.from_user.first_name)
    process_text_message(message, message.text, user_name, None)


# ========== ФОНОВЫЙ ЦИКЛ ЖИЗНИ ==========

def background_life_cycle():
    """Афина живёт своей жизнью в фоне"""
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
    print("🌟 Афина 4.0 - Живая личность с голосом!")
    print(f"📚 Фактов в базе: {len(kb.facts)}")
    print(f"🎭 Настроение: {personality.mood}")
    if recognizer:
        print("🎤 Голосовое распознавание: ВКЛЮЧЕНО")
    else:
        print("⚠️ Голосовое распознавание: отключено (нужен SBER_SPEECH_KEY)")
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
