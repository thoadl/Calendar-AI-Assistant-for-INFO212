import json
from openAIAPI import CalendarAIClient
from googleOAuthAPI import GoogleCalendarExporter
from GoogleCalendarSync import GoogleCalendarSync


def main():
    print("Welcome to the Calendar AI Assistant!")
    api_key = "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"

    # Initialize Google Calendar
    exporter = GoogleCalendarExporter()
    syncer = GoogleCalendarSync()

    # Step 1: Fetch the latest Google Calendar
    print("\nFetching the latest calendar events...")
    events = exporter.fetch_events()
    with open("calendar_export.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f"Exported {len(events)} events to calendar_export.json\n")

    #Initialize AI client
    ai = CalendarAIClient(
        api_key=api_key,
        calendar_file="calendar_export.json",
        delta_file="calendar_delta.json"
    )

    # Step 2: Ask user what they want to do
    while True:
        print("\nWhat would you like to do?")
        print("1. Ask about your calendar or get a summary")
        print("2. Request changes (AI will propose add/update/delete)")
        print("3. Exit")

        choice = input("\nSelect an option (1–3): ").strip()

        if choice == "1":
            user_query = input("\nAsk something about your calendar: ").strip()
            ai.summarize_calendar(user_query)

        elif choice == "2":
            user_request = input(
                "\nDescribe the change (e.g. 'remove all terst events next week and add lunch tomorrow at noon'): "
            ).strip()

            # Regenerate the AI instance in case the calendar file changed
            ai = CalendarAIClient(api_key=api_key)

            delta = ai.generate_calendar_delta(user_request)

            # Show proposed changes
            adds = delta.get("add", [])
            updates = delta.get("update", [])
            deletes = delta.get("delete", [])

            print("\nProposed Changes:")
            print("-------------------")
            print(f"Add: {len(adds)} events")
            for a in adds:
                print(f"{a.get('summary', '(no summary)')}")

            print(f"\nUpdate: {len(updates)} events")
            for u in updates:
                print(f"{u.get('summary', '(no summary)')} (ID: {u.get('id', 'unknown')})")

            print(f"\nDelete: {len(deletes)} events")
            for d in deletes:
                print(f"ID: {d}")

            confirm = input("\nApply these changes to Google Calendar? (yes/no): ").strip().lower()
            if confirm != "yes":
                print("\nCancelled — no changes applied.")
                continue

            # Step 3: Apply the delta file using GoogleCalendarSync
            #confirm_delete = input("Delete events automatically without confirmation? (yes/no): ").strip().lower()
            syncer.apply_delta(auto_delete=(True))

            print("\nChanges applied successfully!")

        elif choice == "3":
            print("Goodbye!")
            break

        else:
            print("Invalid choice, please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
