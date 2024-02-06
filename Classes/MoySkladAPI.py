import aiohttp
import asyncio
from config import TOKEN_MS
from Classes.PGMgr import PGMgr
from Classes.Logger import Logger, LogLevel


class MoyskladAPI:
    BASE_URL = 'https://api.moysklad.ru/api/remap/1.2/entity/'
    REPORT_URL = 'https://api.moysklad.ru/api/remap/1.2/report/'
    COUNTERPARTY_URL = f'{BASE_URL}counterparty'
    STORES_URL = f'{BASE_URL}store'
    UOMS_URL = f'{BASE_URL}uom'
    PRODUCT_FOLDER_URL = f'{BASE_URL}productfolder'
    PRODUCTS_URL = f'{BASE_URL}product'
    STOCK_BY_STORE_URL = f'{REPORT_URL}stock/bystore'
    LIMIT = 1000

    def __init__(self):
        self.logger = Logger()
        self.token = TOKEN_MS
        self.session = None
        self.db = PGMgr()

    async def __aenter__(self):
        try:
            await self.initialize_session()
            await self.db.connect_to_db()
            return self
        except Exception as e:
            await self.logger.log(f"Error during initialization: {e}", LogLevel.ERROR)
            raise

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            await self.close_session()
            await self.db.close_db_connection()
        except Exception as e:
            await self.logger.log(f"Error during cleanup: {e}", LogLevel.ERROR)

    async def initialize_session(self):
        try:
            timeout = aiohttp.ClientTimeout(total=10, connect=5, sock_connect=5, sock_read=5)
            self.session = aiohttp.ClientSession(headers={'Authorization': f'Bearer {self.token}'})
        except aiohttp.ClientError as ce:
            await self.logger.log(f"Aiohttp ClientError during session initialization: {ce}", LogLevel.ERROR)
            raise

    async def close_session(self):
        try:
            if self.session:
                await self.session.close()
        except aiohttp.ClientError as ce:
            await self.logger.log(f"Aiohttp ClientError during session closing: {ce}", LogLevel.ERROR)
            raise

    async def fetch_data(self, url: str, params: dict = None):
        try:
            async with self.session.get(url, params=params, ssl=False) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as ce:
            await self.logger.log(f"Aiohttp ClientError: {ce}", LogLevel.ERROR)
        except asyncio.TimeoutError:
            await self.logger.log("Request timed out", LogLevel.ERROR)
        except Exception as e:
            await self.logger.log(f"Error fetching data: {e}", LogLevel.ERROR)

    async def process_counterparties(self, data):
        for item in data.get('rows', []):
            name = item.get('name', '')
            discount_card_number = item.get('discountCardNumber', '')
            sales_amount = item.get('salesAmount', 0)
            bonus_amount = item.get('bonusPoints', 0)

            if not discount_card_number or bonus_amount == 0 or len(str(discount_card_number)) > 11:
                continue

            await self.db.set_card_balance(discount_card_number, bonus_amount)

            # await self.logger.log(
            #     f"Name: {name}, Discount Card Number: {discount_card_number}, "
            #     f"Sales Amount: {sales_amount}, Bonus Points: {bonus_amount}", LogLevel.INFO
            # )

    async def process_stores(self, data):
        for item in data.get('rows', []):
            name = item.get('name', '')
            uid = item.get('id', '')

            if not name or not uid:
                continue

            await self.db.add_store(uid, name)

    async def process_uoms(self, data):
        for item in data.get('rows', []):
            name = item.get('name', '')
            description = item.get('description', '')
            uid = item.get('id', '')

            if not name or not uid:
                continue

            await self.db.add_uom(uid, name, description)

    async def process_product_folder(self, data):
        for item in data.get('rows', []):
            name = item.get('name', '')
            uid = item.get('id', '')
            parent_href: str = item.get('productFolder', {}).get('meta', {}).get('href', {})
            parent_uid = None
            if parent_href:
                parent_uid = parent_href.split('/')[-1]

            if not name or not uid:
                continue

            await self.db.add_product_folder(uid, parent_uid, name)

    async def process_products(self, data):
        for item in data.get('rows', []):
            uid = item.get('id', '')
            name = item.get('name', '')
            buy_price = item.get('buyPrice', {}).get('value', 0)
            sales_price = item.get('salePrices', [{}])[0].get('value', 0)
            group_href: str = item.get('productFolder', {}).get('meta', {}).get('href', {})
            group_uid = None
            uom_href: str = item.get('uom', {}).get('meta', {}).get('href', {})
            uom_uid = None

            if group_href:
                group_uid = group_href.split('/')[-1]

            if uom_href:
                uom_uid = uom_href.split('/')[-1]

            if not buy_price:
                buy_price = 0

            if not sales_price:
                sales_price = 0

            if not name or not uid or not group_uid:
                continue

            await self.db.add_product(uid, group_uid, uom_uid, name, buy_price, sales_price)

    async def process_stock_by_stores(self, data):
        for item in data.get('rows', []):
            product_href: str = item.get('meta', {}).get('href', '')
            product_uid = None
            stock_by_store = item.get('stockByStore', [])

            if product_href:
                product_uid = product_href.split('?')[0].split('/')[-1]

            if not product_uid or len(stock_by_store) < 1:
                continue

            stocks = [{
                "store_uid": store.get('meta', {}).get('href', '').split('/')[-1],
                "stock": store.get('stock', 0)
            } for store in stock_by_store]

            for store in stocks:
                store_uid = store.get('store_uid', '')
                stock = store.get('stock', 0)

                if not store_uid:
                    continue

                await self.db.add_product_remains(product_uid, store_uid, stock)

    async def get_counterparties(self, tag: str):
        params = {'filter': f'tags={tag}', 'limit': self.LIMIT}
        url = self.COUNTERPARTY_URL

        try:
            while url:
                response = await self.fetch_data(url, params)
                await self.process_counterparties(response)
                url = response.get('meta', {}).get('nextHref')
                params = {}

        except Exception as e:
            await self.logger.log(f"Error processing counterparties: {e}", LogLevel.ERROR)

    async def get_stores(self):
        params = {'limit': self.LIMIT}
        url = self.STORES_URL

        try:
            while url:
                response = await self.fetch_data(url, params)
                await self.process_stores(response)
                url = response.get('meta', {}).get('nextHref')
                params = {}

        except Exception as e:
            await self.logger.log(f"Error processing stores: {e}", LogLevel.ERROR)

    async def get_uoms(self):
        params = {'limit': self.LIMIT}
        url = self.UOMS_URL

        try:
            while url:
                response = await self.fetch_data(url, params)
                await self.process_uoms(response)
                url = response.get('meta', {}).get('nextHref')
                params = {}

        except Exception as e:
            await self.logger.log(f"Error processing uoms: {e}", LogLevel.ERROR)

    async def get_groups_product(self):
        params = {'limit': self.LIMIT}
        url = self.PRODUCT_FOLDER_URL

        try:
            while url:
                response = await self.fetch_data(url, params)
                await self.process_product_folder(response)
                url = response.get('meta', {}).get('nextHref')
                params = {}

        except Exception as e:
            await self.logger.log(f"Error processing product folder: {e}", LogLevel.ERROR)

    async def get_products(self):
        params = {'limit': self.LIMIT}
        url = self.PRODUCTS_URL

        try:
            while url:
                response = await self.fetch_data(url, params)
                await self.process_products(response)
                url = response.get('meta', {}).get('nextHref')
                params = {}

        except Exception as e:
            await self.logger.log(f"Error processing product: {e}", LogLevel.ERROR)

    async def get_stock_by_stores(self):
        params = {'limit': self.LIMIT, 'filter': 'stockMode=all', 'groupBy': 'product'}
        url = self.STOCK_BY_STORE_URL

        try:
            while url:
                response = await self.fetch_data(url, params)
                await self.process_stock_by_stores(response)
                url = response.get('meta', {}).get('nextHref')
                params = {}

        except Exception as e:
            await self.logger.log(f"Error processing stock by stores: {e}", LogLevel.ERROR)


# Пример использования
async def main():
    async with MoyskladAPI() as api:
        await api.get_stores()


if __name__ == '__main__':
    asyncio.run(main())
