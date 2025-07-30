# Performance Optimization Implementation Plan

## Phase 1: Database Optimization (Week 1)

### Critical Database Indexes
```sql
-- Search performance (10-100x improvement)
CREATE INDEX idx_games_name_lower ON games (LOWER(name));

-- Platform filtering with sorting (50-100x improvement)  
CREATE INDEX idx_games_platform_added ON games (platform, added_date DESC);

-- Date-based sorting optimization
CREATE INDEX idx_games_added_date ON games (added_date DESC);

-- Multi-column filtering support
CREATE INDEX idx_games_platform_price ON games (platform, price_cents);
```

### Full-Text Search Implementation
```sql
-- Replace LIKE queries with FTS5
CREATE VIRTUAL TABLE games_fts USING fts5(name, description, tags);
INSERT INTO games_fts SELECT id, name, description, tags FROM games;

-- Search query becomes:
SELECT g.* FROM games g 
JOIN games_fts f ON g.id = f.rowid 
WHERE games_fts MATCH 'search terms';
```

## Phase 2: Virtual Scrolling (Week 2)

### TanStack Virtual Integration
```bash
npm install @tanstack/vue-virtual
```

```vue
<script setup lang="ts">
import { useVirtualizer } from '@tanstack/vue-virtual'

const parentRef = ref<HTMLElement>()
const virtualizer = useVirtualizer({
  count: filteredGames.value.length,
  getScrollElement: () => parentRef.value,
  estimateSize: () => 350, // GameCard height
  overscan: 5, // Render 5 extra items for smoothness
})
</script>

<template>
  <div ref="parentRef" class="game-grid-container">
    <div 
      :style="{
        height: `${virtualizer.getTotalSize()}px`,
        width: '100%',
        position: 'relative',
      }"
    >
      <div
        v-for="virtualRow in virtualizer.getVirtualItems()"
        :key="virtualRow.index"
        :style="{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: `${virtualRow.size}px`,
          transform: `translateY(${virtualRow.start}px)`,
        }"
      >
        <GameCard
          :game="filteredGames[virtualRow.index]"
          :currency="filters.currency"
          :is-highlighted="highlightedGameId === filteredGames[virtualRow.index].id"
          @click="clearHighlight"
          @tag-click="handleTagClick"
        />
      </div>
    </div>
  </div>
</template>
```

### Architecture Preservation
- Keep all existing `filteredGames` reactive logic
- Maintain current filtering and sorting patterns
- Preserve URL state synchronization
- No changes to GameCard component needed

## Phase 3: Progressive & Lazy Loading (Week 3)

### Image Lazy Loading
```vue
<template>
  <img 
    :src="shouldLoadImage ? game.header_image : ''"
    :loading="'lazy'"
    @load="onImageLoad"
    class="game-image"
  />
</template>

<script setup lang="ts">
const imageIntersection = ref(false)
const shouldLoadImage = computed(() => imageIntersection.value)

onMounted(() => {
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting) {
        imageIntersection.value = true
        observer.disconnect()
      }
    },
    { rootMargin: '100px' }
  )
  
  if (gameCardRef.value) {
    observer.observe(gameCardRef.value)
  }
})
</script>
```

### Progressive Game Details Loading
```typescript
// Composable for progressive loading
export const useProgressiveGameLoading = () => {
  const loadVisualElements = (games: Game[]) => {
    // Load: thumbnails, titles, prices, platform indicators
    return games.map(game => ({
      ...game,
      visualDataLoaded: true,
      detailsLoaded: false
    }))
  }
  
  const loadGameDetails = async (game: Game) => {
    // Load on intersection: reviews, genres, release dates, descriptions
    if (!game.detailsLoaded) {
      game.detailsLoaded = true
      // Trigger reactive update for additional game metadata
    }
  }

  return { loadVisualElements, loadGameDetails }
}
```

### Skeleton States
```vue
<template>
  <div class="game-card">
    <!-- Always show visual elements -->
    <img :src="game.header_image" loading="lazy" />
    <h3>{{ game.name }}</h3>
    <div class="price">{{ game.price_final }}</div>
    
    <!-- Progressive details with skeleton -->
    <div v-if="game.detailsLoaded" class="game-details">
      <div class="rating">{{ game.positive_review_percentage }}%</div>
      <div class="genres">{{ game.genres.join(', ') }}</div>
    </div>
    <div v-else class="skeleton-details">
      <div class="skeleton-rating"></div>
      <div class="skeleton-genres"></div>
    </div>
  </div>
</template>
```

## Phase 4: Accessibility & Mobile (Week 4)

### Focus Management for Virtual Scrolling
```typescript
const useFocusManagement = () => {
  const maintainFocus = (scrollContainer: HTMLElement) => {
    const activeElement = document.activeElement
    if (scrollContainer.contains(activeElement)) {
      const focusPath = getFocusPath(activeElement)
      nextTick(() => restoreFocus(focusPath))
    }
  }

  const handleKeyboardNavigation = (event: KeyboardEvent) => {
    if (event.key === 'ArrowDown') {
      focusNextItem()
      event.preventDefault()
    } else if (event.key === 'ArrowUp') {
      focusPreviousItem()
      event.preventDefault()
    }
  }

  return { maintainFocus, handleKeyboardNavigation }
}
```

### ARIA Live Regions
```vue
<template>
  <div aria-live="polite" aria-label="Game list status" class="sr-only">
    Showing {{ virtualizer.getVirtualItems().length }} of {{ filteredGames.length }} games
  </div>
  
  <div 
    role="grid" 
    aria-label="Game discovery grid"
    @keydown="handleKeyboardNavigation"
  >
    <!-- Virtual scroller content -->
  </div>
</template>
```

### Mobile Touch Optimizations
```css
.game-grid-container {
  /* Enable momentum scrolling on iOS */
  -webkit-overflow-scrolling: touch;
  
  /* Prevent scroll chaining on mobile */
  overscroll-behavior: contain;
  
  /* Improve touch responsiveness */
  touch-action: pan-y;
}

.game-card {
  /* Ensure touch targets are 44px minimum */
  min-height: 44px;
  
  /* Prevent text selection on mobile */
  user-select: none;
  -webkit-user-select: none;
}
```

## Performance Targets

- **Initial render**: <1 second (currently ~22s)
- **Filter response**: <100ms (currently ~500ms)  
- **Search response**: <50ms with FTS5
- **Memory usage**: <100MB (currently ~128MB)
- **Scroll performance**: Consistent 60fps
- **Mobile experience**: Smooth touch interactions

## Expected Gains

- **Database optimization**: 10-100x search/filter performance
- **Virtual scrolling**: 39x faster render, 38% less memory
- **Progressive loading**: Faster perceived performance
- **Mobile optimization**: Industry-leading mobile UX