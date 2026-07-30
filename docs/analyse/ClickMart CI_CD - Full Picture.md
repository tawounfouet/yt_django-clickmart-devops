ClickMart CI/CD — Full Picture
1. GitHub Actions Workflows
File: .github/workflows/automate.yml
One workflow exists at /Users/awf/workspace/learning/openclassrooms/02-parcours-formations/DA. Python _ OCR/P13 - Django CI_CD - Architecture Modulaire  /yt_django-clickmart-devops/.github/workflows/automate.yml (149 lines).
Triggers: All pushes and PRs to main, stg, and dev.
Four jobs, sequential pipeline:
Job	Runs	Depends on
test-backend	Always (push + PR)	—
test-frontend	Always (push + PR)	—
build-and-push	Push only on main/stg	test-backend, test-frontend
deploy-staging	Push on stg only	build-and-push
deploy-production	Push on main only	build-and-push
Container registry: ghcr.io/tawounfouet/clickmart-backend and clickmart-frontend, pushed with :latest tag.
Secrets required: LINODE_HOST, LINODE_USER, LINODE_SSH_KEY, GITHUB_TOKEN.
2. Deploy Mechanism
How deployment works in production
The CI/CD pipeline uses appleboy/ssh-action@v1.0.3 to SSH into the Linode VPS. The deploy script:
cd /opt/clickmart                     # (or /opt/clickmart-stg for staging)
git fetch origin main && git reset --hard origin/main
docker login ghcr.io -u ${{ github.actor }} --password-stdin ${{ secrets.GITHUB_TOKEN }}
docker compose -p clickmart -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -p clickmart -f docker-compose.yml -f docker-compose.prod.yml up -d
# Health checks after 15s sleep:
curl -sf http://localhost/api/v1/products/
curl -sf http://localhost/
Key design decisions:
- git reset --hard origin/main (not git pull) to avoid merge conflicts
- Docker images are pre-built in CI and pushed to GHCR; the server only pulls
- Health check via curl on localhost — Nginx reverse proxy routes to backend/frontend
- Post-deploy nginx -s reload ensures config changes take effect
Docker Compose Stack
Base file (docker-compose.yml): 8 services — db (postgres:16-alpine), redis (redis:7-alpine), minio, backend (gunicorn x3), celery-worker, celery-beat, frontend (nginx serving dist/), nginx (reverse proxy).
Production overlay (docker-compose.prod.yml): 
- disables db, minio, redis (using external/managed instances)
- adds certbot service (certbot/certbot image, renews every 12h, deploy hook restarts nginx)
- mounts SSL volumes: infra/certbot/conf:/etc/letsencrypt, infra/certbot/www:/var/www/certbot
- mounts infra/nginx/prod.conf as nginx config (HTTP 80 redirect to HTTPS 443)
Staging overlay (docker-compose.staging.yml):
- Runs local db, redis, minio
- Exposes port 8080 (not 80/443)
- No SSL
- Uses infra/nginx/staging.conf
Dev overlay (docker-compose.override.yml):
- Port 80 locally
- Uses staging nginx config
- Loads .envs/.local
Makefile targets:
- make up-dev / down-dev
- make up-staging / down-staging / logs-staging
- make up-prod / down-prod / logs-prod
3. Test Infrastructure
Backend: Django Tests
Framework: Django's built-in TestCase (no pytest). Run with:
python manage.py test --verbosity=2
Database strategy: In CI, DATABASE_URL is NOT set, so Django falls back to SQLite (in-memory). The settings.py uses dj-database-url:
DATABASE_URL = config('DATABASE_URL', default='')
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
CI environment variables passed in workflow: SECRET_KEY, DEBUG, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS. No DB_ variables* — this forces SQLite.
78 tests total (67 backend + 11 frontend), organized by app:
- users — 12 tests
- products — 15 tests
- carts — 22 tests
- orders — 18 tests
Frontend: Vitest
Config: Inline in vite.config.js (no separate vitest config file):
test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    css: true,
},
Setup file (frontend/src/test/setup.js): Just import '@testing-library/jest-dom'.
Test files found: QuantitySelector.test.jsx, CartProvider.test.jsx.
CI command: npx vitest run --config vite.config.js (in frontend/ directory).
4. Linters
Python: Ruff
Pre-commit config (.pre-commit-config.yaml):
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.5.0
  hooks:
    - id: ruff
      args: [--fix, --ignore, F401,E501,E402]
    - id: ruff-format
Plus generic hooks: trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files, detect-private-key.
CI: ruff check . --ignore F401,E501,E402 || true (non-blocking — || true).
No ruff.toml or pyproject.toml in the repo — ruff uses defaults + the ignore args.
JavaScript/React: ESLint
Config (frontend/eslint.config.js): ESLint flat config (v9), uses:
- @eslint/js recommended
- eslint-plugin-react-hooks (recommended-latest)
- eslint-plugin-react-refresh (vite config)
- Ignores dist/
- Rule: no-unused-vars: error (variables starting with uppercase ignored)
CI: npm run lint || true (non-blocking — || true).
5. Dependencies
Backend (backend/requirements.txt):
Package
Django
djangorestframework
djangorestframework_simplejwt
django-cors-headers
django-storages[s3]
django-cloudinary-storage
gunicorn
psycopg2-binary
python-decouple
celery
redis
pillow
drf-spectacular
boto3
resend
PyJWT
sqlparse
dj-database-url
asgiref
CI adds: ruff, coverage (via pip install).
Frontend (frontend/package.json):
Runtime: react 19, react-dom 19, react-router-dom 7, react-bootstrap 2.10, bootstrap 5.3, bootstrap-icons 1.13, lucide-react, axios, react-toastify.
Dev: vite 7, vitest 4, @testing-library/react, @testing-library/jest-dom, @testing-library/user-event, eslint 9, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, jsdom 29, @vitejs/plugin-react 5.
Dockerfiles:
Backend (backend/Dockerfile): python:3.10-slim, installs curl, pip installs requirements.txt. Health check: curl localhost:8000/api/v1/products/. CMD: gunicorn 3 workers, timeout 180s.
Frontend (frontend/Dockerfile): Multi-stage — Node 18 build stage (npm install, npm run build with VITE_SERVER_BASE_URL and VITE_ENVIRONMENT build args), then nginx:alpine serves dist/.
6. Deploy Documentation (all 6 files in docs/deploy/)
COMPRENDRE_SSL.md (300 lines)
Explains why certbot/conf/ is empty in git but full on the server. Covers the volume-sharing design: certbot writes certs to certbot/conf/ host directory, which is mounted as /etc/letsencrypt in BOTH nginx and certbot containers. Certificates never leave the server, survive rebuilds, and are auto-renewed.
CERTBOT_DOCKER.md (490 lines)
Compares old method (apt install certbot + cron + manual cp) vs new method (certbot as Docker service). Details all required files, volume sharing architecture, renewal cycle (every 12h, deploy-hook restarts nginx). Includes reproduction guide for new projects.
DEPLOIEMENT_LINODE.md (580 lines)
Historical doc. Covers full architecture, 2-layer firewall (cloud + UFW), why only ports 80/443 are needed, step-by-step deployment procedure, env variable table, gitignored-files problem (Dockerfiles + docker-compose.yml were gitignored, requiring SCP), and complete curl verification commands.
GUIDE_DOMAINE_SSL.md (576 lines)
Historical doc. 8-step guide: 1) buy domain, 2) configure DNS A records, 3) update Nginx server_name, 4) update ALLOWED_HOSTS, 5) certbot certonly webroot, 6) HTTPS nginx config, 7) cron auto-renewal, 8) verification. Includes troubleshooting for common errors.
GUIDE_CICD.md (625 lines)
Historical doc. Covers principle, prerequisites, SSH key setup, GitHub secrets, workflow creation, pipeline diagram (3 jobs: test-backend, test-frontend, deploy), testing the pipeline, troubleshooting, and the complete final YAML file.
COMPRENDRE_STATIC.md (365 lines)
Explains why static files (admin CSS) work in dev (Django runserver) but fail in production (gunicorn doesn't serve files). Solution: volume backend/static shared between backend (collectstatic writes) and nginx (alias /static/ reads). Includes debug checklist.
7. Agent-Based Deploy System
The .github/ directory also contains a comprehensive agent-based deployment system designed to deploy Django+React projects on ANY VPS:
Agent definition: .github/agents/deploy-fullstack.yml
4 phases (server-setup mandatory, code-deploy mandatory, cicd optional, ssl optional) with checkpoints at each phase.
4 Phase instructions:
- phase-1-server-setup.md — SSH + Docker + Git + firewall
- phase-2-code-deploy.md — env generation + clone + SCP + docker compose up
- phase-3-cicd.md — workflow YAML + GitHub secrets
- phase-4-ssl.md — DNS + certbot + nginx HTTPS
11 Skills:
- ssh-connect.md — SSH connection, OS/RAM detection
- provider-detect.md — Cloud provider detection via metadata endpoints + RDNS
- docker-install.md — Docker + Compose + Git install
- firewall-config.md — Auto-open ports via cloud APIs (doctl, linode-cli, aws, gcloud, az, hcloud)
- firewall-guide.md — Manual instructions when API unavailable
- env-generator.md — Generate .env.docker and .env.production
- project-deploy.md — Clone, SCP gitignored files, docker compose up
- health-check.md — Container status + endpoint curl checks + static CSS check
- github-cicd.md — Create deploy.yml workflow, set secrets
- dns-guide.md — Per-registrar DNS instructions (Namecheap, GoDaddy, IONOS, OVH, Cloudflare, Linode)
- ssl-setup.md — Docker-based certbot certificate + nginx HTTPS + renewal
Infrastructure scripts (infra/scripts/):
- setup-ssl.sh — Certificate + Nginx HTTPS + ALLOWED_HOSTS update + services restart + verification
- certbot-deploy-hook.sh — Restarts nginx after certificate renewal (called by certbot)
- backup-db.sh — pg_dump + gzip with 7-day retention
- minio-setup.sh — Creates MinIO bucket with public read policy
Nginx configs (infra/nginx/):
- prod.conf — HTTP:80 redirect to HTTPS, HTTPS:443 serves frontend, /api/, /admin/, /static/, /uploads/
- staging.conf — HTTP:80 only, same proxy_pass rules
8. Summary of Architecture
GitHub Push → GitHub Actions (automate.yml)
  ├── test-backend (Python 3.11, ruff, Django tests on SQLite)       ~17s
  ├── test-frontend (Node 20, eslint, vitest, vite build)            ~30s
  ├── build-and-push [main/stg only] (Docker buildx → ghcr.io)
  ├── deploy-staging [stg only] (SSH → /opt/clickmart-stg, port 8080)
  └── deploy-production [main only] (SSH → /opt/clickmart, ports 80/443)
       │
       ▼
    Linode VPS (172.239.20.14)
    docker compose -p clickmart -f docker-compose.yml -f docker-compose.prod.yml up -d
    │
    ├── nginx  (reverse proxy :80→301, :443 SSL)
    ├── frontend (React SPA from Docker image)
    ├── backend (gunicorn from Docker image)
    ├── certbot (auto-renew SSL every 12h)
    ├── celery-worker + celery-beat
    └── (external PostgreSQL, Redis, MinIO)
Production URL: https://webtech-dev.info (Linode 172.239.20.14)
Tests: 78 total (67 backend + 11 frontend)





Voici l'analyse comparative des bonnes pratiques de VocalFit réutilisables pour ClickMart :
Reproductible tel quel (✓)
- working-directory par job — plus propre que les cd successifs dans ClickMart
- Cache npm (cache: npm + cache-dependency-path) — accélère npm ci de ~30s
- Tests strictement bloquants (pas de || true sur lint) — VocalFit fail si lint échoue, ClickMart ignore les erreurs
- Health checks structurés avec messages ❌/✅ explicites par endpoint
- Script de déploiement externalisé (scp scripts/deploy-app.sh) vs commandes inline — plus maintenable
Pas pertinent pour ClickMart
- apps/api vs apps/web — structure différente (backend/ + frontend/)
- root SSH — ClickMart utilise deploy, déjà meilleur
- Pas de Docker — VocalFit ne build pas d'images, ClickMart push vers ghcr.io
Ce que ClickMart fait déjà mieux
- test-backend et test-frontend en parallèle (VocalFit les séquence lint→test)
- Build Docker + push ghcr.io avant le déploiement (VocalFit n'a pas cette étape)
- git reset --hard pour éviter les conflits de merge
Tu veux que j'applique ces améliorations au pipeline ClickMart ? (suppression des || true, caching npm, working-directory, script de déploiement externalisé)
▣  Build · DeepSeek V4 Pro · 2m 35s