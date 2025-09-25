from googleOAuthAPI import main
from events_utils import create_event_dict

service = main()

# create new event
event_dict = create_event_dict("2025-09-27", "08:15", 90, "Study Programming")

# insert in Google Calendar
created_event = service.events().insert(calendarId="primary", body=event_dict).execute()
print(f"Event created: {created_event.get('htmlLink')}")
