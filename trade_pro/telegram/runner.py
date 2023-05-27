import logging

from trade_pro.telegram.bot import telegram_app

logger = logging.getLogger(__name__)


def run():
    logger.info("initialising telegram bot")
    telegram_app.run_polling()
