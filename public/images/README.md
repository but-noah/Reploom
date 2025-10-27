# Reploom Screenshots & Demo Assets

This directory contains screenshots and GIFs for documentation and demo purposes.

## Required Screenshots

For the MVP demo, we need three key screenshots/GIFs:

### 1. Inbox View (`inbox-view.png` or `inbox-view.gif`)
**What to capture:**
- The main draft review table showing multiple pending drafts
- Columns: Thread ID, Original Message Summary, Intent, Confidence, Status, Actions
- Filter controls (status, intent dropdowns)
- At least 3-4 draft reviews visible
- Highlight the clean, organized interface

**How to capture:**
1. Start the application with `make dev` (backend) and `npm run dev` (frontend)
2. Run `make seed` to populate with demo data
3. Navigate to http://localhost:5173/inbox
4. Take a screenshot showing the full inbox interface
5. Optional: Record a GIF showing filtering by status and intent

### 2. Review Page (`review-page.png` or `review-page.gif`)
**What to capture:**
- Single draft detail view
- Original message context displayed prominently
- Generated draft HTML rendered with formatting
- Approve/Reject/Request Edit buttons
- Metadata sidebar showing:
  - Intent classification
  - Confidence score
  - Policy violations (if any)
  - Run ID and timestamps

**How to capture:**
1. From the Inbox, click on any draft review
2. Capture the full review screen showing both the original context and the draft
3. Optional: Record a GIF showing the approval workflow

### 3. Analytics Dashboard (`analytics-view.png` or `analytics-view.gif`)
**What to capture:**
- Analytics page with metrics cards
- Intent distribution chart (support, cs, exec, other)
- Review rate statistics (approved, rejected, editing, pending percentages)
- First Response Time (FRT) metrics with SLA tracking
- Time window selector (7d/30d)
- Trend indicators showing change from previous period

**How to capture:**
1. Navigate to http://localhost:5173/analytics
2. Ensure you have enough demo data (run `make seed` if needed)
3. Capture the full dashboard with all metrics visible
4. Optional: Record a GIF showing switching between 7d and 30d windows

## Screenshot Specifications

- **Format**: PNG for static images, GIF for animations
- **Resolution**: Minimum 1920x1080 (or responsive viewport size)
- **File size**: Keep GIFs under 5MB if possible
- **Naming**: Use kebab-case (e.g., `inbox-view.png`, `review-page.gif`)

## Tools Recommended

- **macOS**: Built-in Screenshot tool (Cmd+Shift+4 or Cmd+Shift+5)
- **Linux**: Flameshot, GNOME Screenshot, or Spectacle
- **Windows**: Snipping Tool or Snip & Sketch
- **GIF Recording**:
  - [Kap](https://getkap.co/) (macOS)
  - [Peek](https://github.com/phw/peek) (Linux)
  - [ScreenToGif](https://www.screentogif.com/) (Windows)
  - [Gifox](https://gifox.app/) (macOS, paid)

## Using Screenshots in Documentation

Once captured, reference them in the main README like this:

```markdown
## Screenshots

### Inbox - Draft Review Queue
![Inbox View](./public/images/inbox-view.png)

### Review - Detailed Draft Analysis
![Review Page](./public/images/review-page.png)

### Analytics - Performance Metrics
![Analytics Dashboard](./public/images/analytics-view.png)
```

## Placeholder Files

For now, this directory contains placeholder documentation. Replace this with actual screenshots before the final demo.

To generate demo data for screenshots:
```bash
cd backend
make up          # Start services
make migrate     # Initialize database
make seed        # Seed demo data
```

Then start the frontend:
```bash
cd frontend
npm run dev
```

Navigate to http://localhost:5173 and capture screenshots as described above.
