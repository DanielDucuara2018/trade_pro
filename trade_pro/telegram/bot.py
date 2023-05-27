import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from trade_pro.telegram.telegram import telegram_app

logger = logging.getLogger(__name__)


async def help_command(
    update_handler: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Displays info on how to use the bot."""
    logger.info(f"Launching help command")
    await update_handler.message.reply_text("Use /start to test this bot.")


telegram_app.add_handler(CommandHandler("help", help_command))
