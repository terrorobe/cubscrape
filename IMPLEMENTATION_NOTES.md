# Implementation Notes

## Key Technical Decisions

### YouTube Scraping Without API
- **Choice**: yt-dlp over YouTube Data API
- **Reason**: No API quotas, rate limiting, or key management
- **Implementation**: Uses playlist pagination with `playliststart`/`playlistend`
- **Reliability**: yt-dlp handles YouTube's anti-scraping measures

### Separated Data Storage
- **Videos**: `data/videos.json` - immutable once fetched
- **Steam Games**: `data/steam_games.json` - refreshed based on staleness
- **Benefit**: Independent update cycles, better cache efficiency

### Steam Review Extraction
- **Challenge**: Steam's inconsistent page structure for reviews
- **Solution**: Text-based regex parsing instead of DOM selectors
- **Patterns**: 
  ```regex
  # Overall Reviews
  r'All Reviews:\s*([^\n\(]+)\s*\((\d{1,3}(?:,\d{3})*)\s*\).*?(\d+)%.*?(\d{1,3}(?:,\d{3})*)'
  
  # Recent Reviews  
  r'Recent Reviews:\s*([^\n\(]+)\s*\((\d{1,3}(?:,\d{3})*)\s*\).*?(\d+)%.*?(\d{1,3}(?:,\d{3})*)'
  ```

### Smart Pagination Logic
- **Problem**: Resume scraping without refetching known videos
- **Solution**: Two-phase approach with smart starting position
- **Phase 1**: Lightweight ID fetching to identify new videos
- **Phase 2**: Full metadata fetching only for new videos
- **Smart Start**: Skip to `len(known_videos) - 10` to avoid redundant API calls
- **Benefit**: Dramatically reduced YouTube API usage and faster processing

### Platform Prioritization (Steam vs Itch.io)
- **Challenge**: Some games have both Steam and itch.io versions
- **Solution**: Prioritize Steam as primary platform, mark itch.io as demo/test version
- **Logic**: When both platforms detected, Steam becomes main game, itch.io flagged as `itch_is_demo: true`
- **Web Display**: Shows "Steam" link as primary + "Itch.io Demo" as secondary
- **Use Case**: Games like Simultree where itch.io hosts the demo/test version

### Bidirectional Demo/Full Game Detection
- **Challenge**: Videos can link to either demos or main games
- **Solution**: Detect relationships in both directions and fetch missing data
- **Demo Detection**: Search for `steam://install/` protocol links and JavaScript modal calls
- **Full Game Detection**: Use Community Hub links and text patterns
- **Auto-fetching**: When updating one, automatically fetch the other if stale
- **Fixed Issue**: Steam protocol links (`steam://install/3707160`) were missed by URL patterns

### Planned Release Date Extraction
- **Challenge**: Steam pages contain system requirements that match date patterns
- **Problem**: "Available... at 1080p resolution" was extracted as "at 1080"
- **Solution**: Added comprehensive validation to filter false matches
- **Invalid Patterns**: `at/while/during + numbers`, resolution specs (`1080p`), performance specs (`fps`)
- **Valid Patterns**: Actual dates, quarters (`Q1 2025`), years (`2025`), month-year combinations
- **Result**: Robust extraction that ignores system requirements and technical specifications

### Environment Configuration
- **Virtual Environment**: Uses `.venv/` directory with pip dependencies
- **Auto-activation**: `.envrc` file enables direnv integration for automatic venv activation
- **Config Loading**: `.env` file loaded at script startup
- **Example Setup**:
  ```bash
  # Virtual environment
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r scraper/requirements.txt
  
  # Configuration
  YOUTUBE_CHANNEL_URL=https://www.youtube.com/@idlecub/videos
  ```

## Performance Optimizations

### Batch Size Strategy
- **Current**: `batch_size = max_new_videos`
- **Reasoning**: Fetch exactly what's needed per iteration
- **Previous**: `max_new_videos * 3` (inefficient over-fetching)

### Review Data Priority
- **Overall Reviews**: Primary metric (long-term reputation)
- **Recent Reviews**: Secondary (recent sentiment)
- **Storage**: Both stored when available

### Web Interface Loading
- **Parallel Requests**: Loads `videos.json` and `steam_games.json` simultaneously
- **Client-side Join**: Combines data in browser for better caching
- **Smart Card Selection**: Shows demo cards for unreleased games with demos
- **Game Consolidation**: Eliminates duplicate games, aggregates videos
- **No Server**: Static files only, works with GitHub Pages

## Error Handling

### Steam Page Parsing
- **Fallback Chain**: Try multiple regex patterns
- **Graceful Degradation**: Continue processing if review extraction fails
- **Rate Limiting**: Built into requests, no explicit delays needed

### Video Processing
- **Skip on Error**: Individual video failures don't stop batch
- **Logging**: Comprehensive error logging for debugging
- **Resume**: Can restart from any point without losing progress

## Testing Strategy

### Manual Testing Commands
```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Test video fetching (uses smart pagination)
python scraper/scraper.py --mode videos --max-new 5

# Test Steam data refresh with enhanced logging
python scraper/scraper.py --mode steam --max-steam-updates 3 --steam-stale-days 0

# Test full pipeline
python scraper/scraper.py --max-new 10

# Reprocess existing video descriptions (apply new platform logic)
python scraper/scraper.py --mode reprocess

# Fetch single Steam app (useful for debugging)
python scraper/scraper.py --mode single-app --app-id 3586420

# Test demo detection (Iron Core example)
python scraper/scraper.py --mode single-app --app-id 3586420  # Main game
python scraper/scraper.py --mode single-app --app-id 3707160  # Demo
```

### Debug Script Pattern
```python
# Create test scripts for specific issues
# Example: test_lootun.py for review extraction debugging
```

## Future Considerations

### Scalability
- Current design handles channels with thousands of videos
- JSON files remain manageable for typical gaming channels
- Consider database if scaling beyond 10k+ games
- Demo relationship detection scales with main game count

### Additional Platforms
- **Itch.io**: Basic support implemented (URL + placeholder)
- **Epic Games**: Could be added with similar pattern
- **GOG**: API available for more comprehensive data
- **Console Platforms**: PlayStation/Xbox store integration possible

### Advanced Features
- **Price Tracking**: Historical price data over time
- **Release Notifications**: Alert for upcoming releases based on planned dates
- **Recommendation Engine**: Based on viewing patterns and demo play
- **Demo Performance Tracking**: Track which demos lead to purchases