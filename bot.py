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


class ChatMemory:
    """
    Класс для хранения истории сообщений пользователей в оперативной памяти.
    Ограничивает количество хранимых сообщений для каждого пользователя.
    """
    def __init__(self, max_history_size: int = 20):
        self.max_history_size = max_history_size
        self.histories: dict[int, list[dict[str, str]]] = {}

    def add_message(self, user_id: int, role: str, content: str) -> None:
        if user_id not in self.histories:
            self.histories[user_id] = []
        self.histories[user_id].append({"role": role, "content": content})
        if len(self.histories[user_id]) > self.max_history_size:
            self.histories[user_id].pop(0)

    def get_history(self, user_id: int) -> list[dict[str, str]]:
        return self.histories.get(user_id, [])

chat_memory = ChatMemory(max_history_size=20)


@dp.message(F.text)
async def handle_message(message: Message) -> None:
    user_id = message.from_user.id
    user_text = message.text
    logger.info("Получено сообщение от %s: %s", user_id, user_text)

    chat_memory.add_message(user_id, "user", user_text)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_memory.get_history(user_id)

    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            extra_headers={"X-Title": "telegram-local-bot"},
            extra_body={"reasoning": {"enabled": True}},
        )
        reply = response.choices[0].message.content
        chat_memory.add_message(user_id, "assistant", reply)
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
