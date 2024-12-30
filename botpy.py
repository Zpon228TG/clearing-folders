import json
from typing import Union
import requests
import telebot
from telebot import types
import sqlite3

from config import REQUIRED_CHANNEL, ADMIN_ID, CRYPTO_BOT_TOKEN, TOKEN, ALLOW_CURRENCIES

bot = telebot.TeleBot(TOKEN)
user_data = {}

def check_subscription_decorator(channel_id):
    def decorator(func):
        def wrapper(call, *args, **kwargs):
            user_id = call.from_user.id
            try:
                chat_member = bot.get_chat_member(channel_id, user_id)
                if chat_member.status != 'left':
                    return func(call, *args, **kwargs)
                else:
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(
                        types.InlineKeyboardButton(
                            text="Подписаться на канал",
                            url=f"https://t.me/{channel_id.lstrip('@')}"
                        ),
                        types.InlineKeyboardButton(
                            text="Проверить подписку",
                            callback_data="check_subscription"
                        )
                    )

                    if hasattr(call, 'message') and call.message:
                        bot.send_message(
                            call.message.chat.id,  # Используем call.message.chat.id
                            "❌ Вы не подписаны на канал. Пожалуйста, подпишитесь, чтобы продолжить.",
                            reply_markup=keyboard
                        )
                    else:
                        if hasattr(call, 'chat') and call.chat:
                            bot.send_message(
                                call.chat.id,
                                "❌ Вы не подписаны на канал. Пожалуйста, подпишитесь, чтобы продолжить.",
                                reply_markup=keyboard
                            )
                        else:
                            pass
            except Exception as e:
                if hasattr(call, 'message') and call.message:
                    bot.send_message(call.message.chat.id, f"Произошла ошибка при проверке подписки: {e}")
                else:
                    pass
        return wrapper

    return decorator



def add_user_to_db(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
@check_subscription_decorator(REQUIRED_CHANNEL)
def start(message):
    user_id = message.from_user.id

    # Добавляем пользователя в базу данных, если его нет
    add_user_to_db(user_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Меню 📋")
    item3 = types.KeyboardButton("Наши каналы 🔗")
    item4 = types.KeyboardButton("Поддержать 💸")
    item5 = types.KeyboardButton("Наши соц.сети 🌐")
    item6 = types.KeyboardButton("Профиль 👤")
    markup.add(item1, item3, item4, item5, item6)

    if int(user_id) == int(ADMIN_ID):
        item_admin = types.KeyboardButton("Админка 🛠️")
        markup.add(item_admin)

    bot.send_message(message.chat.id, "Привет! Я ваш бот. Выберите опцию:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Админка 🛠️" and int(message.from_user.id) == int(ADMIN_ID))
def admin_panel(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Отправить сообщение всем пользователям 📢")
    back_button = types.KeyboardButton("Назад ↩️")
    markup.add(item1, back_button)

    bot.send_message(message.chat.id, "Вы в админке. Выберите действие:", reply_markup=markup)


def get_all_user_ids():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return user_ids


@bot.message_handler(func=lambda message: message.text == "Отправить сообщение всем пользователям 📢" and int(message.from_user.id) == int(ADMIN_ID))
def send_message_to_all(message):
    bot.send_message(message.chat.id, "Введите текст сообщения для рассылки (можно использовать Markdown или HTML): 📝")
    bot.register_next_step_handler(message, get_message_text)


@check_subscription_decorator(REQUIRED_CHANNEL)
def get_message_text(message):
    text = message.text

    user_data[message.from_user.id] = text

    markup = types.InlineKeyboardMarkup()
    yes_button = types.InlineKeyboardButton("Да, с изображением 📸", callback_data="yes_with_image")
    no_button = types.InlineKeyboardButton("Нет, только текст ✉️", callback_data="no_with_image")
    markup.add(yes_button, no_button)

    bot.send_message(message.chat.id, "Хотите прикрепить изображение?", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "yes_with_image")
@check_subscription_decorator(REQUIRED_CHANNEL)
def handle_yes_with_image(call):
    bot.send_message(call.message.chat.id, "Пришлите изображение 🖼️.")
    bot.register_next_step_handler(call.message, send_message_with_image)


@bot.callback_query_handler(func=lambda call: call.data == "no_with_image")
@check_subscription_decorator(REQUIRED_CHANNEL)
def handle_no_with_image(call):
    bot.send_message(call.message.chat.id, "Сообщение будет отправлено без изображения 📭.")
    bot.register_next_step_handler(call.message, send_message_without_image)


def send_message_without_image(message):
    text = user_data.get(message.from_user.id)

    if not text:
        bot.send_message(message.chat.id, "Текст сообщения не найден. Пожалуйста, попробуйте снова.")
        return

    user_ids = get_all_user_ids()
    progress_msg = bot.send_message(message.chat.id, f"Рассылка сообщений: 0/{len(user_ids)}")

    progress_count = 0
    for user_id in user_ids:
        try:
            bot.send_message(user_id, text, parse_mode='Markdown')
            progress_count += 1
            bot.edit_message_text(f"Рассылка сообщений: {progress_count}/{len(user_ids)}",
                                  chat_id=message.chat.id, message_id=progress_msg.message_id)
        except Exception as e:
            pass
    bot.send_message(message.chat.id, f"Рассылка завершена! Сообщение отправлено {progress_count}/{len(user_ids)} пользователям. ✅")


def send_message_with_image(message):
    caption = user_data.get(message.from_user.id)

    if not caption:
        caption = "Текст не был предоставлен. ❌"

    if message.photo:
        user_ids = get_all_user_ids()
        progress_msg = bot.send_message(message.chat.id, f"Рассылка изображений: 0/{len(user_ids)}")

        progress_count = 0
        for user_id in user_ids:
            try:
                bot.send_photo(user_id, message.photo[-1].file_id, caption=caption)
                progress_count += 1
                bot.edit_message_text(f"Рассылка изображений: {progress_count}/{len(user_ids)}",
                                      chat_id=message.chat.id, message_id=progress_msg.message_id)
            except Exception as e:
                pass
        if caption:
            for user_id in user_ids:
                try:
                    bot.send_message(user_id, caption, parse_mode='Markdown')
                except Exception as e:
                    pass
        bot.send_message(message.chat.id, f"Сообщение с изображением и текстом отправлено всем пользователям. 📤")
    else:
        bot.send_message(message.chat.id, "Вы не прислали изображение. 🚫")






@bot.message_handler(func=lambda message: message.text == "Назад ↩️")
@check_subscription_decorator(REQUIRED_CHANNEL)
def go_back(message):
    start(message)

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
@check_subscription_decorator(REQUIRED_CHANNEL)
def check_subscription_callback1_handler(call):
    user_id = call.from_user.id
    try:
        chat_member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)

        if chat_member.status != 'left':  # Если пользователь подписан
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(call.message.chat.id, "✅ Вы успешно подписались на канал! Теперь вы можете использовать бота.")

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Меню 📋")
            item3 = types.KeyboardButton("Наши каналы 🔗")
            item4 = types.KeyboardButton("Поддержать 💸")
            item5 = types.KeyboardButton("Наши соц.сети 🌐")
            item6 = types.KeyboardButton("Панель управления")
            item7 = types.KeyboardButton("Профиль 👤")
            markup.add(item1, item3, item4, item5, item6, item7)
            bot.send_message(call.message.chat.id, "Добро пожаловать! Вы можете использовать все функции.", reply_markup=markup)

        else:  # Если пользователь не подписан
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    text="Подписаться на канал",
                    url=f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}"
                ),
                types.InlineKeyboardButton(
                    text="Проверить подписку",
                    callback_data="check_subscription"
                )
            )

            # Отправляем сообщение с просьбой подписаться
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(call.message.chat.id, "❌ Вы не подписаны на канал. Пожалуйста, подпишитесь, чтобы продолжить.", reply_markup=keyboard)

    except Exception as e:
        pass

@bot.message_handler(func=lambda message: message.text == "Профиль 👤")
@check_subscription_decorator(REQUIRED_CHANNEL)
def profile(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Поддержать (Crypto bot) 💸")
    back_button = types.KeyboardButton("Назад ↩️")
    markup.add(item1, back_button)
    bot.send_message(message.chat.id, f"Ваш ID: {message.chat.id}", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Поддержать (Crypto bot) 💸")
@check_subscription_decorator(REQUIRED_CHANNEL)
def get_payment(message):
    bot.send_message(message.chat.id, "Введите сумму для пополнения:")
    bot.register_next_step_handler(message, ask_currency)



def ask_currency(message):
    try:
        pay_amount = float(message.text)
        markup = types.InlineKeyboardMarkup()

        for currency in ALLOW_CURRENCIES:
            markup.add(types.InlineKeyboardButton(currency, callback_data=f"currency_{currency}_{pay_amount}"))

        bot.send_message(message.chat.id, "Выберите валюту для пополнения:", reply_markup=markup)
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректную сумму!")


@bot.callback_query_handler(func=lambda call: call.data.startswith("currency_"))
@check_subscription_decorator(REQUIRED_CHANNEL)
def create_invoice(call):
    _, currency, pay_amount = call.data.split('_')
    pay_amount = float(pay_amount)

    status, pay_url, bill_id = crypto_api.bill(pay_amount, currency)

    if status:
        bot.send_message(call.message.chat.id, f"Перейдите по следующей ссылке для оплаты: {pay_url}")
        bot.send_message(call.message.chat.id, f"Ваш bill_id: {bill_id}")
    else:
        bot.send_message(call.message.chat.id, "Ошибка при создании счета.")


class CryptobotAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = 'https://pay.crypt.bot/api/'
        self.headers = {
            'Crypto-Pay-API-Token': self.token,
            'Content-Type': 'application/x-www-form-urlencoded',
        }

    def bill(self, pay_amount: Union[float, int], currency: str) -> tuple:
        payload = {
            'currency_type': 'fiat',
            'fiat': 'RUB',
            'amount': str(pay_amount),
            'expires_in': 10800,
            'accepted_assets': currency,
        }
        url = self.base_url + "createInvoice"
        response = requests.post(url, headers=self.headers, data=payload)

        try:
            response_data = json.loads(response.text)

            if response.status_code == 200 and response_data.get("ok"):
                if 'result' in response_data and 'pay_url' in response_data['result']:
                    pay_url = response_data['result']['pay_url']
                    invoice_id = response_data['result'].get('invoice_id', None)
                    if invoice_id:
                        return True, pay_url, invoice_id
                    else:
                        return False, "invoice_id не найден в ответе API.", None
                else:
                    return False, "Ответ API не содержит ожидаемых данных.", None
            else:
                return False, f"Ошибка API: {response_data.get('error', 'Неизвестная ошибка')}", None

        except json.JSONDecodeError:
            return False, "Не удалось распарсить ответ от API.", None

    def get_invoice_status(self, invoice_id: str) -> tuple:
        url = self.base_url + f"getInvoice/{invoice_id}"
        response = requests.get(url, headers=self.headers)

        try:
            response_data = json.loads(response.text)
            if response.status_code == 200 and response_data.get("ok"):
                return True, response_data['result']
            else:
                return False, f"Ошибка API: {response_data.get('error', 'Неизвестная ошибка')}"
        except json.JSONDecodeError:
            return False, "Не удалось распарсить ответ от API."

# Инициализация API
crypto_api = CryptobotAPI(CRYPTO_BOT_TOKEN)

@bot.message_handler(func=lambda message: message.text == "Наши каналы 🔗")
@check_subscription_decorator(REQUIRED_CHANNEL)
def channels(message):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("byvalery Art🔞", url="https://t.me/byvaleryart")
    button2 = types.InlineKeyboardButton("Время Игр", url="https://t.me/vremyigr")
    button3 = types.InlineKeyboardButton("Время Игр🔞", url="https://t.me/vremyaigr")
    markup.add(button1, button2, button3)
    bot.send_message(message.chat.id, "Выберите канал:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Поддержать 💸")
@check_subscription_decorator(REQUIRED_CHANNEL)
def support(message):
    text = """
    🌟 **Дорогие друзья!** 🌟

    🙏 Кто хочет помочь мне в развитии канала, буду очень благодарен!  
    Деньги я собираю на **Telegram подписку**, чтобы выкладывать игры более 2Гб. 📲

    💳 Вы можете поддержать меня через карту: **2200700722520920**  
    Или через **Boosty**: [Перейти на Boosty для доната](https://boosty.to/vremyaigor/donate) 🎁

    🔑 За ваш вклад вы получите доступ к играм и многому другому! 🚀  
    Благодарю за поддержку! 💙
    """
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(func=lambda message: message.text == "Наши соц.сети 🌐")
@check_subscription_decorator(REQUIRED_CHANNEL)
def social_media(message):
    markup = types.InlineKeyboardMarkup()
    youtube_button = types.InlineKeyboardButton("Наш YouTube 📺", url="https://t.me/your_channel_3")
    markup.add(youtube_button)
    bot.send_message(message.chat.id, "Вот ссылки на наши соц.сети:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Возможности ⚙️")
@check_subscription_decorator(REQUIRED_CHANNEL)
def possibilities(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Ссылка1")
    item2 = types.KeyboardButton("Ссылка2")
    item3 = types.KeyboardButton("Написать админу ✉️")
    back_button = types.KeyboardButton("Назад ↩️")
    markup.add(item1, item2, item3 , back_button)
    bot.send_message(message.chat.id, "Какую возможность вы хотите использовать?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Написать админу ✉️")
@check_subscription_decorator(REQUIRED_CHANNEL)
def send_to_admin(message):
    bot.send_message(message.chat.id, "https://t.me/ValerkaIT")

@bot.message_handler(func=lambda message: message.text == "Ссылка1")
@check_subscription_decorator(REQUIRED_CHANNEL)
def send_to_top1(message):
    bot.send_message(message.chat.id, f"Ссылки на интересные ресурсы(не забываем про VPN): https://theporndude.com")

@bot.message_handler(func=lambda message: message.text == "Ссылка2")
@check_subscription_decorator(REQUIRED_CHANNEL)
def send_to_top2(message):
    bot.send_message(message.chat.id, "Ссылки на интересные ресурсы(не забываем про VPN): https://f95zone.to/")

@bot.message_handler(func=lambda message: message.text == "Реклама 📢")
@check_subscription_decorator(REQUIRED_CHANNEL)
def advertising(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Ознакомиться с прайс-листом 💰")
    item2 = types.KeyboardButton("Купить 🛒")
    back_button = types.KeyboardButton("Назад ↩️")
    markup.add(item1)
    markup.add(item2, back_button)
    bot.send_message(message.chat.id, "Что вы хотите сделать?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Ознакомиться с прайс-листом 💰")
@check_subscription_decorator(REQUIRED_CHANNEL)
def price_list(message):
    text = """
    📢 **Прайс-лист на рекламу** 📢

    1️⃣ **200₽ = 1000 просмотров** 👀  
    По достижении 1000 просмотров, пост с рекламой удаляется ⏳

    2️⃣ **500₽ = 7 дней в ленте** 📅  
    Пост с рекламой будет висеть в ленте 7 дней, после чего удаляется 🗑️

    3️⃣ **1000₽ = 30 дней в ленте** 📅  
    Пост с рекламой будет висеть в ленте 30 дней, после чего удаляется 🗑️

    📞 Для покупки рекламы напишите "Купить 🛒"
    """
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# Обработка кнопки "Купить"
@bot.message_handler(func=lambda message: message.text == "Купить 🛒")
@check_subscription_decorator(REQUIRED_CHANNEL)
def buy(message):
    text = """
    ✉️ **Предложения о покупке** присылайте на почту:  
    📧 **vremyaigor@gmail.com**  

    Или пишите мне напрямую:  
    💬 [t.me/ValerkaIT](https://t.me/ValerkaIT) 👨‍💻  
    """
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(func=lambda message: message.text == "Меню 📋")
@check_subscription_decorator(REQUIRED_CHANNEL)
def menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Новости 📢")
    item2 = types.KeyboardButton("Стикеры 🧸")
    item3 = types.KeyboardButton("Реклама 📢")
    back_button = types.KeyboardButton("Назад ↩️")
    markup.add(item1, item2, item3, back_button)
    bot.send_message(message.chat.id, "Выберите раздел:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Новости 📢")
@check_subscription_decorator(REQUIRED_CHANNEL)
def news(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_button = types.KeyboardButton("Назад ↩️")
    markup.add(back_button)
    text = """
    🤖 **Bot VER/1.0.3**

    🕹️ Игры выходят тогда, когда выходят.  
    📱 **Версии для мобильных платформ** есть не на все игры, но как только они выходят, я сразу выкладываю.

    ❓ **Вопросы и предложения** присылайте в чат или личные сообщения.  
    📲 Я слежу за каналом лично и всегда все просматриваю.

    👨‍💻 **Admin**
    """
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "Стикеры 🧸")
@check_subscription_decorator(REQUIRED_CHANNEL)
def stickers(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_button = types.KeyboardButton("Назад ↩️")
    markup.add(back_button)
    bot.send_message(message.chat.id, "https://t.me/addstickers/MurzilkaUSSR")


# Запуск бота
bot.polling(none_stop=True)
