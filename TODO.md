# TODO.md — ClickMart

> Priorisé par criticité. Dernière mise à jour : 30 juillet 2026

---

## ✅ Déjà réalisé

### Session 29/07

- [x] Branches dev/stg/main + CI/CD conditionnel
- [x] Docker Compose split (base + prod + staging overrides)
- [x] Multi-environnement (.envs/, MEDIA_STORAGE_BACKEND, EMAIL_BACKEND_TYPE)
- [x] Celery + Redis + tasks asynchrones
- [x] Storage backend tiers (local / S3 / Cloudinary)
- [x] Email backend tiers (console / SMTP / Resend)
- [x] PostgreSQL + Redis distants (49.13.239.42)
- [x] Services inutiles désactivés en prod (db, redis, minio)
- [x] Build Docker sur GitHub (ghcr.io), pull sur Linode
- [x] Apps media modulaires (core, images, audio, video, documents)
- [x] Agent deploy-fullstack v3.0
- [x] DRY_RUN_REPORT.md + inventory.yml auto-générés
- [x] SECRET_KEY forte, DEBUG=False, CORS configuré
- [x] Nginx resolver DNS + reload auto
- [x] Admin auto-création (create_admin command)
- [x] Documentation (7 rapports, ARCHITECTURE v2, README v2)

### Session 30/07 — CI/CD v3 + Améliorations VocalFit

- [x] Pipeline v3 : jobs split lint/test/build (6 jobs au lieu de 2)
- [x] Lint strict (suppression `|| true` sur ruff et eslint)
- [x] `working-directory` via `defaults` (backend et frontend)
- [x] Script de déploiement externalisé : `infra/scripts/deploy-app.sh`
- [x] Health checks enrichis (frontend + API + swap, 301/302 acceptés)
- [x] Renommage `automate.yml` → `ci-cd.yml`
- [x] Mise à jour `LINODE_SSH_KEY` après reprovisionnement Ansible
- [x] Documentation Ansible complète (10 fichiers) dans `docs/infra/ansible/`
- [x] Documentation bugs CI/CD dans `docs/debug/2026-07-30_CI-CD_bugs.md`
- [x] Mise à jour `docs/reports/GESTION_CICD.md` → v3.0
- [x] Analyse comparative VocalFit : `docs/analyse/2026-07-30_ANALYSE_VOCALFIT_CLICKMART.md`
- [x] Plan d'implémentation : `docs/plans/2026-07-30_PLAN_AMELIORATIONS_VOCALFIT.md`

### Session 30/07 — Quick Wins (VocalFit → ClickMart)

- [x] `django-environ` remplace `python-decouple` + `dj-database-url`
- [x] Sentry backend + frontend intégré, conditionnel (SENTRY_DSN)
- [x] GuestGuard (PrivateRoute existait déjà = AuthGuard)
- [x] apiClient avec singleton refresh queue (remplacement redirect 401 brutale)
- [x] Makefile enrichi (9 cibles : api-test, api-lint, api-shell, web-test, web-lint, web-build, ci)

### Session 30/07 — Qualité (VocalFit → ClickMart)

- [x] pytest + pytest-django + pytest-cov + model_bakery installés
- [x] `pytest.ini` créé + `conftest.py` avec 7 fixtures partagées
- [x] Tous les tests migrés vers pytest + model_bakery (4 apps, 64 tests)
- [x] INDEX.md créé (arborescence + endpoints + composants)

### Session 30/07 — Architecture (UUID & Ops)

- [x] UUID PKs — `id` remplacé par UUIDField sur 6 modèles (User, Product, Cart, CartItem, Order, OrderItem)
- [x] URLs `<int:pk>` → `<uuid:pk>`, serializers nettoyés, fallback legacy supprimé
- [x] fail2ban — ajouté au rôle Ansible docker (SSH jail, maxretry 3, bantime 1h)
- [x] DB backup — rétention hebdomadaire 30j (copie le dimanche)

### Session 31/07 — Analyse django-pro-core

- [x] Analyse comparative : `docs/analyse/2026-07-31_ANALYSE_DJANGO_PRO_CORE.md` (14 patterns)
- [ ] **django-split-settings** — remplacer le `settings.py` monolithique
- [ ] **select_for_update() + transaction.on_commit()** — intégrité des commandes
- [ ] **Poetry** — remplacer `requirements.txt`
- [ ] **ValidateFieldsMixin** — defense in depth pour les serializers
- [ ] **deep_update + env vars** — surcharge de settings par `CLICKMART_*`
- [ ] **Pre-commit mypy + hooks** — typage statique
- [ ] **Concurrency CI** — cancel-in-progress sur deploy
- [ ] **get_or_none()** — QuerySet utilitaire

---

## 🔴 Priorité 1 — Sécurité / Fiabilité

- [ ] **Chiffrer secrets.yml avec ansible-vault**
  - `ansible-vault encrypt infra/ansible/group_vars/secrets.yml`
  - Ajouter `--ask-vault-pass` à la commande de déploiement
  - ⚠️ Le fichier est aussi en clair sur le serveur (`/opt/clickmart/infra/ansible/group_vars/`)
- [ ] **Rate limiting Nginx** — `limit_req_zone` + `limit_req` dans prod.conf
  - Actuellement couvert par DRF throttling (anon 20/min, user 60/min)
- [ ] **django-celery-beat** — scheduler DB-backed pour tâches périodiques
  - `pip install django-celery-beat` → `DatabaseScheduler`
  - Permet de gérer les tâches planifiées depuis l'admin Django

---

## 🟠 Priorité 2 — Améliorations

- [ ] **Upgrade RAM Linode** — 961 MiB → 2 Go (~12$/mois)
  - ⚠️ 6 conteneurs utilisent 740 MB (mem_limit), OS ~200 MB, marge quasi nulle
  - Permettrait staging + prod simultanés
- [x] **Healthchecks Celery dans docker-compose.yml**
  - ✅ Déjà fait (29/07) — `celery inspect ping` configuré
- [ ] **Flower monitoring** — dashboard temps réel Celery
  - `image: mher/flower`, port 5555
- [x] **Sentry** — error tracking conditionnel
  - `SENTRY_DSN` dans .env, chargement conditionnel dans settings.py + main.jsx
- [x] **apiClient refresh token** — singleton queue, retry automatique
- [x] **GuestGuard** — protection login/register si déjà authentifié
- [x] **django-environ** — remplace python-decouple + dj-database-url

---

## 🟡 Priorité 3 — Dette technique

- [x] **pytest + model_bakery** — remplacer Django TestCase
  - ✅ 4 apps migrées, 64 tests, fixtures partagées, `conftest.py`
- [ ] **INDEX.md** — arborescence complète + index des endpoints API
  - Basé sur le pattern VocalFit : `INDEX.md` à la racine du repo
- [x] **UUID PKs** — remplacer auto-increment par UUIDs (non énumérable)
  - ✅ 6 modèles migrés, URLs `<uuid:pk>`, plus de fallback int
- [x] **fail2ban** — protection SSH brute-force dans le rôle Ansible docker
- [x] **DB backup rétention** — rotation quotidienne 7j + hebdomadaire 30j
- [ ] **Nettoyer `deploy-app.sh`** — supprimer le git fetch redondant (fait aussi en inline)

- [x] **Ansible : multi-environnements** — staging ajouté à l'inventory
  - ✅ `clickmart-staging` avec ses propres vars (app_dir, compose_files, branch, ssl_enabled)
  - ✅ Playbook `hosts: all` + `--limit staging` pour déploiement ciblé
- [x] **Ansible : CI/CD** — job `provision` avec `workflow_dispatch`
- [x] **Export Ansible** — `infra/scripts/ansible-export.sh` + mode `@deploy-fullstack export`
- [ ] **Créer secrets.yml.example** — généré par le script export mais pas encore commité
  - ✅ Déclenchement manuel depuis l'UI GitHub Actions
  - ✅ Inputs : target (production/staging) + tags (docker, app, ssl, cicd)
  - ✅ Génération `secrets.yml` depuis les secrets GitHub
  - ✅ SSH key setup via `LINODE_SSH_KEY`

- [ ] **Compléter les skeletons media** — installer les lib et activer les process
  - `apps/audio/` → `pip install pydub` → extract metadata
  - `apps/video/` → `pip install ffmpeg-python` → extract thumbnail
  - `apps/documents/` → `pip install pypdf` → extract metadata
- [ ] **Nettoyer les migrations imbriquées** — `git rm` les dossiers `*_migrations/`
  - audio_migrations, video_migrations, images_migrations, documents_migrations
- [ ] **Tests des tâches Celery** — `task_always_eager=True` dans conftest
  - Couvrir `process_image`, `cleanup_expired_carts`, `send_order_confirmation_email`
- [ ] **`STATIC_URL` et `STATICFILES_DIRS`** — corriger le warning W004
  - `STATIC_URL = '/static/'` (ajouter le `/` initial)
  - `STATICFILES_DIRS = [BASE_DIR / 'config' / 'static']` (Path absolu)

---

## 🟢 Priorité 4 — Documentation

- [ ] **Mettre à jour `docs/deploy/`** — refléter ghcr.io + db distante
- [ ] **Mettre à jour `.github/agents/`** — refléter agent v3.0
- [ ] **Guide onboarding nouveau développeur** — `docs/CONTRIBUTING.md`
