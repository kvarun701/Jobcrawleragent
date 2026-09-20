---
title: CrawlJobs — Multi-Portal Job Crawler
emoji: 💼
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 💼 CrawlJobs — Multi-Platform Job Crawler

Real-time multi-platform job crawler searching **LinkedIn**, **Indeed**, **Naukri**, **Instahyre**, **Cutshort**, and **Remote OK** for verified 24-hour job listings, filtered by keyword, location, and experience level (0 to 45 years).

### Supported Platforms:
1. **LinkedIn** (Past 24 hours recency filter + experience mapping)
2. **Indeed** (India `in.indeed.com` and Global/US `indeed.com` with date sort)
3. **Naukri** (India's leading job portal with 1-day freshness and city filters)
4. **Instahyre** (Curated tech and startup roles across Indian tech hubs)
5. **Cutshort** (Direct-to-recruiter verified startup and tech listings)
6. **Remote OK** (Global remote developer, engineer, and tech opportunities)

### Features:
- **Concurrent Scraping**: Fetches all 6 platforms simultaneously using `asyncio.gather`.
- **Single Unified Dashboard**: View combined listings or filter by individual platform tabs.
- **Direct Apply Links**: Transparent, 1-click links to official recruiter job postings.
- **CSV Export**: Download individual or combined search results for tracking.
- **Zero Registration**: 100% free and open to use without signup or paywalls.
