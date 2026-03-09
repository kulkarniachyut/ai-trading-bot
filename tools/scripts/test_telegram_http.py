import asyncio

from shared.utils.config import load_config
from shared.delivery.telegram import init_telegram, send_message, shutdown_telegram, escape_md

async def main() -> None:
    config = load_config()
    await init_telegram(config)

    text = escape_md("Real HTTP test from ai-trading-bot ✅")
    ok = await send_message(config.telegram.india_chat_id, text)
    print("send_message ok:", ok)

    await shutdown_telegram()

if __name__ == "__main__":
    asyncio.run(main())