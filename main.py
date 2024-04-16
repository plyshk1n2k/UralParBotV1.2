from aiogram.enums import ChatMemberStatus, ParseMode
from config import *
from Classes.CardMgr import CardMgr
from Classes.PGMgr import PGMgr
from Classes.MoySkladAPI import MoyskladAPI
from Classes.Logger import Logger, LogLevel
from keyboards import *
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import FSInputFile, User
from answers import *

# TODO: Сейчас сообщения просто удалются,
# и бывает такое что происходит ошибка из за того что сообщение в чате более 48 часов
# нужно придумать что то получше

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Объект бота
bot = Bot(token=TOKEN_BOT)

# Диспетчер
dp = Dispatcher()

# Класс создающий карту пользователя
card_mgr = CardMgr(1)

# Класс работы с бд
db = PGMgr()

# Класс для логирования
logger = Logger()

# Переменная которая хранит кэш продуктов
product_cash = {}


# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await main_message_handler(message)


# Хэндлер всех сообщений
@dp.message(F.text)
async def message_handler(message: types.Message):
    await main_message_handler(message)


@dp.callback_query(lambda callback_query: True)
async def handle_callback_query(callback_query: types.CallbackQuery):
    query = callback_query.data
    tg_id = callback_query.from_user.id
    user = await db.get_user(tg_id)

    if not user or len(user) < 1:
        user = await registration_user(callback_query.from_user)

        if not user or len(user) < 1:
            await callback_query.answer(text=await get_error_phrase(), show_alert=True)
            await logger.log(f'Ошибка регистрации пользователя! tg_id - {callback_query.from_user.id}',
                             level=LogLevel.ERROR)
            return

    if query == 'bonus_card':
        await show_bonus_card(user, callback_query)
    elif query == 'assortment':
        await show_groups(callback_query, product_cash)
    elif query == 'go_to_main':
        try:
            await callback_query.message.delete()
        except Exception as error:
            await logger.log(error, LogLevel.ERROR)

        await callback_query.message.answer(
            text="Легко взаимодействуйте с ботом🤖, используя кнопки,\nразмещенные ⬇️под сообщением⬇️.",
            reply_markup=get_main_keyboard())
    elif query == 'subscribed':
        is_subscribed = await is_user_in_channel(callback_query.from_user.id, OWN_CHANEL_ID)
        if not is_subscribed:
            await bot.answer_callback_query(callback_query.id, text="Вы не найдены среди подписчиков канала. 📢")
        else:
            await bot.answer_callback_query(callback_query.id, text="Готовлю вашу карту 💳...")
            await show_bonus_card(user, callback_query)
    else:
        group_data = await find_values_by_key_async(product_cash, query)

        if group_data:
            await show_groups(callback_query, group_data=group_data)
        else:
            await bot.answer_callback_query(callback_query.id, text="Я не знаю такой команды🫥")


async def main_message_handler(message: types.Message):
    user_message = message.text.lower()
    tg_id = message.from_user.id
    user = await db.get_user(tg_id)

    if not user or len(user) < 1:
        user = await registration_user(message.from_user)

        if not user or len(user) < 1:
            await message.answer(await get_error_phrase())
            await logger.log(f'Ошибка регистрации пользователя! tg_id - {message.from_user.id}',
                             level=LogLevel.ERROR)
            return

    if user_message != '/start':
        try:
            await message.delete()
        except Exception as error:
            await logger.log(error, LogLevel.ERROR)
    await message.answer(
        text="Легко взаимодействуйте с ботом🤖, используя кнопки,\nразмещенные ⬇️под сообщением⬇️.",
        reply_markup=get_main_keyboard())


async def registration_user(user: User) -> tuple | None:
    tg_id = user.id
    user_name = user.username
    first_name = user.first_name
    last_name = user.last_name
    language_code = user.language_code
    is_bot = user.is_bot
    role = await db.get_role('USER')

    if not role or len(role) < 1:
        await logger.log(f'Не найдена роль USER', level=LogLevel.ERROR)
        return
    role_id = role[0]

    is_create = await db.create_user(tg_id, role_id, user_name, first_name, last_name, language_code, is_bot)
    return is_create


async def create_bonus_card(user: tuple) -> tuple | None:
    card = await db.create_card(user[0], 0, '')
    return card


async def show_bonus_card(user: tuple, callback_query: types.CallbackQuery) -> None:
    subscription_to_chanel = await is_user_in_channel(callback_query.from_user.id, OWN_CHANEL_ID)

    if not subscription_to_chanel:
        await bot.edit_message_text(text="Для создания бонусной карты 😊, "
                                         "необходимо подписаться на канал. 📢",
                                    chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    reply_markup=get_subscribe_keyboard())
        return

    card = await db.get_card(user[0])
    if not card or len(card) < 1:
        card = await create_bonus_card(user)
        if not card or len(card) < 1:
            await callback_query.answer(text=await get_error_phrase(), show_alert=True)
            await logger.log(f'Ошибка создания карты! tg_id - {callback_query.from_user.id}',
                             level=LogLevel.ERROR)
            return

    card_uid = card[1]
    card_balance = str(card[3]).replace('.', ',')
    card_file = card[4]
    caption = f"*Баланс: ||{card_balance} ₽||*"
    if card_file:
        try:
            await callback_query.message.delete()
        except Exception as error:
            await logger.log(error, LogLevel.ERROR)
        result = await bot.send_photo(chat_id=callback_query.message.chat.id, photo=card_file, caption=caption,
                                      reply_markup=get_go_to_main_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await bot.edit_message_text(text="Создаю Вашу карту 💳 ...\nПожалуйста ожидайте.",
                                    chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    reply_markup=get_go_to_main_keyboard())

        async with card_mgr as cm:
            download_card = await cm.run(str(card_uid))

        if not download_card:
            await callback_query.answer(text=await get_error_phrase(), show_alert=True)
            await logger.log(f'Ошибка скачивания карты! tg_id - {callback_query.from_user.id}',
                             level=LogLevel.ERROR)
            return

        card_photo = FSInputFile(download_card)
        try:
            await callback_query.message.delete()
        except Exception as error:
            await logger.log(error, LogLevel.ERROR)
        result = await bot.send_photo(chat_id=callback_query.message.chat.id, photo=card_photo, caption=caption,
                                      reply_markup=get_go_to_main_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)
        card_file_id = result.photo[len(result.photo) - 1].file_id
        await db.set_card_file_id(user[0], card_file_id)


async def show_groups(callback_query: types.CallbackQuery, group_data: dict | list) -> None:
    data_keyboard = {}

    replacement_dict = {
        '_': '\\_',
        '*': '\\*',
        '[': '\\[',
        ']': '\\]',
        '(': '\\(',
        ')': '\\)',
        '~': '\\~',
        '`': '\\`',
        '>': '\\>',
        '#': '\\#',
        '+': '\\+',
        '-': '\\-',
        '=': '\\=',
        '|': '\\|',
        '{': '\\{',
        '}': '\\}',
        '.': '\\.',
        '!': '\\!'
    }

    translation_table = str.maketrans(replacement_dict)
    text_msg = ('*Выберите интересующую группу товаров, используя кнопки, '
                'размещенные ⬇️под сообщением⬇️*')

    if group_data and isinstance(group_data, dict):
        data_keyboard = group_data.keys()
    elif group_data and isinstance(group_data, list):
        data_keyboard = group_data[0].get('subGroups', {})
        products = group_data[0].get('products', {})

        if products:
            text_msg = '\n'.join(
                '*' + str(product).translate(translation_table) + ':*\n' +
                '\n'.join(str('🏪' + key + ' - ' + str(value)).translate(translation_table)
                          for key, value in products.get(product, {}).items()) + '\n'
                for product in products.keys()
            )

    await bot.edit_message_text(
        text=text_msg,
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=get_dynamic_group_product_keyboard(data_keyboard),
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def create_groups_list(parent_uid: str | None) -> dict:
    groups = await db.get_groups_by_parent(parent_uid, ['NoMark'])

    if groups is None:
        await logger.log('Нет данных о группах товаров!', logger.log_level.WARN)
        return {}

    result = {
        group[1]: {
            'products': {
                product[1]: {
                    store[0]: int(store[1])
                    for store in await db.get_product_remains(product[0])
                    if store
                }
                for product in await db.get_products_by_group(group[0])
                if product and any(store for store in await db.get_product_remains(product[0]))
            },
            'subGroups': await create_groups_list(group[0])
        }
        for group in groups
        if await create_groups_list(group[0]) or any([
            product and any(store for store in await db.get_product_remains(product[0]))
            for product in await db.get_products_by_group(group[0])
        ])
    }
    result = dict(sorted(result.items()))
    return result


async def is_user_in_channel(user_id: int, chanel_id: int | str) -> bool:
    chat_member = await bot.get_chat_member(chanel_id, user_id)
    return chat_member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]


async def find_values_by_key_async(dictionary, target_key):
    result = []

    for key, value in dictionary.items():
        if key == target_key:
            result.append(value)

        if isinstance(value, dict):
            # Используем асинхронный вариант цикла for
            nested_values = await find_values_by_key_async(value, target_key)
            result.extend(nested_values)

    return result


async def background_task():
    try:
        await logger.log('Запускаем фоновую задачу...', level=LogLevel.INFO)
        async with MoyskladAPI() as api:
            while True:
                await api.get_counterparties(tag="клиент")
                await asyncio.sleep(60)
                await api.get_stores()
                await asyncio.sleep(60)
                await api.get_uoms()
                await asyncio.sleep(60)
                await api.get_groups_product()
                await asyncio.sleep(60)
                await api.get_products()
                await asyncio.sleep(60)
                await api.get_stock_by_stores()
                global product_cash
                product_cash = await create_groups_list(None)
                await asyncio.sleep(300)  # Пример: ждем 300 секунд между итерациями
    except asyncio.CancelledError:
        await logger.log('Background task is cancelled.', level=LogLevel.INFO)


# Запуск процесса поллинга новых апдейтов
async def main():
    tasks = []
    # Запускаем фоновую задачу и добавляем ее в список задач
    bg_task = asyncio.create_task(background_task())
    tasks.append(bg_task)

    try:
        is_connect_db = await db.connect_to_db()
        if is_connect_db is False:
            await logger.log('НЕ УДАЛОСЬ ПОДКЛЮЧИТЬСЯ К БД!!!', logger.log_level.ERROR)
            return False

        global product_cash
        product_cash = await create_groups_list(None)
        # await logger.log(product_cash)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, polling_timeout=8)
    finally:
        # В блоке finally закрываем все необходимые ресурсы
        await logger.log('Завершаем работу бота.', level=LogLevel.INFO)
        await db.close_db_connection()
        # Ожидаем завершения всех задач в списке
        bg_task.cancel()
        await asyncio.gather(bg_task, return_exceptions=True)


if __name__ == '__main__':
    asyncio.run(main())
