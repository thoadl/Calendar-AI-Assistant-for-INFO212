from __future__ import print_function
import datetime
import json
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete token.json and re-run.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def main():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)

    # Get all events (adjust time range as needed)
    now = datetime.datetime.utcnow().isoformat() + "Z"
    print("Fetching events from Google Calendar...")

    events_result = service.events().list(
        calendarId="primary",
        timeMin="1970-01-01T00:00:00Z",  # start from the beginning
        maxResults=2500,                 # max per call
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])

    # Save to JSON file
    with open("calendar_export.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(events)} events to calendar_export.json")

if __name__ == "__main__":
    main()
