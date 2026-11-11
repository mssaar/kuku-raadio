
import json
with open(r'C:/Users/sverk/.gemini/antigravity-cli/brain/39003446-3b60-4b6c-9167-d4c7c5c3676d/.system_generated/logs/transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get('step_index') in [369, 375, 499]:
            print(data.get('tool_calls'))
