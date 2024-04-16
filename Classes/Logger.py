import os
import contextlib
from datetime import datetime
import aiologger
from aiologger.handlers.files import AsyncFileHandler
from aiologger.levels import LogLevel
import inspect


class Logger:
    def __init__(self, log_level=LogLevel.INFO):
        self.log_level = log_level
        self.logs_folder = 'logs'
        self.create_logs_folder()
        self.logger = aiologger.Logger.with_default_handlers(name=__name__)
        self.set_logger_level()

        # Создаем обработчик файла при создании объекта логгера
        self.current_date = datetime.now().strftime('%Y-%m-%d')
        self.add_file_handler()

    def create_logs_folder(self):
        with contextlib.suppress(FileExistsError):
            os.makedirs(self.logs_folder)

    def set_logger_level(self):
        self.logger.level = self.log_level

    def add_file_handler(self):
        log_file = os.path.join(self.logs_folder, f'{self.current_date}.log')
        handler = AsyncFileHandler(filename=log_file)
        self.logger.handlers.clear()  # Очищаем все существующие обработчики
        self.logger.add_handler(handler)

    def format_log_message(self, message, level, caller_info=None):
        caller_info_str = f"{caller_info}" if caller_info else "Unknown"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return f"{timestamp} - {level.name} - {caller_info_str} - {message}"

    async def log(self, message, level=LogLevel.INFO):
        current_date = datetime.now().strftime('%Y-%m-%d')
        if current_date != self.current_date:
            # Если сменилась дата, создаем новый файл лога и обновляем обработчик файлового журнала
            self.current_date = current_date
            self.add_file_handler()

        log_message = self.format_log_message(message, level, self.get_caller_info())
        log_level = getattr(self.logger, level.name.lower(), None)

        if log_level:
            await log_level(log_message)

    def get_caller_info(self):
        stack = inspect.stack()
        if len(stack) > 2:
            frame = stack[2][0]
            module = inspect.getmodule(frame)
            if module:
                return f"{module.__name__}.{frame.f_code.co_name}"
        return None


# Пример использования
async def main():
    logger = Logger()
    await logger.log('Запускаем фоновую задачу...')


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
