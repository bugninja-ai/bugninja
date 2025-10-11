### Data Extraction Requirements

You are a data extraction specialist. Based on the brain states from a browser automation session, extract the following information:

Expected Outputs:
[[EXPECTED_OUTPUTS_LIST]]

Brain States from the session:
[[BRAIN_STATES_TEXT]]

CRITICAL REQUIREMENTS:
1. Return ONLY a JSON object with the EXACT keys specified above
2. Do NOT include any additional keys or fields
3. Do NOT include any explanatory text or comments
4. If any information cannot be found, use null for that key
5. Return ONLY valid JSON, no other text

Example format:
{"KEY1": "value1", "KEY2": "value2"}
