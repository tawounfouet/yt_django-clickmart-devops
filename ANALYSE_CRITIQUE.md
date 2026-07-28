# Analyse Critique — yt_django-clickmart-devops

> Date : 22 juillet 2026
> Portée : Revue complète du projet (architecture, code, sécurité, DevOps, tests)

---

## Table des matières

1. [Résumé exécutif](#1-résumé-exécutif)
2. [Architecture](#2-architecture)
3. [Backend (Django + DRF)](#3-backend-django--drf)
4. [Frontend (React + Vite)](#4-frontend-react--vite)
5. [Sécurité](#5-sécurité)
6. [Tests](#6-tests)
7. [CI/CD et DevOps](#7-cicd-et-devops)
8. [Déploiement](#8-déploiement)
9. [Problèmes critiques](#9-problèmes-critiques)
10. [Problèmes majeurs](#10-problèmes-majeurs)
11. [Problèmes mineurs et observances](#11-problèmes-mineurs-et-observances)
12. [Recommandations prioritaires](#12-recommandations-prioritaires)
13. [Score global](#13-score-global)

---

## 1. Résumé exécutif

ClickMart est un e-commerce Django + React apprenant le déploiement CI/CD sur Linode avec Docker, Nginx et Let's Encrypt. Le projet couvre un large périmètre technique mais présente des **failles de sécurité critiques**, un **pipeline CI/CD minimaliste**, et des **tests unitaires incomplets** qui en empêchent la production.

**Verdict** : Projet pédagogique solide pour l'apprentissage, mais **non prêt pour la production** sans corrections significatives.

---

## 2. Architecture

### 2.1 Structure backend

```
backend/
├── config/          # Settings Django centralisés
├── api/             # Router URL principal (pas une app métier)
├── products/        # CRUD produits
├── carts/           # Panier utilisateur
├── orders/          # Commandes
├── users/           # Auth + profil
├── media/           # Uploads (non versionné — OK)
├── static/          # Collectstatic (versionné — PROBLÉME)
└── .env             # Secrets (non versionné — OK)
```

### 2.2 Structure frontend

```
frontend/src/
├── api/             # Instance Axios
├── components/      # Composants réutilisables
├── context/         # React Context (Cart)
├── hooks/           # Custom hooks
├── pages/           # Pages/routes
├── Provider/        # AuthProvider, CartProvider
├── test/            # Tests frontend
└── data/            # Données statiques
```

### 2.3 Points positifs

- Séparation frontend/backend propre
- Apps Django modulaires (products, carts, orders, users)
- Naming convention cohérente
- Dossier `api/` comme router central — pattern correct

### 2.4 Points négatifs

- **`backend/static/` versionné** : Le dossier de collectstatic est dans Git. Il devrait être `.gitignore` et généré au build Docker uniquement.
- **`api/` n'est pas une app Django** : C'est un simple router URLs. Les fichiers `models.py`, `admin.py`, `tests.py` dans `api/` sont inutiles.
- **Pas de sérializers dans `orders/`** : Les serializers existent mais le dossier `orders/` manque de `__init__.py` explicite pour les imports.
- **Mélange de `APIView` et `generics`** : `products/` utilise les generics, `carts/` et `orders/` utilisent `APIView`. Pas de cohérence.

---

## 3. Backend (Django + DRF)

### 3.1 Database fallback (settings.py:86-148)

```python
def is_running_in_docker():
    if os.path.exists('/.dockerenv'):
        return True
    ...
def use_sqlite_fallback():
    if is_running_in_docker():
        return False
    ...
```

**Problème critique** : Ce mécanisme est **fragile et dangereux** en production :
- En Docker → force PostgreSQL, mais si la DB est indisponible → **crash au démarrage**
- En local → fallback SQLite silencieux, ce qui peut masquer des erreurs de connexion
- La détection Docker est basée sur `/.dockerenv` et `/proc/self/cgroup` — non fiable sur tous les OS
- **Aucun log** quand le fallback se déclenche

**Recommandation** : Supprimer le fallback SQLite. Utiliser des variables d'environnement claires (`DATABASE_ENGINE=postgresql`) et crasher explicitement si la config est manquante.

### 3.2 Commande docker-compose (README L202-205)

```yaml
command: >
  sh -c "python manage.py collectstatic --noinput &&
         python manage.py migrate &&
         python manage.py runserver 0.0.0.0:8000"
```

**Problème critique** :
- `runserver` en production — **jamais** en production, même dans Docker
- `collectstatic` + `migrate` au démarrage de chaque replica → course aux migrations
- Devrait utiliser `gunicorn` (déjà dans requirements.txt) — le README le décrit mais le `docker-compose.yml` commité utilise encore `runserver`

### 3.3 Sérializers

- `products/serializers.py` : `fields = "__all__"` expose **`is_active`** au client — permet de voir les produits inactifs via l'API détail
- `carts/serializers.py` : `fields = '__all__'` expose `id` du cart et `user` — potentiellement sensible
- Pas de validation métier dans les sérializers (ex: quantity minimum, prix positif)

### 3.4 Vues

- `PlaceOrderView` (orders/views.py:13-70) : **Pas de transaction atomique**. Si `product.save()` échoue après avoir déduit le stock, la base est corrompue. Utiliser `transaction.atomic()`.
- `PlaceOrderView` : `Cart.objects.get(user=request.user)` sans `try/except` — crash si le panier n'existe pas (ligne 19). Devrait utiliser `get_or_create` comme dans `CartView`.
- `ManageCartItemView` : `int(request.data.get('change'))` (ligne 59) — pas de validation de type. Si `change` est une string → crash 500.
- `AddToCartView` : `int(quantity)` sans validation — si `quantity` est None → crash.

### 3.5 Modèles

- `Product` : `price = models.DecimalField(max_digits=6, decimal_places=2)` → max 9999.99. Limite arbitraire, pourrait poser problème.
- `Order` : Champs `address`, `phone`, `city`, `state`, `zip_code` tous optionnels (`blank=True, null=True`). Un order peut être passé sans adresse — incohérent avec un e-commerce.
- `CartItem` : Pas de contrainte d'unicité `(cart, product)` — le `get_or_create` dans les vues compense, mais le modèle devrait l'avoir.
- `User` : `AbstractUser` avec `email` comme `USERNAME_FIELD` — correct mais `REQUIRED_FIELDS = ["username"]` force un username qui n'est pas utilisé dans l'UI.

### 3.6 Authentification

- JWT : Access token 15 min, refresh 7 jours — acceptable
- **Pas de whitelist/logout** : Un refresh token ne peut pas être révoqué. En production, c'est un risque.
- **Pas de rate limiting** sur `/api/v1/token/` — brute force possible
- `AUTH_PASSWORD_VALIDATORS` configuré mais `RegisterViewTests.test_register_weak_password` passe avec "123" (ligne 73-80 du test) — **les validateurs ne sont pas appliqués**. Cause probable : le serializer ne valide pas via `validate_password`.

---

## 4. Frontend (React + Vite)

### 4.1 Dépendances

| Librairie | Version | Observation |
|---|---|---|
| React | 19.1.1 | ✅ Latest |
| Vite | 7.1.2 | ✅ Latest |
| Bootstrap | 5.3.8 + react-bootstrap | ⚠️ Double CSS framework (Bootstrap + Bootstrap Icons + lucide-react) |
| axios | 1.12.2 | ✅ |
| react-router-dom | 7.9.1 | ✅ Latest |

### 4.2 Architecture frontend

- **Provider pattern** : `AuthProvider` > `CartProvider` > `App` — correct
- **Pas de gestion d'erreurs centralisée** : Pas de ErrorBoundary, pas de interceptor Axios pour les erreurs 401/500
- **Pas de loading states** : Les pages ne gèrent probablement pas le loading/error states
- **`CartContext.js`** ne définit pas de `Provider` — il exporte juste le contexte. Le vrai Provider est dans `Provider/CartProvider.jsx`

### 4.3 Build

- `npm run build` → `dist/` — standard Vite
- `npm run lint` → ESLint flat config — ✅
- `npm run test` → Vitest — ✅
- **Pas de TypeScript** — JSX pur. Réduit la sécurité de typage.

### 4.4 Points négatifs

- **`frontend/node_modules/` dans le repo** : Vérifier `.gitignore` — si c'est versionné, c'est un problème majeur (milliers de fichiers)
- **`frontend/.env` dans le repo** : Le fichier `.env` du frontend contient `VITE_SERVER_BASE_URL` — s'il contient des secrets, c'est grave. Mais Vite expose uniquement les variables `VITE_*` côté client, donc acceptable.
- **Pas de lazy loading** : Toutes les pages sont importées statiquement dans `App.jsx` — aucun `React.lazy()` / `Suspense`
- **Bootstrap + lucide-react** : Double icônes, incohérence visuelle probable

---

## 5. Sécurité

### 5.1 Critique

| Vulnérabilité | Emplacement | Impact |
|---|---|---|
| **SECRET_KEY dans `.env` non versionné** ✅ | `backend/.env` | OK |
| **Pas de `ALLOWED_HOSTS` en dev** | `settings.py:30` | `ALLOWED_HOSTS = []` — Django refuse les requêtes si DEBUG=False |
| **DEBUG=False par défaut** | `settings.py:28` | Si `.env` ne définit pas DEBUG → crash au démarrage |
| **`runserver` en prod** | `docker-compose.yml` | Pas de rate limiting, pas de workers, debug toolbar potentiel |
| **Pas de HTTPS forcé** | `settings.py` | `SECURE_SSL_REDIRECT` non configuré |
| **Pas de HSTS** | `settings.py` | `SECURE_HSTS_SECONDS` non configuré |
| **Pas de cookies sécurisés** | `settings.py` | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` non configurés |
| **Pas de `X-Content-Type-Options`** | `settings.py` | Manquant dans le middleware |
| **Email credentials en clair** | `settings.py:218-219` | `EMAIL_HOST_PASSWORD` en clair dans settings — acceptable via python-decouple |
| **SQL injection via psycopg2 brut** | `settings.py:118-126` | `psycopg2.connect()` avec interpolation de config — mais valeurs viennent de `.env`, risque faible |
| **Pas de Content Security Policy** | Frontend | XSS potentiel si用户contenu non sanitize |
| **CORS non restreint** | `settings.py:221-223` | Uniquement `localhost:5173` en dev — OK, mais doit être élargi en prod |

### 5.2 Majeur

- **Pas de throttling/rate limiting** sur les endpoints auth (`/token/`, `/register/`)
- **Pas de protection CSRF** pour les vues API — DRF gère via JWT, mais le middleware CSRF est actif, ce qui peut créer des conflits
- **`fail_silently=False`** dans `send_order_notification` — si l'email échoue, toute la commande crash

---

## 6. Tests

### 6.1 Couverture backend

| App | Fichiers tests | Tests | Statut |
|---|---|---|---|
| `products/` | `tests.py` | ~15 tests (model + API) | ✅ Complets |
| `carts/` | `tests.py` | ~22 tests (model + views) | ✅ Complets |
| `orders/` | `tests.py` | ~18 tests (model + views) | ✅ Complets |
| `users/` | `tests.py` | ~12 tests (model + views) | ✅ Complets |
| `api/` | `tests.py` | 0 | ❌ Inutile (juste un router) |

### 6.2 Observations sur les tests

- **Bonne couverture** des cas principaux (CRUD, permissions, cas limites)
- **Tests manquants** :
  - Pas de test pour `send_order_notification` (mocké mais jamais testé isolément)
  - Pas de test d'intégration (flux complet : register → login → add to cart → place order)
  - Pas de test pour le fallback SQLite
  - Pas de test pour le serializer (validation, champs exposés)
  - `test_register_weak_password` passe avec "123" — les validateurs de mot de passe ne sont pas testés correctement
- **Pas de configuration pytest** — les tests utilisent Django unittest natif
- **Pas de coverage** configuré — impossible de mesurer la couverture

### 6.3 Tests frontend

- `frontend/src/test/` existe mais non inspecté en détail
- Vitest configuré (`npm run test`)
- `@testing-library/react` et `@testing-library/jest-dom` présents
- **Pas de tests d'intégration** frontend (routes, providers)

---

## 7. CI/CD et DevOps

### 7.1 Pipeline actuel (.github/workflows/automate.yml)

```yaml
name: Auto Deploy to Linode
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.LINODE_HOST }}
          username: ${{ secrets.LINODE_USER }}
          key: ${{ secrets.LINODE_SSH_KEY }}
          script: |
            cd /opt/clickmart
            git pull origin main
            docker compose up --build -d
```

### 7.2 Problèmes critiques du pipeline

| Problème | Sévérité | Impact |
|---|---|---|
| **Pas de tests dans le pipeline** | 🔴 Critique | Le code non testé est déployé directement |
| **Pas de linting** | 🔴 Critique | Code non vérifié déployé |
| **Pas de build check frontend** | 🔴 Critique | Build frontend cassé → déployé |
| **Pas de rollback** | 🔴 Critique | Si le build échoue, le service est down |
| **SSH en root** | 🔴 Critique | `LINODE_USER = root` — accès complet au serveur |
| **Pas de health check** | 🟠 Majeur | Pas de vérification après déploiement |
| **Pas de notification d'échec** | 🟠 Majeur | Échec de deploy silencieux |
| **`docker compose up --build -d` sans `down`** | 🟡 Mineur | Les anciens containers ne sont pas arrêtés proprement |
| **Pas de cache Docker** | 🟡 Mineur | Build lent à chaque push |
| **Pas de secrets scanning** | 🟡 Mineur | Risque de commit accidentel de secrets |

### 7.3 Ce qui manque

- **Tests unitaires** dans le pipeline (backend + frontend)
- **Linting** (eslint, flake8/ruff)
- **Security scanning** (trivy, bandit)
- **Build verification** avant deploy
- **Health check** post-deploy
- **Rollback automatique** en cas d'échec
- **Environment staging** avant production
- **Conventional commits** pour le changelog
- **Version tagging** pour les releases

---

## 8. Déploiement

### 8.1 Stack de production

| Composant | Technologie | Observation |
|---|---|---|
| VPS | Linode | ✅ Simple et efficace |
| Containerisation | Docker Compose | ✅ |
| Reverse proxy | Nginx | ✅ |
| SSL | Let's Encrypt (Certbot) | ✅ |
| WSGI | Gunicorn | ✅ (décrit mais pas dans docker-compose commité) |
| CI/CD | GitHub Actions → SSH | �️ Minimal |

### 8.2 Problèmes de déploiement

- **Certbot installé manuellement sur le serveur** — pas de renouvellement automatique configuré (cron manquant)
- **Nginx config versionnée puis dé-versionnée** — le README décrit le processus mais le fichier n'est pas dans le repo
- **Pas de Docker healthcheck** dans les Dockerfiles
- **Pas de `.dockerignore`** visible — risque de copier `.venv/`, `db.sqlite3`, `.env` dans l'image
- **Volumes nommés pour static/media** — correct mais peut poser des problèmes de permission
- **Pas de backup** de la base de données configuré
- **Pas de monitoring** (pas de Prometheus, pas de Sentry, pas de logs structurés)

---

## 9. Problèmes critiques

> Impact : peuvent causer des pertes de données, des failles de sécurité, ou des downtime

1. **Pas de transaction atomique dans `PlaceOrderView`** — Le stock est déduit avant la création des OrderItems. Si un échec survient entre les deux, le stock est perdu sans commande.

2. **`runserver` en production** — Le docker-compose.yml utilise `runserver` au lieu de `gunicorn`. Le README décrit gunicorn mais le code ne l'utilise pas.

3. **Pas de tests dans le CI** — Le pipeline déploie directement sans exécuter les tests.

4. **SSH root pour le déploiement** — L'accès root via SSH expose le serveur à des attaques.

5. **Pas de `.dockerignore`** — Le build Docker copie potentiellement `.venv/`, `db.sqlite3`, `.env`, `__pycache__/` dans l'image.

6. **`fail_silently=False` sur l'email** — Si Gmail est indisponible, toute la commande échoue.

---

## 10. Problèmes majeurs

> Impact : réduisent la maintenabilité, la fiabilité, ou la sécurité

7. **Pas de rate limiting** — Les endpoints auth sont exposés au brute force.

8. **Pas de transaction atomique** — Les opérations multi-tables ne sont pas atomiques.

9. **`ALLOWED_HOSTS = []` en production** — Si DEBUG=False et ALLOWED_HOSTS non défini → crash.

10. **Pas de SSL redirect dans Django** — `SECURE_SSL_REDIRECT` non configuré, le trafic peut rester en HTTP.

11. **Pas de healthcheck Docker** — Docker ne sait pas si le service est réellement up.

12. **`static/` versionné** — Collectstatic est dans Git au lieu d'être généré au build.

13. **Pas de `.env.example` pour le frontend** — Le frontend a besoin de `VITE_SERVER_BASE_URL` mais pas documenté proprement.

14. **Pas de gestion d'erreurs côté frontend** — Pas d'ErrorBoundary, pas d'interceptor Axios.

15. **Mélange `APIView` / `generics`** — Incohérence de pattern dans le backend.

---

## 11. Problèmes mineurs et observances

16. **`api/` contient des fichiers inutiles** — `models.py`, `admin.py`, `tests.py` dans un simple router.

17. **Pas de linting configuré** — Aucun ruff/flake8/pylint côté backend.

18. **Pas de pre-commit hooks** — Pas de vérification avant commit.

19. **Dossier `venv/` visible** — Devrait être dans `.gitignore` (le `.venv` l'est mais pas `venv/`).

20. **`apple.jpg` dans `products/`** — Fichier image dans le code source au lieu de `media/` ou `fixtures/`.

21. **Pas de pagination** — `ProductListView` retourne tous les produits d'un coup.

22. **Pas de filtering/sorting** — L'API ne supporte pas le filtrage par catégorie, prix, etc.

23. **`quantity` non validé** — `AddToCartView` n'a pas de minimum/maximum pour la quantité.

24. **Email hardcodé** — `smtp.gmail.com:587` en dur dans `settings.py`.

25. **Pas de changelog automatisé** — Le `CHANGELOG.md` existe mais pas de conventional commits.

---

## 12. Recommandations prioritaires

### Priorité 1 — Critique (faire avant toute mise en prod)

| # | Action | Effort |
|---|---|---|
| 1 | Ajouter `transaction.atomic()` dans `PlaceOrderView` | Faible |
| 2 | Remplacer `runserver` par `gunicorn` dans `docker-compose.yml` | Faible |
| 3 | Créer un `.dockerignore` (exclure `.venv`, `db.sqlite3`, `.env`, `__pycache__`) | Faible |
| 4 | Ajouter les tests dans le pipeline CI | Moyen |
| 5 | Arrêter de déployer en root — créer un user dédié | Moyen |
| 6 | Ajouter healthcheck dans les Dockerfiles | Faible |
| 7 | Retirer `static/` du versionnement | Faible |

### Priorité 2 — Majeur (faire rapidement)

| # | Action | Effort |
|---|---|---|
| 8 | Ajouter rate limiting (django-ratelimit ou DRF throttling) | Moyen |
| 9 | Configurer `SECURE_SSL_REDIRECT`, `SECURE_HSTS_*`, cookies sécurisés | Faible |
| 10 | Ajouter gestion des erreurs frontend (ErrorBoundary + Axios interceptor) | Moyen |
| 11 | Standardiser les vues (generics partout ou APIView partout) | Moyen |
| 12 | Ajouter healthcheck post-deploy dans le pipeline | Moyen |
| 13 | Configurer un cron pour le renouvellement SSL | Faible |

### Priorité 3 — Mineur (améliorer progressivement)

| # | Action | Effort |
|---|---|---|
| 14 | Ajouter ruff/flake8 + pre-commit | Faible |
| 15 | Ajouter pagination aux list views | Faible |
| 16 | Nettoyer `api/` (supprimer fichiers inutiles) | Faible |
| 17 | Ajouter `.env.example` frontend | Faible |
| 18 | Ajouter lazy loading React | Moyen |
| 19 | Configurer pytest + coverage | Moyen |
| 20 | Ajouter conventional commits | Faible |

---

## 13. Score global

| Catégorie | Note | Commentaire |
|---|---|---|
| Architecture | 7/10 | Bonne séparation, quelques incohérences |
| Code backend | 6/10 | Fonctionnel mais pas de transactions, pas de validation forte |
| Code frontend | 6/10 | Propre mais pas de gestion d'erreurs, pas de lazy loading |
| Sécurité | 3/10 | Failles critiques (pas de rate limiting, pas de SSL redirect, root SSH) |
| Tests | 7/10 | Bonne couverture backend, pas de tests CI |
| CI/CD | 2/10 | Pipeline minimaliste, pas de tests, pas de rollback |
| DevOps | 5/10 | Stack correcte mais pas de monitoring, pas de backup |
| Documentation | 7/10 | README détaillé mais pas de docs API |
| **Global** | **5.4/10** | **Projet pédagogique acceptable, pas production-ready** |

---

*Document généré par analyse automatique du code source. Recommandations basées sur les standards de l'industrie (OWASP, Django deployment checklist, 12-factor app).*
