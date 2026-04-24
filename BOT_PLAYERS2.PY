from email.mime import message

import telebot
from dotenv import load_dotenv 
import os
from telebot import types

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN) 


registered_users = {}
OWNER_ID = 760424840
ADMIN_IDS = [478933251]
GROUP_ID = -4843010970

post_text = "🎭 Добро пожаловать на Мафию!\n\nПроведи вечер в классной компании, сыграй.\n\nНажимай кнопку ниже, чтобы записаться\n"
posted_message_id = None


def is_admin(user_id):
    return user_id == OWNER_ID or user_id in ADMIN_IDS


# ----------------- TEXT -----------------
def build_text():
    final_text = post_text + "\nУчастники:\n"   
    reference = 1
    gang = 0 
    if registered_users:
        for user_id in registered_users:
            username = registered_users[user_id]["username"]
            plus_one = registered_users[user_id]["plus_one"]
            
            line = f"{reference}.  @{username} " 
            
            if plus_one > 0:
                line += f"  +{plus_one}" 

            
            final_text +=line + "\n" 

            
            gang += 1 + plus_one
            
            reference+=1
        
        final_text += f"\nКоличество мафиозников: {gang}"
        
    else:
        final_text += "Пока никого нет"
    
    return final_text


# ----------------- MARKUP -----------------
def build_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Записаться", callback_data="register"),
        types.InlineKeyboardButton("+ 1", callback_data="plus_one"),
        types.InlineKeyboardButton("Отписаться", callback_data="unregister"),
        types.InlineKeyboardButton("- 1", callback_data="minuse_one"),
    )
    return markup


# ----------------- SEND POST -----------------
@bot.message_handler(commands=['post'])
def post(message):
    global posted_message_id

    if not is_admin(message.from_user.id):
        bot.reply_to(message, "Нет прав")
        return

    msg = bot.send_message(
        GROUP_ID,
        build_text(),
        reply_markup=build_markup()
    )

    posted_message_id = msg.message_id
    bot.reply_to(message, "Сообщение отправлено")


# ----------------- START -----------------

@bot.message_handler(commands=['start'])
def start(message):
    registered_users.clear()
    bot.send_message(message.chat.id, build_text(), reply_markup=build_markup())
 

# ----------------- CALLBACK -----------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    # register
    if call.data == "register":
        if user_id not in registered_users:
            registered_users[user_id] = {
                "username": username,
                "plus_one": 0
            }
            bot.answer_callback_query(call.id, "Вы записаны!")
        else:
            bot.answer_callback_query(call.id, "Вы уже записаны!")

    # plus_one
    elif call.data == "plus_one":
        if user_id in registered_users:
            registered_users[user_id]["plus_one"] += 1
            if registered_users[user_id]["plus_one"] > 3:
                registered_users[user_id]["plus_one"] = 3  
        bot.answer_callback_query(call.id, "Ваш +1 добавлен!")

    # minus_one
    elif call.data == "minuse_one":
        if user_id in registered_users:
            if registered_users[user_id]["plus_one"] > 0:
                registered_users[user_id]["plus_one"] -=1
        bot.answer_callback_query(call.id, "Ваш +1 удалён!")

    # unregister
    elif call.data == "unregister":
        if user_id in registered_users:
            del registered_users[user_id]
            bot.answer_callback_query(call.id, "Вы отписаны!")
        else:
            bot.answer_callback_query(call.id, "Вы не записаны!")

    # UPDATE MESSAGE
    if call.data in ["register", "plus_one", "minuse_one", "unregister"]:
        bot.edit_message_text(
            text=build_text(),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=build_markup()
        )
@bot.message_handler(content_types=['text'])
def admin_set_post(message):
        global post_text
        if message.chat.type != "private":
            return

        if not is_admin(message.from_user.id):
            bot.reply_to(message, "Нет прав")
            return
      
        post_text = message.text
        bot.send_message(message.chat.id, "text updated")
@bot.message_handler(commands=['clear'])
def clear(message):
    global registered_users
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "Нет прав")
        return
# ----------------- RUN -----------------
bot.polling(none_stop=True)
