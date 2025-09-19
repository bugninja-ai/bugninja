# test_init

This is a Bugninja browser automation project.

## Project Structure

- `bugninja.toml` - Global project configuration (LLM, logging, etc.)
- `.env` - Sensitive configuration (API keys, etc.)
- `tasks/` - Task definitions and configurations
  - Each task has its own `screenshots/` and `traversals/` subdirectories
  - Task-specific settings in `task_*.toml` files

## Getting Started

1. Copy `.env.example` to `.env` and fill in your API keys
2. Create tasks with `bugninja add <task-name>`
3. Run automation with `bugninja run --task <task-name>`
4. Replay sessions with `bugninja replay`

## Configuration

- **Global settings**: Edit `bugninja.toml` for LLM, logging, and project settings
- **Task settings**: Edit individual `task_*.toml` files for browser, agent, and run-specific settings

For more information, see the [Bugninja documentation](https://github.com/bugninja/bugninja).
