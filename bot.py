from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import DatabaseManager, hide_img
import schedule
import threading
import time
from config import API_TOKEN, DATABASE
import logging

bot = TeleBot(API_TOKEN)
manager = DatabaseManager(DATABASE)

def gen_markup(prize_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Получить!", callback_data=prize_id))
    return markup

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    prize_id = call.data
    user_id = call.message.chat.id

    if manager.get_winners_count(prize_id) < 3:
        res = manager.add_winner(user_id, prize_id)
        if res:
            img = manager.get_prize_img(prize_id)
            with open(f'img/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Поздравляем! Ты получил картинку! Тебе начислено 10 баллов.")
        else:
            bot.send_message(user_id, 'Ты уже получил картинку!')
    else:
        bot.send_message(user_id, "К сожалению, ты не успел получить картинку! Попробуй в следующий раз!)")

def send_message():
    try:
        prize_id, img = manager.get_random_prize()[:2]
        manager.mark_prize_used(prize_id)
        hide_img(img)

        for user in manager.get_users():
            with open(f'hidden_img/{img}', 'rb') as photo:
                bot.send_photo(user, photo, reply_markup=gen_markup(prize_id))
    except Exception as e:
        logging.error(f"Error sending message: {e}")

def schedule_thread():
    schedule.every(1).minute.do(send_message)
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    if user_id in manager.get_users():
        bot.reply_to(message, "Ты уже зарегистрирован!")
    else:
        manager.add_user(user_id, message.from_user.username)
        bot.reply_to(message, """Привет! Добро пожаловать! 
Тебя успешно зарегистрировали!
Каждый час тебе будут приходить новые картинки, и у тебя будет шанс их получить!
Для этого нужно быстрее всех нажать на кнопку 'Получить!'

Только три первых пользователя получат картинку!)""")

@bot.message_handler(commands=['rating'])
def handle_rating(message):
    res = manager.get_rating()
    res = [f'| @{x[0]:<11} | {x[1]:<11}|\n{"_"*26}' for x in res]
    res = '\n'.join(res)
    res = f'|USER_NAME    |COUNT_PRIZE|\n{"_"*26}\n' + res
    bot.send_message(message.chat.id, res)

@bot.message_handler(commands=['points'])
def handle_points(message):
    user_id = message.chat.id
    points = manager.get_points(user_id)
    bot.send_message(user_id, f"У тебя {points} баллов.")

@bot.message_handler(commands=['redeem'])
def handle_redeem(message):
    user_id = message.chat.id
    args = message.text.split()
    if len(args) == 2 and args[1].isdigit():
        points = int(args[1])
        if manager.redeem_points(user_id, points):
            bot.send_message(user_id, f"Ты успешно обменял {points} баллов на бонус!")
            # Implement the actual bonus awarding logic here
        else:
            bot.send_message(user_id, f"У тебя недостаточно баллов для обмена. У тебя {manager.get_points(user_id)} баллов.")
    else:
        bot.send_message(user_id, "Пожалуйста, используй формат: /redeem <количество_баллов>")

def polling_thread():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    polling_threadX = threading.Thread(target=polling_thread)
    polling_schedule = threading.Thread(target=schedule_thread)

    polling_threadX.start()
    polling_schedule.start()
