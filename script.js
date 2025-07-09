let videosData = {};
let steamData = {};
let otherGamesData = {};
let filteredGames = [];
let channels = {};

// Constants
const MAX_TAGS_DISPLAY = 3;
const PLATFORMS = {
    STEAM: 'steam',
    ITCH: 'itch',
    CRAZYGAMES: 'crazygames'
};
const RELEASE_FILTERS = {
    ALL: 'all',
    RELEASED: 'released',
    EARLY_ACCESS: 'early-access',
    COMING_SOON: 'coming-soon'
};

// Utility Functions
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function getStatusText(game) {
    if (game.platform === PLATFORMS.ITCH) return 'Itch.io';
    if (game.platform === PLATFORMS.CRAZYGAMES) return 'CrazyGames';
    if (game.is_demo) return 'Demo';
    if (game.coming_soon) return game.planned_release_date || 'Coming Soon';
    if (game.is_early_access) return 'Early Access';
    return game.release_date ? `Released ${game.release_date}` : 'Released';
}

function getStatusClass(game) {
    if (game.coming_soon) return 'coming-soon';
    if (game.is_early_access) return 'early-access';
    if (game.is_demo) return 'demo';
    return '';
}

function getRatingClass(percentage) {
    if (!percentage) return '';
    if (percentage >= 80) return 'positive';
    if (percentage >= 50) return 'mixed';
    return 'negative';
}

// Load and process data
async function loadData() {
    try {
        // Load config first
        const configResponse = await fetch('config.json');
        const config = await configResponse.json();
        channels = config.channels || {};
        
        // Load Steam data
        const steamResponse = await fetch('data/steam_games.json');
        const steam = await steamResponse.json();
        steamData = steam.games || {};
        
        // Load other games data (itch.io, crazygames)
        try {
            const otherGamesResponse = await fetch('data/other_games.json');
            const otherGames = await otherGamesResponse.json();
            otherGamesData = otherGames.games || {};
        } catch (error) {
            console.warn('No other games data found:', error);
            otherGamesData = {};
        }
        
        // Load all channel video files
        const channelKeys = Object.keys(channels);
        const videoPromises = channelKeys.map(channelId => 
            fetch(`data/videos-${channelId}.json`).then(response => {
                if (!response.ok) {
                    console.warn(`No video data found for channel ${channelId}`);
                    return { videos: {} };
                }
                return response.json();
            }).catch(error => {
                console.warn(`Error loading videos for channel ${channelId}:`, error);
                return { videos: {} };
            })
        );
        
        const videoResults = await Promise.all(videoPromises);
        
        // Combine all video data with channel attribution
        videosData = {};
        channelKeys.forEach((channelId, index) => {
            const channelVideos = videoResults[index].videos || {};
            Object.keys(channelVideos).forEach(videoId => {
                videosData[videoId] = {
                    ...channelVideos[videoId],
                    channel_id: channelId,
                    channel_name: channels[channelId].name
                };
            });
        });
        
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
    const videosWithGames = collectVideosWithGames();
    const gameGroups = groupVideosByGame(videosWithGames);
    
    // Convert back to array and sort
    filteredGames = Object.values(gameGroups)
        .sort((a, b) => (b.positive_review_percentage || 0) - (a.positive_review_percentage || 0));
}

function collectVideosWithGames() {
    return Object.values(videosData)
        .filter(video => video.steam_app_id || video.itch_url || video.crazygames_url)
        .map(video => addGameMetadata(video))
        .filter(game => game !== null && game.name);
}

function addGameMetadata(video) {
    let gameData = {
        video_title: video.title,
        video_date: video.published_at,
        video_thumbnail: video.thumbnail,
        video_id: video.video_id,
        ...video
    };
    
    const platformHandler = {
        [PLATFORMS.STEAM]: () => handleSteamGame(video, gameData),
        [PLATFORMS.ITCH]: () => handleItchGame(video, gameData),
        [PLATFORMS.CRAZYGAMES]: () => handleCrazyGamesGame(video, gameData)
    };
    
    if (video.steam_app_id) {
        return platformHandler[PLATFORMS.STEAM]();
    } else if (video.itch_url) {
        return platformHandler[PLATFORMS.ITCH]();
    } else if (video.crazygames_url) {
        return platformHandler[PLATFORMS.CRAZYGAMES]();
    }
    
    return null;
}

function handleSteamGame(video, gameData) {
    if (!steamData[video.steam_app_id]) {
        return null; // Steam app ID exists but data is missing
    }
    
    gameData = { ...gameData, ...steamData[video.steam_app_id] };
    gameData.platform = PLATFORMS.STEAM;
    gameData.game_key = video.steam_app_id;
    
    // Add additional platform links
    if (video.itch_is_demo && video.itch_url) {
        gameData.itch_demo_url = video.itch_url;
    }
    if (video.crazygames_url) {
        gameData.crazygames_url = video.crazygames_url;
    }
    
    // Handle demo/full game relationships
    if (gameData.is_demo && gameData.full_game_app_id && steamData[gameData.full_game_app_id]) {
        gameData.full_game = steamData[gameData.full_game_app_id];
    }
    if (gameData.has_demo && gameData.demo_app_id && steamData[gameData.demo_app_id]) {
        gameData.demo = steamData[gameData.demo_app_id];
    }
    
    return gameData;
}

function handleItchGame(video, gameData) {
    gameData.platform = PLATFORMS.ITCH;
    
    if (otherGamesData[video.itch_url]) {
        gameData = { ...gameData, ...otherGamesData[video.itch_url] };
    } else {
        gameData.name = video.itch_url.split('/').pop() || 'Unknown Game';
    }
    
    gameData.steam_url = video.itch_url;
    gameData.game_key = video.itch_url;
    
    if (video.crazygames_url) {
        gameData.crazygames_url = video.crazygames_url;
    }
    
    return gameData;
}

function handleCrazyGamesGame(video, gameData) {
    gameData.platform = PLATFORMS.CRAZYGAMES;
    
    if (otherGamesData[video.crazygames_url]) {
        gameData = { ...gameData, ...otherGamesData[video.crazygames_url] };
    } else {
        const gameName = video.crazygames_url.split('/').pop() || 'Unknown Game';
        gameData.name = gameName.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    gameData.steam_url = video.crazygames_url;
    gameData.game_key = video.crazygames_url;
    
    return gameData;
}

function groupVideosByGame(videosWithGames) {
    const gameGroups = {};
    
    videosWithGames.forEach(video => {
        let displayKey = getDisplayKey(video);
        
        if (!gameGroups[displayKey]) {
            gameGroups[displayKey] = createGameGroup(video, displayKey);
        }
        
        addVideoToGroup(gameGroups[displayKey], video);
    });
    
    return gameGroups;
}

function getDisplayKey(video) {
    // Smart card selection: prefer demo for unreleased main games
    if (video.has_demo && video.demo_app_id && video.coming_soon) {
        return video.demo_app_id;
    }
    return video.game_key;
}

function createGameGroup(video, displayKey) {
    let cardGameData = video;
    
    // If we're showing a demo card for an unreleased main game, use demo data
    if (displayKey !== video.game_key && steamData[displayKey]) {
        cardGameData = {
            ...video,
            ...steamData[displayKey],
            platform: PLATFORMS.STEAM,
            game_key: displayKey,
            full_game: video.has_demo ? {
                ...video,
                steam_app_id: video.game_key
            } : undefined
        };
    }
    
    return {
        ...cardGameData,
        videos: [],
        video_count: 0
    };
}

function addVideoToGroup(gameGroup, video) {
    gameGroup.videos.push({
        video_id: video.video_id,
        video_title: video.video_title,
        video_date: video.video_date,
        video_thumbnail: video.video_thumbnail,
        channel_id: video.channel_id,
        channel_name: video.channel_name
    });
    gameGroup.video_count++;
    
    // Use the most recent video's info for display
    if (new Date(video.video_date) > new Date(gameGroup.video_date)) {
        gameGroup.video_title = video.video_title;
        gameGroup.video_date = video.video_date;
        gameGroup.video_thumbnail = video.video_thumbnail;
        gameGroup.video_id = video.video_id;
    }
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
    
    // Populate channel filter
    const channelFilter = document.getElementById('channelFilter');
    channelFilter.innerHTML = '<option value="">All Channels</option>';
    
    Object.keys(channels).forEach(channelId => {
        const option = document.createElement('option');
        option.value = channelId;
        option.textContent = channels[channelId].name;
        channelFilter.appendChild(option);
    });
}

// Apply filters and render
function applyFilters() {
    const releaseFilter = document.getElementById('releaseFilter').value;
    const platformFilter = document.getElementById('platformFilter').value;
    const ratingFilter = parseInt(document.getElementById('ratingFilter').value);
    const tagFilter = document.getElementById('tagFilter').value;
    const channelFilter = document.getElementById('channelFilter').value;
    const sortBy = document.getElementById('sortBy').value;
    
    let filtered = [...filteredGames];
    
    // Platform filter
    if (platformFilter !== 'all') {
        filtered = filtered.filter(game => game.platform === platformFilter);
    }
    
    // Release status filter
    filtered = applyReleaseFilter(filtered, releaseFilter);
    
    // Rating filter
    if (ratingFilter > 0) {
        filtered = filtered.filter(game => (game.positive_review_percentage || 0) >= ratingFilter);
    }
    
    // Tag filter
    if (tagFilter) {
        filtered = filtered.filter(game => game.tags && game.tags.includes(tagFilter));
    }
    
    // Channel filter
    if (channelFilter) {
        filtered = filtered.filter(game => game.channel_id === channelFilter);
    }
    
    // Sorting
    const sortFunctions = {
        rating: (a, b) => (b.positive_review_percentage || 0) - (a.positive_review_percentage || 0),
        date: (a, b) => new Date(b.video_date) - new Date(a.video_date),
        name: (a, b) => a.name.localeCompare(b.name)
    };
    
    if (sortFunctions[sortBy]) {
        filtered.sort(sortFunctions[sortBy]);
    }
    
    renderFilteredGames(filtered);
}

// Render games to grid
function renderGames() {
    applyFilters();
}

function applyReleaseFilter(games, releaseFilter) {
    const filterMap = {
        [RELEASE_FILTERS.RELEASED]: (game) => 
            game.platform === PLATFORMS.ITCH || 
            game.platform === PLATFORMS.CRAZYGAMES || 
            (game.platform === PLATFORMS.STEAM && !game.coming_soon && !game.is_early_access && !game.is_demo),
        [RELEASE_FILTERS.EARLY_ACCESS]: (game) => 
            game.platform === PLATFORMS.STEAM && game.is_early_access,
        [RELEASE_FILTERS.COMING_SOON]: (game) => 
            game.platform === PLATFORMS.STEAM && game.coming_soon
    };
    
    const filter = filterMap[releaseFilter];
    return filter ? games.filter(filter) : games;
}

function generateChannelGroupedVideos(videos) {
    const videosByChannel = groupVideosByChannel(videos);
    return generateChannelHTML(videosByChannel);
}

function groupVideosByChannel(videos) {
    const videosByChannel = {};
    
    videos.forEach(video => {
        const channelKey = video.channel_id || 'unknown';
        if (!videosByChannel[channelKey]) {
            videosByChannel[channelKey] = {
                name: video.channel_name || 'Unknown Channel',
                videos: []
            };
        }
        videosByChannel[channelKey].videos.push(video);
    });
    
    // Sort videos within each channel by date (newest first)
    Object.values(videosByChannel).forEach(channel => {
        channel.videos.sort((a, b) => new Date(b.video_date) - new Date(a.video_date));
    });
    
    return videosByChannel;
}

function generateChannelHTML(videosByChannel) {
    return Object.entries(videosByChannel).map(([channelId, channel]) => {
        const videoItems = channel.videos.map(generateVideoItemHTML).join('');
        return `
            <div class="channel-group">
                <div class="channel-header">${channel.name} (${channel.videos.length})</div>
                ${videoItems}
            </div>
        `;
    }).join('');
}

function generateVideoItemHTML(video) {
    return `
        <div class="video-item">
            <a href="https://youtube.com/watch?v=${video.video_id}" target="_blank">
                ${video.video_title}
            </a>
            <span class="video-item-date">${formatDate(video.video_date)}</span>
        </div>
    `;
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
    gameGrid.innerHTML = games.map(generateGameCardHTML).join('');
}

function generateGameCardHTML(game) {
    const statusText = getStatusText(game);
    const statusClass = getStatusClass(game);
    const ratingClass = getRatingClass(game.positive_review_percentage);
    const topTags = (game.tags || []).slice(0, MAX_TAGS_DISPLAY);
    
    return `
        <div class="game-card" onclick="window.open('${game.steam_url}', '_blank')">
            ${generateGameImageHTML(game)}
            <div class="game-info">
                ${generateGameTitleHTML(game)}
                ${generateGameMetaHTML(game, statusText, statusClass, ratingClass)}
                ${generateGamePriceHTML(game)}
                ${generateGameTagsHTML(topTags)}
                ${generateVideoInfoHTML(game)}
                ${generateGameLinksHTML(game)}
                ${generateUpdateInfoHTML(game)}
            </div>
        </div>
    `;
}

function generateGameImageHTML(game) {
    return game.header_image ? 
        `<img class="game-image" src="${game.header_image}" alt="${game.name}" loading="lazy">` : '';
}

function generateGameTitleHTML(game) {
    return `<h3 class="game-title">${game.name || 'Unknown Game'}</h3>`;
}

function generateGameMetaHTML(game, statusText, statusClass, ratingClass) {
    const reviewHTML = generateReviewHTML(game, ratingClass);
    const statusHTML = generateStatusHTML(statusText, statusClass, game);
    const fullGameHTML = generateFullGameHTML(game);
    
    return `
        <div class="game-meta">
            ${reviewHTML}
            ${statusHTML}
            ${fullGameHTML}
        </div>
    `;
}

function generateReviewHTML(game, ratingClass) {
    // Show "Too few reviews" block when there are reviews but insufficient for percentage
    if (game.insufficient_reviews || (game.review_count !== undefined && !game.positive_review_percentage)) {
        return `
            <span class="game-rating rating-insufficient">
                Too few reviews (${game.review_count || 0})
            </span>
        `;
    }
    
    // Show normal review percentage when available
    if (!game.positive_review_percentage) return '';
    
    const recentReviewHTML = game.recent_review_percentage && game.recent_review_count ? `
        <div class="recent-reviews">
            Recent: ${game.recent_review_percentage}% (${game.recent_review_count.toLocaleString()})
        </div>
    ` : '';
    
    return `
        <span class="game-rating rating-${ratingClass}">
            ${game.positive_review_percentage}% ${game.review_summary || 'Positive'}
            ${game.review_count ? ` (${game.review_count.toLocaleString()})` : ''}
        </span>
        ${recentReviewHTML}
    `;
}

function generateStatusHTML(statusText, statusClass, game) {
    return `
        <span class="game-status ${statusClass ? 'status-' + statusClass : ''}">
            ${statusText}
            ${game.itch_demo_url ? ' + Itch Demo' : ''}
        </span>
    `;
}

function generateFullGameHTML(game) {
    if (!game.full_game) return '';
    
    const fullGameStatus = getStatusText(game.full_game);
    const priceInfo = game.full_game.price && !game.full_game.coming_soon ? ` - ${game.full_game.price}` : '';
    
    return `
        <div class="full-game-info">
            Full game: ${fullGameStatus}${priceInfo}
        </div>
    `;
}

function generateGamePriceHTML(game) {
    return game.price ? `<div class="game-price">${game.price}</div>` : '';
}

function generateGameTagsHTML(topTags) {
    if (topTags.length === 0) return '';
    
    return `
        <div class="game-tags">
            ${topTags.map(tag => `<span class="tag">${tag}</span>`).join('')}
        </div>
    `;
}

function generateVideoInfoHTML(game) {
    const channelInfo = generateChannelInfoHTML(game);
    const multiVideoHTML = generateMultiVideoHTML(game);
    
    return `
        <div class="video-info">
            <div class="video-title">${game.video_title}</div>
            <div class="video-date">Video: ${formatDate(game.video_date)}</div>
            ${channelInfo}
            ${multiVideoHTML}
        </div>
    `;
}

function generateChannelInfoHTML(game) {
    const uniqueChannels = [...new Set(game.videos.map(v => v.channel_name))];
    const channelText = uniqueChannels.length > 1 ? 
        `Channels: ${uniqueChannels.join(', ')}` : 
        `Channel: ${game.channel_name}`;
    
    return `<div class="channel-info">${channelText}</div>`;
}

function generateMultiVideoHTML(game) {
    if (game.video_count <= 1) return '';
    
    return `
        <div class="video-count">Featured in ${game.video_count} videos</div>
        <div class="video-expand" onclick="toggleVideos('${game.game_key}', event)">
            <span class="expand-text">Show all videos</span>
        </div>
        <div class="all-videos" id="videos-${game.game_key}" style="display: none;">
            ${generateChannelGroupedVideos(game.videos)}
        </div>
    `;
}

function generateGameLinksHTML(game) {
    const platformName = game.platform === PLATFORMS.ITCH ? 'Itch.io' : 
                        game.platform === PLATFORMS.CRAZYGAMES ? 'CrazyGames' : 'Steam';
    
    const itchDemoLink = game.itch_demo_url ? `
        <a href="${game.itch_demo_url}" target="_blank" onclick="event.stopPropagation()">
            Itch.io Demo
        </a>
    ` : '';
    
    const crazyGamesLink = game.crazygames_url && game.platform !== PLATFORMS.CRAZYGAMES ? `
        <a href="${game.crazygames_url}" target="_blank" onclick="event.stopPropagation()">
            CrazyGames
        </a>
    ` : '';
    
    return `
        <div class="game-links">
            <a href="${game.steam_url}" target="_blank" onclick="event.stopPropagation()">
                ${platformName}
            </a>
            ${itchDemoLink}
            ${crazyGamesLink}
            <a href="https://youtube.com/watch?v=${game.video_id}" target="_blank" onclick="event.stopPropagation()">YouTube</a>
        </div>
    `;
}

function generateUpdateInfoHTML(game) {
    if (!game.last_updated) return '';
    
    const platformName = game.platform === PLATFORMS.STEAM ? 'Steam' : game.platform;
    return `<div class="update-info">${platformName} data: ${formatDate(game.last_updated)}</div>`;
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
document.getElementById('channelFilter').addEventListener('change', applyFilters);
document.getElementById('sortBy').addEventListener('change', applyFilters);

// Initialize
loadData();