import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Вставьте ваш токен бота
TOKEN = '8042568924:AAF7i2Z_tADj-QvKuQMxwyc8kAs84A8HX5Y'
CHANNEL_ID = '@marketbotX'

# Ваш Telegram ID
ADMIN_ID = 6578018656  # Замените на ваш ID

bot = telebot.TeleBot(TOKEN)

# Словарь для хранения временных данных пользователя
user_data = {}

# Проверка на админа
def is_admin(user_id):
    return user_id == ADMIN_ID

# Кнопка для начала заявки
@bot.message_handler(commands=['start'])
def start_handler(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "У вас нет прав для использования этого бота.")
        return
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Создать заявку"))
    bot.send_message(message.chat.id, "Добро пожаловать! Нажмите 'Создать заявку', чтобы начать. 📋", reply_markup=markup)

# Начало заявки
@bot.message_handler(func=lambda message: message.text == "Создать заявку")
def create_request(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "У вас нет прав для использования этого бота.")
        return
    user_data[message.chat.id] = {}
    bot.send_message(message.chat.id, "Введите название проекта:", reply_markup=ReplyKeyboardRemove())

# Обработка этапов заявки
@bot.message_handler(func=lambda message: message.chat.id in user_data and 'name' not in user_data[message.chat.id])
def name_handler(message):
    user_data[message.chat.id]['name'] = message.text
    bot.send_message(message.chat.id, "Отлично! Теперь напишите описание проекта:")

@bot.message_handler(func=lambda message: 'description' not in user_data[message.chat.id])
def description_handler(message):
    user_data[message.chat.id]['description'] = message.text
    # Клавиатура с выбором языка программирования
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Python"), KeyboardButton("JavaScript"), KeyboardButton("Java"))
    markup.add(KeyboardButton("C++"), KeyboardButton("Другое"))
    bot.send_message(message.chat.id, "Какой язык программирования вы используете? 🖥️", reply_markup=markup)

@bot.message_handler(func=lambda message: 'language' not in user_data[message.chat.id])
def language_handler(message):
    user_data[message.chat.id]['language'] = message.text
    bot.send_message(message.chat.id, "Какие библиотеки вы используете? 📚", reply_markup=ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: 'libraries' not in user_data[message.chat.id])
def libraries_handler(message):
    user_data[message.chat.id]['libraries'] = message.text
    bot.send_message(message.chat.id, "Укажите стоимость проекта (в цифрах): 💰")

@bot.message_handler(func=lambda message: 'cost' not in user_data[message.chat.id])
def cost_handler(message):
    try:
        user_data[message.chat.id]['cost'] = float(message.text)
        bot.send_message(message.chat.id, "Добавьте ссылку на фотографию проекта: 🖼️")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, укажите стоимость в числовом формате.")

@bot.message_handler(func=lambda message: 'photo_url' not in user_data[message.chat.id])
def photo_url_handler(message):
    if message.text.startswith("http://") or message.text.startswith("https://"):
        user_data[message.chat.id]['photo_url'] = message.text
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Да"), KeyboardButton("Нет"))
        bot.send_message(
            message.chat.id,
            "Продается ли бот один раз и только в одни руки? Нажмите 'Да' или 'Нет':",
            reply_markup=markup,
        )
    else:
        bot.send_message(message.chat.id, "Пожалуйста, укажите корректную ссылку на фотографию (http:// или https://).")

@bot.message_handler(func=lambda message: 'exclusive' not in user_data[message.chat.id])
def exclusive_handler(message):
    if message.text in ['Да', 'Нет']:
        user_data[message.chat.id]['exclusive'] = (message.text == 'Да')
        send_to_channel(message.chat.id)
        bot.send_message(message.chat.id, "Спасибо! Ваши данные успешно отправлены. 🎉", reply_markup=start_keyboard())
        del user_data[message.chat.id]
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите 'Да' или 'Нет'.")

# Клавиатура для главного меню
def start_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Создать заявку"))
    return markup

# Функция отправки данных в канал
def send_to_channel(user_id):
    data = user_data[user_id]
    message = (
        f"📌 <b>Название:</b> {data['name']}\n"
        f"📝 <b>Описание:</b> {data['description']}\n"
        f"💻 <b>Язык программирования:</b> {data['language']}\n"
        f"📚 <b>Библиотеки:</b> {data['libraries']}\n"
        f"💰 <b>Стоимость:</b> {data['cost']}\n"
        f"🔒 <b>Продается только в одни руки:</b> {'Да' if data['exclusive'] else 'Нет'}\n"
        f"🖼️ <b>Фото:</b> {data['photo_url']}"
    )
    bot.send_message(CHANNEL_ID, message, parse_mode='HTML')

# Запуск бота
bot.polling(none_stop=True)
