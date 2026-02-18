import os
import asyncio
from typing import Optional
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()

class TutorTelegramBot:
    """
    @brief Gestore delle comunicazioni via Telegram per TutorFlow.
    """
    def __init__(self):
        self.token: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id: str = os.getenv('TELEGRAM_CHAT_ID', '')
        self.bot: Bot = Bot(token=self.token)

    async def send_confirmation_request(self, student: str, duration: str) -> bool:
        """
        @brief Invia un messaggio con bottoni per confermare la lezione.
        
        @param student: Nome dello studente (dal sommario del calendario).
        @param duration: Durata calcolata della lezione.
        @return bool: True se il messaggio è stato inviato con successo.
        """
        text = (
            f"🎓 *Lezione Terminata!*\n\n"
            f"👤 *Studente:* {student}\n"
            f"⏳ *Durata:* {duration}\n\n"
            f"Hai effettivamente svolto questa lezione?"
        )
        
        # Creazione bottoni inline
        keyboard = [
            [
                InlineKeyboardButton("✅ Sì", callback_data=f"confirm_yes|{student}"),
                InlineKeyboardButton("❌ No", callback_data="confirm_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            print(f"❌ Errore invio Telegram: {e}")
            return False

# Test rapido del modulo
if __name__ == "__main__":
    async def test():
        bot = TutorTelegramBot()
        await bot.send_confirmation_request("Giovanni (Test)", "1h 30min")
    
    asyncio.run(test())