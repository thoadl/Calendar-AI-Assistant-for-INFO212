# 📅 AI Calendar Assistant

An intelligent calendar management system that syncs with Google Calendar and uses AI to help you manage your schedule through natural language conversations.

**Features:**
- 🤖 Chat with AI about your schedule
- 📆 Two-way Google Calendar sync
- ✏️ Add, update, or delete events using natural language
- 📊 Day, week, and month calendar views
- 🎨 Dark mode support

---

## 🚀 Setup

### Prerequisites
- Python 3.8+
- OpenAI API key (Described in the assignment document file)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://git.app.uib.no/alicia.carretero/system-development.git
   cd system-development
   ```

   OR

   ```bash
   git clone https://github.com/thoadl/Calendar-AI-Assistant-for-INFO212.git
   cd Calendar-AI-Assistant-for-INFO212
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib openai flask flask-cors
   ```

4. **Set up environment variables**

Consult the assignment file


6. **Start the application**
   ```bash
   # Start Flask backend
   python app.py
   
   # Open index.html in your browser
   # The app will prompt you to authenticate with Google Calendar
   ```

---

## 🔑 Google Calendar Credentials

Consult the assignment file

## 💬 Usage Examples

**Chat Mode:**
- "What do I have tomorrow?"
- "Am I free on Friday afternoon?"

**Actions Mode:**
- "Add lunch with Sarah tomorrow at noon"
- "Delete all meetings on Friday"
- "Move my 2pm meeting to 3pm"

---

## 📁 Project Structure

```
├── app.py                  # Flask backend
├── index.html             # Web interface
├── styles.css             # Styling
├── GoogleCalendarSync.py  # Calendar sync logic
├── oop_events.py         # Event management
├── openAIAPI.py          # AI integration
└── credentials.json      # Google API credentials
```

---



## 🐛 Troubleshooting

**"OPENAI_API_KEY not set"**
- Make sure `.env` exists with your API key
- Restart the Flask server


**Port already in use**
- Kill existing process or change port in `app.py`
