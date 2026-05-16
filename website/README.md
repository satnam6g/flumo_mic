# Wireless Mic - Landing Page

A complete, production-ready landing page website for the "Wireless Mic" open-source application.

## 🚀 Features

- **Pure HTML/CSS/JS**: No frameworks or build tools required.
- **Responsive Design**: Looks great on mobile, tablet, and desktop.
- **Dark/Light Mode**: Smooth theme toggling that respects system preferences.
- **Animations**: Scroll-based fade-ins, hover effects, and accordion transitions.
- **Performance Optimized**: Uses system fonts, CSS variables, and native Intersection Observer.

## 📂 File Structure

```
website/
├── index.html        # Main HTML file containing all sections
├── css/
│   └── style.css     # All styles, CSS variables, and media queries
├── js/
│   ├── main.js       # Core logic (Theme, Nav, Carousel, Tabs)
│   ├── animations.js # Interactive animations (Cursor, Parallax, Canvas Audio)
│   └── github-api.js # Live GitHub stats fetching and caching
├── assets/
│   ├── logo.svg      # Simple SVG microphone logo
│   └── encryption-diagram.svg # (Replaced by inline SVG in HTML, kept for reference)
└── README.md
```

## 🛠️ Usage & Deployment

Since this is a static site with no build process, deployment is incredibly simple:

1. **Local Testing**:
   You can open `index.html` directly in your browser, or use a local server (e.g., VS Code Live Server, or Python's `python -m http.server`).

2. **GitHub Pages Deployment**:
   - Push this code to a GitHub repository.
   - Go to Settings > Pages.
   - Select the `main` branch as the source.
   - Save, and your site will be live!

3. **Vercel / Netlify / Cloudflare Pages**:
   - Connect your GitHub repository.
   - Leave build command empty.
   - Leave publish directory empty (or set to `.`).
   - Deploy.

## 🎨 Customization

### Colors & Themes
All colors are defined as CSS variables at the top of `css/style.css`.
To change the primary color, simply modify `--primary-color` and `--primary-hover`.

### Images
Replace the Unsplash placeholders in `index.html` with your actual screenshots:
- Search for `src="https://images.unsplash.com/...`
- Update the paths to point to your `assets/screenshots/` folder.

## 📄 License
This landing page is provided under the MIT License.
