# Deployment

## Build and Deploy

```bash
uv run cubscrape build-db  # Generate fresh SQLite database from JSON data
npm run build              # Build Vue app, copies public/ to dist/ (including database via symlink)
# Deploy dist/ folder
```

The database file gets included because `public/data` is a symlink to `data/`, and Vite resolves symlinks when copying to `dist/`. The `dist/` folder contains everything needed for production.

## GitHub Actions

See `.github/workflows/pages-with-db.yml` for automated deployment to GitHub Pages.