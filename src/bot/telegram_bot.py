import os
import logging
import asyncio
from typing import Optional, Any, List, Dict
from dotenv import load_dotenv

# Import Telegram modules
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class TutorTelegramBot:
    """
    @class TutorTelegramBot
    @brief Core class to manage Telegram Bot communications for the TutorFlow project.
    
    @details This class initializes the Telegram Application and manages the 
             asynchronous flow between Calendar events and Excel logging. 
             It handles button clicks and text inputs to gather lesson data.
    """

    def __init__(self) -> None:
        """
        @brief Initializes the TutorTelegramBot instance and registers handlers.
        
        @details Sets up the shared results state, builds the Application, 
                 and registers both CallbackQueryHandlers (for buttons) and 
                 MessageHandlers (for text input like custom amounts).
        """
        self._token: Optional[str] = os.getenv('TELEGRAM_BOT_TOKEN')
        self._chat_id: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')
        
        # Shared state for the Orchestrator
        self._active_results: Dict[str, Any] = {}

        if not self._token or not self._chat_id:
            raise ValueError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env file.")

        self.application: Application[Any, Any, Any, Any, Any, Any] = (
            ApplicationBuilder()
            .token(self._token)
            .connect_timeout(30)
            .read_timeout(30)
            .build()
        )
        
        # Register Handlers
        self.application.add_handler(CallbackQueryHandler(self._handle_callbacks))
        # This handler catches text messages (numbers) when waiting for custom amounts
        self.application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self._handle_message))
        
        self.bot: Bot = self.application.bot
        logging.info("TutorTelegramBot successfully instantiated with Text Handlers.")

    async def _handle_callbacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        @brief Internal dispatcher for all button clicks.
        
        @param update: Update - Telegram update object.
        @param context: ContextTypes.DEFAULT_TYPE - Callback context.
        
        @details Manages the flow from confirmation (Yes/No) to payment choice.
                 If 'Custom Amount' is selected, it sets a state in user_data 
                 to wait for a text message.
        """
        query = update.callback_query
        if not query or not query.data:
            return

        await query.answer()
        data: str = str(query.data)

        # Logic 1: Lesson not held
        if data.startswith("confirm_no"):
            student = data.split("|")[1]
            await query.edit_message_text(f"❌ Lesson with {student} marked as NOT held.")
            self._active_results[student] = {"student": student, "held": False, "payment_status": "none", "amount": 0.0}

        # Logic 2: Lesson held -> Go to Payment choices
        elif data.startswith("confirm_yes"):
            await self._prompt_payment_status(update, context)

        # Logic 3: Payment - Standard or None
        elif data.startswith("pay_std") or data.startswith("pay_none"):
            action, student = data.split("|")
            status = "standard" if action == "pay_std" else "none"
            text_status = "Paid (Standard)" if status == "standard" else "Not Paid (0€)"
            await query.edit_message_text(f"✅ Recorded: {student} - {text_status}")
            
            self._active_results[student] = {"student": student, "held": True, "payment_status": status, "amount": 0.0}

        # Logic 4: Payment - Custom Amount requested
        elif data.startswith("pay_custom"):
            student = data.split("|")[1]
            # Set state: tell the bot that the next message from the user is an amount for THIS student
            context.user_data["waiting_for_amount_for"] = student # type: ignore
            await query.edit_message_text(f"🔢 Please type the exact amount paid by *{student}* (e.g. 35.50):", parse_mode=ParseMode.MARKDOWN)

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        @brief Processes text messages, specifically used for 'Custom Amount' input.
        
        @param update: Update - The update containing the user's text.
        @param context: ContextTypes.DEFAULT_TYPE - Context storing the current state.
        
        @details Checks if the bot is currently waiting for an amount for a student.
                 Validates that the input is a valid number. If valid, it updates 
                 the orchestrator results and clears the waiting state.
        """
        if not update.message or not update.message.text:
            return

        # Check if we are actually expecting a number for a student
        student = context.user_data.get("waiting_for_amount_for") # type: ignore

        if student:
            raw_text = update.message.text.replace(',', '.') # Handle European decimals
            
            try:
                amount = float(raw_text)
                await update.message.reply_text(f"✅ Recorded: {student} paid {amount}€.")
                
                # Update orchestrator results -> This breaks the wait loop
                self._active_results[student] = {
                    "student": student,
                    "held": True,
                    "payment_status": "custom",
                    "amount": amount
                }
                # Clear state
                context.user_data["waiting_for_amount_for"] = None # type: ignore
                
            except ValueError:
                await update.message.reply_text("❌ Invalid number. Please enter a value like '25' or '30.50':")
        else:
            # Optional: handle unexpected messages
            pass

    async def orchestrate_tutoring_sessions(
        self: "TutorTelegramBot", 
        students: List[str], 
        duration: str
    ) -> List[Dict[str, Any]]:
        """
        @brief Main orchestration loop for processing tutoring sessions.
        """
        logging.info(f"Starting orchestration for {len(students)} students.")
        results: List[Dict[str, Any]] = []

        for student in students:
            success = await self._send_single_lesson_confirmation(student, duration)
            if not success: continue
            
            # This loop effectively "pauses" here until _active_results[student] is set
            user_response = await self._wait_for_user_response(student)
            results.append(user_response)
            results[-1]["duration"] = duration # Ensure duration is kept

        return results

    async def _send_single_lesson_confirmation(self: "TutorTelegramBot", student: str, duration: str) -> bool:
        """
        @brief Helper to send the initial Yes/No confirmation message.
        """
        message_text: str = (
            "🎓 *Lezione Terminata!*\n\n"
            f"👤 *Studente:* {student}\n"
            f"⏳ *Durata:* {duration}\n\n"
            f"Hai svolto la lezione con *{student}*?"
        )
        keyboard = [[InlineKeyboardButton("✅ Yes", callback_data=f"confirm_yes|{student}"),
                     InlineKeyboardButton("❌ No", callback_data=f"confirm_no|{student}")]]
        
        try:
            await self.bot.send_message(chat_id=str(self._chat_id), text=message_text,
                                        parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
            return True
        except Exception as e:
            await self.send_error_report(e, context=f"Confirmation error for {student}")
            return False

    async def _prompt_payment_status(self: "TutorTelegramBot", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        @brief Updates the message to ask for the payment status.
        """
        query = update.callback_query
        if not query: return
        student_name = str(query.data).split("|")[1]
        
        keyboard = [
            [InlineKeyboardButton("✅ Paid (Standard)", callback_data=f"pay_std|{student_name}")],
            [InlineKeyboardButton("❌ Not Paid (0€)", callback_data=f"pay_none|{student_name}")],
            [InlineKeyboardButton("🔢 Custom Amount", callback_data=f"pay_custom|{student_name}")]
        ]

        await query.edit_message_text(
            text=f"💰 *Payment Confirmation*\n\nDid *{student_name}* pay for this session?",
            parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _wait_for_user_response(self: "TutorTelegramBot", student: str) -> Dict[str, Any]:
        """
        @brief Polling loop that waits for handlers to populate results for a student.
        """
        if student not in self._active_results:
            self._active_results[student] = None 
        while self._active_results.get(student) is None:
            await asyncio.sleep(1) 
        return self._active_results.pop(student)

    async def send_error_report(self, error: Exception, context: Optional[str] = None) -> None:
        """
        @brief Sends error details to Telegram.
        """
        error_text = f"🚨 *Error* [{context}]: `{error}`"
        try:
            await self.bot.send_message(chat_id=str(self._chat_id), text=error_text, parse_mode=ParseMode.MARKDOWN)
        except: logging.error(f"Telegram error report failed: {error}")

# --- Test Main ---
if __name__ == "__main__":
    async def test_main() -> None:
        tutor_bot = TutorTelegramBot()
        async with tutor_bot.application:
            await tutor_bot.application.start()
            await tutor_bot.application.updater.start_polling() # type: ignore
            
            print("\n🚀 TEST STARTED - Testing 'Custom Amount' for Giovanni")
            try:
                final_results = await tutor_bot.orchestrate_tutoring_sessions(
                    students=["Giovanni", "Francesco"], duration="1h 0min"
                )
                print(f"\n📊 FINAL RESULTS: {final_results}")
            finally:
                await tutor_bot.application.updater.stop() # type: ignore
                await tutor_bot.application.stop()

    asyncio.run(test_main())