from __future__ import print_function
import datetime
import json
import os.path
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete token.json and re-run.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarExporter:
    def __init__(
        self,
        scopes: Optional[List[str]] = None,
        token_file: str = "token.json",
        credentials_file: str = "credentials.json",
        export_file: str = "calendar_export.json",
    ) -> None:
        self.scopes = scopes or SCOPES
        self.token_file = token_file
        self.credentials_file = credentials_file
        self.export_file = export_file
        self.creds: Optional[Credentials] = None
        self.service = None

    def authenticate(self) -> Credentials:
        """Return valid credentials, refreshing or prompting as needed."""
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
        if self.service:
            return self.service
        self.service = build("calendar", "v3", credentials=self.authenticate())
        return self.service

    def fetch_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = "2019-01-01T00:00:00Z",
        max_results: int = 2500,
    ) -> List[dict]:
        service = self.build_service()
        effective_time_min = time_min or datetime.datetime.utcnow().isoformat() + "Z"

        print("Fetching events from Google Calendar...")
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=effective_time_min,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return events_result.get("items", [])

    def export(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = "2019-01-01T00:00:00Z",
        max_results: int = 2500,
    ) -> List[dict]:
        events = self.fetch_events(calendar_id, time_min, max_results)
        with open(self.export_file, "w", encoding="utf-8") as export_target:
            json.dump(events, export_target, indent=2, ensure_ascii=False)
        print(f"Exported {len(events)} events to {self.export_file}")
        return events

    def run(self) -> None:
        """Kick off authentication and export using default settings."""
        self.export()


def main():
    exporter = GoogleCalendarExporter()
    exporter.run()
    return exporter.service


if __name__ == "__main__":
    main()
