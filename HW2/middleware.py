import logging
import sys
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - User ID: %(user_id)s - Text: %(text)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]  # Use stdout for logs
)

class LoggingMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: Message, data: dict):
        logging.info("", extra={"user_id": message.from_user.id, "text": message.text})

    async def on_pre_process_callback_query(self, callback: CallbackQuery, data: dict):
        logging.info("", extra={"user_id": callback.from_user.id, "text": callback.data})