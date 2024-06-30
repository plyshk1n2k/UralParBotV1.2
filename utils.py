import asyncio

from Classes.Logger import Logger
from Classes.Logger import LogLevel
from Classes.MoySkladAPI import MoyskladAPI


async def background_task():
    logger = Logger()
    try:
        await logger.log('Запускаем фоновую задачу...', level=LogLevel.INFO)
        async with MoyskladAPI() as api:
            while True:
                print('Получаем данные о клиентах')
                await api.get_counterparties(tag="клиент")
                await asyncio.sleep(60)
                print('Получаем данные о магазинах')
                await api.get_stores()
                await asyncio.sleep(60)
                print('Получаем данные о единицах измерения')
                await api.get_uoms()
                await asyncio.sleep(60)
                print('Получаем данные о группах товаров')
                await api.get_groups_product()
                await asyncio.sleep(60)
                print('Получаем данные о товарах')
                await api.get_products()
                await asyncio.sleep(60)
                print('Получаем данные об остатках на складах')
                await api.get_stock_by_stores()
                await asyncio.sleep(60)
                print('Получаем данные о бонусных операциях')
                await api.get_bonus_operations()
                print('Ожидаем следующего цикла')
                await asyncio.sleep(300)  # Пример: ждем 300 секунд между итерациями
    except asyncio.CancelledError:
        await logger.log('Background task is cancelled.', level=LogLevel.INFO)

if __name__ == '__main__':
    asyncio.run(background_task())