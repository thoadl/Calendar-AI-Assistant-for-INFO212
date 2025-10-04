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
            model="gpt-5-nano",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a calendar assistant. You read the calendar JSON and respond "
                        "to user questions or summarize insights about upcoming events."
                        f"The current local date and time is {now}."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Here is my JSON:\n```json\n{self.json_str}\n```\n\n{user_request}",
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
            model="gpt-5-nano",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "[no prose] You are a calendar editor. "
                        "You must always return valid JSON matching the schema: "
                        "{ add: [new events], update: [events with id to update], delete: [ids to remove] }. "
                        "The IDs you are asked to remove are suggestions that will later be confirmed by the user. "
                        "Never include explanations or text."
                        f"The current local date and time is {now}."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Here is my JSON:\n```json\n{self.json_str}\n```\n\n{user_request}",
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "calendar_delta",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "add": {"type": "array", "items": {"type": "object"}},
                            "update": {"type": "array", "items": {"type": "object"}},
                            "delete": {"type": "array", "items": {"type": "string"}},
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
        "Please remove all 'terst' events for next week (October 5th to 11th) and add lunch with Jeanette tomorrow at noon."
    )
