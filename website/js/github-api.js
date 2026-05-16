// js/github-api.js
document.addEventListener('DOMContentLoaded', () => {
    const CACHE_KEY = 'wm_github_stats';
    const CACHE_TIME_MS = 60 * 60 * 1000; // 1 hour
    const REPO = 'facebook/react'; // Using React as a placeholder with lots of stats, change to your repo

    const container = document.getElementById('github-stats-container');
    if(!container) return;

    function formatNumber(num) {
        if(num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if(num >= 1000) return (num / 1000).toFixed(1) + 'k';
        return num.toString();
    }

    function renderStats(data) {
        container.innerHTML = `
            <div class="stat-item">
                <div class="stat-val">${formatNumber(data.stargazers_count)}</div>
                <div class="stat-label">Stars</div>
            </div>
            <div class="stat-item">
                <div class="stat-val">${formatNumber(data.forks_count)}</div>
                <div class="stat-label">Forks</div>
            </div>
            <div class="stat-item">
                <div class="stat-val">${formatNumber(data.open_issues_count)}</div>
                <div class="stat-label">Issues</div>
            </div>
        `;
    }

    function renderFallback() {
        renderStats({
            stargazers_count: 1200,
            forks_count: 250,
            open_issues_count: 15
        });
    }

    async function fetchStats() {
        try {
            // Check cache
            const cached = localStorage.getItem(CACHE_KEY);
            if (cached) {
                const parsed = JSON.parse(cached);
                if (Date.now() - parsed.timestamp < CACHE_TIME_MS) {
                    renderStats(parsed.data);
                    return;
                }
            }

            // Fetch
            const res = await fetch(`https://api.github.com/repos/${REPO}`);
            if(!res.ok) throw new Error('API Error');
            const data = await res.json();
            
            // Save cache
            localStorage.setItem(CACHE_KEY, JSON.stringify({
                timestamp: Date.now(),
                data: data
            }));

            renderStats(data);

        } catch (error) {
            console.error('GitHub API error:', error);
            // Try to use stale cache if available
            const cached = localStorage.getItem(CACHE_KEY);
            if (cached) {
                renderStats(JSON.parse(cached).data);
            } else {
                renderFallback();
            }
        }
    }

    // Call API when section is near viewport
    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if(entry.isIntersecting) {
                fetchStats();
                obs.disconnect();
            }
        });
    }, { rootMargin: '200px' });

    const githubSection = document.querySelector('.github-section');
    if(githubSection) {
        observer.observe(githubSection);
    }
});
