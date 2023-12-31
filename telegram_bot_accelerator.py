import json
from typing import Union, TypedDict
import requests
from telegram import __version__ as TG_VER
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import os
from logger import logger
from dotenv import load_dotenv

# bot_name = @harrypotter_gryf_bot

"""
start - Start the bot
set_engine - To choose the engine 
set_language - To choose language of your choice
"""

load_dotenv()

bot = Bot(token=os.environ['token'])
TELEGRAM_BOT_NAME=os.environ["botName"]
try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_name = update.message.chat.first_name
    logger.info({"id": update.effective_chat.id,"username": user_name, "category": "logged_in", "label": "logged_in"})
    tBotName = os.environ['botName']
    await bot.send_message(chat_id=update.effective_chat.id, text=f'Hi {user_name}, welcome to {tBotName} bot')
    await relay_handler(update, context)


async def relay_handler(update: Update, context: CallbackContext):
    # setting engine manually
    context.user_data['engine'] = 'engine_langchain_gpt4'
    engine = context.user_data.get('engine')
    language = context.user_data.get('language')

    if engine is None:
        await engine_handler(update)
    elif language is None:
        await language_handler(update)


async def engine_handler(update: Update):
    langchain_gpt3_button = InlineKeyboardButton('Langchain-GPT3', callback_data='engine_langchain_gpt3')
    langchain_gpt4_button = InlineKeyboardButton('Langchain-GPT4', callback_data='engine_langchain_gpt4')

    inline_keyboard_buttons = [[langchain_gpt3_button], [langchain_gpt4_button]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard_buttons)

    await update.message.reply_text("Choose an engine:", reply_markup=reply_markup)


async def preferred_engine_callback(update: Update, context: CallbackContext):
    callback_query = update.callback_query
    preferred_engine = callback_query.data
    context.user_data['engine'] = preferred_engine
    preferred_engine_name = 'Langchain GPT3' if preferred_engine == 'engine_langchain_gpt3' else 'Langchain GPT4'

    await bot.send_message(chat_id=update.effective_chat.id, text=f'You have chosen {preferred_engine_name} engine.')
    await relay_handler(update, context)


async def language_handler(update: Update):
    inline_keyboard_buttons = [
        [InlineKeyboardButton('English', callback_data='lang_en')], [InlineKeyboardButton('বাংলা', callback_data='lang_bn')], 
        [InlineKeyboardButton('ગુજરાતી', callback_data='lang_gu')], [InlineKeyboardButton('हिंदी', callback_data='lang_hi')],
        [InlineKeyboardButton('ಕನ್ನಡ', callback_data='lang_kn')], [InlineKeyboardButton('മലയാളം', callback_data='lang_ml')],
        [InlineKeyboardButton('मराठी', callback_data='lang_mr')], [InlineKeyboardButton('ଓଡ଼ିଆ', callback_data='or')],
        [InlineKeyboardButton('ਪੰਜਾਬੀ', callback_data='lang_pa')], [InlineKeyboardButton('தமிழ்', callback_data='lang_ta')],
        [InlineKeyboardButton('తెలుగు', callback_data='lang_te')]
        ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard_buttons)

    await bot.send_message(chat_id=update.effective_chat.id, text="Choose a Language:", reply_markup=reply_markup)


async def preferred_language_callback(update: Update, context: CallbackContext):
    # setting engine manually
    context.user_data['engine'] = 'engine_langchain_gpt4'
    logger.info({"id":update.effective_chat.id ,"username": update.effective_chat.first_name, "category": "engine_selection", "label": "engine_selection", "value": context.user_data['engine']})
    callback_query = update.callback_query
    preferred_language = callback_query.data.lstrip('lang_')
    context.user_data['language'] = preferred_language
    if os.environ.get('promptMsg'):
        prompt_msg=os.environ.get('promptMsg')
    else:
        prompt_msg='Give your query now'
    logger.info({"id":update.effective_chat.id ,"username": update.effective_chat.first_name, "category": "language_selection", "label": "engine_selection", "value": preferred_language})
    await bot.send_message(chat_id=update.effective_chat.id, text=f'You have chosen {preferred_language}. \n{prompt_msg}')
    return query_handler


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


class ApiResponse(TypedDict):
    output: any

class ApiError(TypedDict):
    error: Union[str, requests.exceptions.RequestException]


async def get_query_response(engine: str, query: str, voice_message_url: str, voice_message_language: str) -> Union[ApiResponse, ApiError]:
    _domain = os.environ['upstream']
    try:
        if voice_message_url is None:
            reqBody = json.dumps({
                "input": {
                    "language": voice_message_language,
                    "text": query
                },
                "output": {
                    'format': 'text'
                }
            })
        else:
            reqBody = json.dumps({
                "input": {
                    "language": voice_message_language,
                    "audio": voice_message_url
                },
                "output": {
                    'format': 'audio'
                }
            })
        url = f'{_domain}/v1/query'
        response = requests.post(url, data=reqBody)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return {'error': e}
    except (KeyError, ValueError):
        return {'error': 'Invalid response received from API'}


async def response_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await query_handler(update, context)


async def query_handler(update: Update, context: CallbackContext):
    engine = context.user_data.get('engine')
    voice_message_language = context.user_data.get('language') or 'en'
    voice_message = None
    query = None

    if update.message.text:
        query = update.message.text
        logger.info({"id":update.effective_chat.id ,"username": update.effective_chat.first_name, "category": "query_handler", "label": "question", "value": query})
    elif update.message.voice:
        voice_message = update.message.voice

    voice_message_url = None
    if voice_message is not None:
        voice_file = await voice_message.get_file()
        voice_message_url = voice_file.file_path
        logger.info({"id":update.effective_chat.id ,"username": update.effective_chat.first_name, "category": "query_handler", "label": "voice_question", "value": voice_message_url})

    await bot.send_message(chat_id=update.effective_chat.id, text=f'Just a few seconds...')

    await handle_query_response(update, query, voice_message_url, voice_message_language, engine)
    return query_handler


async def handle_query_response(update: Update, query: str, voice_message_url: str, voice_message_language: str,
                                engine: str):
    response = await get_query_response(engine, query, voice_message_url, voice_message_language)
    if "error" in response:
        await bot.send_message(chat_id=update.effective_chat.id,
                               text='An error has been encountered. Please try again.')
        info_msg = {"id":update.effective_chat.id ,"username": update.effective_chat.first_name, "category": "handle_query_response", "label": "question_sent", "value": query}
        logger.info(info_msg)
        merged = dict()
        merged.update(info_msg)
        merged.update(response)
        logger.error(merged)
    else:
        logger.info({"id":update.effective_chat.id ,"username": update.effective_chat.first_name, "category": "handle_query_response", "label": "answer_received", "value": query})
        answer = response['output']["text"]
        await bot.send_message(chat_id=update.effective_chat.id, text=answer)

        if response['output']['audio']:
            audio_output_url = response['output']["audio"]
            audio_request = requests.get(audio_output_url)
            audio_data = audio_request.content
            await bot.send_voice(chat_id=update.effective_chat.id, voice=audio_data)


def main() -> None:
    logger.info('################################################')
    logger.info('# Telegram bot name %s', os.environ['botName'])
    logger.info('################################################')
    application = ApplicationBuilder().bot(bot).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # engine_handler_command = CommandHandler('set_engine', engine_handler)
    # application.add_handler(engine_handler_command)

    language_handler_command = CommandHandler('set_language', language_handler)
    application.add_handler(language_handler_command)

    # application.add_handler(CallbackQueryHandler(preferred_engine_callback, pattern=r'engine_\w*'))
    application.add_handler(CallbackQueryHandler(preferred_language_callback, pattern=r'lang_\w*'))

    application.add_handler(MessageHandler(filters.TEXT | filters.VOICE, response_handler))

    application.run_polling()


if __name__ == "__main__":
    main()
