# DiggingScriptures.com — Gap Analysis Report
**Date:** March 2, 2026  
**Site:** https://diggingscriptures.com  
**Stack:** Astro 5 + Tailwind 4 + React (SSG on Netlify)  
**Content:** 751 pages (680 research + 55 pilgrimage + 16 static)

---

## Executive Summary

The site has a strong content foundation (735 articles, good meta descriptions, hero images, sitemap, canonical URLs, JSON-LD) but has **17 gaps** across navigation, E-E-A-T, technical SEO, and UX that are limiting its ability to rank, retain visitors, and grow traffic.

**The two most damaging gaps:** 680 research articles are invisible from the main navigation, and there's no analytics tracking — meaning you can't even measure what's happening.

---

## CRITICAL (2 issues)

### 1. No /research link in header or footer navigation
The header links to Journeys, Places, Routes, Stories, and Context — but NOT Research. The footer mirrors this. That means **680 articles (92% of the site's content)** are completely unreachable from the main navigation. Users can only find them via direct links, search engines, or the homepage "Browse by type" section buried below the fold.

**Impact:** Massive crawlability and link equity problem. Google may undervalue these pages without clear nav paths.  
**Fix:** Add "Research" to header and footer nav. Consider making it the first or second item given it's 92% of content.

### 2. No custom 404 page
The site uses Netlify's default "Page not found" — a generic white page with no branding, navigation, or links back to the site. Any visitor who hits a broken link leaves immediately.

**Impact:** 100% bounce rate on 404s. Lost recovery opportunities.  
**Fix:** Create `src/pages/404.astro` with site branding, search suggestions, and links to popular content.

---

## HIGH (9 issues)

### 3. No Google Analytics or tracking
There is zero analytics code on the site. No GA4, no Plausible, no Fathom, nothing. You cannot measure traffic, user behavior, popular content, or conversion paths.

**Impact:** Flying completely blind. Can't make data-driven decisions.  
**Fix:** Add GA4 or a privacy-friendly alternative (Plausible, Fathom). Minimum viable: GA4 gtag in BaseLayout.

### 4. No Google Search Console verification
No `google-site-verification` meta tag. Without GSC you can't monitor indexing status, submit sitemaps, see search queries, or get notified of crawl errors.

**Impact:** No visibility into how Google sees the site.  
**Fix:** Add verification meta tag to BaseLayout head.

### 5. No About page (E-E-A-T gap)
Biblical archaeology and scripture content is YMYL-adjacent (Your Money or Your Life). Google's quality raters explicitly look for author credentials and site authority signals. There is no /about page explaining who runs the site, what their qualifications are, or why readers should trust the content.

**Impact:** Major E-E-A-T deficiency. Could suppress rankings for competitive queries.  
**Fix:** Create /about with editorial mission, author bios, credentials, and methodology.

### 6. No author bios on articles
Research articles show no author name, bio, credentials, or expertise indicators. There's no Author component in the codebase.

**Impact:** Google can't associate content with expert authors. E-E-A-T signal completely missing.  
**Fix:** Add author schema (Person), byline component, and author pages.

### 7. 179 research articles with zero internal links
26% of research articles (179 out of 680) contain no internal links whatsoever. These are effectively orphaned content — they receive link equity but don't pass it anywhere, and they don't guide readers to related content.

**Impact:** Wasted link equity, poor user engagement, higher bounce rates.  
**Fix:** Run a second pass of the cross-linking script targeting these 179 articles specifically.

### 8. No related articles section on research pages
Research article pages end abruptly after the content. There's no "Related Articles" or "Read Next" section to keep readers engaged.

**Impact:** High exit rates. Missed opportunity to increase pageviews per session and strengthen internal linking.  
**Fix:** Add a related articles component using category matching and keyword similarity.

### 9. No email signup / newsletter
There is no mechanism to capture visitor email addresses. No newsletter signup, no lead magnet, no notification opt-in.

**Impact:** Zero ability to build a returning audience. 100% reliant on search traffic.  
**Fix:** Add email capture (e.g., ConvertKit, Buttondown, or Netlify Forms) in article sidebar or footer.

### 10. OG image is static site-wide default
Every page uses the same `/images/og-default.jpg` for social sharing. Research articles have unique hero images but these aren't used as OG images.

**Impact:** All social shares look identical. Dramatically reduces click-through from social.  
**Fix:** Pass article hero image to BaseLayout as dynamic OG image prop.

### 11. No Article schema on research pages
Research pages have the global WebSite schema but no Article/ScholarlyArticle JSON-LD. Missing datePublished, author, publisher, and articleSection.

**Impact:** Missed rich result opportunities (article cards, knowledge panel entries).  
**Fix:** Add Article schema in ResearchLayout with datePublished, author, image, etc.

---

## MEDIUM (4+ issues)

### 12. No search functionality
735 articles with no way to search. The only discovery path is browsing category pages that dump all articles at once.

**Impact:** Users looking for specific topics can't find them efficiently.  
**Fix:** Add client-side search (Pagefind, Fuse.js, or Lunr) — Pagefind is ideal for static sites.

### 13. No breadcrumbs on research pages
Research articles don't pass breadcrumbs to BaseLayout. Category hub pages do have breadcrumbs, but the articles themselves don't. This is inconsistent with Place/Route layouts which all have breadcrumbs.

**Impact:** SEO (Google uses breadcrumbs for sitelinks) and UX (users can't navigate up).  
**Fix:** Add breadcrumbs prop to ResearchLayout: Home → Research → Category → Article.

### 14. No table of contents on long articles
Research articles average 1,754 words but have no TOC. HubLayout has a TOC with scroll spy, but ResearchLayout doesn't.

**Impact:** Poor UX on long articles. Users can't scan or jump to sections.  
**Fix:** Add auto-generated TOC from article headings (Astro has plugins for this).

### 15. No pagination on category listing pages
The biblical-archaeology category has 190 articles, all rendered on a single page. Same for other large categories.

**Impact:** Slow page loads, poor UX, and Google may not crawl deeply into unpaginated lists.  
**Fix:** Add pagination (20-30 articles per page) or infinite scroll.

### 16. No WebP source images
All 733 images are JPEG. Netlify Image CDN can serve WebP via the `format` parameter, but the CdnImage component doesn't appear to request WebP format.

**Impact:** ~30-40% larger images than necessary.  
**Fix:** Add `format=webp` to Netlify Image CDN URLs in CdnImage component.

---

## LOW (2 issues)

### 17. No reading time on articles
No estimated reading time displayed. Minor UX enhancement.

### 18. No social sharing buttons
No share buttons for Twitter/X, Facebook, LinkedIn, or copy-link on articles.

---

## What's Working Well

- **Solid technical foundation:** Canonical URLs, meta descriptions, OG tags, Twitter cards, JSON-LD, sitemap, robots.txt
- **Strong content volume:** 680 research articles averaging 1,754 words — substantial depth
- **All articles have hero images** with proper width/height attributes and CLS prevention
- **Hub-spoke architecture** properly links pilgrimage content
- **Responsive design** now works across all layouts (after today's fixes)
- **Good page speed potential:** Static site with font preloading, inlined styles, lazy loading
- **Cross-silo internal linking** connects pilgrimage and research content
- **Proper legal pages:** Privacy, Terms, Affiliate Disclaimer all present

---

## Priority Action Plan

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| 1 | Add /research to header + footer nav | 5 min | Critical |
| 2 | Add Google Analytics (GA4) | 10 min | High |
| 3 | Add Google Search Console verification | 5 min | High |
| 4 | Create custom 404 page | 30 min | Critical |
| 5 | Create /about page with E-E-A-T content | 1 hr | High |
| 6 | Add breadcrumbs to research pages | 20 min | Medium |
| 7 | Add Article schema to research pages | 30 min | High |
| 8 | Dynamic OG images per article | 20 min | High |
| 9 | Fix 179 orphaned articles (internal links) | 1 hr | High |
| 10 | Add related articles component | 2 hrs | High |
| 11 | Add Pagefind search | 1 hr | Medium |
| 12 | Add table of contents to research layout | 1 hr | Medium |
| 13 | Add pagination to category pages | 1 hr | Medium |
| 14 | Newsletter/email capture | 1 hr | High |
| 15 | Author bios + schema | 2 hrs | High |
| 16 | WebP via Netlify CDN | 15 min | Medium |
| 17 | Reading time + social share | 30 min | Low |
