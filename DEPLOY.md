# Deployment Guide

This document outlines what files should be deployed to production for the web application.

## Production Deployment Files

For a production deployment, only these files/folders are needed:

### Required Files
```
dist/                   # Complete built application (includes everything needed)
```

**Note**: The `dist/` folder contains everything needed for production, including:
- Processed `index.html` 
- Bundled JavaScript and CSS
- All contents from `public/` (data, favicons, manifests)

### Build Process
1. **Generate database**: `uv run cubscrape build-db`
2. **Build web assets**: `npm run build` (automatically includes all data via symlink resolution)
3. **Deploy dist/ contents** (complete and self-contained)

### Files to Exclude from Deployment

These files are for development only and should NOT be deployed:

```
# Development source code
src/                    # Vue source files
scripts/                # Build and dev scripts
docs/                   # Technical documentation
scraper/                # Python scraper source
archive/                # Archived code

# Configuration files
*.config.js             # Build configurations
tsconfig*.json          # TypeScript config
package*.json           # Node.js config (not needed at runtime)
pyproject.toml          # Python config
uv.lock                 # Python dependencies
eslint.config.js        # Linting config
postcss.config.js       # CSS processing config

# Development files
CLAUDE.md               # Development notes
README-vue.md           # Development docs
.venv/                  # Python virtual environment
node_modules/           # Node.js dependencies
.vite/                  # Vite cache

# Logs and temporary files
*.log                   # All log files
dev-server.log          # Development server logs
test_*.log              # Test logs
cubscrape*.log          # Application logs
data/*.db               # Database files (regenerated)
```

## Deployment Commands

### Full Production Build
```bash
# 1. Generate fresh database with latest data
uv run cubscrape build-db

# 2. Build optimized web assets
npm run build

# 3. Deploy contents of dist/ folder (includes all data automatically)
```

### Deployment
```bash
# Deploy the dist/ folder directly - that's it!
# OR create deployment package:
mkdir deploy
cp -r dist/* deploy/
```

## Notes

- **`dist/` folder** is self-contained and includes everything needed for production:
  - Processed `index.html` with optimized asset references
  - Bundled and minified JavaScript and CSS files  
  - All static assets copied from `public/` (data, favicons, manifests)
- **`public/` folder** is the source for static assets but gets copied into `dist/` during build (symlinks are resolved)
- **Source code** and development tools are not needed in production
- **Logs** should never be deployed as they may contain sensitive information

Total production deployment size should be < 50MB with optimized assets.