import time
from itertools import zip_longest

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


# Главное меню пользователя
def get_main_keyboard():
    # Добавляем кнопки
    btn1 = InlineKeyboardButton(text='💳Бонусная карта', callback_data='bonus_card')
    btn2 = InlineKeyboardButton(text='📋Ассортимент', callback_data='assortment')

    # Создаем inline клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn1, btn2]])
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
