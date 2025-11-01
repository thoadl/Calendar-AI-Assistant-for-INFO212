import json
import datetime
from openai import OpenAI


class CalendarAIClient:
    """
    Handles AI-based calendar editing and analysis using OpenAI.
    """

    def __init__(self, api_key: str, calendar_file: str = "calendar_export.json", delta_file: str = "calendar_delta.json"):
        self.client = OpenAI(api_key=api_key)
        self.calendar_file = calendar_file
        self.delta_file = delta_file

        # Load calendar JSON file
        with open(self.calendar_file, "r", encoding="utf-8") as f:
            self.calendar_json = json.load(f)

        # Convert to string for model input
        self.json_str = json.dumps(self.calendar_json, indent=2)

    # ------------------- SUMMARIZE / INSIGHT PROMPT -------------------
    def summarize_calendar(self, user_request: str) -> str:
        """
        Ask the AI to analyze or summarize the calendar and optionally respond to a user query.
        Returns a natural language text answer.
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        response = self.client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a calendar assistant. You read the calendar JSON and respond "
                        "to user questions or summarize insights about upcoming events. "
                        "Be concise and helpful. "
                        f"The current local date and time is {now}."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Here is my calendar JSON:\n```json\n{self.json_str}\n```\n\n{user_request}",
                },
            ],
        )

        answer = response.choices[0].message.content.strip()
        print("Summary / Answer:")
        print(answer)
        return answer

    # ------------------- JSON DELTA PROMPT -------------------
    def generate_calendar_delta(self, user_request: str) -> dict:
        """
        Ask the AI to generate a JSON delta (add/update/delete).
        Returns the parsed JSON dict and saves it to delta_file.
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response = self.client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "[no prose] You are a calendar editor. "
                        "You must always return valid JSON matching the schema. "
                        "CRITICAL: When deleting events, you MUST use the actual 'id' field from the calendar JSON. "
                        "The 'id' field is the Google Calendar event ID (like 'abc123xyz'). "
                        "DO NOT create IDs from event names or dates. "
                        "For add: create new events with summary, start, end (no id needed). "
                        "For update: include the existing 'id' field plus the fields to change. "
                        "For delete: use ONLY the 'id' field values from the calendar JSON. "
                        "Never include explanations or text. "
                        f"The current local date and time is {now}."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Here is my calendar JSON:\n```json\n{self.json_str}\n```\n\nUser request: {user_request}\n\nIMPORTANT: For deletions, use the exact 'id' values from the JSON above.",
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "calendar_delta",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "add": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "summary": {"type": "string"},
                                        "start": {
                                            "type": "object",
                                            "properties": {
                                                "dateTime": {"type": "string"}
                                            },
                                            "required": ["dateTime"]
                                        },
                                        "end": {
                                            "type": "object",
                                            "properties": {
                                                "dateTime": {"type": "string"}
                                            },
                                            "required": ["dateTime"]
                                        },
                                        "description": {"type": "string"},
                                        "location": {"type": "string"}
                                    },
                                    "required": ["summary", "start", "end"]
                                }
                            },
                            "update": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "summary": {"type": "string"},
                                        "start": {"type": "object"},
                                        "end": {"type": "object"},
                                        "description": {"type": "string"},
                                        "location": {"type": "string"}
                                    },
                                    "required": ["id"]
                                }
                            },
                            "delete": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Array of event IDs to delete (use exact 'id' values from calendar JSON)"
                            },
                        },
                        "required": ["add", "update", "delete"],
                    },
                },
            },
        )

        delta_json = json.loads(response.choices[0].message.content)
        print("Delta JSON received.")
        print(json.dumps(delta_json, indent=2, ensure_ascii=False))

        # Save to file for GoogleCalendarSync to apply
        with open(self.delta_file, "w", encoding="utf-8") as f:
            json.dump(delta_json, f, indent=2, ensure_ascii=False)

        return delta_json


# ------------------- Example Usage -------------------

if __name__ == "__main__":
    ai = CalendarAIClient(
        api_key="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",
        calendar_file="calendar_export.json",
        delta_file="calendar_delta.json",
    )

    # Step 1: Ask for a summary
    ai.summarize_calendar("Please summarize key events and insights from next week.")

    # Step 2: Ask it to make edits
    ai.generate_calendar_delta(
        "Please remove all 'test' events for next week and add lunch with Jeanette tomorrow at noon."
    )
