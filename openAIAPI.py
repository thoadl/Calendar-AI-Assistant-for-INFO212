import json
from openai import OpenAI

client = OpenAI(api_key="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")

with open("calendar_export.json", "r", encoding="utf-8") as f:
    calendar_file = json.load(f)

json_str = json.dumps(calendar_file, indent=2)

response = client.chat.completions.create(
    model="gpt-5-nano",
    messages=[
        {"role": "system", "content": "You are a calendar assistant, you read the calendar which is in json format and the user's commands to make changes or answer questions about the calendar"},
        {"role": "user", "content": f"Here is my JSON:\n```json\n{json_str}\n```\n\nPlease summarize the key insights."}
    ]
)

print(response.choices[0].message.content)