#!/usr/bin/env python3
"""
Merged Claude Status Line - Combines session tracking with cost monitoring
Merges features from claude-code-hooks-mastery v4 and claude-statusline nerd template
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import re

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright foreground colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

# Model pricing (per million tokens)
MODEL_PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30},
    "claude-3-5-haiku-20241022": {"input": 1.00, "output": 5.00, "cache_write": 1.25, "cache_read": 0.10},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50},
    "claude-opus-4-1-20250805": {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50},
}

def get_git_info(cwd):
    """Get git branch and status information."""
    try:
        # Get current branch
        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
        
        # Get git status (check if there are any changes)
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2
        )
        has_changes = bool(status_result.stdout.strip()) if status_result.returncode == 0 else False
        
        return branch, has_changes
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        return "", False

def format_path(path, max_length=30):
    """Format path to fit within max_length, using ~ for home directory."""
    if not path:
        return ""
    
    # Replace home directory with ~
    home = os.path.expanduser("~")
    if path.startswith(home):
        path = "~" + path[len(home):]
    
    # Truncate if too long
    if len(path) > max_length:
        # Keep the last part that's most relevant
        return "..." + path[-(max_length-3):]
    
    return path

def get_prompt_icon(prompt: str) -> str:
    """Determine icon based on prompt content"""
    prompt_lower = prompt.lower()
    
    # Priority order for icon selection
    if any(word in prompt_lower for word in ['fix', 'bug', 'error', 'issue', 'problem']):
        return '🐛'
    elif any(word in prompt_lower for word in ['test', 'testing', 'verify']):
        return '🧪'
    elif any(word in prompt_lower for word in ['deploy', 'deployment', 'production']):
        return '🚀'
    elif any(word in prompt_lower for word in ['optimize', 'performance', 'speed']):
        return '⚡'
    elif any(word in prompt_lower for word in ['analyze', 'review', 'check']):
        return '🔍'
    elif any(word in prompt_lower for word in ['create', 'build', 'implement', 'add']):
        return '🔨'
    elif any(word in prompt_lower for word in ['refactor', 'restructure', 'reorganize']):
        return '♻️'
    elif any(word in prompt_lower for word in ['document', 'docs', 'readme']):
        return '📝'
    elif any(word in prompt_lower for word in ['help', 'explain', 'understand']):
        return '💡'
    elif any(word in prompt_lower for word in ['config', 'configure', 'setup']):
        return '⚙️'
    else:
        return '💬'

def truncate_prompt(prompt: str, max_length: int = 40) -> str:
    """Truncate prompt to fit status line"""
    if len(prompt) <= max_length:
        return prompt
    return prompt[:max_length-3] + "..."

def format_tokens(tokens: int) -> str:
    """Format token count for display"""
    if tokens >= 1_000_000:
        return f"{tokens/1_000_000:.1f}M"
    elif tokens >= 1_000:
        return f"{tokens/1_000:.1f}k"
    else:
        return str(tokens)

def calculate_cost_from_logs(model_id: str = None, current_dir: str = None) -> tuple[float, int, int]:
    """Calculate session cost and token usage from logs"""
    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    
    # Determine the project directory for logs
    project_path = None
    if current_dir:
        # Convert current directory to project path format
        project_name = current_dir.replace("/", "-")
        if project_name.startswith("-"):
            project_name = project_name[1:]
        project_path = Path.home() / ".claude" / "projects" / f"-{project_name}"
    
    # Try project-specific logs first, then fall back to general logs
    log_dirs = []
    if project_path and project_path.exists():
        log_dirs.append(project_path)
    log_dirs.append(Path.home() / ".claude" / "logs")
    
    for logs_dir in log_dirs:
        if logs_dir.exists():
            # Find most recent conversation log
            log_files = sorted(logs_dir.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)
            if log_files:
                try:
                    with open(log_files[0], 'r') as f:
                        for line in f:
                            try:
                                entry = json.loads(line)
                                # Handle different log entry formats
                                if entry.get("type") == "assistant" and "message" in entry:
                                    msg = entry.get("message", {})
                                    if "usage" in msg:
                                        usage = msg["usage"]
                                        model = msg.get("model", model_id or "claude-3-5-sonnet-20241022")
                                        
                                        if model in MODEL_PRICING:
                                            pricing = MODEL_PRICING[model]
                                            
                                            # Calculate input cost
                                            input_tokens = usage.get("input_tokens", 0)
                                            cache_read = usage.get("cache_read_input_tokens", 0)
                                            cache_write = usage.get("cache_creation_input_tokens", 0)
                                            regular_input = input_tokens - cache_read - cache_write
                                            
                                            input_cost = (
                                                (regular_input / 1_000_000) * pricing["input"] +
                                                (cache_read / 1_000_000) * pricing["cache_read"] +
                                                (cache_write / 1_000_000) * pricing["cache_write"]
                                            )
                                            
                                            # Calculate output cost
                                            output_tokens = usage.get("output_tokens", 0)
                                            output_cost = (output_tokens / 1_000_000) * pricing["output"]
                                            
                                            total_cost += input_cost + output_cost
                                            total_input_tokens += input_tokens
                                            total_output_tokens += output_tokens
                            except json.JSONDecodeError:
                                continue
                except Exception:
                    pass
                # If we found data, return it
                if total_cost > 0:
                    return total_cost, total_input_tokens, total_output_tokens
    
    return total_cost, total_input_tokens, total_output_tokens

def get_model_short_name(model_name: str) -> str:
    """Get short display name for model from display name"""
    if 'Claude 3.5 Sonnet' in model_name or 'claude-3-5-sonnet' in model_name:
        return "3.5S"
    elif 'Claude 3.5 Haiku' in model_name or 'claude-3-5-haiku' in model_name:
        return "3.5H"
    elif 'Claude 3 Opus' in model_name or 'claude-3-opus' in model_name:
        return "Opus3"
    elif 'Opus 4.1' in model_name or 'claude-opus-4-1' in model_name:
        return "Opus4.1"
    elif 'Claude' in model_name:
        return "Claude"
    else:
        # Try to extract version from model name
        return model_name[:10] if len(model_name) > 10 else model_name

def get_model_id_from_name(model_name: str) -> str:
    """Convert display name to model ID for pricing"""
    if 'Claude 3.5 Sonnet' in model_name:
        return "claude-3-5-sonnet-20241022"
    elif 'Claude 3.5 Haiku' in model_name:
        return "claude-3-5-haiku-20241022"
    elif 'Claude 3 Opus' in model_name:
        return "claude-3-opus-20240229"
    elif 'Opus 4.1' in model_name:
        return "claude-opus-4-1-20250805"
    else:
        return "claude-3-5-sonnet-20241022"  # Default

def main():
    try:
        # Read JSON input from stdin (this is how Claude Code passes data)
        input_data = json.loads(sys.stdin.read())
        
        # Extract model information
        model_info = input_data.get('model', {})
        model_name = model_info.get('display_name', 'Claude')
        model_id = model_info.get('id', get_model_id_from_name(model_name))
        
        # Extract workspace information
        workspace = input_data.get('workspace', {})
        current_dir = workspace.get('current_dir', input_data.get('cwd', ''))
        
        # Extract output style
        output_style = input_data.get('output_style', {}).get('name', '')
        
        # Get git information
        git_branch, has_changes = get_git_info(current_dir)
        
        # Calculate cost and usage from logs
        total_cost, input_tokens, output_tokens = calculate_cost_from_logs(model_id, current_dir)
        total_tokens = input_tokens + output_tokens
        
        # Build status line components
        components = []
        
        # Model name (shortened with color and emoji)
        model_short = get_model_short_name(model_name)
        model_emoji = "🤖"
        if "Opus" in model_short:
            model_emoji = "🎭"
        elif "3.5S" in model_short:
            model_emoji = "✨"
        elif "3.5H" in model_short:
            model_emoji = "⚡"
        components.append(f"{model_emoji} {Colors.BRIGHT_CYAN}{model_short}{Colors.RESET}")
        
        # Output style (if not default)
        if output_style and output_style.lower() != 'default':
            components.append(f"{Colors.DIM}[{output_style}]{Colors.RESET}")
        
        # Current directory (formatted with color and emoji)
        formatted_dir = format_path(current_dir, 25)
        if formatted_dir:
            components.append(f"📁 {Colors.BRIGHT_YELLOW}{formatted_dir}{Colors.RESET}")
        
        # Git branch with status indicator (with color and emoji)
        if git_branch:
            git_emoji = "🌿" if not has_changes else "🔥"
            git_info = f"{git_branch}"
            if has_changes:
                git_info += "*"
            components.append(f"{git_emoji} {Colors.BRIGHT_MAGENTA}{git_info}{Colors.RESET}")
        
        # Token usage (if available with emoji)
        if total_tokens > 0:
            components.append(f"🧠 {Colors.BRIGHT_BLUE}{format_tokens(total_tokens)}{Colors.RESET}")
        
        # Cost tracking (highlighted with emoji)
        if total_cost > 0:
            cost_str = f"${total_cost:.2f}"
            if total_cost > 100:
                # Red for high cost with warning emoji
                components.append(f"💸 {Colors.BRIGHT_RED}{Colors.BOLD}{cost_str}{Colors.RESET}")
            elif total_cost > 50:
                # Yellow for medium cost with caution emoji
                components.append(f"💰 {Colors.BRIGHT_YELLOW}{cost_str}{Colors.RESET}")
            else:
                # Green for low cost with money emoji
                components.append(f"💵 {Colors.BRIGHT_GREEN}{cost_str}{Colors.RESET}")
        
        # Join components with separator
        status_line = " | ".join(components)
        
        print(status_line)
        
    except (json.JSONDecodeError, KeyError, Exception):
        # Fallback status line if something goes wrong
        print(f"{Colors.BRIGHT_CYAN}Claude Code{Colors.RESET}")

if __name__ == "__main__":
    main()