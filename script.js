let videosData = {};
let steamData = {};
let otherGamesData = {};
let filteredGames = [];
let channels = {};

// Performance tracking (disable for production)
const PERFORMANCE_TRACKING = window.location.hostname === 'localhost' || window.location.search.includes('debug=true');

const performanceTracker = {
    startTimer(name) {
        if (!PERFORMANCE_TRACKING) return;
        performance.mark(`${name}-start`);
        console.time(name);
    },
    
    endTimer(name) {
        if (!PERFORMANCE_TRACKING) return;
        performance.mark(`${name}-end`);
        performance.measure(name, `${name}-start`, `${name}-end`);
        console.timeEnd(name);
        
        const measure = performance.getEntriesByName(name)[0];
        console.log(`📊 ${name}: ${measure.duration.toFixed(2)}ms`);
    },
    
    measureImageLoading() {
        if (!PERFORMANCE_TRACKING) return;
        const images = document.querySelectorAll('img');
        let loadedCount = 0;
        const totalImages = images.length;
        const startTime = performance.now();
        
        console.log(`🖼️ Starting to load ${totalImages} images`);
        
        images.forEach((img, index) => {
            if (img.complete) {
                loadedCount++;
            } else {
                img.addEventListener('load', () => {
                    loadedCount++;
                    if (loadedCount === totalImages) {
                        const duration = performance.now() - startTime;
                        console.log(`🖼️ All ${totalImages} images loaded: ${duration.toFixed(2)}ms`);
                    }
                });
            }
        });
        
        if (loadedCount === totalImages) {
            console.log('🖼️ All images already loaded');
        }
    },
    
    measureMemoryUsage() {
        if (!PERFORMANCE_TRACKING) return;
        if (performance.memory) {
            const used = Math.round(performance.memory.usedJSHeapSize / 1024 / 1024);
            const total = Math.round(performance.memory.totalJSHeapSize / 1024 / 1024);
            console.log(`🧠 Memory usage: ${used}MB / ${total}MB`);
        }
    }
};

// Lazy loading image observer
const imageObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src; // Load the actual image
            img.classList.remove('lazy-image'); // Remove lazy class
            imageObserver.unobserve(img); // Stop observing this image
        }
    });
}, {
    // Start loading when image is 500px from entering viewport
    rootMargin: '500px'
});

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
    // Use unified display status if available, otherwise fallback to original logic
    if (game.display_status) {
        return game.display_status;
    }
    
    if (game.platform === PLATFORMS.ITCH) {
        return 'Itch.io';
    }
    if (game.platform === PLATFORMS.CRAZYGAMES) {
        return 'CrazyGames';
    }
    if (game.is_demo) {
        return 'Demo';
    }
    if (game.coming_soon) {
        return game.planned_release_date || 'Coming Soon';
    }
    if (game.is_early_access) {
        return 'Early Access';
    }
    return game.release_date ? `Released ${game.release_date}` : 'Released';
}

function getStatusClass(game) {
    // Use unified display status class if available, otherwise fallback to original logic
    if (game.display_status_class !== undefined) {
        return game.display_status_class;
    }
    
    if (game.is_demo) {
        return 'demo';
    }
    if (game.coming_soon) {
        return 'coming-soon';
    }
    if (game.is_early_access) {
        return 'early-access';
    }
    return '';
}

function getRatingClass(percentage) {
    if (!percentage) {
        return '';
    }
    if (percentage >= 80) {
        return 'positive';
    }
    if (percentage >= 50) {
        return 'mixed';
    }
    return 'negative';
}

// Load and process data
async function loadData() {
    performanceTracker.startTimer('loadData');
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
        loadFiltersFromURL();
        renderGames();
        
        performanceTracker.endTimer('loadData');
        performanceTracker.measureMemoryUsage();
        
        // Images now load progressively with lazy loading
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('gameGrid').innerHTML = '<div class="loading">Error loading game data. Please check back later.</div>';
        performanceTracker.endTimer('loadData');
    }
}

// Process and combine video and steam data
function processGames() {
    const videosWithGames = collectVideosWithGames();
    const gameGroups = groupVideosByGame(videosWithGames);
    
    // Create unified game data for cleaner display
    const unifiedGames = createUnifiedGameData(gameGroups);
    
    // Convert back to array and sort
    filteredGames = unifiedGames
        .sort((a, b) => (b.positive_review_percentage || 0) - (a.positive_review_percentage || 0));
}

function collectVideosWithGames() {
    return Object.values(videosData)
        .filter(video => video.steam_app_id || video.itch_url || video.crazygames_url)
        .map(video => addGameMetadata(video))
        .filter(game => game !== null && game.name);
}

function addGameMetadata(video) {
    const gameData = {
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
        const displayKey = getDisplayKey(video);
        
        if (!gameGroups[displayKey]) {
            gameGroups[displayKey] = createGameGroup(video, displayKey);
        }
        
        addVideoToGroup(gameGroups[displayKey], video);
    });
    
    return gameGroups;
}

// Helper functions for unified game data creation
function getDemoReviewData(game) {
    // Get review data from the appropriate source
    const source = game.original_demo_data || game;
    return {
        positive_review_percentage: source.positive_review_percentage,
        review_count: source.review_count,
        review_summary: source.review_summary,
        recent_review_percentage: source.recent_review_percentage,
        recent_review_count: source.recent_review_count,
        insufficient_reviews: source.insufficient_reviews
    };
}

function getUnifiedDisplayProperties(game, isReleased) {
    const baseProperties = {
        card_type: 'unified',
        display_name: game.name
    };
    
    if (isReleased) {
        return {
            ...baseProperties,
            display_status: game.full_game.release_date ? 
                `Released ${game.full_game.release_date}` : 'Released',
            display_status_class: '',
            display_image: game.original_demo_data?.header_image || game.header_image,
            display_price: game.full_game.price,
            is_demo: false
        };
    }
    
    // Unreleased game - show demo content
    const fullGame = game.full_game || game;
    let status, statusClass;
    
    if (fullGame.coming_soon) {
        status = fullGame.planned_release_date || 'Coming Soon';
        statusClass = 'coming-soon';
    } else if (fullGame.is_early_access) {
        status = 'Early Access';
        statusClass = 'early-access';
    } else {
        status = 'Coming Soon';
        statusClass = 'coming-soon';
    }
    
    return {
        ...baseProperties,
        display_status: status,
        display_status_class: statusClass,
        display_image: game.original_demo_data?.header_image || game.header_image,
        header_image: game.original_demo_data?.header_image || game.header_image,
        display_price: null,
        is_demo: true
    };
}

function createUnifiedDisplayLinks(game) {
    const demoId = game.original_demo_data?.steam_app_id || 
                   game.demo?.steam_app_id || 
                   game.steam_app_id;
    const fullGameId = game.full_game?.steam_app_id || 
                       game.steam_app_id;
    
    return {
        main: fullGameId ? `https://store.steampowered.com/app/${fullGameId}` : game.steam_url,
        demo: demoId ? `https://store.steampowered.com/app/${demoId}` : null
    };
}

function createUnifiedGameData(gameGroups) {
    return Object.values(gameGroups).map(game => {
        // Determine card type and unified display properties
        // Use shallow copy - deep copy was losing review data
        const unifiedGame = { ...game };
        
        // Check if this should be a unified card
        const isUnifiedCard = (game.is_demo && game.full_game && game.full_game.steam_app_id) || 
                            (game.has_demo && game.demo && game.original_demo_data);
        
        if (isUnifiedCard) {
            // Demo+Full game unified card
            const fullGame = game.full_game || game;
            const isReleased = fullGame.release_date && 
                             !fullGame.coming_soon && 
                             !fullGame.is_early_access;
            
            // Get display properties based on release status
            const displayProps = getUnifiedDisplayProperties(game, isReleased);
            Object.assign(unifiedGame, displayProps);
            
            // Always use demo review data for unified cards
            const reviewData = getDemoReviewData(game);
            Object.assign(unifiedGame, reviewData);
            
            // Set up unified links
            unifiedGame.display_links = createUnifiedDisplayLinks(game);
            
            // Set main card link - demos link to demo page, released games to full game
            unifiedGame.steam_url = unifiedGame.is_demo ? 
                unifiedGame.display_links.demo : 
                unifiedGame.display_links.main;
            
            // Clean up to avoid confusion
            delete unifiedGame.full_game;
            delete unifiedGame.demo;
            delete unifiedGame.original_demo_data;
            
        } else if (game.has_demo && game.demo_app_id) {
            // Full game with demo available
            unifiedGame.card_type = 'full_with_demo';
            unifiedGame.display_name = game.name;
            unifiedGame.display_status = game.coming_soon ? (game.planned_release_date || 'Coming Soon') : 
                game.is_early_access ? 'Early Access' :
                    game.release_date ? `Released ${game.release_date}` : 'Released';
            unifiedGame.display_status_class = game.coming_soon ? 'coming-soon' : 
                game.is_early_access ? 'early-access' : '';
            unifiedGame.display_image = game.header_image;
            unifiedGame.display_price = game.price;
            unifiedGame.display_links = {
                main: game.steam_url,
                demo: game.demo_app_id ? `https://store.steampowered.com/app/${game.demo_app_id}` : null
            };
        } else {
            // Regular single game (demo-only, full-only, or other platforms)
            unifiedGame.card_type = 'single';
            unifiedGame.display_name = game.name;
            unifiedGame.display_status = game.platform === PLATFORMS.ITCH ? 'Itch.io' :
                game.platform === PLATFORMS.CRAZYGAMES ? 'CrazyGames' :
                    game.is_demo ? 'Demo' :
                        game.coming_soon ? (game.planned_release_date || 'Coming Soon') :
                            game.is_early_access ? 'Early Access' :
                                game.release_date ? `Released ${game.release_date}` : 'Released';
            unifiedGame.display_status_class = game.coming_soon ? 'coming-soon' :
                game.is_early_access ? 'early-access' :
                    game.is_demo ? 'demo' : '';
            unifiedGame.display_image = game.header_image;
            unifiedGame.display_price = game.price;
            unifiedGame.display_links = {
                main: game.steam_url,
                demo: null
            };
        }
        
        return unifiedGame;
    });
}

function getDisplayKey(video) {
    // Smart card selection: prefer full game for released games, demo for unreleased
    if (video.has_demo && video.demo_app_id && video.coming_soon) {
        return video.demo_app_id;
    }
    
    // If this is a demo video, check if full game exists and prefer full game
    if (video.is_demo && video.full_game_app_id && steamData[video.full_game_app_id]) {
        return video.full_game_app_id;
    }
    
    return video.game_key;
}

function createGameGroup(video, displayKey) {
    let cardGameData = video;
    
    // If we're using a different display key, get the appropriate game data
    if (displayKey !== video.game_key && steamData[displayKey]) {
        cardGameData = {
            ...video,
            ...steamData[displayKey],
            platform: PLATFORMS.STEAM,
            game_key: displayKey
        };
        
        // Handle demo/full game relationships
        if (video.has_demo && video.demo_app_id) {
            // Showing demo card for unreleased main game - use demo data for visuals
            const demoData = steamData[video.demo_app_id];
            if (demoData && video.coming_soon) {
                // Use demo image and data for unreleased games
                cardGameData = {
                    ...cardGameData,
                    header_image: demoData.header_image,
                    screenshots: demoData.screenshots,
                    is_demo: demoData.is_demo
                };
            }
            cardGameData.full_game = {
                ...video,
                steam_app_id: video.game_key
            };
        } else if (video.is_demo && video.full_game_app_id) {
            // Showing full game card but this video is from demo
            // Store the original demo data before it gets overwritten
            const originalDemoData = {
                ...steamData[video.game_key]
            };
            
            cardGameData.demo = {
                ...originalDemoData,
                steam_app_id: video.game_key
            };
            
            // For unreleased full games, we need to preserve demo info
            const fullGameData = steamData[video.full_game_app_id];
            if (fullGameData && fullGameData.coming_soon) {
                // Preserve demo's essential data for unified card creation
                cardGameData.demo_review_count = originalDemoData.review_count;
                cardGameData.demo_positive_review_percentage = originalDemoData.positive_review_percentage;
                cardGameData.demo_review_summary = originalDemoData.review_summary;
                cardGameData.demo_header_image = originalDemoData.header_image;
                cardGameData.original_demo_data = originalDemoData;
            }
        }
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
    
    // Update URL with current filter values
    updateURLParams({
        release: releaseFilter || null,
        platform: platformFilter !== 'all' ? platformFilter : null,
        rating: ratingFilter > 0 ? ratingFilter : null,
        tag: tagFilter || null,
        channel: channelFilter || null,
        sort: sortBy !== 'rating' ? sortBy : null
    });
    
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
    performanceTracker.startTimer('renderGames');
    applyFilters();
    performanceTracker.endTimer('renderGames');
}

function applyReleaseFilter(games, releaseFilter) {
    const filterMap = {
        [RELEASE_FILTERS.RELEASED]: (game) => 
            game.platform === PLATFORMS.ITCH || 
            game.platform === PLATFORMS.CRAZYGAMES || 
            (game.platform === PLATFORMS.STEAM && !game.coming_soon && !game.is_early_access && !game.is_demo),
        [RELEASE_FILTERS.EARLY_ACCESS]: (game) => 
            game.platform === PLATFORMS.STEAM && game.is_early_access && !game.coming_soon,
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
    performanceTracker.startTimer('renderFilteredGames');
    const gameGrid = document.getElementById('gameGrid');
    const gameCount = document.getElementById('gameCount');
    
    if (games.length === 0) {
        gameGrid.innerHTML = '<div class="no-results">No games match your filters.</div>';
        gameCount.textContent = 'No games found';
        performanceTracker.endTimer('renderFilteredGames');
        return;
    }
    
    gameCount.textContent = `Showing ${games.length} games`;
    
    // Use document fragment for batch DOM updates
    const fragment = document.createDocumentFragment();
    games.forEach(game => {
        const gameCardHTML = generateGameCardHTML(game);
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = gameCardHTML;
        const gameCard = tempDiv.firstElementChild; // Use firstElementChild instead of firstChild
        
        // Add lazy loading to images
        if (gameCard) {
            const img = gameCard.querySelector('.game-image');
            if (img && img.src) {
                img.dataset.src = img.src;
                img.classList.add('lazy-image');
                img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDYwIiBoZWlnaHQ9IjIxNSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZWVlIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkxvYWRpbmcuLi48L3RleHQ+PC9zdmc+';
            }
            fragment.appendChild(gameCard);
        }
    });
    
    // Single DOM update instead of many
    gameGrid.innerHTML = ''; // Clear existing content
    gameGrid.appendChild(fragment);
    
    // Start observing lazy images
    const lazyImages = gameGrid.querySelectorAll('.lazy-image');
    lazyImages.forEach(img => {
        imageObserver.observe(img);
    });
    
    performanceTracker.endTimer('renderFilteredGames');
    
    // Note: Image loading measurement less relevant with lazy loading
    // Images now load on-demand as user scrolls
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
    // Handle "No user reviews" case explicitly
    if (game.review_summary === 'No user reviews' || game.review_count === 0) {
        return `
            <span class="game-rating rating-insufficient">
                No user reviews
            </span>
        `;
    }
    
    // Show "Too few reviews" block when there are reviews but insufficient for percentage
    if (game.insufficient_reviews || (game.review_count !== undefined && game.review_count > 0 && !game.positive_review_percentage)) {
        return `
            <span class="game-rating rating-insufficient">
                Too few reviews (${game.review_count || 0})
            </span>
        `;
    }
    
    // Show normal review percentage when available
    if (!game.positive_review_percentage) {
        return '';
    }
    
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
    // Unified games handle this in their main status - no need for separate full game info
    if (game.card_type === 'unified') {
        return '';
    }
    
    if (!game.full_game) {
        return '';
    }
    
    const fullGameStatus = getStatusText(game.full_game);
    const priceInfo = game.full_game.price && !game.full_game.coming_soon ? ` - ${game.full_game.price}` : '';
    
    return `
        <div class="full-game-info">
            Full game: ${fullGameStatus}${priceInfo}
        </div>
    `;
}

function generateGamePriceHTML(game) {
    const price = game.display_price !== undefined ? game.display_price : game.price;
    return price ? `<div class="game-price">${price}</div>` : '';
}

function generateGameTagsHTML(topTags) {
    if (topTags.length === 0) {
        return '';
    }
    
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
    if (game.video_count <= 1) {
        return '';
    }
    
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
    // Use unified display links if available
    if (game.display_links) {
        const mainLinkText = game.platform === PLATFORMS.ITCH ? 'Itch.io' : 
            game.platform === PLATFORMS.CRAZYGAMES ? 'CrazyGames' : 'Steam';
        
        const demoLink = game.display_links.demo ? `
            <a href="${game.display_links.demo}" target="_blank" onclick="event.stopPropagation()">
                Steam Demo
            </a>
        ` : '';
        
        const crazyGamesLink = game.crazygames_url && game.platform !== PLATFORMS.CRAZYGAMES ? `
            <a href="${game.crazygames_url}" target="_blank" onclick="event.stopPropagation()">
                CrazyGames
            </a>
        ` : '';
        
        return `
            <div class="game-links">
                <a href="${game.display_links.main}" target="_blank" onclick="event.stopPropagation()">
                    ${mainLinkText}
                </a>
                ${demoLink}
                ${crazyGamesLink}
                <a href="https://youtube.com/watch?v=${game.video_id}" target="_blank" onclick="event.stopPropagation()">YouTube</a>
            </div>
        `;
    }
    
    // Fallback to original logic for non-unified games
    const platformName = game.platform === PLATFORMS.ITCH ? 'Itch.io' : 
        game.platform === PLATFORMS.CRAZYGAMES ? 'CrazyGames' : 'Steam';
    
    const itchDemoLink = game.itch_demo_url ? `
        <a href="${game.itch_demo_url}" target="_blank" onclick="event.stopPropagation()">
            Itch.io Demo
        </a>
    ` : '';
    
    const steamDemoLink = game.demo && game.demo.steam_app_id ? `
        <a href="https://store.steampowered.com/app/${game.demo.steam_app_id}" target="_blank" onclick="event.stopPropagation()">
            Steam Demo
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
            ${steamDemoLink}
            ${itchDemoLink}
            ${crazyGamesLink}
            <a href="https://youtube.com/watch?v=${game.video_id}" target="_blank" onclick="event.stopPropagation()">YouTube</a>
        </div>
    `;
}

function generateUpdateInfoHTML(game) {
    if (!game.last_updated) {
        return '';
    }
    
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

// URL parameter handling
function updateURLParams(params) {
    const url = new URL(window.location);
    
    // Remove null/undefined values and update URL
    Object.keys(params).forEach(key => {
        if (params[key] === null || params[key] === undefined) {
            url.searchParams.delete(key);
        } else {
            url.searchParams.set(key, params[key]);
        }
    });
    
    // Update URL without page reload
    window.history.replaceState({}, '', url);
}

function loadFiltersFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Load each filter from URL if present
    if (urlParams.has('release')) {
        document.getElementById('releaseFilter').value = urlParams.get('release');
    }
    
    if (urlParams.has('platform')) {
        document.getElementById('platformFilter').value = urlParams.get('platform');
    }
    
    if (urlParams.has('rating')) {
        document.getElementById('ratingFilter').value = urlParams.get('rating');
    }
    
    if (urlParams.has('tag')) {
        document.getElementById('tagFilter').value = urlParams.get('tag');
    }
    
    if (urlParams.has('channel')) {
        document.getElementById('channelFilter').value = urlParams.get('channel');
    }
    
    if (urlParams.has('sort')) {
        document.getElementById('sortBy').value = urlParams.get('sort');
    }
}

// Event listeners
const filterIds = ['releaseFilter', 'platformFilter', 'ratingFilter', 'tagFilter', 'channelFilter', 'sortBy'];
filterIds.forEach(id => {
    document.getElementById(id).addEventListener('change', () => {
        performanceTracker.startTimer('filterChange');
        applyFilters();
        performanceTracker.endTimer('filterChange');
    });
});

// Core Web Vitals tracking
new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const lastEntry = entries[entries.length - 1];
    console.log('🎯 LCP (Largest Contentful Paint):', lastEntry.startTime.toFixed(2) + 'ms');
}).observe({entryTypes: ['largest-contentful-paint']});

new PerformanceObserver((list) => {
    const entries = list.getEntries();
    entries.forEach(entry => {
        console.log('⚡ FID (First Input Delay):', (entry.processingStart - entry.startTime).toFixed(2) + 'ms');
    });
}).observe({entryTypes: ['first-input']});

new PerformanceObserver((list) => {
    let clsValue = 0;
    list.getEntries().forEach(entry => {
        if (!entry.hadRecentInput) {
            clsValue += entry.value;
        }
    });
    if (clsValue > 0) {
        console.log('📐 CLS (Cumulative Layout Shift):', clsValue.toFixed(4));
    }
}).observe({entryTypes: ['layout-shift']});

// Initialize
loadData();