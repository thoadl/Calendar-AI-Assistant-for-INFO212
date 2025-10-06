# System Development



## Getting started with the terminal app

To get started you need some packages from Google and OpenAI installed:

run this to get
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib openai

Once the repo is pulled and the libraries are installed you can run the Calendar_Terminal_app.py in your IDE for a terminal based interface.
This app will open a browser window to sign in to google and allow the app access to your calendar (Google account is necessary for this, and it might be unstable in firefox)(Files are stored only locally on your device)
A Google account with a sample calendar has been set up for testing the app, with these credentials:
sd9872163@gmail.com
:J1"zJ:yIw\xD4hueQtn
If you want to test with your own Google account, send me an e-mail at thadl2832@uib.no with your Google accounts e-mail address, and I can give you access.

Once signed in you get some choices; 
1. Ask about your calendar or get a summary: Only returns a natural language answer, is unable to make changes to your google calendar
2. Request changes (AI will propose add/update/delete): Only returns JSON formatted data following a set schema, allows for doing changes to your calendar
3. Exit: Exits the app

