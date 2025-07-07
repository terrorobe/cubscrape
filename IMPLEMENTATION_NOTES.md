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
- **Solution**: Track `videos_fetched_total` and use as offset
- **Benefit**: Efficient channel traversal, natural termination

### Bidirectional Demo/Full Game Detection
- **Challenge**: Videos can link to either demos or main games
- **Solution**: Detect relationships in both directions and fetch missing data
- **Demo Detection**: Search HTML for Steam app URLs containing "demo"
- **Full Game Detection**: Use Community Hub links and text patterns
- **Auto-fetching**: When updating one, automatically fetch the other if stale

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

# Test video fetching
python scraper/scraper.py --mode videos --max-new 5

# Test Steam data refresh
python scraper/scraper.py --mode steam --max-steam-updates 3 --steam-stale-days 0

# Test full pipeline
python scraper/scraper.py --max-new 10

# Test demo detection (force refresh BROTANK demo)
python scraper/scraper.py --mode steam --max-steam-updates 1 --steam-stale-days 0
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