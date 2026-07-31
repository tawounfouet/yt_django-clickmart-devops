VOCALFIT — Complete Codebase Architecture
1. PROJECT OVERVIEW
Attribute	Value
Name	VocalFit
Tagline	"Le Strava de la communication orale professionnelle"
Production URL	https://vocalfit.fr
API	https://api.vocalfit.fr
Server	IONOS VPS (87.106.195.45), Ubuntu 24.04
Repo	github.com/tawounfouet/vocalfit
License	Proprietary
Current version	0.7.0 (2026-07-21)
Test suite	56 API tests (pytest) + 3 frontend tests (vitest)
Sprint status	MVP complete: 9/9 tickets done (VF-000 through VF-009)
2. DIRECTORY STRUCTURE
vocalfit/
├── .github/workflows/ci-cd.yml     # 6-job CI/CD pipeline
├── Makefile                         # 45 targets (api, web, docker, db, deploy, utils)
├── AGENTS.md                        # Agent instructions and architecture quirks
├── ANALYSIS.md                      # Exhaustive analysis (182 files, ~29k LOC)
├── ARCHITECTURE.md                  # Full architecture: stack, flux, API, models, scoring, decisions
├── CHANGELOG.md                     # v0.1.0 through v0.7.0
├── INDEX.md                         # Full project file tree + endpoint index
├── ROADMAP.md                       # Phase 0 → V2
├── SDLC.md                          # 7-phase development lifecycle
├── TODOS.md                         # 171 checked items, 36 remaining
├── NEXT-STEPS.md                    # Post-MVP priorities
│
├── apps/
│   ├── api/                         # Django 5.2 + DRF backend
│   │   ├── config/                  # settings.py, urls.py, asgi.py, wsgi.py
│   │   ├── accounts/                # Auth app (User, OralProfile, WaitlistSubscriber)
│   │   ├── goals/                   # Goals app (Goal model)
│   │   ├── training/                # Main app (Sessions, Transcriptions, Metrics, AudioJournal, AITranscription)
│   │   ├── conftest.py              # pytest fixtures (user, api_client, authenticated_client)
│   │   ├── pytest.ini               # pytest config
│   │   ├── requirements.txt         # 17 packages
│   │   ├── Dockerfile               # Python 3.13-slim
│   │   └── manage.py
│   ├── web/                         # Next.js 16 + React 19 frontend
│   │   ├── src/app/                 # App Router pages
│   │   ├── src/components/          # 15+ components
│   │   ├── src/hooks/               # useRecorder, useTimer
│   │   ├── src/lib/                 # apiClient, auth-context, tokens
│   │   └── Dockerfile               # Node 22-alpine
│   └── mobile/.gitkeep              # Expo React Native (V1+)
│
├── packages/vocalfit-engine/.gitkeep  # Python vocal analysis engine (V2)
│
├── infra/
│   └── docker/
│       ├── docker-compose.yml        # 6 services: db, api, web, minio, mc, adminer
│       └── postgres/init.sql         # CREATE EXTENSION pg_trgm
│
├── scripts/                          # 5 deploy/DB scripts + README
├── docs/                             # 50+ documentation files
│   ├── architecture/                 # ADRs, data model, engine docs
│   ├── backend/                      # 20 operational docs (runbook, DIAGNOSTIC, etc.)
│   ├── product/                      # Pitch deck, naming, inspiration
│   ├── analyses/                     # 6 technical analyses
│   ├── plans/                        # 7 implementation plans
│   └── feedbacks/                    # 6 post-mortems
└── archives/                         # Session transcripts
3. BACKEND — Django 5.2 + DRF (apps/api)
3.1 Django Settings (config/settings.py)
- Django-environ loads .env then .env.local (override)
- Database: SQLite by default, PostgreSQL via DATABASE_URL env
- Auth: Custom User model (email-based, no username), JWT via simplejwt
- DRF: JSONRenderer, MultiPartParser, FormParser, PageNumberPagination (20/page)
- JWT: Access token 2h, refresh 30 days, Bearer prefix
- CORS: django-cors-headers, origins from env
- OpenAI: OPENAI_API_KEY env (optional)
- Storage: S3/MinIO via django-storages + boto3 if AWS creds present, else local FileSystemStorage
- Sentry: sentry-sdk[django], init only in production with DSN
- Language: fr_FR, timezone Europe/Paris
- INSTALLED_APPS order critical: training must precede django.contrib.staticfiles (custom runserver)
- Media: /media/ served from BASE_DIR/media
3.2 Models (6 models across 3 apps)
accounts/models.py:
- User(AbstractUser): email PK, name, UUID, custom UserManager
- OralProfile: OneToOne with User, 5 fields (context, main_blockage, speaking_frequency, comfort_level, main_objective), UUID
- WaitlistSubscriber: email, created_at
goals/models.py:
- Goal: FK User, 3 title choices (clarity, confidence, structure), UUID
training/models.py:
- TrainingSession: FK User, topic, status (in_progress/completed), 3 round durations, UUID
- Transcription: FK TrainingSession, round_number, raw_text, UUID, unique_together(session, round)
- Metrics: OneToOne TrainingSession, clarity_score, euh_count, conclusion_clear, total_duration, UUID
- AudioJournal: UUID PK, FK User, audio_file, topic, duration, consent_given, transcript, word_count, sentence_count, file_size
- AITranscription: FK User, audio_file, raw_text, enhanced_text, mode (5 choices), duration, word_count, UUID
3.3 API Endpoints (15 endpoints)
Method	URL
GET	/
POST	/api/auth/register/
POST	/api/auth/login/
POST	/api/auth/refresh/
GET	/api/auth/me/
GET/PUT	/api/auth/profile/
POST	/api/auth/waitlist/
GET/POST	/api/goals/
GET/POST	/api/sessions/
GET/PATCH	/api/sessions/<uuid>/
POST	/api/sessions/<uuid>/transcribe/
GET/POST	/api/journal/
GET	/api/journal/<uuid>/
GET/POST	/api/ai-transcriptions/
GET/DELETE	/api/ai-transcriptions/<uuid>/
3.4 Transcription Pipeline (training/transcribe.py)
Core logic:
- transcribe_audio(audio_bytes): Calls OpenAI Whisper API (whisper-1, language=fr), handles 413 errors for large files
- compress_for_whisper(audio_bytes): Two-tier compression: pydub → ffmpeg fallback, threshold 10MB
- count_eugh(text): Regex \b(euh|heu|euhh|heuu)\b
- has_conclusion(text): Regex for 8 conclusion keywords (donc, pour résumer, en conclusion, etc.)
- compute_clarity_score(euh_count, concluded, total_duration): Score = 0.5 * euh_density_score + 0.5 * conclusion_score
- enhance_transcription(text, mode): GPT-4o-mini with 5 mode prompts (standard, email, code, chat, combo)
Compression: Two-stage: pydub (opus 16k → mp3 64k) → ffmpeg (libmp3lame 64k). Threshold: 10MB
3.5 Serializers
- RegisterSerializer: email, name, password (min 8 chars, write-only)
- OralProfileSerializer: all fields except user
- GoalSerializer: id, uuid, title, chosen_at
- SessionListSerializer: includes computed metrics via SerializerMethodField (handles DoesNotExist)
- SessionDetailSerializer: includes nested transcriptions + computed metrics
- SessionCreateSerializer: topic only, id read-only
- SessionUpdateSerializer: status + 3 round durations
- TranscriptionSerializer: round_number, raw_text
- MetricsSerializer: clarity_score, euh_count, conclusion_clear, total_duration
- JournalSerializer: computed fields (euh_count, conclusion_clear, clarity_score, speaking_rate, avg_words_per_sentence)
- JournalCreateSerializer: with transcribe flag
- AITranscriptionSerializer / AITranscriptionCreateSerializer
3.6 Views Architecture
- SessionListCreateView: switches serializer based on method (POST → create, GET → list)
- SessionDetailView: UUID lookup, switches between retrieve and update serializers
- TranscribeView: Custom view, reads audio bytes, transcribes, accumulates metrics cumulatively
- JournalListCreateView: Auto-transcribes on create, can skip via transcribe=false flag
- AITranscriptionListCreateView: Overrides create(), handles Whisper + GPT-4o-mini pipeline
3.7 Tests (56 tests, pytest-django + model_bakery)
- accounts/tests/: test_models (10), test_serializers (9), test_views (11)
- goals/tests/: test_models (5)
- training/tests/: test_models (12), test_ai_transcription (9)
- conftest.py: Shared fixtures user, api_client, authenticated_client
- pytest.ini: --reuse-db, --tb=short, --strict-markers
4. FRONTEND — Next.js 16 + React 19 (apps/web)
4.1 Package Dependencies
Dependency
next
react
react-dom
@sentry/nextjs
lucide-react
tailwindcss
typescript
vitest
@testing-library/react
jsdom
4.2 Route Structure (App Router)
src/app/
├── layout.tsx                    # Root layout: AuthProvider wrapper, Outfit + Sora fonts
├── globals.css                   # Dark theme (#08080e), cyan/violet accents, custom animations
├── page.tsx                      # Landing page (12 sections)
├── login/page.tsx                # Login form
├── register/page.tsx             # Register form
├── onboarding/page.tsx           # 2-step onboarding (5 questions + goal selection)
├── api/waitlist/route.ts         # Waitlist API route (proxies to Django)
└── (app)/                        # Authenticated routes group
    ├── layout.tsx                # Sidebar layout (255px, fixed left)
    ├── dashboard/page.tsx        # Welcome, session CTA, latest sessions
    ├── sessions/
    │   ├── page.tsx              # Progression: stats cards, SVG chart, history list
    │   ├── new/page.tsx          # Creates session via POST then redirects
    │   └── [id]/
    │       ├── page.tsx          # 3-round training UI (timer + recording + transcription)
    │       └── results/page.tsx  # Detailed results with all transcriptions + metrics
    ├── journal/
    │   ├── page.tsx              # List with clarity scores
    │   ├── new/page.tsx          # Record/upload, consent, review, save
    │   ├── [id]/page.tsx         # Detail with 8 metric cards
    │   └── import/page.tsx       # Batch file uploader
    ├── dictation/
    │   ├── page.tsx              # Dictée IA: 5 modes, real-time speech, waveform, markdown render
    │   └── [uuid]/page.tsx       # Detail page with raw/enhanced text display modes
    └── profile/page.tsx          # Read-only oral profile display
4.3 Auth & API Client (src/lib/)
tokens.ts: JWT stored in localStorage (keys: vocalfit_access_token, vocalfit_refresh_token)
api.ts — apiClient<T>():
- Auto-prepends NEXT_PUBLIC_API_URL
- Injects Bearer token header
- Auto-refresh: On 401, singleton refresh using refresh token, queues concurrent requests
- Redirects to /login on refresh failure
- Handles both JSON and FormData bodies
- Generic typed: apiClient<User>("/api/auth/me/")
auth-context.tsx — AuthProvider:
- React Context with user, profile, loading state
- On mount: validates stored tokens via /auth/me/
- login(): POST login → store tokens → fetch user
- register(): POST register → auto-login
- logout(): clear tokens, redirect
4.4 Hooks
useRecorder.ts (useRecorder()): MediaRecorder API wrapper
- Opus codec (audio/webm;codecs=opus)
- Permission error handling (NotAllowedError)
- Returns isRecording, isSupported, startRecording(), stopRecording() → Promise<Blob>
useTimer.ts (useTimer(initialDuration, { onFinish })):
- Countdown timer with setInterval(100ms)
- Ref-based to avoid stale state issues
- endTimeRef for precise elapsed time
- start(), pause(), reset(duration?), isFinished
4.5 Guard Components
AuthGuard: Checks user auth → /login if not, /onboarding if no profile
GuestGuard: Redirects to /dashboard or /onboarding if already logged in
4.6 Key Components
Component	File
Header	Header.tsx
HeroSection	HeroSection.tsx
WaitlistForm	WaitlistForm.tsx
LineChart	LineChart.tsx
AuthGuard	AuthGuard.tsx
GuestGuard	GuestGuard.tsx
9+ landing sections	ProblemSection, ProgressionLoopSection, etc.
4.7 Design System (globals.css)
- Background: #08080e (near-black)
- Surface: #0f0f18, elevated: #181825
- Accent: cyan #22d3ee, violet #8b5cf6, emerald #34d399
- Fonts: Outfit (headings via font-display), Sora (body via font-sans)
- Animations: fade-in-up, fade-in, pulse-glow, slide-in-right, count-up
- Utilities: gradient-text, gradient-border, glow
4.8 Sentry Integration
- Client: sentry.client.config.ts — NEXT_PUBLIC_SENTRY_DSN, traces 0.1, replays off
- Server: sentry.server.config.ts — SENTRY_DSN, traces 0.1
- Both enabled only in production
5. INFRASTRUCTURE
5.1 Docker Compose (infra/docker/docker-compose.yml)
6 services:
Service	Image	Port
db	postgres:17-alpine	5434:5432
api	Built from apps/api/	8000:8000
web	Built from apps/web/	3000:3000
minio	minio/minio:latest	9000, 9001
mc	minio/mc:latest	—
adminer	adminer:latest	8080:8080
5.2 CI/CD Pipeline (.github/workflows/ci-cd.yml)
6 jobs, sequential:
api-lint (ruff) → api-test (pytest) → web-lint (eslint) → web-test (vitest) → web-build (next build) → deploy
- Trigger: push/PR to main
- Deploy: SSH to VPS → sudo bash deploy-app.sh → health check (curl HTTPS API + Web)
- Secrets: SERVER_HOST, SERVER_SSH_KEY, DB_PASSWORD, SECRET_KEY
5.3 Deployment Script (scripts/deploy-app.sh - 362 lines)
7-step idempotent deployment:
1. Swap: 2GB swap file for OOM protection
2. PostgreSQL: Create user/database, configure pg_hba.conf for scram-sha-256
3. Application: Git pull, pip install, Django migrate + collectstatic
4. Frontend build: npm ci && npm run build (incremental via commit hash caching)
5. Gunicorn systemd: vocalfit-api.service (2 workers, timeout 30s, binds 127.0.0.1:8000)
6. Next.js systemd: vocalfit-web.service (port 3000)
7. Nginx + TLS: API vhost (api.vocalfit.fr), web vhost (vocalfit.fr), certbot Let's Encrypt
5.4 Server Setup (scripts/setup-server.sh - 139 lines)
8-step idempotent VPS initialization: hostname, SSH hardening, system update, timezone/locale, ufw (ports 22/80/443), fail2ban, application user creation, package installation (nginx, postgresql 16, python3, certbot, etc.)
5.5 Backup (scripts/backup-db.sh)
Daily cron (3am): pg_dump → gzip → daily retention 7d → weekly copy (Sundays) → 30d weekly retention
5.6 Production Architecture
User → Nginx (:80/:443)
  ├── vocalfit.fr → proxy_pass Next.js :3000
  │   └── /api/* → proxy_pass Gunicorn :8000
  └── api.vocalfit.fr → proxy_pass Gunicorn :8000
      └── /static/ → alias staticfiles/
6. MONOREPO TOOLING
6.1 Makefile (45 targets)
Category	Targets
API	api-venv, api-dev, api-migrate, api-shell, api-seed, api-test, api-lint, api-format
Web	web-install, web-dev, web-build, web-start, web-lint, web-test
Docker	docker-up, docker-down, docker-rebuild, docker-logs, docker-reset, docker-exec
DB	db-setup-local, db-setup-docker, db-reset-local, db-reset-sqlite, db-shell
Deploy	deploy-scp-setup, deploy-setup, setup-github-deploy, deploy-scp-app, deploy-app
CI	check, ci, clean, git-info, git-push, setup
6.2 Connection Between apps/api and apps/web
- No shared code package between API and web (MVP architecture decision)
- API types: No generated TypeScript types; types are defined manually in page components
- Communication: REST JSON via apiClient() function, FormData for file uploads
- API URL: NEXT_PUBLIC_API_URL env var (defaults to http://localhost:8000)
- Auth flow: Web stores JWT in localStorage → sends Bearer token → auto-refresh on 401
- Docker: Web build arg NEXT_PUBLIC_API_URL set to API container
6.3 Shared Infrastructure
- Both apps share: PostgreSQL, MinIO S3, compilation via Makefile
- Production: both served by Nginx on same VPS, systemd managed
- CI: both tested independently, deployed together
7. SECURITY MODEL
Current (MVP)
- Auth: JWT (access 2h, refresh 30d) via SimpleJWT, HS256 signing
- CORS: django-cors-headers, origins from env
- CSRF: Django's CsrfViewMiddleware active
- Password hashing: Argon2 (Django default)
- Rate limiting: Not implemented
- Audio storage: Not persisted in MVP (session-only, except AudioJournal with explicit consent)
- Sentry: send_default_pii=false
- Server: ufw (22, 80, 443), fail2ban SSH, password auth disabled
- HTTPS: Let's Encrypt via certbot
Planned (V1+)
- Rate limiting on auth endpoints (django-ratelimit)
- CSP headers
- RS256 JWT rotation
- Full RGPD compliance (consent, retention, deletion, audit logs)
- Audio encryption at-rest
8. SCORING ALGORITHM
euh_density = euh_count / (total_duration_minutes)
euh_score = max(0, 1.0 - euh_density / 10)
conclusion_score = 1.0 if conclusion detected, 0.0 otherwise
clarity_score = 0.5 * euh_score + 0.5 * conclusion_score
9. KEY ARCHITECTURAL DECISIONS (ADRs)
1. Django > FastAPI: ORM, admin, ecosystem maturity for MVP
2. No MinIO/Celery/Redis in MVP: Audio not persisted, synchronous transcription, zero queue infrastructure
3. JWT > Sessions: Stateless, mobile-compatible
4. Next.js App Router: RSC, modern DX
5. Whisper API > local: Zero GPU infra, $0.006/min
6. No E2E tests, no Expo mobile, no LLM feedback in MVP: Prioritize core functionality
10. ROADMAP STATUS
Phase	Status
Phase 0 (Validation)	COMPLETE
Phase 1 (Sprint MVP)	COMPLETE (9/9)
Phase 2 (Retention)	BACKLOG
Phase 3 (Boucle métier)	BACKLOG
Phase 4 (Stabilization)	BACKLOG
V2 (Moteur + Mobile)	BACKLOG
11. FILE COUNT SUMMARY
Category
Root config/docs
Django source (py)
Django tests (py)
React/Next.js source (tsx/ts)
Infrastructure (yaml/sh)
Documentation (md)
Total
This is the COMPLETE picture. Every file has been read and analyzed. The project is a well-structured, fully-functional Django 5.2 + DRF backend with 6 models and 15 REST endpoints, paired with a Next.js 16 App Router frontend featuring auth, 3-round training sessions, journal, AI dictation, progression charts, and full CI/CD deployment to IONOS VPS with PostgreSQL 16, Gunicorn, Nginx, and Let's Encrypt.