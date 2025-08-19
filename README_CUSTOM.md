# Custom Merged Status Line

This custom status line merges features from:
- claude-code-hooks-mastery (session tracking, git info, directory display)
- claude-statusline (cost tracking, token usage)

## Features

- **Model Display** with emojis (🎭 Opus, ✨ Sonnet, ⚡ Haiku)
- **Directory Path** with 📁 emoji
- **Git Branch** with status (🌿 clean, 🔥 changes)
- **Token Usage** with 🧠 emoji (formatted as k/M)
- **Cost Tracking** with color-coded display:
  - 💵 Green for < $50
  - 💰 Yellow for $50-100
  - 💸 Red for > $100

## Installation

1. Copy `custom_merged_statusline.py` to `~/.claude/status_line/status_line.py`
2. Update `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 /home/fire/.claude/status_line/status_line.py"
  }
}
```

## Display Format

```
✨ 3.5S | 📁 ~/project | 🔥 main* | 🧠 65.9M | 💵 $42.50
```

## How It Works

The status line:
1. Reads JSON input from stdin (provided by Claude Code)
2. Parses project-specific JSONL logs from `~/.claude/projects/`
3. Calculates token usage and costs based on model pricing
4. Displays formatted output with ANSI colors and emojis

## Model Pricing

- **Opus 4.1**: $15/$75 per million tokens (input/output)
- **Sonnet 3.5**: $3/$15 per million tokens
- **Haiku 3.5**: $1/$5 per million tokens

## Customization

Edit the script to modify:
- Emoji mappings in the main() function
- Color schemes in the Colors class
- Model pricing in MODEL_PRICING dictionary
- Path truncation length in format_path()