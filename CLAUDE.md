# Claude Development Notes

## Python Environment Setup

This project uses **uv** for Python dependency management and virtual environment handling.

### Key Files
- `pyproject.toml` - Project configuration and dependency specifications with version ranges
- `uv.lock` - Locked exact versions for reproducible builds (committed to git)
- `.venv/` - Virtual environment directory (not committed)

### Environment Commands

```bash
# Install dependencies and create/activate virtual environment
uv sync

# Install with development dependencies (includes ruff linter)
uv sync --extra dev

# Update packages to latest versions within constraints
uv sync --upgrade --extra dev

# Run commands in the virtual environment
uv run python scraper.py
uv run ruff check

# Check installed packages
uv pip list
```

### Development Workflow

1. **Initial setup**: `uv sync --extra dev`
2. **Add dependencies**: Edit `pyproject.toml` then run `uv sync`
3. **Update packages**: `uv sync --upgrade --extra dev`
4. **Run linter**: `uv run ruff check` (or `uv run ruff check --fix`)
5. **Run scripts**: `uv run python scraper/scraper.py cron`

### Dependencies

**Runtime dependencies** (in `[project.dependencies]`):
- yt-dlp - YouTube video metadata extraction
- requests - HTTP client
- beautifulsoup4 - HTML parsing
- lxml - XML/HTML parser

**Development dependencies** (in `[project.optional-dependencies.dev]`):
- ruff - Python linter and formatter

### Notes
- Always commit `uv.lock` for reproducible builds
- Use version ranges (>=) in `pyproject.toml`, not exact pins (==)
- The virtual environment is automatically activated when using `uv run`
- No need to manually activate/deactivate the virtual environment