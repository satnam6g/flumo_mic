// js/main.js — Wireless Mic Website
document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lucide Icons
    if (window.lucide) {
        lucide.createIcons();
    }

    // 2. Theme Toggle
    const themeToggle = document.getElementById('themeToggle');
    const htmlElement = document.documentElement;
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');

    htmlElement.setAttribute('data-theme', savedTheme);

    function toggleTheme() {
        const current = htmlElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        htmlElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    const bottomThemeToggle = document.getElementById('bottomThemeToggle');
    if (bottomThemeToggle) {
        bottomThemeToggle.addEventListener('click', toggleTheme);
    }

    // 3. Mobile Menu
    const mobileToggle = document.getElementById('mobileToggle');
    const navLinks = document.getElementById('navLinks');

    if (mobileToggle && navLinks) {
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
        if (navbar) {
            if (window.scrollY > 20) navbar.classList.add('scrolled');
            else navbar.classList.remove('scrolled');
        }
        if (progressBar) {
            const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
            const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            if (height > 0) {
                progressBar.style.width = ((winScroll / height) * 100) + "%";
            }
        }
    }, { passive: true });

    // 5. Active Nav Link
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a').forEach(link => {
        const href = link.getAttribute('href');
        if (href) {
            const linkPage = href.split('/').pop();
            if (currentPage === linkPage || (currentPage === '' && linkPage === 'index.html') ||
                (currentPage === 'index.html' && href.includes('#'))) {
                // Don't mark anchor links on home as active
            } else if (currentPage === linkPage) {
                link.classList.add('active');
            }
        }
    });

    // 6. Dynamic PIN Generator
    const diagramPin = document.getElementById('diagram-pin');
    const stepPin = document.getElementById('step-pin');

    function updatePins() {
        const newPin = Math.floor(1000 + Math.random() * 9000).toString();
        if (diagramPin) diagramPin.textContent = `Your PIN: ${newPin}`;
        if (stepPin) stepPin.innerText = newPin;
    }
    updatePins();
    setInterval(updatePins, 5000);

    // 7. Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const targetId = `tab-${btn.getAttribute('data-tab')}`;
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add('active');
            }
        });
    });

    // 8. FAQ Accordion
    document.querySelectorAll('.faq-question').forEach(btn => {
        btn.addEventListener('click', () => {
            const item = btn.closest('.faq-item');
            const isOpen = item.classList.contains('open');

            // Close all
            document.querySelectorAll('.faq-item').forEach(i => {
                i.classList.remove('open');
                i.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
            });

            // Toggle clicked
            if (!isOpen) {
                item.classList.add('open');
                btn.setAttribute('aria-expanded', 'true');
            }
        });
    });

    // 9. Intersection Observer (Animations + Counters)
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');

                // Trigger Counters
                const counters = entry.target.querySelectorAll('.counter');
                counters.forEach(counter => {
                    const target = +counter.getAttribute('data-target');
                    let current = 0;
                    const step = target / 60;

                    const updateCounter = () => {
                        current += step;
                        if (current < target) {
                            counter.innerText = Math.ceil(current);
                            requestAnimationFrame(updateCounter);
                        } else {
                            counter.innerText = target;
                        }
                    };
                    requestAnimationFrame(updateCounter);
                    counter.classList.remove('counter');
                });

                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15 });

    document.querySelectorAll('.animate-up, .step-connector').forEach(el => observer.observe(el));

    // 10. Canvas Audio Waveform
    const canvas = document.getElementById('audio-waveform-canvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        let time = 0;

        function drawWave() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.lineWidth = 2;

            for (let j = 0; j < 3; j++) {
                ctx.beginPath();
                ctx.strokeStyle = j === 0 ? '#3b82f6' : (j === 1 ? '#8b5cf6' : '#10b981');
                ctx.globalAlpha = 1 - (j * 0.3);

                for (let i = 0; i < canvas.width; i++) {
                    const y = Math.sin(i * 0.02 + time + j) * 20 * Math.sin(time * 0.5) + (canvas.height / 2);
                    if (i === 0) ctx.moveTo(i, y);
                    else ctx.lineTo(i, y);
                }
                ctx.stroke();
            }
            ctx.globalAlpha = 1;
            time += 0.05;
            requestAnimationFrame(drawWave);
        }
        drawWave();
    }

    // 11. SVG Packets Animation
    const packetContainer = document.getElementById('packet-container');
    if (packetContainer) {
        function createPackets(pathId, color) {
            for (let i = 0; i < 3; i++) {
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
        createPackets('path1', '#10b981');
        createPackets('path2', '#3b82f6');
    }
});
