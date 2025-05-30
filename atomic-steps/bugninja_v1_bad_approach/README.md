# BugNinja V1 - Simple Prototype

A simple prototype implementation of the AI Web Navigation Agent based on the design document in `../DESIGN_V1.md`.

## Project Structure (Keep It Simple!)

```
atomic-steps/bugninja_v1/
├── main.py           # Main agent logic (element extraction, AI decisions, actions)
├── config.py         # Configuration and Azure OpenAI setup
├── requirements.txt  # Dependencies
├── .env             # Environment variables (already provided)
└── README.md        # This file
```

## Features

- **Element Extraction**: Find all interactive elements on a page
- **Screenshot Annotation**: Visual representation with bounding boxes
- **AI Decision Making**: Azure OpenAI chooses next action
- **Atomic Actions**: Basic click, type, scroll, hover actions
- **State Logging**: Track states and transitions for replay
- **Beautiful Logging**: Clear, colorful logs with loguru

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Patchright browser**:
   ```bash
   patchright install chrome
   ```

3. **Configure environment variables** in `.env`:
   ```
   AZURE_OPENAI_ENDPOINT=your_endpoint
   AZURE_OPENAI_API_KEY=your_key
   AZURE_MODEL_NAME=gpt-4o
   ```

4. **Run the prototype**:
   ```bash
   python main.py
   ```

## What It Does

1. Opens a webpage with Patchright (stealth browser)
2. Extracts all clickable/interactive elements
3. Takes an annotated screenshot with element bounding boxes
4. Asks Azure OpenAI to choose the best next action
5. Executes that atomic action (click, type, etc.)
6. Logs the state transition
7. Repeats until goal achieved or max steps reached

## Logging

The prototype uses `loguru` for beautiful, clear logging:
- **Console**: Colorful, structured logs
- **File**: Detailed logs saved to `bugninja.log`
- **Levels**: DEBUG, INFO, SUCCESS, WARNING, ERROR

## Next Steps

Once the prototype proves the concept, we can:
- Add exploration mode
- Build the navigation graph
- Implement deterministic replay
- Scale to full architecture 