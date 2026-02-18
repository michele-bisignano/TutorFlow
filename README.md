# 🎓 TutorFlow

**TutorFlow** is an intelligent automation system designed to streamline the administrative management of private tutoring sessions. The system automatically detects completed lessons from your calendar, requests confirmation via a Telegram Bot, and updates a cloud-based accounting ledger on Microsoft Excel (OneDrive).

## 🚀 Key Features
- **Automatic Sync:** Monitors Google Calendar for events tagged as "Ripetizioni" (Tutoring).
- **Interactive Telegram Interface:** Sends a notification at the end of each session to confirm attendance and log payment details.
- **Cloud Accounting:** Automatically updates an Excel spreadsheet hosted on OneDrive via the Microsoft Graph API.
- **Dynamic Calculation:** Supports automated pricing from a client list while allowing manual overrides for custom discounts or surcharges.
- **Balance Tracking:** Keeps track of paid lessons, partial payments, and outstanding balances in real-time.

## 🛠️ Tech Stack
- **Language:** Python 3.x
- **Google APIs:** Google Calendar API (for fetching lesson events).
- **Microsoft APIs:** Microsoft Graph API (for Excel/OneDrive integration).
- **Telegram Bot:** `python-telegram-bot` library (for user interaction and logic).
- **Deployment:** [Insert your cloud service here, e.g., PythonAnywhere / Railway / Render]

## 📁 Project Structure
- `src/services/`: Modules for external API integrations (Google, Microsoft).
- `src/bot/`: Telegram bot logic, command handling, and conversation flows.
- `src/utils/`: Helper functions for data formatting, date calculations, and price processing.
- `main.py`: The main entry point that orchestrates the polling and triggers.

## 🛠 Setup (Coming Soon)
*Instructions on how to configure API credentials, environment variables, and the virtual environment will be provided here.*

---
*Developed to spend less time on spreadsheets and more time teaching.*