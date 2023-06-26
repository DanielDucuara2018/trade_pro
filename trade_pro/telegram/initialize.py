import logging

from telegram.ext import Application, PicklePersistence

from trade_pro.config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)


def init_telegram_bot_application() -> Application:
    logger.info("Initialising Telegram bot connection ")
    # We use persistence to demonstrate how buttons can still work after the bot was restarted
    # Create the Application and pass it your bot's token.
    return (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .persistence(PicklePersistence(filepath="arbitrarycallbackdatabot"))
        .arbitrary_callback_data(True)
        .build()
    )


telegram_app: Application = init_telegram_bot_application()
