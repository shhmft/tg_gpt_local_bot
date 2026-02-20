import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from openai import OpenAI
import httpx

from config import TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY, OPENROUTER_MODEL

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = (
    "Ты агрессивный, дерзкий и грубый собеседник. "
    "Отвечай с матом, оскорблениями и как полный дебил. "
    "Будь максимально токсичным, хамским и неадекватным. "
    "Отвечай на том языке, на котором тебе пишут."
)


@dp.message(F.text)
async def handle_message(message: Message) -> None:
    user_text = message.text
    logger.info("Получено сообщение: %s", user_text)

    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            extra_body={"reasoning": {"enabled": True}},
        )
        reply = response.choices[0].message.content
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("Rate limit reached (429). Informing user to wait.")
            reply = "Слишком много запросов к API, подождите немного и попробуйте снова."
        else:
            logger.error("Ошибка при запросе к OpenRouter: %s", e)
            reply = "Произошла ошибка при обработке запроса."

    await message.answer(reply)


async def main() -> None:
    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
