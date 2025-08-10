# Bugninja Configuration System

Bugninja uses a hybrid configuration system that combines TOML files for project settings and environment variables for sensitive data. This approach provides better organization, security, and flexibility.

## Configuration Architecture

### **TOML Configuration (`bugninja.toml`)**
- **Non-sensitive project settings**: Logging, file paths, browser config, agent config
- **Version controlled**: Safe to commit to repository
- **Structured**: Better organization than flat environment variables

### **Environment Variables (`.env`)**
- **Sensitive data only**: API keys, passwords, tokens
- **Local only**: Never committed to repository
- **Minimal footprint**: Only what absolutely needs to be secret

## Configuration Files

### `bugninja.toml` - Main Configuration File

```toml
# Bugninja Configuration
# This file contains all non-sensitive project configuration

[project]
name = "bugninja"

[llm]
# Azure OpenAI Configuration (non-sensitive)
model = "gpt-4.1"
temperature = 0.001
api_version = "2024-02-15-preview"
# Note: endpoint and key are loaded from .env file

[logging]
level = "INFO"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
enable_rich_logging = true

[development]
debug_mode = false
enable_verbose_logging = false

[paths]
traversals_dir = "./traversals"
screenshots_dir = "./screenshots"
tasks_dir = "./tasks"

[browser]
viewport_width = 1280
viewport_height = 960
user_agent = ""
device_scale_factor = 0.0
timeout = 30000

[agent]
max_steps = 100
planner_interval = 5
enable_vision = true
enable_memory = false
wait_between_actions = 0.1

[replicator]
sleep_after_actions = 1.0
pause_after_each_step = true
fail_on_unimplemented_action = false
max_retries = 2
retry_delay = 0.5

[screenshot]
format = "png"

[events]
publishers = ["null"]
```

### `.env` - Sensitive Configuration

```bash
# Bugninja Sensitive Configuration
# Copy this file to .env and fill in your secret values

# Azure OpenAI endpoint URL (required)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Azure OpenAI API key (required)
AZURE_OPENAI_KEY=your-api-key-here
```

## Usage Examples

### **Basic Configuration Loading**

```python
from bugninja.config import ConfigurationFactory

# Load settings
settings = ConfigurationFactory.get_settings()
print(f"Project: {settings.project_name}")
print(f"Log Level: {settings.log_level}")
print(f"Debug Mode: {settings.debug_mode}")
```

### **Direct TOML Access**

```python
from bugninja.config import TOMLConfigLoader

# Load TOML configuration directly
loader = TOMLConfigLoader()
config = loader.load_config()

# Access specific values
model = config.get("llm.model")
max_steps = config.get("agent.max_steps")
```

### **Environment Variable Override**

```python
import os
from bugninja.config import ConfigurationFactory

# Override specific settings via environment variables
os.environ["AZURE_OPENAI_MODEL"] = "gpt-4-turbo"
os.environ["LOG_LEVEL"] = "DEBUG"

# Load settings (environment variables take precedence)
settings = ConfigurationFactory.get_settings()
```

## Configuration Priority

The configuration system follows this priority order (highest to lowest):

1. **Environment Variables** - Highest priority, always override
2. **TOML Configuration** - Project settings from bugninja.toml
3. **Code Defaults** - Fallback values in code

## Migration from .env-only Configuration

If you're migrating from the old .env-only system:

1. **Copy your current `.env` file** to preserve sensitive data
2. **Create `bugninja.toml`** using the template above
3. **Move non-sensitive settings** from `.env` to `bugninja.toml`
4. **Keep only secrets** in `.env` file
5. **Test the configuration** with your application

### **Example Migration**

**Old `.env` file:**
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key-here
AZURE_OPENAI_MODEL=gpt-4.1
AZURE_OPENAI_TEMPERATURE=0.001
LOG_LEVEL=INFO
DEBUG_MODE=false
TRAVERSALS_DIR=./traversals
```

**New `.env` file:**
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key-here
```

**New `bugninja.toml` file:**
```toml
[project]
name = "bugninja"

[llm]
model = "gpt-4.1"
temperature = 0.001

[logging]
level = "INFO"

[development]
debug_mode = false

[paths]
traversals_dir = "./traversals"
```

## Benefits of This Approach

### **Security**
- Sensitive data stays in `.env` (gitignored)
- Project configuration is version controlled
- Clear separation of concerns

### **Flexibility**
- TOML supports complex nested structures
- Easy to read and maintain
- Structured configuration organization

### **Developer Experience**
- Better organization than flat environment variables
- Self-documenting configuration structure
- IDE support for TOML syntax

### **Deployment**
- Easy configuration management
- Consistent across team members
- Simple setup and maintenance

## Troubleshooting

### **Configuration Not Loading**
- Ensure `bugninja.toml` exists in project root
- Check TOML syntax validity
- Verify environment variable names match expected format

### **Sensitive Data Not Found**
- Ensure `.env` file exists
- Check environment variable names
- Verify `.env` file is not gitignored

## Advanced Configuration

### **Custom Configuration Paths**

```python
from bugninja.config import TOMLConfigLoader

# Load from custom path
loader = TOMLConfigLoader(Path("/custom/path/bugninja.toml"))
config = loader.load_config()
```

### **Dynamic Configuration Updates**

```python
from bugninja.config import ConfigurationFactory

# Reset configuration cache to reload
ConfigurationFactory.reset()

# Load fresh configuration
settings = ConfigurationFactory.get_settings()
```

This configuration system provides a robust, secure, and flexible way to manage Bugninja settings while maintaining clear separation between sensitive and non-sensitive data.
