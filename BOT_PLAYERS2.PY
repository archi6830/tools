import os
import time
import threading
import pytz
import psycopg2
import telebot

from datetime import datetime
from dotenv import load_dotenv
from telebot import types

# ----------------- ENV -----------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
TOKEN = os.getenv("BOT_TOKEN")

# ----------------- DB -----------------
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# чтобы меньше падал на Railway
conn.autocommit = True

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    plus_one INT DEFAULT 0
)
""")

# ----------------- BOT -----------------
bot = telebot.TeleBot(TOKEN)

CANADA_TZ = pytz.timezone("America/Toronto")

OWNER_ID = 760424840
ADMIN_IDS = [478933251]
GROUP_IDS = [-4843010970, -1002830983691]

post_text = "🎭 Добро пожаловать на Мафию!\n\nПроведи вечер в классной компании, сыграй.\n\nНажимай кнопку ниже, чтобы записаться\n"


# ----------------- ADMIN -----------------
def is_admin(user_id):
    return user_id == OWNER_ID or user_id in ADMIN_IDS


# ----------------- TEXT -----------------
def build_text():
    final_text = post_text + "\nУчастники:\n"

    cursor.execute("SELECT username, plus_one FROM users ORDER BY user_id")
    users = cursor.fetchall()

    gang = 0
    reference = 1

    if users:
        for username, plus_one in users:
            line = f"{reference}. @{username}"

            if plus_one and plus_one > 0:
                line += f" +{plus_one}"

            final_text += line + "\n"

            gang += 1 + (plus_one or 0)
            reference += 1

        final_text += f"\nКоличество мафиозников: {gang}"
    else:
        final_text += "Пока никого нет"

    return final_text


# ----------------- BUTTONS -----------------
def build_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Записаться", callback_data="register"),
        types.InlineKeyboardButton("+ 1", callback_data="plus_one"),
        types.InlineKeyboardButton("- 1", callback_data="minuse_one"),
        types.InlineKeyboardButton("Отписаться", callback_data="unregister"),
    )
    return markup
# ----------------- CALLBACK -----------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    # ---------------- REGISTER ----------------
    if call.data == "register":
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(
                "INSERT INTO users (user_id, username, plus_one) VALUES (%s, %s, %s)",
                (user_id, username, 0)
            )
            bot.answer_callback_query(call.id, "Вы записаны!")
        else:
            bot.answer_callback_query(call.id, "Вы уже записаны!")

    # ---------------- PLUS ONE ----------------
    elif call.data == "plus_one":
        cursor.execute("SELECT plus_one FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if user:
            cursor.execute("""
                UPDATE users
                SET plus_one = LEAST(plus_one + 1, 3)
                WHERE user_id = %s
            """, (user_id,))
            bot.answer_callback_query(call.id, "+1 добавлен")
        else:
            bot.answer_callback_query(call.id, "Сначала запишитесь!")

    # ---------------- MINUS ONE ----------------
    elif call.data == "minuse_one":
        cursor.execute("SELECT plus_one FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if user:
            cursor.execute("""
                UPDATE users
                SET plus_one = GREATEST(plus_one - 1, 0)
                WHERE user_id = %s
            """, (user_id,))
            bot.answer_callback_query(call.id, "-1 удалён")
        else:
            bot.answer_callback_query(call.id, "Сначала запишитесь!")

    # ---------------- UNREGISTER ----------------
    elif call.data == "unregister":
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        bot.answer_callback_query(call.id, "Вы отписаны!")

    # ---------------- UPDATE MESSAGE ----------------
    if call.data in ["register", "plus_one", "minuse_one", "unregister"]:
        try:
            bot.edit_message_text(
                text=build_text(),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=build_markup()
            )
        except:
            pass


# ----------------- POST -----------------
@bot.message_handler(commands=['post'])
def post(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "Нет прав")
        return

    for group_id in GROUP_IDS:
        bot.send_message(
            group_id,
            build_text(),
            reply_markup=build_markup()
        )

    bot.reply_to(message, "Сообщение отправлено")


# ----------------- START -----------------
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        build_text(),
        reply_markup=build_markup()
    )


# ----------------- RUN -----------------
bot.polling(none_stop=True)
