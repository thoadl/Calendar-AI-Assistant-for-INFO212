# This guide is AI-generated

# Developer Guide: Using Calendar AI Classes

## Overview
This guide shows how to use three classes together to fetch calendar data, make AI-powered changes, and sync back to Google Calendar.

## Required Files
- `googleOAuthAPI.py` - Google Calendar authentication & export
- `openAIAPI.py` - AI-powered calendar analysis & modifications
- `GoogleCalendarSync.py` - Syncs changes back to Google Calendar

## Setup

```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client openai
```

## Basic Usage Pattern

### 1. Import the Classes

```python
from googleOAuthAPI import GoogleCalendarExporter
from openAIAPI import CalendarAIClient
from GoogleCalendarSync import GoogleCalendarSync
import json
```

### 2. Fetch Calendar Data

```python
# Initialize the exporter
exporter = GoogleCalendarExporter()

# Fetch events from Google Calendar
events = exporter.fetch_events()

# Save to JSON file
with open("calendar_export.json", "w", encoding="utf-8") as f:
    json.dump(events, f, indent=2, ensure_ascii=False)

print(f"Exported {len(events)} events")
```

### 3. Query Your Calendar with AI

```python
# Initialize AI client with your OpenAI API key
ai = CalendarAIClient(
    api_key="your-openai-api-key",
    calendar_file="calendar_export.json"
)

# Ask questions about your calendar (User input if applicable in the web app)
ai.summarize_calendar("What meetings do I have this week?")
```

### 4. Generate Calendar Changes with AI

```python
# Request changes in natural language (User input if applicable in the web app)
delta = ai.generate_calendar_delta(
    "Remove all test events and add a team meeting tomorrow at 2pm"
)

# Delta structure contains:
# {
#   "add": [...],      # New events to create
#   "update": [...],   # Events to modify
#   "delete": [...]    # Event IDs to remove
# }

# Preview the changes
print(f"Will add: {len(delta.get('add', []))} events")
print(f"Will update: {len(delta.get('update', []))} events")
print(f"Will delete: {len(delta.get('delete', []))} events")
```

### 5. Apply Changes to Google Calendar

```python
# Initialize syncer
syncer = GoogleCalendarSync()

# Apply the delta file (created by AI client)
syncer.apply_delta(
    auto_delete=True  # Set False to confirm each deletion
)

print("Changes applied successfully!")
```

## Complete Example

```python
from googleOAuthAPI import GoogleCalendarExporter
from openAIAPI import CalendarAIClient
from GoogleCalendarSync import GoogleCalendarSync
import json

# 1. Fetch current calendar
exporter = GoogleCalendarExporter()
events = exporter.fetch_events()

with open("calendar_export.json", "w") as f:
    json.dump(events, f, indent=2)

# 2. Initialize AI
ai = CalendarAIClient(
    api_key="your-api-key",
    calendar_file="calendar_export.json",
    delta_file="calendar_delta.json"
)

# 3. Ask AI to make changes
delta = ai.generate_calendar_delta(
    "Add a dentist appointment next Monday at 3pm"
)

# 4. Apply changes
syncer = GoogleCalendarSync()
syncer.apply_delta(auto_delete=True)
```

## File Flow

```
calendar_export.json  →  [AI Processing]  →  calendar_delta.json  →  [Google Calendar]
     (fetch)                                        (changes)            (sync)
```

## Common Patterns

### Query Only (No Changes)
```python
exporter = GoogleCalendarExporter()
events = exporter.fetch_events()

ai = CalendarAIClient(api_key="your-key")
ai.summarize_calendar("What's my schedule tomorrow?")
```

### Make Changes
```python
# Always fetch fresh data first
exporter = GoogleCalendarExporter()
events = exporter.fetch_events()
with open("calendar_export.json", "w") as f:
    json.dump(events, f, indent=2)

# Generate changes
ai = CalendarAIClient(api_key="your-key")
delta = ai.generate_calendar_delta("your request here")

# Apply to Google Calendar
syncer = GoogleCalendarSync()
syncer.apply_delta(auto_delete=True)
```

## Tips

- Always fetch fresh calendar data before making changes
- The AI client saves delta changes to `calendar_delta.json` by default
- Use `auto_delete=False` for safer deletion (manual confirmation)
    - If you do auto_delete=False it will not delete the events from the calendar json. You would need to do auto_delete=True or have some sort of check for whether the user is happy with the change, returning true or false
- Reinitialize `CalendarAIClient` if the calendar file changes between operations