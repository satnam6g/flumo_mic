# Website Refinement Plan

This plan addresses the feedback to make the website feel more professional, authentic, and simple, removing "fake" complexity.

## User Review Required

> [!IMPORTANT]
> Please review this plan to ensure it aligns with your expectations for a clean, professional design.
> 
> * We will remove the custom cursor and simplify animations.
> * We will combine the JavaScript into a single `js/main.js` file for simplicity.
> * We will create realistic CSS mockups for the carousel and setup steps since actual images are not available.

## Proposed Changes

---

### Global / Cleanup
#### [DELETE] `js/animations.js` and `js/github-api.js`
- We will consolidate all necessary vanilla JavaScript into `main.js` to keep the architecture simple.
- Remove all custom cursor CSS and JS logic.

### 1. HTML Structure (`index.html`)
#### [MODIFY] [index.html](file:///d:/vs/wo%20mic%20app/website/index.html)
- **Hero Section:** Remove floating blobs. Add a subtle CSS noise texture overlay. Restructure to a 2-column layout with text on the left and a CSS mockup of the Phone/PC on the right. Remove "Trusted by..." text.
- **Bento Grid:** Update grid CSS classes to strictly follow: 2 large cards on top, 4 smaller cards below. Ensure Lucide icons load correctly.
- **Encryption Diagram:** Add a `<text>` element for the dynamic PIN below the lock. Ensure inline SVG packet animations are working.
- **Setup Steps:** Replace icons with realistic CSS mini-mockups. Add an SVG connecting line that draws between steps on desktop.
- **Carousel:** Implement realistic CSS mockups (Android green Start button, Windows client dark UI with `192.168.18.109`). Ensure dots and arrows work perfectly.
- **Under the Hood:** Ensure canvas waveform, SVG latency graph, and animated counters exist and trigger on scroll.
- **GitHub Stats:** Implement a robust `fetch` to the GitHub API. If it fails, fallback gracefully without showing fake "245k" numbers (just show "Open Source" links).
- **Footer:** Ensure real links are present with ample whitespace.

### 2. CSS Styling (`css/style.css`)
#### [MODIFY] [css/style.css](file:///d:/vs/wo%20mic%20app/website/css/style.css)
- Remove custom cursor styles and overly complex glow animations.
- Implement realistic box shadows (`box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3)`).
- Increase whitespace (padding/margins) between sections (`padding: 120px 0`).
- Create specific CSS classes for the mockups (Android device frame, Windows window frame, green Start buttons, IP input fields).
- Update the Bento Grid layout with proper `grid-template-areas` for the 2-top / 4-bottom layout.
- Add button hover states (`transform: scale(1.02)` and increased shadow).

### 3. JavaScript Logic (`js/main.js`)
#### [MODIFY] [js/main.js](file:///d:/vs/wo%20mic%20app/website/js/main.js)
- Combine all logic (theme, mobile menu, tabs, carousel, canvas waveform, GitHub fetch).
- Add PIN generator logic that updates both the Setup Step PIN and the Diagram PIN every 5 seconds.
- Ensure all animations use `requestAnimationFrame` for smoothness.
- Add Intersection Observer to trigger the counters and drawing of the connecting line in Setup Steps.

## Verification Plan
1. **Visual Check:** Verify the custom cursor is gone and standard cursor behaves normally.
2. **Layout Check:** Ensure the Features section uses the exact 2x top, 4x bottom grid.
3. **Mockup Check:** Verify the carousel and setup steps show realistic CSS-drawn UI elements instead of just text/icons.
4. **Logic Check:** Confirm the PIN changes every 5 seconds and GitHub stats fetch correctly without fake numbers.
