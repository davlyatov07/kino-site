import asyncio
from telegram import Bot

async def set_wh():
    bot = Bot('8550706241:AAHFkE5voCV3aUbjGXZouSOkYw3OgHU3HIw')
    result = await bot.set_webhook('https://davlyatov.pythonanywhere.com/telegram-webhook/')
    print('Результат:', result)

asyncio.run(set_wh())