// js/animations.js
document.addEventListener('DOMContentLoaded', () => {
    // Custom Cursor (Desktop only)
    const cursor = document.getElementById('custom-cursor');
    if (window.matchMedia('(pointer: fine)').matches && cursor) {
        let mouseX = window.innerWidth / 2;
        let mouseY = window.innerHeight / 2;
        let cursorX = mouseX;
        let cursorY = mouseY;
        
        document.addEventListener('mousemove', (e) => {
            mouseX = e.clientX;
            mouseY = e.clientY;
        });

        function renderCursor() {
            // Lerp
            cursorX += (mouseX - cursorX) * 0.2;
            cursorY += (mouseY - cursorY) * 0.2;
            cursor.style.transform = `translate(${cursorX}px, ${cursorY}px)`;
            requestAnimationFrame(renderCursor);
        }
        renderCursor();

        document.querySelectorAll('a, button, .gallery-trigger, .tab-btn').forEach(el => {
            el.addEventListener('mouseenter', () => cursor.classList.add('hover'));
            el.addEventListener('mouseleave', () => cursor.classList.remove('hover'));
        });
    }

    // Scroll Progress
    const progressBar = document.getElementById('scroll-progress');
    if(progressBar) {
        window.addEventListener('scroll', () => {
            const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
            const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            const scrolled = (winScroll / height) * 100;
            progressBar.style.width = scrolled + "%";
        });
    }

    // Intersection Observer for animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');
                
                // SVG Labels
                if(entry.target.classList.contains('encryption-flow')){
                    entry.target.querySelectorAll('.svg-label').forEach((label, idx) => {
                        setTimeout(() => label.style.opacity = '1', idx * 200);
                    });
                }

                // Progress Bar in Setup Step 1
                const prog = entry.target.querySelector('.progress-bar.fill-animation');
                if(prog) { prog.style.width = '100%'; }

                // Counters
                const counters = entry.target.querySelectorAll('.counter');
                counters.forEach(counter => {
                    const target = +counter.getAttribute('data-target');
                    const duration = 2000;
                    const step = target / (duration / 16);
                    let current = 0;
                    const update = () => {
                        current += step;
                        if(current < target) {
                            counter.innerText = Math.ceil(current);
                            requestAnimationFrame(update);
                        } else {
                            counter.innerText = target;
                        }
                    };
                    update();
                });

                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.animate-up').forEach(el => observer.observe(el));

    // Parallax effect on Hero
    const heroWrapper = document.querySelector('.parallax-wrapper');
    const blobs = document.querySelectorAll('.blob');
    if (heroWrapper && window.matchMedia('(pointer: fine)').matches) {
        heroWrapper.addEventListener('mousemove', (e) => {
            const x = (window.innerWidth - e.pageX) / 50;
            const y = (window.innerHeight - e.pageY) / 50;
            
            blobs.forEach((blob, idx) => {
                const speed = idx + 1;
                blob.style.transform = `translate(${x * speed}px, ${y * speed}px)`;
            });
        });
    }

    // Dynamic PIN Generator
    const pinDisplay = document.getElementById('demo-pin');
    if(pinDisplay) {
        setInterval(() => {
            pinDisplay.style.opacity = '0';
            setTimeout(() => {
                pinDisplay.innerText = Math.floor(1000 + Math.random() * 9000);
                pinDisplay.style.opacity = '1';
            }, 300);
        }, 8000);
    }

    // Canvas Audio Waveform
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
                    const y = Math.sin(i * 0.02 + time + j) * 30 * Math.sin(time * 0.5) + (canvas.height/2);
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

    // SVG Packets Animation
    const packetContainer = document.getElementById('packet-container');
    if(packetContainer) {
        // Create packets for path 1
        for(let i=0; i<3; i++) {
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('r', '4');
            circle.setAttribute('fill', '#10B981');
            packetContainer.appendChild(circle);
            
            const animateMotion = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
            animateMotion.setAttribute('dur', '2s');
            animateMotion.setAttribute('repeatCount', 'indefinite');
            animateMotion.setAttribute('begin', `${i * 0.6}s`);
            const mpath = document.createElementNS('http://www.w3.org/2000/svg', 'mpath');
            mpath.setAttributeNS('http://www.w3.org/1999/xlink', 'href', '#path1');
            animateMotion.appendChild(mpath);
            circle.appendChild(animateMotion);
        }

        // Create packets for path 2
        for(let i=0; i<3; i++) {
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('r', '4');
            circle.setAttribute('fill', '#3B82F6');
            packetContainer.appendChild(circle);
            
            const animateMotion = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
            animateMotion.setAttribute('dur', '2s');
            animateMotion.setAttribute('repeatCount', 'indefinite');
            animateMotion.setAttribute('begin', `${i * 0.6}s`);
            const mpath = document.createElementNS('http://www.w3.org/2000/svg', 'mpath');
            mpath.setAttributeNS('http://www.w3.org/1999/xlink', 'href', '#path2');
            animateMotion.appendChild(mpath);
            circle.appendChild(animateMotion);
        }
    }
});
