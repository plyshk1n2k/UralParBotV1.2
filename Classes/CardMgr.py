import asyncio
import contextlib
import json
import os
from PIL import Image
import aiohttp
import aiofiles
import qrcode
from fake_useragent import UserAgent
import cairosvg
from Classes.Logger import Logger, LogLevel


class CardMgr:
    mode = 1  # 1 - create local | 2 - create with api
    size = 500
    user_agent = None
    save_path = 'qr'
    qr_file_name_result = ''
    logger = None
    session = None

    def __init__(self, mode: int):
        self.user_agent = UserAgent()
        self.mode = mode
        self.logger = Logger()

    async def __aenter__(self):
        # Создаем сессию при входе в контекст
        timeout = aiohttp.ClientTimeout(total=15, connect=10, sock_connect=10, sock_read=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Закрываем сессию при выходе из контекста
        if self.session and not self.session.closed:
            await asyncio.shield(self.session.close())
            self.session = None

    async def close(self):
        # Закрываем сессию в явном виде
        if self.session:
            await self.session.close()
            self.session = None

    async def run(self, qr_text: str) -> bool | str:
        await self.create_qr_folder()
        self.qr_file_name_result = f'{qr_text}.png'

        if self.mode == 1:
            await self.generate_local_qr(qr_text)
        elif self.mode == 2:
            url_image = await self.create_qr(qr_text)
            if url_image:
                await self.download_qr(url_image)

        if os.path.exists(os.path.join(self.save_path, self.qr_file_name_result)):
            return os.path.join(self.save_path, self.qr_file_name_result)
        else:
            return False

    async def create_qr(self, qr_text: str) -> str | bool:
        url = 'https://api.qrcode-monkey.com//qr/custom'
        logo = 'fbab5742d4184e88968674d0f2157bbe9d863207.jpeg'
        payload = {
            "data": qr_text,
            "config": {"body": "rounded-pointed", "eye": "frame14", "eyeBall": "ball16", "erf1": [], "erf2": ["fh"],
                       "erf3": ["fv"], "brf1": [], "brf2": ["fh"], "brf3": ["fv"], "bodyColor": "#000000",
                       "bgColor": "#FFFFFF", "eye1Color": "#3f6b2b", "eye2Color": "#3f6b2b", "eye3Color": "#3f6b2b",
                       "eyeBall1Color": "#60a541", "eyeBall2Color": "#60a541", "eyeBall3Color": "#60a541",
                       "gradientColor1": "#5c8b29", "gradientColor2": "#25492f", "gradientType": "radial",
                       "gradientOnEyes": 'false', "logo": logo,
                       "logoMode": "clean"},
            "size": self.size,
            "download": "imageUrl",
            "file": "png"
        }
        headers = {
            'User-Agent': self.user_agent.random,
            'authority': 'api.qrcode-monkey.com',
            'accept': '*/*',
            'accept-language': 'ru,en;q=0.9',
            'origin': 'https://www.qrcode-monkey.com',
            'referer': 'https://www.qrcode-monkey.com/',
            'sec-ch-ua': '"Chromium";v="118", "YaBrowser";v="23", "Not=A?Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            "content-type": "application/json",
        }

        try:
            async with self.session.post(url, json=payload, headers=headers, ssl=False) as response:
                response.raise_for_status()  # Поднимаем исключение в случае ошибки HTTP
                result = json.loads(await response.text())
                url_image: str = 'https:' + result['imageUrl']
                return url_image
        except aiohttp.ClientError as ce:
            await self.logger.log(f"Aiohttp ClientError: {ce}", LogLevel.ERROR)
        except asyncio.TimeoutError:
            await self.logger.log("Request timed out", LogLevel.ERROR)
        except Exception as e:
            await self.logger.log(f"Error fetching data: {e}", LogLevel.ERROR)

        return False

    async def download_qr(self, url: str) -> bool:
        try:
            async with self.session.get(url, ssl=False) as response:
                response.raise_for_status()  # Поднимаем исключение в случае ошибки HTTP
                file = await aiofiles.open(os.path.join(self.save_path, self.qr_file_name_result), mode='wb')
                await file.write(await response.read())
                await file.close()
                return True
        except aiohttp.ClientError as ce:
            await self.logger.log(f"Aiohttp ClientError: {ce}", LogLevel.ERROR)
        except asyncio.TimeoutError:
            await self.logger.log("Request timed out", LogLevel.ERROR)
        except Exception as e:
            await self.logger.log(f"Error fetching data: {e}", LogLevel.ERROR)

        return False

    async def svg_to_png(self, path_file: str, save_path: str) -> bool:
        try:
            cairosvg.svg2png(url=path_file, write_to=save_path, output_width=500, output_height=500)
            return True
        except Exception as error:
            await self.logger.log(f'Ошибка конвертации файла: {error}', level=LogLevel.ERROR)
            return False

    async def create_qr_folder(self):
        with contextlib.suppress(FileExistsError):
            os.makedirs(self.save_path)

    async def generate_local_qr(self, qr_text: str) -> None:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1,
        )
        qr.add_data(qr_text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#0070f0", back_color="white")
        img = img.resize((self.size, self.size), resample=Image.LANCZOS)  # Изменяем размер изображения
        img.save(os.path.join(self.save_path, self.qr_file_name_result))
