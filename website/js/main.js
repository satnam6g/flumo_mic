// js/main.js
document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Icons
    if(window.lucide) {
        lucide.createIcons();
    }

    // 2. Theme Toggle
    const themeToggle = document.getElementById('themeToggle');
    const htmlElement = document.documentElement;
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    
    htmlElement.setAttribute('data-theme', savedTheme);

    if(themeToggle) {
        themeToggle.addEventListener('click', () => {
            const current = htmlElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            htmlElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        });
    }

    // 3. Mobile Menu
    const mobileToggle = document.getElementById('mobileToggle');
    const navLinks = document.getElementById('navLinks');
    
    if(mobileToggle && navLinks) {
        mobileToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            document.body.style.overflow = navLinks.classList.contains('active') ? 'hidden' : '';
        });
        
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('active');
                document.body.style.overflow = '';
            });
        });
    }

    // 4. Navbar Scroll & Progress Bar
    const navbar = document.getElementById('navbar');
    const progressBar = document.getElementById('scroll-progress');
    
    window.addEventListener('scroll', () => {
        if(navbar) {
            if (window.scrollY > 20) navbar.classList.add('scrolled');
            else navbar.classList.remove('scrolled');
        }
        if(progressBar) {
            const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
            const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            progressBar.style.width = ((winScroll / height) * 100) + "%";
        }
    }, {passive: true});

    // 5. Dynamic PIN Generator
    const heroPhonePin = document.getElementById('hero-phone-pin');
    const heroPcPin = document.getElementById('hero-pc-pin');
    const diagramPin = document.getElementById('diagram-pin');
    const stepPin = document.getElementById('step-pin');

    function updatePins() {
        const newPin = Math.floor(1000 + Math.random() * 9000).toString();
        if(heroPhonePin) heroPhonePin.innerText = newPin;
        if(heroPcPin) heroPcPin.innerText = newPin;
        if(diagramPin) diagramPin.textContent = `Your PIN: ${newPin}`;
        if(stepPin) stepPin.innerText = newPin;
    }
    updatePins(); // init
    setInterval(updatePins, 5000); // update every 5s

    // 6. Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            
            btn.classList.add('active');
            const targetId = `tab-${btn.getAttribute('data-tab')}`;
            const targetPane = document.getElementById(targetId);
            if(targetPane) {
                targetPane.classList.add('active');
            }
        });
    });

    // 7. Carousel (Removed)
    // Removed because Interface Preview now uses static screenshot images.

    // Bottom Theme Toggle
    const bottomThemeToggle = document.getElementById('bottomThemeToggle');
    if(bottomThemeToggle) {
        bottomThemeToggle.addEventListener('click', () => {
            if(themeToggle) themeToggle.click(); // reuse logic
        });
    }

    // 8. Intersection Observer (Animations, Counters, Packets)
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');
                
                // Trigger Counters
                const counters = entry.target.querySelectorAll('.counter');
                counters.forEach(counter => {
                    const target = +counter.getAttribute('data-target');
                    let current = 0;
                    const step = target / 60; // assume 60 frames
                    
                    const updateCounter = () => {
                        current += step;
                        if(current < target) {
                            counter.innerText = Math.ceil(current);
                            requestAnimationFrame(updateCounter);
                        } else {
                            counter.innerText = target;
                        }
                    };
                    requestAnimationFrame(updateCounter);
                    counter.classList.remove('counter'); // prevent re-trigger
                });

                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15 });

    document.querySelectorAll('.animate-up, .step-connector').forEach(el => observer.observe(el));

    // 9. Canvas Audio Waveform
    const canvas = document.getElementById('audio-waveform-canvas');
    if(canvas) {
        const ctx = canvas.getContext('2d');
        let time = 0;

        function drawWave() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.lineWidth = 2;
            
            for(let j = 0; j < 3; j++) {
                ctx.beginPath();
                ctx.strokeStyle = j === 0 ? '#3b82f6' : (j === 1 ? '#8b5cf6' : '#10b981');
                ctx.globalAlpha = 1 - (j * 0.3);
                
                for(let i = 0; i < canvas.width; i++) {
                    const y = Math.sin(i * 0.02 + time + j) * 20 * Math.sin(time * 0.5) + (canvas.height/2);
                    if(i===0) ctx.moveTo(i, y);
                    else ctx.lineTo(i, y);
                }
                ctx.stroke();
            }
            time += 0.05;
            requestAnimationFrame(drawWave);
        }
        drawWave();
    }

    // 10. SVG Packets Animation Setup
    const packetContainer = document.getElementById('packet-container');
    if(packetContainer) {
        function createPackets(pathId, color) {
            for(let i=0; i<3; i++) {
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('r', '4');
                circle.setAttribute('fill', color);
                packetContainer.appendChild(circle);
                
                const animateMotion = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
                animateMotion.setAttribute('dur', '2s');
                animateMotion.setAttribute('repeatCount', 'indefinite');
                animateMotion.setAttribute('begin', `${i * 0.6}s`);
                const mpath = document.createElementNS('http://www.w3.org/2000/svg', 'mpath');
                mpath.setAttributeNS('http://www.w3.org/1999/xlink', 'href', `#${pathId}`);
                animateMotion.appendChild(mpath);
                circle.appendChild(animateMotion);
            }
        }
        createPackets('path1', '#10b981'); // Green before lock
        createPackets('path2', '#3b82f6'); // Blue after lock
    }

    // 11. GitHub API Fetch
    const githubContainer = document.getElementById('github-stats-container');
    if(githubContainer) {
        const REPO = 'facebook/react'; // Placeholder for high stats
        const CACHE_KEY = 'wm_github_stats';
        
        async function fetchGithubStats() {
            try {
                const cached = localStorage.getItem(CACHE_KEY);
                if(cached) {
                    const parsed = JSON.parse(cached);
                    if(Date.now() - parsed.timestamp < 3600000) {
                        renderStats(parsed.data);
                        return;
                    }
                }

                const res = await fetch(`https://api.github.com/repos/${REPO}`);
                if(!res.ok) throw new Error('API Failed');
                const data = await res.json();
                
                localStorage.setItem(CACHE_KEY, JSON.stringify({timestamp: Date.now(), data}));
                renderStats(data);
            } catch (err) {
                // Graceful fallback without fake numbers
                githubContainer.innerHTML = `
                    <div class="stat-item">
                        <div class="stat-val"><i data-lucide="check-circle" class="text-accent"></i></div>
                        <div class="stat-label">Active Development</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-val"><i data-lucide="users" class="text-primary"></i></div>
                        <div class="stat-label">Community Driven</div>
                    </div>
                `;
                if(window.lucide) lucide.createIcons();
            }
        }

        function renderStats(data) {
            function fmt(num) {
                if(num >= 1000000) return (num/1000000).toFixed(1) + 'M';
                if(num >= 1000) return (num/1000).toFixed(1) + 'k';
                return num;
            }
            githubContainer.innerHTML = `
                <div class="stat-item">
                    <div class="stat-val">${fmt(data.stargazers_count)}</div>
                    <div class="stat-label">Stars</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val">${fmt(data.forks_count)}</div>
                    <div class="stat-label">Forks</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val">${fmt(data.open_issues_count)}</div>
                    <div class="stat-label">Issues</div>
                </div>
            `;
        }

        // Fetch when in view
        const gitObserver = new IntersectionObserver((entries, obs) => {
            if(entries[0].isIntersecting) {
                fetchGithubStats();
                obs.disconnect();
            }
        });
        gitObserver.observe(document.querySelector('#github'));
    }
});
