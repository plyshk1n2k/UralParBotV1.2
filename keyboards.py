import time
from itertools import zip_longest

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


# Главное меню пользователя
def get_main_keyboard():
    # Добавляем кнопки
    btn1 = InlineKeyboardButton(text='💳Бонусная карта', callback_data='bonus_card')
    btn2 = InlineKeyboardButton(text='📋Ассортимент', callback_data='assortment')
    btn3 = InlineKeyboardButton(text='🌏Адреса магазинов', callback_data='addresses')

    # Создаем inline клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn1, btn2], [btn3]])
    return keyboard


# Возвращает на главное меню
def get_go_to_main_keyboard():
    # Добавляем кнопки
    btn1 = InlineKeyboardButton(text='⬅️Вернуться на главную', callback_data='go_to_main')

    # Создаем inline клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn1]])
    return keyboard


# Клавиатура подписки на канал
def get_subscribe_keyboard():
    # Добавляем кнопки
    btn1 = InlineKeyboardButton(text='📢Подписаться на канал', url=f'https://t.me/+OmT46KCal_tjNTYy')
    btn2 = InlineKeyboardButton(text='✔️Подписан(а)', callback_data='subscribed')
    btn3 = InlineKeyboardButton(text='⬅️Вернуться на главную', callback_data='go_to_main')

    # Создаем inline клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn1], [btn2], [btn3]])
    return keyboard


# Клавиатура подписки на канал
def get_dynamic_group_product_keyboard(groups: list):
    grouped_buttons = zip_longest(*[iter(groups)] * 2, fillvalue=None)
    keyboard_arr = [
        [InlineKeyboardButton(text=value, callback_data=value) for value in row if value]
        for row in grouped_buttons
    ]

    keyboard_arr.append([InlineKeyboardButton(text='⬅️Вернуться на главную', callback_data='go_to_main')])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_arr)

    # end_time = time.time()  # Замеряем время окончания выполнения
    # execution_time = end_time - start_time
    # print(f"Время выполнения функции: {execution_time} секунд")
    return keyboard


# Клавиатура списка магазинов
def get_shops_keyboard():
    # Создаем список магазинов с их координатами
    shops = [
        {"name": "Братьев Кашириных 110", "eng_name": "kashirka", "latitude": 55.177751, "longitude": 61.312398},
        {"name": "Блюхера 85", "eng_name": "bluhera", "latitude": 55.122854, "longitude": 61.364345},
        {"name": "250-летия Челябинска 67", "eng_name": "topolinka", "latitude": 55.165129, "longitude": 61.285950}
    ]
    buttons_arr = []
    # Создаем клавиатуру для отправки местоположения в каждый магазин
    for shop in shops:
        button_text = f"{shop['name']} 🏪"
        callback_data = f"location_{shop['latitude']}_{shop['longitude']}_{shop['eng_name']}"
        button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
        buttons_arr.append([button])
    buttons_arr.append([InlineKeyboardButton(text='⬅️Вернуться на главную', callback_data='go_to_main')])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons_arr)

    return keyboard


def get_go_back_to_addresses_keyboard():
    # Добавляем кнопки
    btn1 = InlineKeyboardButton(text='⬅️Вернуться к адресам', callback_data='go_back_to_addresses')
    btn2 = InlineKeyboardButton(text='⬅️Вернуться на главную', callback_data='go_to_main')

    # Создаем inline клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn1], [btn2]])
    return keyboard
