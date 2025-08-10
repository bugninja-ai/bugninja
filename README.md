# almafa

This is a Bugninja browser automation project.

## Project Structure

- `bugninja.toml` - Project configuration
- `.env` - Sensitive configuration (API keys, etc.)
- `traversals/` - Recorded browser sessions
- `screenshots/` - Screenshots from automation runs
- `tasks/` - Task definitions and descriptions

## Getting Started

1. Copy `.env.example` to `.env` and fill in your API keys
2. Define your tasks in the `tasks/` directory
3. Run automation with `bugninja run`
4. Replay sessions with `bugninja replay`

## Configuration

Edit `bugninja.toml` to customize:
- LLM settings
- Browser configuration
- Logging options
- Directory paths

For more information, see the [Bugninja documentation](https://github.com/bugninja/bugninja).
