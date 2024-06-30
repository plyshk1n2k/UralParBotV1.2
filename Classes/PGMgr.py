import aiopg
import psycopg2
from Classes.Logger import Logger, LogLevel
from config import *


class PGMgr:
    def __init__(self):
        self.pg_con = None
        self.pg_user = PG_USER
        self.pg_pass = PG_PASS
        self.pg_host = PG_HOST
        self.pg_port = PG_PORT
        self.database = DATABASE
        self.database_test = DATABASE_TEST
        self.logger = Logger()

    async def connect_to_db(self):
        dsn = f'dbname={self.database} user={self.pg_user} password={self.pg_pass} host={self.pg_host}'
        try:
            self.pg_con = await aiopg.create_pool(dsn)
            async with self.pg_con.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute('SELECT version()')
                    version = await cur.fetchone()
                    await self.logger.log(f"Вы подключены к - {version}", level=LogLevel.INFO)
            return True
        except (Exception, psycopg2.Error) as e:
            await self.logger.log(f"Ошибка при подключении к базе данных: {e}", level=LogLevel.ERROR)
            return False

    async def close_db_connection(self):
        try:
            if hasattr(self, 'pg_con') and self.pg_con:
                self.pg_con.close()
                await self.pg_con.wait_closed()
                await self.logger.log(f"Соединение с базой данных закрыто", level=LogLevel.INFO)
        except (Exception, psycopg2.Error) as e:
            await self.logger.log(f"Ошибка при закрытии соединения с базой данных: {e}", level=LogLevel.ERROR)
            raise

    async def execute_query(self, query, *args, fetch_all: bool = False):
        try:
            async with self.pg_con.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, args)
                    if fetch_all:
                        return await cur.fetchall()
                    else:
                        return await cur.fetchone()

        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка выполнения запроса: {error}", level=LogLevel.ERROR)
            return None

    async def create_user(self, tg_id, role_id, user_name, first_name, last_name, language_code, is_bot):
        try:
            user_row = (tg_id, role_id, user_name, first_name, last_name, language_code, is_bot)
            insert_user_query = """INSERT INTO users (tg_id, role_id, user_name, first_name, last_name, language_code, is_bot) 
                                   VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *"""
            result = await self.execute_query(insert_user_query, *user_row)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка добавления пользователя: {tg_id} - {error}", level=LogLevel.ERROR)
            return None

    async def create_card(self, user_id, balance, file_id):
        try:
            card_row = (user_id, balance, file_id)
            insert_card_query = """INSERT INTO cards (user_id, balance, file_id) VALUES (%s, %s, %s) RETURNING *"""
            result = await self.execute_query(insert_card_query, *card_row)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка добавления карты пользователя: {user_id} - {error}", level=LogLevel.ERROR)
            return None

    async def add_store(self, uid: str, name: str) -> None | list:
        try:
            store_row = (uid, name)
            insert_store_query = """INSERT INTO stores (uid, name) VALUES (%s, %s) 
                                    ON CONFLICT (uid) DO UPDATE
                                    SET name = EXCLUDED.name
                                    RETURNING *"""
            result = await self.execute_query(insert_store_query, *store_row)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка добавления склада: {uid} {name} - {error}", level=LogLevel.ERROR)
            return None

    async def add_uom(self, uid: str, name: str, description: str) -> None | list:
        try:
            uom_row = (uid, name, description)
            insert_uom_query = """INSERT INTO uoms (uid, name, description) VALUES (%s, %s, %s) 
                                  ON CONFLICT (uid) DO UPDATE
                                  SET name = EXCLUDED.name, description = EXCLUDED.description
                                  RETURNING *"""
            result = await self.execute_query(insert_uom_query, *uom_row)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка добавления единицы измерения: {uid} {name} - {error}", level=LogLevel.ERROR)
            return None

    async def add_product_folder(self, uid: str, parent_uid: str | None, name: str) -> None | list:
        try:
            product_folder_row = (uid, parent_uid, name)
            insert_product_folder_query = """INSERT INTO product_groups (uid, parent_uid, name) VALUES (%s, %s, %s) 
                                             ON CONFLICT (uid) DO UPDATE
                                             SET parent_uid = EXCLUDED.parent_uid, name = EXCLUDED.name
                                             RETURNING *"""
            result = await self.execute_query(insert_product_folder_query, *product_folder_row)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка добавления группы товаров: {uid} {name} - {error}", level=LogLevel.ERROR)
            return None

    async def add_product(self, uid: str, group_uid: str, uom_uid: str, name: str, buy_price: float | int,
                          sales_price: float | int) -> None | list:
        try:
            uom = await self.get_uom(uom_uid)
            if not uom:
                uom_uid = None

            product_row = (uid, group_uid, uom_uid, name, buy_price, sales_price)
            insert_product_query = """INSERT INTO products (uid, group_uid, uom_uid, name, buy_price, sales_price) 
                                      VALUES (%s, %s, %s, %s, %s, %s) 
                                      ON CONFLICT (uid) DO UPDATE
                                      SET group_uid = EXCLUDED.group_uid, uom_uid = EXCLUDED.uom_uid, 
                                          name = EXCLUDED.name, buy_price = EXCLUDED.buy_price, 
                                          sales_price = EXCLUDED.sales_price
                                      RETURNING *"""
            result = await self.execute_query(insert_product_query, *product_row)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка добавления товара: {uid} {name} - {error}", level=LogLevel.ERROR)
            return None

    async def add_product_remains(self, product_uid: str, store_uid: str, count: float | int) -> None | list:
        try:
            product_remains_row = (product_uid, store_uid, count)
            insert_product_remains_query = """INSERT INTO product_remains (product_uid, store_uid, count) 
                                      VALUES (%s, %s, %s) 
                                      ON CONFLICT (product_uid, store_uid) DO UPDATE
                                      SET count = EXCLUDED.count
                                      RETURNING *"""
            result = await self.execute_query(insert_product_remains_query, *product_remains_row)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка добавления остатка товара product_uid: {product_uid}, "
                                  f"store_uid: {store_uid} - {error}", level=LogLevel.ERROR)
            return None

    async def add_bonus_operation(self, card_id, operation_id, moment_operation, points_earned) -> None | list:
        try:
            bonus_operation_row = (operation_id, card_id, points_earned, moment_operation)
            insert_bonus_operation_query = """INSERT INTO bonus_operations (operation_id, card_id, points_earned, 
                                                                            moment_operation) 
                                              VALUES (%s, %s, %s, %s) 
                                              ON CONFLICT (operation_id) DO NOTHING 
                                              RETURNING *"""
            result = await self.execute_query(insert_bonus_operation_query, *bonus_operation_row)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка добавления бонусной операции: {operation_id}, "
                                  f"card_id: {card_id} - {error}", level=LogLevel.ERROR)
            return None

    async def get_role(self, role_name):
        try:
            get_role_query = """SELECT * FROM roles WHERE role = %s"""
            result = await self.execute_query(get_role_query, role_name)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка получения роли: {role_name} - {error}", level=LogLevel.ERROR)
            return None

    async def get_user(self, tg_id):
        try:
            get_user_query = """SELECT * FROM users WHERE tg_id = %s"""
            result = await self.execute_query(get_user_query, tg_id)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка получения пользователя: {tg_id} - {error}", level=LogLevel.ERROR)
            return None

    async def get_card(self, user_id):
        try:
            get_card_query = """SELECT * FROM cards WHERE user_id = %s"""
            result = await self.execute_query(get_card_query, user_id)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка получения карты пользователя: {user_id} - {error}", level=LogLevel.ERROR)
            return None

    async def get_card_by_number(self, card_number):
        try:
            get_card_query = """SELECT * FROM cards WHERE uid = %s LIMIT 1"""
            result = await self.execute_query(get_card_query, card_number)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка получения карты: {card_number} - {error}", level=LogLevel.ERROR)
            return None

    async def get_uom(self, uid: str) -> None | list:
        try:
            get_uom_query = """SELECT * FROM uoms WHERE uid = %s"""
            result = await self.execute_query(get_uom_query, uid)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка получения единицы измерения uid: {uid} - {error}", level=LogLevel.ERROR)
            return None

    async def get_groups_by_parent(self, parent_uid: str | None, except_groups=None) -> None | list:
        if except_groups is None:
            except_groups = []
        try:
            where = 'WHERE parent_uid IS NULL' if not parent_uid else 'WHERE parent_uid = %s'
            params = () if not parent_uid else (parent_uid,)

            if except_groups:
                where += ' AND name NOT IN %s'
                params += (tuple(except_groups),)

            get_groups_query = f"""SELECT uid, name FROM product_groups {where}"""
            result = await self.execute_query(get_groups_query, *params, fetch_all=True)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка получения группы товаров parent_uid: {parent_uid} - {error}",
                                  level=LogLevel.ERROR)
            return None

    async def get_products_by_group(self, group_uid: str) -> list | None:
        try:
            get_products_query = """SELECT uid, name FROM products WHERE group_uid = %s"""
            result = await self.execute_query(get_products_query, group_uid, fetch_all=True)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка получения товаров по группе group_uid: {group_uid} - {error}",
                                  level=LogLevel.ERROR)
            return None

    async def get_product_remains(self, product_uid: str) -> list | None:
        try:
            get_products_query = """SELECT st.name, 
                                           pr.count 
                                      FROM product_remains pr
                                      JOIN stores st ON pr.product_uid = %s AND pr.store_uid = st.uid
                                     WHERE pr.count > 0"""
            result = await self.execute_query(get_products_query, product_uid, fetch_all=True)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка получения остатков товара product_uid: {product_uid} - {error}",
                                  level=LogLevel.ERROR)
            return None

    async def set_card_file_id(self, user_id, file_id):
        try:
            set_card_file_id_query = """UPDATE cards SET file_id = %s WHERE user_id = %s RETURNING *"""
            result = await self.execute_query(set_card_file_id_query, file_id, user_id)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка установки идентификатора файла карты пользователя: {user_id} - {error}",
                                  level=LogLevel.ERROR)
            return None

    async def set_card_balance(self, card_uid, balance):
        try:
            set_card_balance_query = """UPDATE cards SET balance = %s WHERE uid = %s RETURNING *"""
            result = await self.execute_query(set_card_balance_query, balance, card_uid)
            return result
        except (Exception, psycopg2.Error) as error:
            await self.logger.log(f"Ошибка установки баланса карты пользователя: {card_uid} - {error}",
                                  level=LogLevel.ERROR)
            return None
