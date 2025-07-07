let videosData = {};
let steamData = {};
let filteredGames = [];

// Load and process data
async function loadData() {
    try {
        // Load both data files
        const [videosResponse, steamResponse] = await Promise.all([
            fetch('data/videos.json'),
            fetch('data/steam_games.json')
        ]);
        
        const videos = await videosResponse.json();
        const steam = await steamResponse.json();
        
        videosData = videos.videos || {};
        steamData = steam.games || {};
        
        processGames();
        populateFilters();
        renderGames();
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('gameGrid').innerHTML = '<div class="loading">Error loading game data. Please check back later.</div>';
    }
}

// Process and combine video and steam data
function processGames() {
    // First, collect all videos with game info
    const videosWithGames = Object.values(videosData)
        .filter(video => video.steam_app_id || video.itch_url)
        .map(video => {
            let gameData = {
                video_title: video.title,
                video_date: video.published_at,
                video_thumbnail: video.thumbnail,
                video_id: video.video_id,
                ...video
            };
            
            // Add Steam data if available
            if (video.steam_app_id && steamData[video.steam_app_id]) {
                gameData = { ...gameData, ...steamData[video.steam_app_id] };
                gameData.platform = 'steam';
                gameData.game_key = video.steam_app_id; // Unique identifier for grouping
                
                // If itch.io is also available and marked as demo, add it
                if (video.itch_is_demo && video.itch_url) {
                    gameData.itch_demo_url = video.itch_url;
                }
                
                // If this is a demo, also get full game data
                if (gameData.is_demo && gameData.full_game_app_id && steamData[gameData.full_game_app_id]) {
                    gameData.full_game = steamData[gameData.full_game_app_id];
                }
                
                // If this main game has a demo, get demo data
                if (gameData.has_demo && gameData.demo_app_id && steamData[gameData.demo_app_id]) {
                    gameData.demo = steamData[gameData.demo_app_id];
                }
            } else if (video.itch_url) {
                // For itch-only games, extract basic info from URL
                gameData.platform = 'itch';
                gameData.name = video.itch_url.split('/').pop() || 'Unknown Game';
                gameData.steam_url = video.itch_url; // Reuse for links
                gameData.header_image = null; // No image for itch games
                gameData.game_key = video.itch_url; // Unique identifier for grouping
            }
            
            return gameData;
        });
    
    // Group by game_key and consolidate
    const gameGroups = {};
    const demoToMainGameMap = {}; // Track demo -> main game relationships
    const mainGameToDemoMap = {}; // Track main game -> demo relationships
    
    // First pass: build relationship maps
    videosWithGames.forEach(video => {
        if (video.is_demo && video.full_game_app_id) {
            demoToMainGameMap[video.game_key] = video.full_game_app_id;
        }
        if (video.has_demo && video.demo_app_id) {
            mainGameToDemoMap[video.game_key] = video.demo_app_id;
        }
    });
    
    videosWithGames.forEach(video => {
        let displayKey = video.game_key;
        
        // Smart card selection: prefer demo for unreleased main games
        if (video.has_demo && video.demo_app_id && video.coming_soon) {
            // This is an unreleased main game with a demo - redirect to demo card
            displayKey = video.demo_app_id;
        }
        
        if (!gameGroups[displayKey]) {
            // Determine which game data to use for the card
            let cardGameData = video;
            
            // If we're showing a demo card for an unreleased main game, use demo data
            if (displayKey !== video.game_key && steamData[displayKey]) {
                cardGameData = {
                    ...video,
                    ...steamData[displayKey],
                    platform: 'steam',
                    game_key: displayKey,
                    // Keep the main game as full_game for display
                    full_game: video.has_demo ? {
                        ...video,
                        steam_app_id: video.game_key
                    } : undefined
                };
            }
            
            gameGroups[displayKey] = {
                ...cardGameData,
                videos: [],
                video_count: 0
            };
        }
        
        // Add this video to the group
        gameGroups[displayKey].videos.push({
            video_id: video.video_id,
            video_title: video.video_title,
            video_date: video.video_date,
            video_thumbnail: video.video_thumbnail
        });
        gameGroups[displayKey].video_count++;
        
        // Use the most recent video's info for display
        if (new Date(video.video_date) > new Date(gameGroups[displayKey].video_date)) {
            gameGroups[displayKey].video_title = video.video_title;
            gameGroups[displayKey].video_date = video.video_date;
            gameGroups[displayKey].video_thumbnail = video.video_thumbnail;
            gameGroups[displayKey].video_id = video.video_id;
        }
    });
    
    // Convert back to array and sort
    filteredGames = Object.values(gameGroups)
        .sort((a, b) => (b.positive_review_percentage || 0) - (a.positive_review_percentage || 0));
}

// Populate filter dropdowns
function populateFilters() {
    const allTags = new Set();
    
    filteredGames.forEach(game => {
        if (game.tags) {
            game.tags.forEach(tag => allTags.add(tag));
        }
    });
    
    const tagFilter = document.getElementById('tagFilter');
    tagFilter.innerHTML = '<option value="">All Tags</option>';
    
    Array.from(allTags).sort().forEach(tag => {
        const option = document.createElement('option');
        option.value = tag;
        option.textContent = tag;
        tagFilter.appendChild(option);
    });
}

// Apply filters and render
function applyFilters() {
    const releaseFilter = document.getElementById('releaseFilter').value;
    const platformFilter = document.getElementById('platformFilter').value;
    const ratingFilter = parseInt(document.getElementById('ratingFilter').value);
    const tagFilter = document.getElementById('tagFilter').value;
    const sortBy = document.getElementById('sortBy').value;
    
    let filtered = [...filteredGames];
    
    // Platform filter
    if (platformFilter === 'steam') {
        filtered = filtered.filter(game => game.platform === 'steam');
    } else if (platformFilter === 'itch') {
        filtered = filtered.filter(game => game.platform === 'itch');
    }
    
    // Release status filter (only applies to Steam games)
    if (releaseFilter === 'released') {
        filtered = filtered.filter(game => game.platform === 'itch' || (!game.coming_soon && !game.is_early_access));
    } else if (releaseFilter === 'early-access') {
        filtered = filtered.filter(game => game.platform === 'steam' && game.is_early_access);
    } else if (releaseFilter === 'coming-soon') {
        filtered = filtered.filter(game => game.platform === 'steam' && game.coming_soon);
    }
    
    // Rating filter
    if (ratingFilter > 0) {
        filtered = filtered.filter(game => (game.positive_review_percentage || 0) >= ratingFilter);
    }
    
    // Tag filter
    if (tagFilter) {
        filtered = filtered.filter(game => game.tags && game.tags.includes(tagFilter));
    }
    
    // Sorting
    if (sortBy === 'rating') {
        filtered.sort((a, b) => (b.positive_review_percentage || 0) - (a.positive_review_percentage || 0));
    } else if (sortBy === 'date') {
        filtered.sort((a, b) => new Date(b.video_date) - new Date(a.video_date));
    } else if (sortBy === 'name') {
        filtered.sort((a, b) => a.name.localeCompare(b.name));
    }
    
    renderFilteredGames(filtered);
}

// Render games to grid
function renderGames() {
    applyFilters();
}

function renderFilteredGames(games) {
    const gameGrid = document.getElementById('gameGrid');
    const gameCount = document.getElementById('gameCount');
    
    if (games.length === 0) {
        gameGrid.innerHTML = '<div class="no-results">No games match your filters.</div>';
        gameCount.textContent = 'No games found';
        return;
    }
    
    gameCount.textContent = `Showing ${games.length} games`;
    
    gameGrid.innerHTML = games.map(game => {
        const ratingClass = (game.positive_review_percentage && game.positive_review_percentage >= 80) ? 'positive' : 
                           (game.positive_review_percentage && game.positive_review_percentage >= 50) ? 'mixed' : 
                           (game.positive_review_percentage ? 'negative' : '');
        
        const statusText = game.platform === 'itch' ? 'Itch.io' :
                          game.is_demo ? 'Demo' :
                          (game.coming_soon ? 
                              (game.planned_release_date ? `Coming ${game.planned_release_date}` : 'Coming Soon') :
                          game.is_early_access ? 'Early Access' : 
                          (game.release_date ? `Released ${game.release_date}` : 'Released'));
        
        const statusClass = game.coming_soon ? 'coming-soon' :
                           game.is_early_access ? 'early-access' : 
                           game.is_demo ? 'demo' : '';
        
        const topTags = (game.tags || []).slice(0, 3);
        
        const formattedDate = new Date(game.video_date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
        
        // Show when Steam data was last updated
        const steamUpdateDate = game.last_updated ? new Date(game.last_updated).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        }) : 'Unknown';
        
        return `
            <div class="game-card" onclick="window.open('${game.steam_url}', '_blank')">
                ${game.header_image ? `<img class="game-image" src="${game.header_image}" alt="${game.name}" loading="lazy">` : ''}
                <div class="game-info">
                    <h3 class="game-title">${game.name}</h3>
                    <div class="game-meta">
                        ${game.platform === 'steam' && game.positive_review_percentage ? `
                            <span class="game-rating rating-${ratingClass}">
                                ${game.positive_review_percentage}% ${game.review_summary || 'Positive'}
                                ${game.review_count ? ` (${game.review_count.toLocaleString()})` : ''}
                            </span>
                            ${game.recent_review_percentage && game.recent_review_count ? `
                                <div class="recent-reviews">
                                    Recent: ${game.recent_review_percentage}% (${game.recent_review_count.toLocaleString()})
                                </div>
                            ` : ''}
                        ` : ''}
                        <span class="game-status ${statusClass ? 'status-' + statusClass : ''}">
                            ${statusText}
                            ${game.itch_demo_url ? ' + Itch Demo' : ''}
                        </span>
                        ${game.full_game ? `
                            <div class="full-game-info">
                                Full game: ${game.full_game.coming_soon ? 
                                    (game.full_game.planned_release_date ? `Coming ${game.full_game.planned_release_date}` : 'Coming Soon') : 
                                    game.full_game.is_early_access ? 'Early Access' :
                                    game.full_game.release_date ? `Released ${game.full_game.release_date}` : 'Released'}
                                ${game.full_game.price && !game.full_game.coming_soon ? ` - ${game.full_game.price}` : ''}
                            </div>
                        ` : ''}
                    </div>
                    ${game.price ? `<div class="game-price">${game.price}</div>` : ''}
                    ${topTags.length > 0 ? `
                        <div class="game-tags">
                            ${topTags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                        </div>
                    ` : ''}
                    <div class="video-info">
                        <div class="video-title">${game.video_title}</div>
                        <div class="video-date">Video: ${formattedDate}</div>
                        ${game.video_count > 1 ? `
                            <div class="video-count">Featured in ${game.video_count} videos</div>
                            <div class="video-expand" onclick="toggleVideos('${game.game_key}', event)">
                                <span class="expand-text">Show all videos</span>
                            </div>
                            <div class="all-videos" id="videos-${game.game_key}" style="display: none;">
                                ${game.videos.map(video => `
                                    <div class="video-item">
                                        <a href="https://youtube.com/watch?v=${video.video_id}" target="_blank">
                                            ${video.video_title}
                                        </a>
                                        <span class="video-item-date">${new Date(video.video_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                    <div class="game-links">
                        <a href="${game.steam_url}" target="_blank" onclick="event.stopPropagation()">
                            ${game.platform === 'itch' ? 'Itch.io' : 'Steam'}
                        </a>
                        ${game.itch_demo_url ? `
                            <a href="${game.itch_demo_url}" target="_blank" onclick="event.stopPropagation()">
                                Itch.io Demo
                            </a>
                        ` : ''}
                        <a href="https://youtube.com/watch?v=${game.video_id}" target="_blank" onclick="event.stopPropagation()">YouTube</a>
                    </div>
                    ${game.platform === 'steam' ? `<div class="update-info">Steam data: ${steamUpdateDate}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// Toggle videos display
function toggleVideos(gameKey, event) {
    event.stopPropagation(); // Prevent card click
    const videosDiv = document.getElementById(`videos-${gameKey}`);
    const expandText = event.target.querySelector('.expand-text') || event.target;
    
    if (videosDiv.style.display === 'none') {
        videosDiv.style.display = 'block';
        expandText.textContent = 'Hide videos';
    } else {
        videosDiv.style.display = 'none';
        expandText.textContent = 'Show all videos';
    }
}

// Event listeners
document.getElementById('releaseFilter').addEventListener('change', applyFilters);
document.getElementById('platformFilter').addEventListener('change', applyFilters);
document.getElementById('ratingFilter').addEventListener('change', applyFilters);
document.getElementById('tagFilter').addEventListener('change', applyFilters);
document.getElementById('sortBy').addEventListener('change', applyFilters);

// Initialize
loadData();