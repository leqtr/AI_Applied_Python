import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

### логирование в консоль
formatter = logging.Formatter("%(asctime)s - INFO - %(log_type)s: %(content)s", datefmt="%Y-%m-%d %H:%M:%S")
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger = logging.getLogger("bot_logger")
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        log_data = {"log_type": "", "content": ""}

        if isinstance(event, Message) and event.text:
            log_data["log_type"] = "Text"
            log_data["content"] = event.text
        elif isinstance(event, CallbackQuery) and event.data:
            log_data["log_type"] = "Button"
            log_data["content"] = event.data

        if log_data["log_type"]: ### только текст или кнопки в боте
            logger.info("", extra=log_data)

        return await handler(event, data)
