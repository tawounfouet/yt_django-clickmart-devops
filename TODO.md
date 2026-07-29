# TODO.md — ClickMart

> Priorisé par criticité. Dernière mise à jour : 29 juillet 2026

---

## ✅ Déjà réalisé (session du 29/07)

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

---

## 🔴 Priorité 1 — Sécurité / Fiabilité

- [ ] **Rate limiting Nginx** — `limit_req_zone` + `limit_req` dans prod.conf
  - Actuellement couvert par DRF throttling (anon 20/min, user 60/min)
- [ ] **django-celery-beat** — scheduler DB-backed pour tâches périodiques
  - `pip install django-celery-beat` → `DatabaseScheduler`
  - Permet de gérer les tâches planifiées depuis l'admin Django

---

## 🟠 Priorité 2 — Améliorations

- [ ] **Upgrade RAM Linode** — 961 MiB → 2 Go (~12$/mois)
  - Permettrait staging + prod simultanés
  - Actuellement 275 MB libre, stable mais limite
- [x] **Healthchecks Celery dans docker-compose.yml**
  - ✅ Déjà fait (29/07) — `celery inspect ping` configuré
- [ ] **Flower monitoring** — dashboard temps réel Celery
  - `image: mher/flower`, port 5555
- [ ] **Sentry** — error tracking conditionnel
  - `SENTRY_DSN` dans .env, chargement conditionnel dans celery.py

---

## 🟡 Priorité 3 — Dette technique

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
