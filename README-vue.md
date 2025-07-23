# Vue Game Discovery Interface

A modern Vue.js implementation of the game discovery interface, built with Vue 3, Vite, and Tailwind CSS.

## Features

- **Vue 3 Composition API** - Modern reactive framework
- **Tailwind CSS** - Utility-first styling
- **SQLite Integration** - Uses sql.js to load database client-side
- **Responsive Design** - Mobile-friendly grid layout
- **Real-time Filtering** - Filter by channel, rating, and tags
- **Sorting Options** - Sort by newest, rating, name, or release date

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Data Source

The app loads data from the SQLite database (`/data/games.db`) using sql.js, maintaining compatibility with the existing data structure while providing a modern Vue.js interface.

## Components

- **App.vue** - Main application with data loading and state management
- **GameCard.vue** - Individual game card component with ratings and links
- **GameFilters.vue** - Filter controls for channels, ratings, tags, and sorting

## URL

Development server runs at: http://localhost:5173/