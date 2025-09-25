from datetime import datetime, timedelta
import json
import os

def save_draft_event(event_dict, filename="draft_calendar.json"):
    """Saves an event on the draft calendar"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            draft = json.load(f)
    except FileNotFoundError:
        draft = []

    draft.append(event_dict)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(draft, f, indent=2, ensure_ascii=False)


def apply_changes(service):
    """Applies changes getting the events on the draft calendar 
        and inserting them on the real calendar"""
    
    with open("draft_calendar.json", "r", encoding="utf-8") as f:
        draft_events = json.load(f)

    for ev in draft_events:
        service.events().insert(calendarId="primary", body=ev).execute()

    # erase draft
    os.remove("draft_calendar.json")


def create_event_dict(date: str, start_time: str, duration_minutes: int, title: str):
    start = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
    end = start + timedelta(minutes=duration_minutes)
    return {
        "summary": title,
        "start": {"dateTime": start.isoformat(), "timeZone": "Europe/Madrid"},
        "end":   {"dateTime": end.isoformat(), "timeZone": "Europe/Madrid"}
    }


def create_task_dict(date: str, time: str, title: str):
    # tasks are treated as 1 minute events
    from datetime import datetime, timedelta
    start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    end = start + timedelta(minutes=1)  # duración mínima

    return {
        "summary": f"[TASK] {title}",
        "description": "Deadline task",
        "start": {"dateTime": start.isoformat(), "timeZone": "Europe/Madrid"},
        "end":   {"dateTime": end.isoformat(), "timeZone": "Europe/Madrid"}
    }


def load_events_real(real_file="calendar_export.json"):
    events = []
    # load real events (exported from Google)
    try:
        with open(real_file, "r", encoding="utf-8") as f:
            real_events = json.load(f)
            for e in real_events:
                if "start" in e and "end" in e:
                    start = e["start"].get("dateTime") or e["start"].get("date")
                    end = e["end"].get("dateTime") or e["end"].get("date")
                    if start and end:
                        events.append({
                            "title": e.get("summary", "Untitled"),
                            "start": start,
                            "end": end,
                            "source": "real"
                        })
    except FileNotFoundError:
        pass
    return events

def load_events_draft(draft_file="draft_calendar.json"):
    events = []
    # load draft (proposed changes)
    try:
        with open(draft_file, "r", encoding="utf-8") as f:
            draft_events = json.load(f)
            for e in draft_events:
                events.append({
                    "title": e.get("summary", "Untitled"),
                    "start": e["start"]["dateTime"],
                    "end": e["end"]["dateTime"],
                    "source": "draft"
                })
    except FileNotFoundError:
        pass

    return events


def find_overlaps(real_events: list, draft_events: list) -> list:
    """Identifies overlaps in events between the real calendar
        and the draft and returns them on a list"""
    events = []
    events.append(real_events)
    events.append(draft_events)
    overlaps = []
    parsed = []

    # convert ISO strings to datetime
    for e in events:
        start = datetime.fromisoformat(e["start"])
        end = datetime.fromisoformat(e["end"])
        parsed.append((e["title"], start, end, e["source"]))

    # order by begining
    parsed.sort(key=lambda x: x[1])

    # find overlaps
    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            t1, s1, e1, src1 = parsed[i]
            t2, s2, e2, src2 = parsed[j]
            if s2 < e1:
                overlaps.append(((t1, src1), (t2, src2)))
            else:
                break

    return overlaps