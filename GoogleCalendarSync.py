import os
import json
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarSync:
    def __init__(
        self,
        scopes: Optional[List[str]] = None,
        token_file: str = "token.json",
        credentials_file: str = "credentials.json",
        sync_file: str = "calendar_delta.json",
    ):
        self.scopes = scopes or SCOPES
        self.token_file = token_file
        self.credentials_file = credentials_file
        self.sync_file = sync_file
        self.creds: Optional[Credentials] = None
        self.service = None

    # ------------------- AUTHENTICATION -------------------
    def authenticate(self) -> Credentials:
        """Authenticate with Google and return valid credentials."""
        if self.creds and self.creds.valid:
            return self.creds

        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes
                )
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        self.creds = creds
        return creds

    def build_service(self):
        """Build the Google Calendar API service object."""
        if not self.service:
            self.service = build("calendar", "v3", credentials=self.authenticate())
        return self.service

    # ------------------- BASIC OPERATIONS -------------------
    def insert_event(self, event: dict, calendar_id="primary") -> dict:
        """Insert a new event into Google Calendar."""
        service = self.build_service()
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"✅ Inserted event: {created_event.get('summary')}")
        return created_event

    def update_event(self, event_id: str, event: dict, calendar_id="primary") -> dict:
        """Update an existing event by ID."""
        service = self.build_service()
        updated_event = service.events().update(
            calendarId=calendar_id, eventId=event_id, body=event
        ).execute()
        print(f"🔄 Updated event: {updated_event.get('summary')}")
        return updated_event

    def delete_event(self, event_id: str, calendar_id="primary") -> None:
        """Delete an event by ID."""
        service = self.build_service()
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        print(f"🗑️ Deleted event ID: {event_id}")

    # ------------------- CLEANING -------------------
    def clean_event(self, event: dict) -> dict:
        """Keep only safe fields for Google Calendar insert/update."""
        safe_fields = ["id", "summary", "start", "end", "description", "location", "attendees"]
        cleaned = {k: event[k] for k in safe_fields if k in event}

        # 🧹 Remove invalid attendees (no email)
        if "attendees" in cleaned:
            valid_attendees = [a for a in cleaned["attendees"] if "email" in a]
            if valid_attendees:
                cleaned["attendees"] = valid_attendees
            else:
                cleaned.pop("attendees", None)

        return cleaned


    def clean_delta_json(self, delta_json: dict) -> dict:
        """Clean add/update events in a delta JSON response from the AI."""
        cleaned = {
            "add": [self.clean_event(e) for e in delta_json.get("add", [])],
            "update": []
        }

        for e in delta_json.get("update", []):
            if "id" not in e:
                continue
            cleaned_event = {"id": e["id"]}
            cleaned_event.update(self.clean_event(e))
            cleaned["update"].append(cleaned_event)

        cleaned["delete"] = delta_json.get("delete", [])
        return cleaned

    # ------------------- APPLY DELTA JSON -------------------
    def apply_delta(self, calendar_id="primary", auto_delete=False) -> None:
        """Apply AI-generated delta JSON (add, update, delete)."""
        print(f"▶️ Applying delta from {self.sync_file}")

        if not os.path.exists(self.sync_file):
            raise FileNotFoundError(f"{self.sync_file} not found")

        with open(self.sync_file, "r", encoding="utf-8") as f:
            raw_delta = json.load(f)

        print("📂 Raw delta loaded:", raw_delta)
        delta = self.clean_delta_json(raw_delta)
        print("✨ Cleaned delta:", delta)
        
        # Handle adds
        for event in delta.get("add", []):
            print("🧾 Final event before insert:", json.dumps(event, indent=2))

            print("➡️ Adding:", event.get("summary"))
            self.insert_event(event, calendar_id)

        # Handle updates
        for event in delta.get("update", []):
            print("➡️ Updating:", event.get("summary"))
            if "id" in event:
                self.update_event(event["id"], event, calendar_id)
            else:
                print("⚠️ Skipped update — missing 'id' field.")

        # Handle deletions
        deletions = delta.get("delete", [])
        if not deletions:
            print("🟢 No deletions suggested.")
        else:
            if auto_delete:
                for event_id in deletions:
                    print("➡️ Deleting:", event_id)
                    self.delete_event(event_id, calendar_id)
            else:
                print("⚠️ Suggested deletions (not executed):", deletions)

        print("✅ Delta sync complete.")
