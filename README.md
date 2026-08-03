# <img src="frontend/public/starjyotish.svg" width="24" height="24" alt="" valign="middle" /> Star Jyotish

**Meet Your Personal AI Vedic Astrologer.**

Star Jyotish combines authentic Vedic astrology calculations (Swiss Ephemeris) with AI-generated insights, providing ongoing guidance rather than one-time predictions.

**Live:** [starjyotish.com](https://starjyotish.com)

---

## Product

### User Journey

```
Landing (/)
  → /generate  (enter birth details)
  → /kundli    (full chart viewer + AI)
  
Sign in (/login)
  → /onboarding (first-time: save chart to account)
  → /home       (personal dashboard with inline chart summary)
  → /kundli     (deep-dive from home page sections)
  → /account    (profile, saved charts, subscription)

Learn (/learn)
  → /learn/zodiac
  → /learn/zodiac/aries  (etc.)
```

### Pages

| Route | Description |
|-------|-------------|
| `/` | Landing — product intro, AI demo, how-it-works |
| `/generate` | Birth details form (date, time, place) |
| `/kundli` | Full chart viewer: Birth Chart, Divisional, Planets, Dasha, Transit, Download, Advanced, Insights (AI reading, Rajyogas, Career), Ask AI |
| `/home` | Authenticated dashboard: identity, inline chart, planets grid, dasha timeline, yogas, topic snapshots, Ask AI, Knowledge Center links |
| `/onboarding` | First-time chart setup wizard for authenticated users |
| `/account` | Profile (name, avatar, language), saved astrology profiles, subscription status |
| `/login` | Phone OTP or Google OAuth |
| `/learn` | Knowledge Center hub |
| `/learn/zodiac` | Zodiac signs hub |
| `/learn/zodiac/:sign` | Individual sign guide |
| `/blog` | Blog listing |
| `/blog/:slug` | Blog article |
| `/pricing` | Pricing page |
| `/about` | About Star Jyotish |
| `/faq` | Frequently asked questions |
| `/contact` | Contact form |
| `/privacy` | Privacy Policy |
| `/terms` | Terms of Use |
| `/refund-policy` | Refund Policy |
| `/disclaimer` | Disclaimer |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite 5, Tailwind CSS 3 |
| **Routing** | react-router-dom 7 |
| **i18n** | react-i18next (English + Hindi) |
| **SEO** | react-helmet-async, JSON-LD schema, sitemap.xml |
| **Backend** | FastAPI (Python 3.12) |
| **Astrology** | pyswisseph (Swiss Ephemeris C binding) |
| **Database** | PostgreSQL, SQLAlchemy 2.x, Alembic (8 migrations) |
| **Auth** | Phone OTP (MSG91 / 2Factor) + Google OAuth, JWT + rotating httpOnly refresh tokens |
| **AI** | OpenRouter (configurable model, defaults to a free tier) primary, Claude direct fallback, Groq/Llama final fallback |
| **Deployment** | Frontend → Vercel, Backend → Railway |
| **Monitoring** | Sentry (frontend + backend, opt-in via env var) |
| **Security** | CSP, HSTS, X-Frame-Options, slowapi rate limiting |

---

## Chart Features

- **North Indian chart style** (SVG) with KP toggle
- **Navamsa (D9)** always shown alongside Lagna
- **Full Shodashvarga** — all 16 divisional charts (D1–D60)
- **KP Chart** (Krishnamurti Paddhati sub-lord system)
- **Bhava Chalit** chart
- **Ashtakavarga** (Bhinnashtakavarga + Sarvashtakavarga)
- **Transit chart** — current planets over natal
- **Vimshottari Dasha** — Mahadasha / Antardasha / Pratyantar with progress
- **Rajyoga detection** — 19 classical combinations checked against exact positions
- **Planetary table** — sign, house, nakshatra, pada, retrograde, dignity, exaltation

---

## AI Features

- **AI Reading** — full narrative chart reading (OpenRouter primary, Claude direct then Groq fallback). Prompts grounded in `astro-skills/` reference library (~1.1 MB covering career, gemstones, marriage, nakshatra, houses, planets, numerology, children)
- **Ask AI** — up to 10 chart-specific Q&A per session, with suggested starter questions
- **Career Report** — dedicated D10 + Dasha + Rajyoga analysis (English or Hindi)
- **Topic snapshots** — inline career / relationship / health / wealth derivations on the home dashboard (no extra API call — derived from chart data already fetched)

---

## Authentication & Sessions

- Phone OTP or Google OAuth sign-in
- **Access token**: 15-minute JWT, memory-only (never `localStorage`)
- **Refresh token**: 30-day rotating opaque token in an `httpOnly, Secure, SameSite=None` cookie — single-use, theft-detection via revocation replay check
- Sessions listed and revocable at `/account`
- No idle-timeout (users stay logged in until they explicitly log out or 30 days of inactivity)

---

## Astrology Profiles (Cross-Device Persistence)

When authenticated, birth profiles are saved to the backend (`POST /api/account/birth-profiles/me`) and retrieved on every device (`GET /api/account/birth-profiles/me`). Chart calculation results are cached in `localStorage` for fast loads; on a cold device the chart is silently re-computed from the stored birth details.

Unauthenticated users' chart data is `localStorage`-only.

---

## Project Structure

```
StarJyotish/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── home/            # PersonalHome sub-components
│   │   │   ├── knowledge/       # Knowledge Center components
│   │   │   ├── auth/            # Login-specific components
│   │   │   ├── SiteHeader.jsx   # Fixed top nav — identical on every page
│   │   │   ├── CompactFooter.jsx # Footer for authenticated pages
│   │   │   ├── Footer.jsx       # Full marketing footer (Landing/Learn/Pricing)
│   │   │   └── ...
│   │   ├── pages/               # One file per route
│   │   ├── config/
│   │   │   ├── homeData.js      # Data helpers for PersonalHome
│   │   │   ├── knowledgeGraph.js # Knowledge Center guide graph
│   │   │   └── topics.js        # Chart topic definitions
│   │   ├── services/
│   │   │   └── astrologyProfiles.js  # Profile create/list with backend sync
│   │   ├── contexts/
│   │   │   └── AuthContext.jsx  # Auth state, access token, authedRequest()
│   │   ├── hooks/               # useScrollProgress, useScrolledPast, etc.
│   │   ├── api/                 # fetch wrappers for each backend endpoint
│   │   └── i18n/
│   │       ├── en.json
│   │       └── hi.json
│   └── public/
│       ├── starjyotish.svg
│       ├── icon-192.png
│       └── icon-512.png
│
├── backend/
│   ├── routes/                  # /api/kundli/* — chart, reading, ask, etc.
│   ├── routers/                 # /api/auth/*, /api/account/*
│   ├── services/                # chart_context, jwt_service, geocode, etc.
│   ├── db/
│   │   ├── models/              # SQLAlchemy models (User, UserSession, BirthProfile, …)
│   │   └── repositories/        # Data access layer
│   └── alembic/                 # 8 migrations: 0001_initial → 0008_*
│
├── docs/
│   ├── vision/                  # PRODUCT_ARCHITECTURE.md, USER_JOURNEY.md, etc.
│   ├── design/                  # DESIGN_PHILOSOPHY.md
│   └── engineering/             # ENGINEERING_PRINCIPLES.md
│
└── astro-skills/                # Vedic astrology reference library for AI prompts
```

---

## Design System

All design tokens are in `frontend/tailwind.config.js`. Key colours:

| Token | Value | Usage |
|-------|-------|-------|
| `night` | `#171B33` | Header bg, dark section bg |
| `primary` | `#D4A017` (saffron gold) | CTAs, active states |
| `primary-light` | light tint | Selected chips, hover backgrounds |
| `parchment` | `#F8F3E7` | Page background |
| `parchment-card` | slightly darker parchment | Card backgrounds |
| `ink` | dark navy | Body text |
| `ink-muted` | muted navy | Secondary text |
| `ink-faint` | light muted | Tertiary text, labels |
| `ink-onnight` | light cream | Text on dark backgrounds |
| `mauve` | muted purple | Rashi chips |
| `vermillion` | muted red | Mahadasha chips, retrograde |

Typography: **Fraunces** (serif, headings) + **Inter** (sans-serif, body).

---

## Local Development

### Prerequisites
- Node.js 20+, Python 3.12+, PostgreSQL 15+

### Frontend
```bash
cd frontend
npm install
cp .env.example .env          # set VITE_API_BASE=http://localhost:8000
npm run dev                   # http://localhost:5173
```

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set DATABASE_URL, JWT_SECRET_KEY, COOKIE_SECURE=false
alembic upgrade head
uvicorn main:app --reload     # http://localhost:8000
```

### Environment variables

**Backend `.env`:**
```
DATABASE_URL=postgresql://user:pass@localhost:5432/starjyotish
JWT_SECRET_KEY=<64-char random hex>
COOKIE_SECURE=false           # true in production
OPENROUTER_API_KEY=           # primary LLM
OPENROUTER_MODEL=             # model OpenRouter is asked for — defaults to a free-tier model
ANTHROPIC_API_KEY=            # 1st fallback (direct Claude)
GROQ_API_KEY=                 # final fallback LLM
GOOGLE_CLIENT_ID=             # for Google OAuth
RESEND_API_KEY=               # for email OTP
SENTRY_DSN=                   # optional
```

**Frontend `.env`:**
```
VITE_API_BASE=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=
VITE_SENTRY_DSN=              # optional
```

---

## Deployment

| Service | Platform | Trigger |
|---------|----------|---------|
| Frontend | Vercel | Push to `main` (GitHub Actions) |
| Backend | Railway | Push to `main` (GitHub Actions) |
| Database | Railway PostgreSQL | Persistent, Alembic migrated on deploy |

---

## Remaining Work - will keep updating this list as we go

- **Payments** — Razorpay integration pending company registration + GST
- **Reading history tracking** — backend model exists (`ReportSummaryOut`); frontend "Continue Your Journey" still uses a static graph rather than real history
- **Ask Jyoti / Reports as canonical routes** — currently tabs inside `/kundli`; promoted to global nav once they have standalone URLs
- **Idle timeout** — no inactivity logout yet; straightforward to add via `useIdleLogout` hook in `AuthContext.jsx`
