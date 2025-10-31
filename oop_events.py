from datetime import datetime, timedelta
import json
import os
from typing import List, Tuple, Optional

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
            # check if event already exists in real_calendar by title+start
            exists = any(
                e.title == ev.title and e.start == ev.start for e in self.real_calendar.events
            )
            if not exists and service:
                event_body = {
                    "summary": ev.title,
                    "start": {"dateTime": ev.start.isoformat(), "timeZone": "Europe/Madrid"},
                    "end": {"dateTime": ev.end.isoformat(), "timeZone": "Europe/Madrid"},
                }
                service.events().insert(calendarId="primary", body=event_body).execute() 

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
    
    def find_free_slot(self, start_from: datetime, duration_minutes: int=90, max_days_ahead: int = 7,):
        """
        Return the earliest start datetime (same day preferred) where
        `duration_minutes` fits without overlapping any *real* event.
        """
        search_day = start_from.replace(hour=0, minute=0, second=0, microsecond=0)
        end_search = search_day + timedelta(days=max_days_ahead)

        while search_day < end_search:
            day_end = search_day.replace(hour=23, minute=59)

            # Build a list of occupied intervals for this day
            occupied: List[Tuple[datetime, datetime]] = []
            for ev in self.real_calendar.events:
                if ev.start.date() != search_day.date():
                    continue
                occupied.append((ev.start, ev.end))

            # Sort by start time
            occupied.sort(key=lambda x: x[0])

            candidate = search_day.replace(hour=8)  # start looking at 08:00
            while candidate + timedelta(minutes=duration_minutes) <= day_end:
                # check overlap with any occupied slot
                overlaps = any(
                    candidate < occ_end and candidate + timedelta(minutes=duration_minutes) > occ_start
                    for occ_start, occ_end in occupied
                )
                if not overlaps:
                    return candidate
                candidate += timedelta(minutes=15)  # 15-min granularity

            # No slot today → try next day
            search_day += timedelta(days=1)

        return None   # no free slot found in the horizon
    def move_study_block(
        self,
        old_event: Event,
        new_start: datetime,
    ) -> Event:
        """Create a new draft event with the same title/duration."""
        duration = int((old_event.end - old_event.start).total_seconds() // 60)
        new_end = new_start + timedelta(minutes=duration)
        new_ev = Event(
            title=old_event.title,
            start=new_start,
            end=new_end,
            source="draft",
        )
        # remove the old draft (if it was a draft) or mark it for deletion later
        if old_event in self.draft_calendar.events:
            self.draft_calendar.events.remove(old_event)
        return new_ev
    
    def auto_reschedule_study_blocks(
        self,
        new_event: Event,
    ) -> List[dict]:
        """
        1. Find overlapping study blocks.
        2. For each, find next free slot.
        3. Replace the old block with a new draft.
        Returns a list of dicts: {"old": {...}, "new": {...}}
        """
        moved = []

        # Identify study blocks (you can customise the prefix)
        STUDY_PREFIX = "[STUDY]"

        overlapping_study = [
            ev for ev in self.draft_calendar.events
            if ev.title.startswith(STUDY_PREFIX)
            and new_event.start < ev.end
            and new_event.end > ev.start
        ]

        for study in overlapping_study:
            duration = int((study.end - study.start).total_seconds() // 60)
            # start searching *after* the conflicting new event
            search_from = max(study.start, new_event.end)
            new_start = self.find_free_slot(search_from, duration)

            if new_start is None:
                # fallback: just keep it (or you could delete it)
                continue

            new_ev = self.move_study_block(study, new_start)
            self.draft_calendar.add_event(new_ev)
            moved.append({
                "old": study.to_dict(),
                "new": new_ev.to_dict(),
            })

        # Persist drafts
        self.draft_calendar.save_to_file(self.draft_file)
        return moved