# TODO.md — ClickMart

> Priorisé par criticité. Cocher au fur et à mesure.
> Dernière mise à jour : 28 juillet 2026

---

## 🔴 Priorité 1 — Sécurité (2-3h)

- [x] **Créer un user SSH dédié** (`deploy`) — remplacer `root` dans le CI/CD
  - `adduser deploy && usermod -aG docker deploy`
  - Copier `authorized_keys`, mettre à jour `LINODE_USER` dans GitHub Secrets
- [x] **Rate limiting** sur `/api/v1/token/` et `/api/v1/register/`
  - `backend/config/settings.py` → ajouter `DEFAULT_THROTTLE_CLASSES` + `DEFAULT_THROTTLE_RATES`
  - `auth: 5/minute`, `anon: 20/minute`
- [x] **Headers de sécurité Django**
  - `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`
  - `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`
  - `SECURE_CONTENT_TYPE_NOSNIFF=True`
- [x] **Validation mot de passe** dans `UserRegisterSerializer`
  - Ajouter `validate_password()` + `from django.contrib.auth.password_validation import validate_password`
- [x] **Exclure `is_active`** du `ProductSerializer`
  - Remplacer `fields = "__all__"` par une liste explicite

---

## 🟠 Priorité 2 — Fiabilité backend (2-3h)

- [x] **`transaction.atomic()`** dans `PlaceOrderView` (`orders/views.py`)
  - Stock déduit + OrderItems créés dans la même transaction
  - `select_for_update()` sur le produit pour éviter les race conditions
- [x] **Validation des entrées** dans `carts/views.py`
  - `AddToCartView` : valider `product_id` (int), `quantity` (int > 0), vérifier stock
  - `ManageCartItemView` : valider `change` (int)
- [x] **Gestion panier inexistant** dans `PlaceOrderView`
  - Remplacer `Cart.objects.get()` par `get_object_or_create` ou try/except
- [x] **Email non bloquant** (`orders/utils.py`)
  - `fail_silently=True` + logging au lieu de crasher toute la commande
- [x] **Nettoyer les imports inutilisés**
  - `products/views.py`, `orders/views.py`, `carts/views.py` → supprimer `render` non utilisé
- [x] **Contrainte d'unicité** sur `CartItem` (`carts/models.py`)
  - `class Meta: unique_together = ('cart', 'product')` + migration

---

## 🟡 Priorité 3 — DevOps & résilience (1-2h)

- [ ] **Backup automatique DB** (cron quotidien)
  - Script `infra/scripts/backup-db.sh` → `pg_dump | gzip`
  - Rotation 7 jours, cron `0 2 * * *`
- [x] **Renouvellement SSL** — remplacé par le service Docker certbot
  - Boucle `while :; do certbot renew; sleep 12h; done` dans le container
- [ ] **Healthchecks Docker** dans `docker-compose.yml`
  - `db`: `pg_isready`, `backend`: `curl localhost:8000`, `nginx`: `curl localhost:80`
- [ ] **`.dockerignore`** backend + frontend
  - Exclure `__pycache__`, `.venv`, `.env`, `db.sqlite3`, `media/`
- [ ] **Logging structuré** (`backend/config/settings.py`)
  - Configurer `LOGGING` : console, niveaux par module

---

## 🟢 Priorité 4 — CI/CD améliorations (1h)

- [x] **Corriger les tests frontend** (vitest + jsdom)
  - Configurer `vite.config.js` avec `environment: 'jsdom'`
  - Retirer `|| true` une fois les tests fonctionnels
- [x] **Ajouter badge CI** dans le README
  - `[![CI/CD](https://github.com/tawounfouet/.../actions/workflows/automate.yml/badge.svg)](...)`
- [x] **Ajouter `ruff` + `pre-commit`** en local
  - `.pre-commit-config.yaml` → ruff, trailing-whitespace, check-yaml
  - `pip install pre-commit && pre-commit install`

---

## 🔵 Priorité 5 — Frontend (2-3h)

- [x] **ErrorBoundary** global (`src/components/ErrorBoundary.jsx`)
  - Wrapper dans `main.jsx` autour de `<App />`
- [x] **Axios interceptor** amélioré (`src/api/index.js`)
  - Redirection auto vers `/login` sur 401
  - Gestion des erreurs 500 avec toast/notification
- [x] **Lazy loading** des routes (`App.jsx`)
  - `React.lazy()` + `<Suspense>` pour chaque page
- [x] **Pagination backend** (`products/views.py`)
  - `PageNumberPagination`, `page_size=20`
- [x] **Corriger les warnings ESLint** (12 warnings)
  - Variables non utilisées dans 6 fichiers

---

## ⚪ Priorité 6 — Nettoyage & documentation (1h)

- [x] **Sortir `backend/static/` du git** (163 fichiers)
  - `echo "backend/static/" >> .gitignore && git rm -r --cached backend/static/`
- [x] **Supprimer `apple.jpg`** de `products/`
- [x] **Supprimer fichiers inutiles** dans `api/` (`models.py`, `admin.py`, `tests.py` vides)
- [x] **Refactor API** — structure par app (`users/api/`, `products/api/`, etc.)
  - Supprimé `backend/api/`, créé `api/urls.py` dans chaque app
- [x] **Mettre à jour `README.md`**
  - Corriger les sections obsolètes (ports 8000/5173 → 80/443, runserver → gunicorn)
  - Ajouter lien vers `docs/deploy/`
- [x] **Documentation API** (DRF Spectacular)
  - `pip install drf-spectacular` → Swagger UI sur `/api/docs/`

---

## ✅ Fait

- [x] Déploiement sur Linode (`http://172.239.20.14`)
- [x] CI/CD GitHub Actions (67 tests → build → deploy auto)
- [x] `ALLOWED_HOSTS` et `CORS_ALLOWED_ORIGINS` dynamiques
- [x] Firewall cloud : ports 80/443 ouverts, 8000/5173 supprimés
- [x] `.env.docker` + `.env.production` créés sur le serveur
- [x] Tests backend commités (67 tests)
- [x] Documentation : analyse critique, recommandations, plan, état des lieux, guides déploiement + CI/CD
- [x] `ETAT_DES_LIEUX.md` + `PLAN_IMPLEMMENTATION.md` mis à jour

---

## Résumé

```
Priorité 1 (sécurité)  : ✅ FAIT 5/5
Priorité 2 (fiabilité) : ✅ FAIT 6/6
Priorité 3 (devops)    : ██░░░░░░░░ 1/5
Priorité 4 (CI/CD)     : ✅ FAIT 3/3
Priorité 5 (frontend)  : ✅ FAIT 5/5
Priorité 6 (nettoyage) : ✅ FAIT 5/5
─────────────────────────────────
Total restant          : 4 tâches
Total fait             : 35 tâches
```
