# PRODAFLT Content Researcher Pipeline

Async Python pipeline for the PRODAFLT gambling creative production system.

## What it does

1. **Scrape** — Downloads metadata + media from Instagram Reels, TikTok, YouTube Shorts
2. **Classify** — Maps content to 9 gambling-creative formats (newsjacking, fake-podcast, UGC, etc.)
3. **Score** — Virality (0-10) × 0.6 + Adaptation Potential (0-10) × 0.4 = Final Score
4. **Video Analyze** — ffmpeg frame extraction + Whisper transcription + hook/CTA tagging
5. **Persist** — Writes results to Neon PostgreSQL (`content_analysis`, `patterns`)
6. **Report** — Sends daily top-15 digest to Telegram / webhook

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your real tokens (NEVER commit .env)

# 3. Run daily pipeline
python -m content_researcher_pipeline.tasks daily --limit 15

# 4. Research a single URL
python -m content_researcher_pipeline.tasks research --url "https://..."
```

## Environment Variables

See `.env.example` for all placeholders. Required:

- `DATABASE_URL` — Neon PostgreSQL connection string
- `KIMI_API_KEY` — Moonshot AI API key (for future LLM enrichment)
- `ROUTER_BOT_TOKEN` — Telegram bot token for notifications

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   links     │───→│  scraper    │───→│ classifier  │───→│   scorer    │
│  (pending)  │    │(yt-dlp/httpx│    │(9 formats)  │    │(V×0.6+A×0.4)│
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                 │
                    ┌─────────────┐    ┌─────────────┐          │
                    │    DB       │←───│  pipeline   │←─────────┘
                    │(content_    │    │(orchestrator│
                    │ analysis)   │    │             │
                    └─────────────┘    └──────┬──────┘
                                              │
                    ┌─────────────┐    ┌──────┴──────┐
                    │  Telegram   │←───│   tasks     │
                    │   /webhook  │    │(scheduler)  │
                    └─────────────┘    └─────────────┘
```

## 9 Content Formats

| Format | Description |
|--------|-------------|
| `newsjacking` | Exploits breaking news / viral events |
| `fake_podcast` | Simulates podcast/TV interview |
| `ugc_testimonial` | User-generated win story |
| `money_counter` | Visual counter / growing stack |
| `fake_live` | Simulated live stream |
| `challenge` | Social challenge + reward |
| `transformation` | Before/after lifestyle change |
| `fomo_urgency` | Scarcity / limited-time offer |
| `educational_hook` | Strategy tutorial → CTA pivot |

## Scoring Formula

```
Final Score = Virality_Score × 0.6 + Adaptation_Potential × 0.4

Virality (0-10):
  • Hook strength      25%
  • Emotional trigger  20%
  • Shareability       15%
  • Pattern strength   20%
  • Platform fit       20%

Adaptation (0-10):
  • Creative flexibility  25%
  • Cost to produce       20%
  • Compliance risk       20%
  • Audience breadth      15%
  • CTA clarity           20%
```

## Database Schema

Uses existing PRODAFLT tables:
- `links` — source URLs to analyze
- `content_analysis` — classification + scores per link
- `patterns` — aggregated pattern frequency data
- `users`, `tz_specs`, `campaign_metrics`, `alerts_log` — shared tables

## Scheduled Tasks

| Task | Schedule | Command |
|------|----------|---------|
| Daily Research | Daily 09:00 UTC | `tasks.py daily --limit 15` |
| Trend Monitor | Mon/Wed/Fri 18:00 | `tasks.py trends` |

## License

Internal — PRODAFLT / Mercurio Group
