
from hal_config import TELEGRAM_BOT_TOKEN
import telebot
from googletrans import Translator
import time
import sqlite3
import re


from sqlite3 import Connection

class ConnectionPool:
    def __init__(self, max_connections: int = 5):
        self.max_connections = max_connections
        self.connections = []

    def get_connection(self) -> Connection:
        if len(self.connections) < self.max_connections:
            conn = sqlite3.connect('haldata.db')
            self.connections.append(conn)
            return conn

        return self.connections.pop()

    def release_connection(self, conn: Connection):
        self.connections.append(conn)

pool = ConnectionPool()
bot = telebot.TeleBot(token=TELEGRAM_BOT_TOKEN)
translator = Translator(service_urls=['translate.google.com'])

def get_db_conn():
    conn = sqlite3.connect('haldata.db')
    return conn

conn = get_db_conn()
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS auxdict (user_id TEXT, english TEXT, russian TEXT)")
conn.commit()
c.execute("CREATE TABLE IF NOT EXISTS lessons (user_id TEXT, date TEXT, theme TEXT, grade TEXT)")
conn.commit()
c.execute("CREATE TABLE IF NOT EXISTS refmat (user_id TEXT, name TEXT, link TEXT)")
conn.commit()
conn.close()

@bot.message_handler(commands=['start', 'hello'])
def send_unwelcome(message):
    bot.reply_to(message, "Howdy, how are you doing? I'm here to help you learn english")

@bot.message_handler(commands=[ 'начать', 'привет'])
def send_welcome(message):
    bot.reply_to(message, "Даров, че как? Я готов помочь с изучением английского")

@bot.message_handler(commands=['help', 'помощь'])
def send_explanation(message):
    bot.send_message(chat_id=message.chat.id, text='Список команд: \n*/start /hello /начать /привет* - приветствие \n*/help /помощь* - список комманд(да неужели) \n*/translate /перевод* _слово_ - переводит слова(может и целый текст) \n*/addtranslation /добавить перевод* _слово1 слово2_ - добавляет в вашь личный словарь дополнительные переводы(перезаписывает изначальный словарь) \n*/addlesson /добавить урок* _дата тема оценка_ - позволяет записывать информацию о уже пройденных уроках \n*/showlessons /показатьуроки* - показывает все записанные вами уроки \n*/addrefmat /добавитьматериал* _название ссылка_ - позволяет записывать информацию соссылками на дополнительные матерьялы\n*/showrefmats /показатьматериалы* - показывает список записанных материалов \n*/rate /оценить* - позволяет выставить боту оценку за его работу', parse_mode= 'Markdown')

@bot.message_handler(commands=['translate'])
def translate_message(message):
    user_id = message.from_user.id  # get user ID
    text = message.text.split(' ', 1)[1]  # Get the text to be translated
    time.sleep(1)  # Add a delay of 1 second in case google servers are sleepy today
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, english, russian FROM auxdict WHERE user_id=? AND english=?", (user_id, text,))
    translation1 = c.fetchone()
    conn.close()
    if translation1 == []:
        translation = translator.translate(text, dest='ru').text  # Translate to English
        bot.reply_to(message, translation)
    else:
        bot.reply_to(message, translation1[2])

@bot.message_handler(commands=['перевод'])
def translate_message2(message):
    user_id = message.from_user.id  # get user ID
    text = message.text.split(' ', 1)[1] # Get the text to be translated
    time.sleep(1) # Add a delay of 1 second in case google servers are sleepy today
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, english, russian FROM auxdict WHERE user_id=? AND russian=?", (user_id, text,))
    translation1 = c.fetchone()
    conn.close()
    if translation1 == []:
        translation = translator.translate(text, dest='en').text # Translate to English
        bot.reply_to(message, translation)
    else:
        bot.reply_to(message, translation1[1])

@bot.message_handler(commands=['addtranslation', 'добавитьперевод'])
def addtranslation(message):
    user_id = message.from_user.id # get user ID
    text = message.text.split(' ', 2) # Get the text to be translated
    detext = re.search('[a-zA-Z]+', text[1])


    if detext == None:
        conn = get_db_conn()
        c = conn.cursor()
        c.execute("INSERT INTO auxdict (user_id, english, russian) VALUES (?, ?, ?)", (user_id, text[2], text[1]))
        conn.commit()
        conn.close()
    else:
        conn = get_db_conn()
        c = conn.cursor()
        c.execute("INSERT INTO auxdict (user_id, english, russian) VALUES (?, ?, ?)", (user_id, text[1], text[2]))
        conn.commit()
        conn.close()
    bot.reply_to(message, "Auxiliary dictionary entry  added successfully")


@bot.message_handler(commands=['addlesson', 'добавитьурок'])
def addlesson(message):
    user_id = message.from_user.id # get user ID
    text = message.text.split(' ', 3) # Get the text to be saved

    with pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO lessons (user_id, date, theme, grade) VALUES (?, ?, ?, ?)", (user_id, text[1], text[2], text[3]))
        conn.commit()

    bot.reply_to(message, "Lesson added successfully")


@bot.message_handler(commands=['showlessons', 'показатьуроки'])
def showlessons(message):
    user_id = message.from_user.id # get user ID

    with pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT date, theme, grade FROM lessons WHERE user_id=?", (user_id,))
        lessons = c.fetchall()

    if not lessons:
        bot.reply_to(message, "You have no lessons yet")
    else:
        for lesson in lessons:
            bot.reply_to(message, f"Date: {lesson[0]}, Theme: {lesson[1]}, Grade: {lesson[2]}")


@bot.message_handler(commands=['addrefmat', 'добавитьматериал'])
def addlesson(message):
    user_id = message.from_user.id # get user ID
    text = message.text.split(' ', 2) # Get the text to be saved

    with pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO refmat (user_id, name, link) VALUES (?, ?, ?)", (user_id, text[1], text[2]))
        conn.commit()

    bot.reply_to(message, "Reference material added successfully")

@bot.message_handler(commands=['showrefmats', 'показатьматериалы'])
def showlessons(message):
    user_id = message.from_user.id # get user ID

    with pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT name, link FROM refmat WHERE user_id=?", (user_id,))
        refmats = c.fetchall()

    if not refmats:
        bot.reply_to(message, "You have no reference materials yet")
    else:
        for refmat in refmats:
            bot.reply_to(message, f"Name: {refmat[0]}, Link: {refmat[1]}")


@bot.message_handler(commands=['rate', 'оценить'])
def rate_handler(message):
    # создаем кастомную клавиатуру с кнопками от 1 до 5
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        *[telebot.types.KeyboardButton(text) for text in ['Отлично', 'Хорошо', 'Нормально', 'Не очень', 'Плохо']])

    # отправляем сообщение с клавиатурой
    bot.send_message(chat_id=message.chat.id, text='Пожалуйста, оцените бота используя специальную клавиатуру', reply_markup=keyboard)


# обработчик сообщений с оценкой
@bot.message_handler(func=lambda message: message.text in ['Отлично', 'Хорошо', 'Нормально', 'Не очень', 'Плохо'])
def rating_handler(message):
    # словарь с возможными ответами на оценку
    responses = {
        'Отлично': 'Спасибо за высокую оценку!',
        'Хорошо': 'Рад, что вам понравилось!',
        'Нормально': 'Будем стараться улучшиться!',
        'Не очень': 'Очень жаль, что вы не оценили нашу работу.',
        'Плохо': 'Мы будем стараться исправить все недочеты.'
    }

    # отправляем ответ на оценку
    bot.send_message(chat_id=message.chat.id, text=responses[message.text])
bot.polling()