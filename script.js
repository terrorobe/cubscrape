let channels = {};

// SQLite database support
let db = null;

// Performance tracking (disable for production)
const PERFORMANCE_TRACKING = window.location.hostname === 'localhost' || window.location.search.includes('debug=true');

const performanceTracker = {
    startTimer(name) {
        if (!PERFORMANCE_TRACKING) {
            return;
        }
        performance.mark(`${name}-start`);
        console.time(name);
    },
    
    endTimer(name) {
        if (!PERFORMANCE_TRACKING) {
            return;
        }
        performance.mark(`${name}-end`);
        performance.measure(name, `${name}-start`, `${name}-end`);
        console.timeEnd(name);
        
        const measure = performance.getEntriesByName(name)[0];
        console.log(`📊 ${name}: ${measure.duration.toFixed(2)}ms`);
    },
    
    measureImageLoading() {
        if (!PERFORMANCE_TRACKING) {
            return;
        }
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
        if (!PERFORMANCE_TRACKING) {
            return;
        }
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
    if (!dateString) {
        return '';
    }
    
    // Handle different date formats
    let date;
    if (dateString.includes('T')) {
        // ISO format: "2025-06-11T22:30:08"
        date = new Date(dateString);
    } else {
        // Human readable format: "13 Sep, 2024"
        date = new Date(dateString);
    }
    
    if (isNaN(date.getTime())) {
        return dateString; // Return original if parsing fails
    }
    
    return date.toLocaleDateString('en-US', {
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
        // Check if this is a unified card (demo data + full game coming soon)
        if (game.coming_soon) {
            return game.planned_release_date || 'Coming Soon';
        }
        return 'Demo';
    }
    if (game.coming_soon) {
        // If main game is coming soon but has a demo, show demo info
        if (game.demo_steam_app_id) {
            return 'Demo Available';
        }
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
        // Check if this is a unified card (demo data + full game coming soon)
        if (game.coming_soon) {
            return 'coming-soon';
        }
        return 'demo';
    }
    if (game.coming_soon) {
        // If main game is coming soon but has a demo, use demo styling
        if (game.demo_steam_app_id) {
            return 'demo';
        }
        return 'coming-soon';
    }
    if (game.is_early_access) {
        return 'early-access';
    }
    return '';
}

function getRatingClass(percentage, reviewSummary) {
    if (!percentage) {
        return '';
    }
    
    // Use review summary for more specific classification when available
    if (reviewSummary) {
        const summary = reviewSummary.toLowerCase();
        if (summary.includes('overwhelmingly positive')) {
            return 'positive';
        }
        if (summary.includes('very positive')) {
            return 'positive rating-very-positive';
        }
        if (summary.includes('mostly positive')) {
            return 'positive rating-mostly-positive';
        }
        if (summary.includes('positive')) {
            return 'positive rating-just-positive';
        }
        if (summary.includes('mixed')) {
            return 'mixed';
        }
        if (summary.includes('mostly negative')) {
            return 'negative';
        }
        if (summary.includes('overwhelmingly negative')) {
            return 'negative rating-overwhelmingly-negative';
        }
        if (summary.includes('negative')) {
            return 'negative rating-very-negative';
        }
    }
    
    // Fallback to percentage-based classification
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
        // Load SQLite database
        db = await loadSQLiteDatabase();
        
        // Load config for channel info
        const configResponse = await fetch('config.json');
        const config = await configResponse.json();
        channels = config.channels || {};
        
        // Populate filters from SQLite
        populateFilters();
        loadFiltersFromURL();
        renderGames();
        
        performanceTracker.endTimer('loadData');
        performanceTracker.measureMemoryUsage();
        
        // Images now load progressively with lazy loading
    } catch (error) {
        console.error('Error loading database:', error);
        document.getElementById('gameGrid').innerHTML = '<div class="loading">Database failed to load. Please refresh the page.</div>';
        performanceTracker.endTimer('loadData');
    }
}

async function loadSQLiteDatabase() {
    const SQL = await initSqlJs({
        locateFile: file => `https://sql.js.org/dist/${file}`
    });
    
    const response = await fetch('data/games.db');
    if (!response.ok) {
        throw new Error(`Failed to load database: ${response.status}`);
    }
    
    const dbBuffer = await response.arrayBuffer();
    return new SQL.Database(new Uint8Array(dbBuffer));
}



// Populate filter dropdowns
function populateFilters() {
    // Get all unique tags from SQLite
    const tagResults = db.exec('SELECT DISTINCT tags FROM games WHERE tags IS NOT NULL AND tags != \'[]\'');
    const allTags = new Set();
    
    if (tagResults.length > 0) {
        tagResults[0].values.forEach(row => {
            try {
                const tags = JSON.parse(row[0] || '[]');
                tags.forEach(tag => allTags.add(tag));
            } catch (e) {
                console.warn('Failed to parse tags:', row[0]);
            }
        });
    }
    
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
        option.value = channels[channelId].name;  // Use channel name as value
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
    
    // Use SQLite for filtering
    const filtered = applyFiltersSQL(releaseFilter, platformFilter, ratingFilter, tagFilter, channelFilter, sortBy);
    renderFilteredGames(filtered);
}

function applyFiltersSQL(releaseFilter, platformFilter, ratingFilter, tagFilter, channelFilter, sortBy) {
    // Build SQL query with filters, including latest video title
    let query = `
        SELECT g.*, 
               gv.video_title as latest_video_title,
               gv.video_id as latest_video_id
        FROM games g
        LEFT JOIN game_videos gv ON g.id = gv.game_id 
        AND gv.video_date = g.latest_video_date
        WHERE 1=1
    `;
    const params = [];
    
    // Platform filter
    if (platformFilter !== 'all') {
        query += ' AND platform = ?';
        params.push(platformFilter);
    }
    
    // Release status filter
    if (releaseFilter !== 'all') {
        if (releaseFilter === 'released') {
            query += ' AND (platform IN (\'itch\', \'crazygames\') OR (platform = \'steam\' AND coming_soon = 0 AND is_early_access = 0 AND is_demo = 0))';
        } else if (releaseFilter === 'early-access') {
            query += ' AND platform = \'steam\' AND is_early_access = 1 AND coming_soon = 0';
        } else if (releaseFilter === 'coming-soon') {
            query += ' AND platform = \'steam\' AND coming_soon = 1';
        }
    }
    
    // Rating filter
    if (ratingFilter > 0) {
        query += ' AND positive_review_percentage >= ?';
        params.push(ratingFilter);
    }
    
    // Tag filter
    if (tagFilter) {
        query += ' AND tags LIKE ?';
        params.push(`%"${tagFilter}"%`);
    }
    
    // Channel filter
    if (channelFilter) {
        query += ' AND unique_channels LIKE ?';
        params.push(`%"${channelFilter}"%`);
    }
    
    // Sorting
    const sortMappings = {
        rating: 'positive_review_percentage DESC',
        date: 'latest_video_date DESC',
        name: 'name ASC'
    };
    
    if (sortMappings[sortBy]) {
        query += ` ORDER BY ${sortMappings[sortBy]}`;
    } else {
        query += ' ORDER BY positive_review_percentage DESC';
    }
    
    // Execute query
    const results = db.exec(query, params);
    
    if (results.length === 0) {
        return [];
    }
    
    const columns = results[0].columns;
    const rows = results[0].values;
    
    // Convert SQLite results to game objects and add video details
    return rows.map(row => {
        const game = {};
        columns.forEach((col, index) => {
            game[col] = row[index];
        });
        
        // Parse JSON columns
        try {
            game.genres = JSON.parse(game.genres || '[]');
            game.tags = JSON.parse(game.tags || '[]');
            game.categories = JSON.parse(game.categories || '[]');
            game.developers = JSON.parse(game.developers || '[]');
            game.publishers = JSON.parse(game.publishers || '[]');
            game.unique_channels = JSON.parse(game.unique_channels || '[]');
        } catch (e) {
            console.warn('Failed to parse JSON columns for game:', game.name);
        }
        
        return game;
    });
}

function getGameVideos(gameId) {
    const videoQuery = 'SELECT * FROM game_videos WHERE game_id = ? ORDER BY video_date DESC';
    const videoResults = db.exec(videoQuery, [gameId]);
    
    if (videoResults.length === 0) {
        return [];
    }
    
    const videoColumns = videoResults[0].columns;
    const videoRows = videoResults[0].values;
    
    return videoRows.map(row => {
        const video = {};
        videoColumns.forEach((col, index) => {
            video[col] = row[index];
        });
        return video;
    });
}

// Render games to grid
function renderGames() {
    performanceTracker.startTimer('renderGames');
    applyFilters();
    performanceTracker.endTimer('renderGames');
}


function generateChannelGroupedVideos(videos) {
    const videosByChannel = groupVideosByChannel(videos);
    return generateChannelHTML(videosByChannel);
}

function groupVideosByChannel(videos) {
    const videosByChannel = {};
    
    videos.forEach(video => {
        const channelKey = video.channel_name || 'Unknown Channel';
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
            <a href="https://youtube.com/watch?v=${video.video_id}" target="_blank" >
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
    const ratingClass = getRatingClass(game.positive_review_percentage, game.review_summary);
    const topTags = (game.tags || []).slice(0, MAX_TAGS_DISPLAY);
    
    // Get the correct platform URL for card click
    const cardClickUrl = game.platform === PLATFORMS.ITCH ? game.itch_url : 
        game.platform === PLATFORMS.CRAZYGAMES ? game.crazygames_url : game.steam_url;
    
    return `
        <div class="game-card" data-url="${cardClickUrl}">
            ${generateGameImageHTML(game)}
            <div class="game-info">
                <div class="game-content">
                    ${generateGameTitleHTML(game)}
                    ${generateGameMetaHTML(game, statusText, statusClass, ratingClass)}
                    ${generateGamePriceHTML(game)}
                    ${generateGameTagsHTML(topTags)}
                    ${generateVideoInfoHTML(game)}
                </div>
                <div class="game-footer">
                    ${generateGameLinksHTML(game)}
                    ${generateUpdateInfoHTML(game)}
                </div>
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
    const fullGameHTML = generateFullGameHTML(game);
    
    return `
        <div class="game-meta">
            ${reviewHTML}
            ${fullGameHTML}
        </div>
    `;
}

function generateReviewHTML(game, ratingClass) {
    // Handle "No user reviews" case explicitly
    if (game.review_summary === 'No user reviews' || game.review_count === 0) {
        return `
            <div class="game-rating rating-insufficient">
                No user reviews
            </div>
        `;
    }
    
    // Show "Too few reviews" block when there are reviews but insufficient for percentage
    if (game.insufficient_reviews || (game.review_count !== undefined && game.review_count > 0 && !game.positive_review_percentage)) {
        return `
            <div class="game-rating rating-insufficient">
                Too few reviews (${game.review_count || 0})
            </div>
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
        <div class="game-rating rating-${ratingClass}">
            <div class="rating-numbers">
                ${game.positive_review_percentage}% ${game.review_count ? `(${game.review_count.toLocaleString()})` : ''}
            </div>
            <div class="rating-summary">
                ${game.review_summary || 'Positive'}
            </div>
        </div>
        ${recentReviewHTML}
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
    const priceHTML = price ? `<span class="price-value">${price}</span>` : '';
    
    // Get release status info
    const releaseInfo = getReleaseInfo(game);
    const releaseHTML = releaseInfo ? `<span class="release-info">${releaseInfo}</span>` : '';
    
    if (!priceHTML && !releaseHTML) {
        return '';
    }
    
    return `
        <div class="game-price-line">
            ${priceHTML}
            ${releaseHTML}
        </div>
    `;
}

function getReleaseInfo(game) {
    // For unified display
    if (game.display_status) {
        return game.display_status;
    }
    
    // Platform-specific games
    if (game.platform === PLATFORMS.ITCH) {
        return 'Available on Itch.io';
    }
    if (game.platform === PLATFORMS.CRAZYGAMES) {
        return 'Play on CrazyGames';
    }
    
    // Steam games
    if (game.is_demo) {
        if (game.coming_soon) {
            return `Demo • Full game ${game.planned_release_date || 'coming soon'}`;
        }
        return 'Demo available';
    }
    if (game.coming_soon) {
        return game.planned_release_date || 'Coming soon';
    }
    if (game.is_early_access) {
        return 'Early Access';
    }
    if (game.release_date) {
        return `Released ${game.release_date}`;
    }
    return 'Released';
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
    
    // Get latest video info for display
    const latestVideoDate = game.latest_video_date ? formatDate(game.latest_video_date) : '';
    const latestVideoTitle = game.latest_video_title || '';
    const latestVideoId = game.latest_video_id || '';
    
    return `
        <div class="video-info">
            ${latestVideoTitle ? `<div class="video-title">
                <a href="https://youtube.com/watch?v=${latestVideoId}" target="_blank" >
                    ${latestVideoTitle}
                </a>
            </div>` : ''}
            ${latestVideoDate ? `<div class="video-date">Latest video: ${latestVideoDate}</div>` : ''}
            ${channelInfo}
            ${multiVideoHTML}
        </div>
    `;
}

function generateChannelInfoHTML(game) {
    const uniqueChannels = game.unique_channels || [];
    const channelText = uniqueChannels.length > 1 ? 
        `Channels: ${uniqueChannels.join(', ')}` : 
        `Channel: ${uniqueChannels[0] || 'Unknown'}`;
    
    return `<div class="channel-info">${channelText}</div>`;
}

function generateMultiVideoHTML(game) {
    if (game.video_count <= 1) {
        return '';
    }
    
    return `
        <div class="video-count video-expand-toggle" data-game-key="${game.game_key}" data-game-id="${game.id}" style="cursor: pointer;">
            <span class="expand-icon">▶</span>
            <span class="expand-text" data-game-key="${game.game_key}">Featured in ${game.video_count} videos</span>
        </div>
        <div class="all-videos" id="videos-${game.game_key}" style="display: none;">
            <div class="loading">Loading videos...</div>
        </div>
    `;
}

function generateGameLinksHTML(game) {
    // Use unified display links if available
    if (game.display_links) {
        const mainLinkText = game.platform === PLATFORMS.ITCH ? 'Itch.io' : 
            game.platform === PLATFORMS.CRAZYGAMES ? 'CrazyGames' : 'Steam';
        
        const demoLink = game.display_links.demo ? `
            <a href="${game.display_links.demo}" target="_blank" >
                Demo
            </a>
        ` : '';
        
        const crazyGamesLink = game.crazygames_url && game.platform !== PLATFORMS.CRAZYGAMES ? `
            <a href="${game.crazygames_url}" target="_blank" >
                CrazyGames
            </a>
        ` : '';
        
        return `
            <div class="game-links">
                <a href="${game.display_links.main}" target="_blank" >
                    ${mainLinkText}
                </a>
                ${demoLink}
                ${crazyGamesLink}
                ${game.latest_video_id ? `<a href="https://youtube.com/watch?v=${game.latest_video_id}" target="_blank" >YouTube</a>` : ''}
            </div>
        `;
    }
    
    // Fallback to original logic for non-unified games
    const platformName = game.platform === PLATFORMS.ITCH ? 'Itch.io' : 
        game.platform === PLATFORMS.CRAZYGAMES ? 'CrazyGames' : 'Steam';
    
    const itchDemoLink = game.demo_itch_url ? `
        <a href="${game.demo_itch_url}" target="_blank" >
            Itch.io Demo
        </a>
    ` : '';
    
    const steamDemoLink = game.demo_steam_app_id ? `
        <a href="${game.demo_steam_url}" target="_blank" >
            Demo
        </a>
    ` : '';
    
    const crazyGamesLink = game.crazygames_url && game.platform !== PLATFORMS.CRAZYGAMES ? `
        <a href="${game.crazygames_url}" target="_blank" >
            CrazyGames
        </a>
    ` : '';
    
    // Get the correct platform URL
    const platformUrl = game.platform === PLATFORMS.ITCH ? game.itch_url : 
        game.platform === PLATFORMS.CRAZYGAMES ? game.crazygames_url : game.steam_url;
    
    return `
        <div class="game-links">
            <a href="${platformUrl}" target="_blank" >
                ${platformName}
            </a>
            ${steamDemoLink}
            ${itchDemoLink}
            ${crazyGamesLink}
            ${game.latest_video_id ? `<a href="https://youtube.com/watch?v=${game.latest_video_id}" target="_blank" >YouTube</a>` : ''}
        </div>
    `;
}

function generateUpdateInfoHTML(game) {
    if (!game.last_updated) {
        return '';
    }
    
    const platformName = game.platform === PLATFORMS.STEAM ? 'Steam' : game.platform;
    return `<div class="update-info" title="${platformName} data last updated">${formatDate(game.last_updated)}</div>`;
}

// Toggle videos display
function toggleVideos(gameKey, gameId, event) {
    // Event propagation is handled by event delegation
    const videosDiv = document.getElementById(`videos-${gameKey}`);
    const expandText = document.querySelector(`.expand-text[data-game-key="${gameKey}"]`);
    const expandIcon = expandText.previousElementSibling;
    
    // Store video count in a data attribute for reliable retrieval
    if (!expandText.dataset.videoCount) {
        const match = expandText.textContent.match(/\d+/);
        expandText.dataset.videoCount = match ? match[0] : '0';
    }
    const videoCount = expandText.dataset.videoCount;
    
    if (videosDiv.style.display === 'none') {
        // Check if videos are already loaded
        if (videosDiv.innerHTML.trim() === '<div class="loading">Loading videos...</div>') {
            // Fetch and display videos
            const videos = getGameVideos(gameId);
            videosDiv.innerHTML = generateChannelGroupedVideos(videos);
        }
        videosDiv.style.display = 'block';
        expandText.textContent = 'Hide videos';
        expandIcon.textContent = '▼';
    } else {
        videosDiv.style.display = 'none';
        expandText.textContent = `Featured in ${videoCount} videos`;
        expandIcon.textContent = '▶';
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

// Set up event delegation for game cards
document.addEventListener('click', (e) => {
    // Handle game card clicks
    const gameCard = e.target.closest('.game-card');
    if (gameCard && !e.target.closest('a') && !e.target.closest('.video-expand-toggle')) {
        const url = gameCard.dataset.url;
        if (url) {
            window.open(url, '_blank');
        }
    }
    
    // Handle video toggle clicks
    const videoToggle = e.target.closest('.video-expand-toggle');
    if (videoToggle) {
        const gameKey = videoToggle.dataset.gameKey;
        const gameId = videoToggle.dataset.gameId;
        if (gameKey && gameId) {
            toggleVideos(gameKey, gameId, e);
        }
    }
});

// Initialize
loadData();