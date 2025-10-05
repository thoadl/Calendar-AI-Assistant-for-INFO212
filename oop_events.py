from datetime import datetime, timedelta
import json
import os


class Event:
    """Represents a calendar event"""

    def __init__(self, title: str, start: datetime, end: datetime, source: str = "draft"):
        self.title = title
        self.start = start
        self.end = end
        self.source = source

    @staticmethod
    def from_dict(data: dict, source: str = "draft"):
        """Create an Event object from a JSON/dict representation"""
        start = data["start"].get("dateTime") or data["start"].get("date")
        end = data["end"].get("dateTime") or data["end"].get("date")
        return Event(
            title=data.get("summary", "Untitled"),
            start=datetime.fromisoformat(start),
            end=datetime.fromisoformat(end),
            source=source,
        )

    def to_dict(self) -> dict:
        """Convert event to Google Calendar API format"""
        return {
            "summary": self.title,
            "start": {"dateTime": self.start.isoformat(), "timeZone": "Europe/Madrid"},
            "end": {"dateTime": self.end.isoformat(), "timeZone": "Europe/Madrid"},
            "draft": self.source == "draft"
        }


class Calendar:
    """A calendar containing a collection of events"""

    def __init__(self, name: str, source: str = "draft"):
        self.name = name
        self.source = source
        self.events: list[Event] = []

    def add_event(self, event: Event):
        event.source = self.source
        self.events.append(event)

    def load_from_file(self, filename: str):
        """Load events from a JSON file"""
        self.events = []
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                for e in data:
                    ev = Event.from_dict(e, source=self.source)
                    if ev:
                        self.add_event(ev)
        except FileNotFoundError:
            pass

    def save_to_file(self, filename: str):
        """Save current events to a JSON file"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump([ev.to_dict() for ev in self.events], f, indent=2, ensure_ascii=False)

    def clear(self):
        self.events = []

    def find_overlaps(self) -> list[tuple]:
        """Find overlapping events inside this calendar"""
        parsed = [(e.title, e.start, e.end, e.source) for e in self.events]
        parsed.sort(key=lambda x: x[1])  # sort by start time

        overlaps = []
        for i in range(len(parsed)):
            for j in range(i + 1, len(parsed)):
                t1, s1, e1, src1 = parsed[i]
                t2, s2, e2, src2 = parsed[j]
                if s2 < e1:
                    overlaps.append(((t1, src1), (t2, src2)))
                else:
                    break
        return overlaps


    def find_overlaps_between(cal1, cal2) -> list[tuple]:
        """Find overlaps between two calendars"""
        parsed = [(e.title, e.start, e.end, e.source) for e in cal1.events + cal2.events]
        parsed.sort(key=lambda x: x[1])

        overlaps = []
        for i in range(len(parsed)):
            for j in range(i + 1, len(parsed)):
                t1, s1, e1, src1 = parsed[i]
                t2, s2, e2, src2 = parsed[j]
                if s2 < e1:
                    overlaps.append(((t1, src1), (t2, src2)))
                else:
                    break
        return overlaps


class CalendarManager:
    """Manages a real calendar and a draft calendar"""

    def __init__(self, draft_file="draft_calendar.json", real_file="calendar_export.json"):
        self.draft_file = draft_file
        self.real_file = real_file
        self.draft_calendar = Calendar("Draft", source="draft")
        self.real_calendar = Calendar("Real", source="real")

        self.draft_calendar.load_from_file(self.draft_file)
        self.real_calendar.load_from_file(self.real_file)

    def create_event(self, date: str, start_time: str, duration_minutes: int, title: str) -> Event:
        start = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        end = start + timedelta(minutes=duration_minutes)
        return Event(title, start, end, source="draft")

    def create_task(self, date: str, time: str, title: str) -> Event:
        start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end = start + timedelta(minutes=1)
        return Event(f"[TASK] {title}", start, end, source="draft")

    def save_draft_event(self, event: Event):
        self.draft_calendar.add_event(event)
        self.draft_calendar.save_to_file(self.draft_file)

    def apply_changes(self, service):
        """Push draft events into Google Calendar API"""
        for ev in self.draft_calendar.events:
            if service:
                service.events().insert(calendarId="primary", body=ev.to_dict()).execute()            # mover a real
            
            ev.source = "real"
            self.real_calendar.add_event(ev)

        # clear draft after pushing
        self.draft_calendar.clear()
        if os.path.exists(self.draft_file):
            os.remove(self.draft_file)

        # save calendar
        self.real_calendar.save_to_file(self.real_file)

    def find_all_overlaps(self) -> list[tuple]:
        """Find overlaps between real and draft calendars"""
        return Calendar.find_overlaps_between(self.real_calendar, self.draft_calendar)