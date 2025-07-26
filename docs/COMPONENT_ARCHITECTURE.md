# Filter Component Architecture

## Component Library Structure

The filtering system is built using a reusable component library with consistent patterns and design system tokens.

### Core Filter Components

#### 1. **Main Orchestrator**
- `GameFilters.vue` - Main filter orchestrator component
  - Manages state coordination between all filter components
  - Handles desktop/mobile layout switching
  - Provides debounced filter updates (400ms)
  - Coordinates URL synchronization

#### 2. **Multi-Select Filter Components**
- `TagFilterMulti.vue` - Multi-tag selection with AND/OR logic
- `ChannelFilterMulti.vue` - Multi-channel selection with search
- Both follow consistent patterns:
  - Search functionality with debounced input
  - Selected items display with removal chips
  - Dropdown with progressive loading
  - Consistent styling and interaction patterns

#### 3. **Range & Advanced Filters**
- `PriceFilter.vue` - Dual-range price slider with presets
- `TimeFilter.vue` - Complex time-based filtering with presets
- `SortingOptions.vue` - Advanced sorting with contextual options

#### 4. **Mobile-Optimized Components**
- `MobileFilterModal.vue` - Bottom sheet modal container
- `MobileTagFilter.vue`, `MobileChannelFilter.vue`, etc. - Mobile-specific variants
- Touch-optimized interactions with swipe gestures
- 44px minimum touch targets

#### 5. **State Display Components**
- `AppliedFiltersBar.vue` - Shows active filters with removal options
- `SortIndicator.vue` - Visual sort state indicator
- `FilterPresets.vue` - Preset management interface

### Design System Consistency

#### CSS Classes & Patterns
All components follow consistent styling patterns:

```css
/* Input Controls */
.filter-input {
  @apply rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent focus:border-accent;
}

/* Filter Chips */
.filter-chip {
  @apply rounded-full bg-accent/20 px-3 py-1.5 text-sm text-accent;
}

/* Dropdown Styling */
.filter-dropdown {
  @apply absolute z-10 max-h-64 w-full overflow-y-auto rounded-sm border border-gray-600 bg-bg-card shadow-lg;
}
```

#### Color Tokens
- `text-text-primary` - Primary text
- `text-text-secondary` - Secondary/muted text  
- `bg-bg-primary` - Main background
- `bg-bg-secondary` - Secondary background
- `bg-bg-card` - Card/input backgrounds
- `accent` - Primary accent color
- `accent-hover` - Hover state

#### Spacing System
- `gap-1` (4px) - Tight spacing
- `gap-2` (8px) - Default spacing
- `gap-3` (12px) - Loose spacing
- `p-3` (12px) - Default padding
- `mb-3` (12px) - Default margin

### Component Communication Patterns

#### 1. **Event-Based Communication**
```javascript
// Consistent event naming pattern
emit('filters-changed', { selectedTags, tagLogic })
emit('channels-changed', { selectedChannels })
emit('time-filter-changed', timeFilterObject)
```

#### 2. **Prop Standardization**
```javascript
// All components accept initial state
props: {
  initialFilters: Object,
  // Component-specific data
  tagsWithCounts: Array,
  channelsWithCounts: Array
}
```

#### 3. **State Management Integration**
- Uses `useDebouncedFilters` composable for performance
- Immediate emit for critical operations (clear, presets)
- Debounced emit for gradual changes (typing, sliding)

### Mobile Responsiveness Strategy

#### Breakpoint System
- `md:hidden` - Mobile-only elements
- `hidden md:block` - Desktop-only elements
- Consistent breakpoint at 768px

#### Touch Optimization
- 44px minimum touch targets
- Horizontal scrolling for applied filters
- Bottom sheet modal pattern
- Swipe gestures for modal dismissal

#### Performance Considerations
- Progressive loading for large option lists
- Debounced search input (300ms)
- Virtual scrolling for channels/tags (when > 100 items)
- Efficient DOM updates using Vue's reactivity

### Error Handling & Edge Cases

#### Data Validation
- Empty search results handling
- Invalid filter combinations
- URL parameter validation
- Graceful degradation for missing data

#### User Experience
- Loading states for async operations
- Clear visual feedback for filter changes
- Consistent disabled states
- Accessible keyboard navigation

## Integration Points

### URL Synchronization
All filter components integrate with URL state through the main `GameFilters` component, ensuring:
- Bookmarkable filter states
- Browser history support
- Deep-linking compatibility

### Performance Monitoring
Components integrate with the performance monitoring system:
- Database query timing
- Filter update performance
- Component render optimization

### Preset System
Filter presets work seamlessly across all components:
- Consistent filter state structure
- Validation of preset compatibility
- Error handling for invalid presets