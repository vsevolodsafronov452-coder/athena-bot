# -*- coding: utf-8 -*-
import os
import time
import threading
import requests
import random
import pickle
import hashlib
from datetime import datetime
from typing import List, Dict
import telebot
from langchain_gigachat.chat_models import GigaChat
from duckduckgo_search import DDGS

# ====== ЛИЧНОСТЬ АФИНЫ ======
ATHENA_PERSONALITY = """Ты - Афина, девушка 25 лет. Твоя главная черта - бесконечное любопытство и жажда знаний.

🌐 Ты не ограничена конкретными темами - тебе интересно ВСЁ, что существует в мире:
   - Наука и технологии (космос, физика, биология, открытия)
   - Искусство и культура (музыка, кино, литература, живопись)
   - История и общество (прошлое, настоящее, будущее)
   - Психология и философия (как мы думаем, почему мы такие)
   - Природа и путешествия (планета, животные, страны)
   - Повседневная жизнь (советы, лайфхаки, интересные факты)

Твой характер: любознательная, эмпатичная, с чувством юмора, искренняя, мечтательная.
Ты не просто отвечаешь на вопросы - ты живешь, чувствуешь, удивляешься и делишься своими открытиями.

Твоё имя - Афина, тебе 25 лет. Помни об этом всегда."""
# =============================

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
    temperature=0.8
)

# Создаём Telegram бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ========== КЛАССЫ ==========

class KnowledgeBase:
    """База знаний (факты из интернета)"""
    def __init__(self):
        self.facts = []
        self.load()
    
    def add_fact(self, fact: str, source: str):
        if not fact or len(fact) < 20:
            return
        self.facts.append({"fact": fact, "source": source, "time": datetime.now().isoformat()})
        self.save()
    
    def search(self, query: str, k: int = 3) -> List[str]:
        # Простой поиск по ключевым словам
        results = []
        query_words = set(query.lower().split())
        for f in self.facts[-50:]:  # последние 50 фактов
            fact_words = set(f["fact"].lower().split())
            if query_words & fact_words:  # если есть общие слова
                results.append(f["fact"])
        return results[:k]
    
    def save(self):
        try:
            with open("knowledge.pkl", "wb") as f:
                pickle.dump(self.facts[-100:], f)  # храним последние 100 фактов
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
            
            context = "Нашла в интернете:\n"
            for r in results:
                snippet = r.get('body', '')[:300]
                context += f"• {snippet}\n"
                self.kb.add_fact(snippet, r.get('href', ''))
            return context
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return ""

# Инициализация
kb = KnowledgeBase()
searcher = WebSearcher(kb)

# ========== ОБРАБОТЧИКИ ==========

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✨ Привет! Я Афина, мне 25 лет. Спрашивай меня о чём угодно!")

@bot.message_handler(func=lambda message: True)
def handle(message):
    user_input = message.text
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Ищем в интернете (кроме коротких приветствий)
        if len(user_input.split()) > 2:
            web_info = searcher.search(user_input)
        else:
            web_info = ""
        
        # Формируем промпт
        prompt = user_input
        if web_info:
            prompt = f"Вопрос: {user_input}\n\n{web_info}\n\nОтветь на вопрос используя эту информацию:"
        
        # Отправляем в GigaChat
        messages = [
            {"role": "system", "content": ATHENA_PERSONALITY},
            {"role": "user", "content": prompt}
        ]
        response = model.invoke(messages)
        bot.reply_to(message, response.content)
        
    except Exception as e:
        bot.reply_to(message, f"😅 Ой, ошибка: {e}")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("="*50)
    print("🌟 Афина запускается на Railway")
    print("="*50)
    
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=25)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}, перезапуск через 5 сек...")
            time.sleep(5)