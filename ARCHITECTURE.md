# Architecture — ClickMart

> Vue d'ensemble de l'architecture, des flux de données et des décisions de conception.

---

## 1. Diagramme de déploiement

```
┌───────────┐     ┌─────────────────────────────────────────────────────┐
│ Client    │────▶│  Nginx (ports 80/443)                              │
│ Browser   │     │  reverse proxy + SSL termination + static files    │
└───────────┘     └──────┬──────────────────────┬──────────────────────┘
                         │                      │
                         ▼                      ▼
              ┌──────────────────┐   ┌──────────────────────┐
              │  Frontend        │   │  Backend             │
              │  nginx:alpine    │   │  Gunicorn × 3 workers│
              │  sert /dist/     │   │  Django 5.2 + DRF    │
              │  (React SPA)     │   │                      │
              └──────────────────┘   └──────────┬───────────┘
                                                 │
                                                 ▼
                                      ┌──────────────────┐
                                      │  PostgreSQL 16   │
                                      │  (Docker volume)  │
                                      └──────────────────┘
```

---

## 2. Flux de données

### 2.1 Navigation publique (non auth)

```
Browser ──GET /──▶ Nginx ──proxy──▶ Frontend (SPA React)
                                           │
                              ┌────────────┴────────────┐
                              │ axios.get /api/v1/products/
                              ▼
                         Backend ──▶ PostgreSQL
                              │
                              ▼
                         JSON → Browser (render React)
```

### 2.2 Authentification JWT

```
Browser ──POST /api/v1/token/──▶ Backend
       { email, password }          │
                                    │ simplejwt.validate()
                                    ▼
                               { access, refresh }
                                    │
                                    ▼
                            localStorage + AuthContext
                                    │
                           ┌────────┴────────┐
                           │                 │
                    Requêtes auth      Expiration (15min)
                           │                 │
                    Header Bearer      Intercepteur 401
                           │                 │
                           ▼           POST /token/refresh/
                     Backend ────▶    { new access }
                                           │
                                    Retry requête originale
```

### 2.3 Placement de commande (flux critique)

```
Client (Checkout)             Backend                      PostgreSQL
      │                          │                            │
      │── POST /orders/place/ ──▶│                            │
      │   { shippingAddress }    │── Cart.objects.get() ─────▶│  [peut lever 500]
      │                          │── vérifie panier non vide  │
      │                          │── CRÉE Order ─────────────▶│  [trop tôt !]
      │                          │── valide stock items ─────▶│
      │                          │   (si échec → 400)         │  [Order orphelin]
      │                          │── décrémente stock ───────▶│
      │                          │── crée OrderItems ────────▶│
      │                          │── vide panier ────────────▶│
      │                          │── send_mail()              │  [peut planter]
      │◀── 201 { order } ────────│                            │
```

**Problème identifié :** L'Order est créée avant la validation du stock (ligne 25 vs ligne 42). Voir `ANALYSE_CODECOMPLETE.md` section 7.

---

## 3. Arbre des composants frontend

```
<AuthProvider>                            ← useState({ accessToken, refreshToken })
  <CartProvider>                          ← useReducer(items, total, itemCount, loading)
    <App>
      <BrowserRouter>
        <Header />                        ← Navbar + badge panier + dropdown profil
        <Routes>
          ── Publiques ──
          <Home>          → <Hero /> + <Products /> (GET /products/)
          <ProductDetail>                 ← GET /products/:id/ + POST /cart/add/
          <Cart>                          ← GET /cart/ + PATCH|DELETE /cart/items/:id/
          <Checkout>                      ← 2 steps: Shipping → Review, POST /orders/place/
          <Login>                         ← POST /token/
          <Register>                      ← POST /register/
          <OrderSuccess />                ← Confirmation statique
          ── Protégées (PrivateRoute) ──
          <Dashboard>
            <Sidebar />
            <Outlet>
              <DashboardHome />           ← Profile + orders récents
              <ProfileSettings />         ← SKELETON (non fonctionnel)
              <Orders> → <OrderDetail />  ← Liste + modal
            </Outlet>
          </Dashboard>
        </Routes>
        <Footer />
      </BrowserRouter>
    </App>
  </CartProvider>
</AuthProvider>
```

---

## 4. Modèle de données

```
User (AbstractUser)
├── email (unique, USERNAME_FIELD)
├── username (REQUIRED_FIELDS)
├── first_name, last_name
├── is_active, is_staff, date_joined
│
├─── 1:1 ─── Cart
│             ├── created_at
│             ├── items ──1:N── CartItem
│             │                  ├── product → Product (CASCADE)
│             │                  └── quantity (PositiveInteger, default=1)
│             ├── subtotal (property, O(n))
│             ├── tax_amount (property)
│             └── grand_total (property)
│
└─── 1:N ─── Order
              ├── subtotal, tax_amount, grand_total (snapshots)
              ├── status (PENDING → CONFIRMED → DELIVERED)
              ├── address, phone, city, state, zip_code
              ├── created_at
              └── items ──1:N── OrderItem
                           ├── product → Product (PROTECT)  ← intégrité préservée
                           ├── quantity, price, total_price (snapshots)
                           └── pas de lien direct vers CartItem

Product
├── name, description
├── image (ImageField, uploads/products/)
├── price (max 9999.99)
├── stock (PositiveInteger)
├── tax_percent (Decimal, default=0.00)
├── is_active (soft delete)
├── created_at, updated_at
```

---

## 5. Flux d'authentification

```
[AuthProvider]                        [useAxios hook]
     │                                      │
     │── lit localStorage au mount           │── intercepteur request
     │── { accessToken, refreshToken }       │    ajoute Bearer token
     │                                      │── intercepteur response
     │── Login :                             │    si 401 + refreshToken existe :
     │   POST /token/                        │      singleton refresh
     │   → store localStorage                │      POST /token/refresh/
     │   → setAuth()                         │      retry originale
     │                                      │    si refresh échoue :
     │── Logout :                            │      clear localStorage
     │   clear localStorage                  │      navigate("/")
     │   setAuth({})
     │   resetCart()
```

**Problème connu :** Chaque `useAxios()` ajoute des intercepteurs à l'instance partagée `api`. Voir `ANALYSE_CODECOMPLETE.md` section 9.3.3.

---

## 6. Infrastructure Docker

| Service | Image | Dépend de | Commandes |
|---------|-------|-----------|-----------|
| `db` | `postgres:16-alpine` | — | PostgreSQL par défaut |
| `backend` | `python:3.10-slim` custom | `db` | `collectstatic --noinput` → `migrate` → `gunicorn` |
| `frontend` | `nginx:alpine` custom | `backend` | Nginx sert `dist/` (port 80) |
| `nginx` | `nginx:alpine` officielle | `frontend`, `backend` | Proxy reverse (ports 80:80, 443:443) |

### Volumes

```
db:       postgres_data:/var/lib/postgresql/data    (persistance DB)
backend:  ./backend/static → /app/static             (collectstatic output)
backend:  ./backend/media  → /app/media              (uploads)
nginx:    ./nginx/default.conf → /etc/nginx/conf.d/   (config proxy)
nginx:    ./certbot/{www,conf}                        (SSL Let's Encrypt)
nginx:    ./backend/media → /media                    (serve direct uploads)
```

### Réseau

Un réseau bridge par défaut est créé automatiquement par Docker Compose. Communication via noms de service (`backend`, `frontend`, `db`, `nginx`).

---

## 7. Sécurité — Couches

```
[Nginx]                          ─── Terminaison SSL, rate limiting (non configuré)
  │
  ▼
[CORS Headers]                   ─── Configuré localhost:5173 uniquement
  │
  ▼
[Django ALLOWED_HOSTS]           ─── [] (vide → rejette tout en prod)
  │
  ▼
[JWTAuthentication]              ─── Access 15min + Refresh 7d, pas de rotation
  │
  ▼
[Permissions DRF]                ─── IsAuthenticated sur endpoints auth
  │
  ▼
[Propriété des objets]           ─── Filtrage par request.user dans les querysets
  │
  ▼
[PostgreSQL]                     ─── Données persistées
```

**État actuel :** 2 failles bloquantes (ALLOWED_HOSTS, CORS), pas de rate limiting, pas de HTTPS dans la config commitée.

---

## 8. États et transitions

```
Commande:
  PENDING ──(admin)──▶ CONFIRMED ──(admin)──▶ DELIVERED

Produit:
  is_active=True ──(admin)──▶ is_active=False  (soft delete)

Panier:
  [Créé au premier add] → [Items ajoutés/incrementés]
    → [Commandé (vidé)] → [Recréé au prochain add]

Auth:
  [Non connecté] ──login──▶ [Connecté (JWT)]
    ──(15min)──▶ [Token expiré] ──refresh──▶ [Connecté]
    ──(7 jours)──▶ [Session expirée] ──login──▶ [Connecté]
```

---

## 9. Points d'entrée

| Point d'entrée | Fichier | Port |
|---------------|---------|------|
| API REST | `backend/config/wsgi.py` (via gunicorn) | 8000 |
| Admin Django | `/admin/` via Nginx → backend | — |
| Frontend SPA | `frontend/dist/index.html` (via Nginx) | 80 |
| Dev backend | `python manage.py runserver` | 8000 |
| Dev frontend | `npm run dev` (Vite) | 5173 |

---

## 10. Dépendances externes

| Service | Usage | Configuration |
|---------|-------|---------------|
| PostgreSQL | Base de données principale | Via variables d'env Docker |
| Gmail SMTP | Envoi email confirmation commande | `smtp.gmail.com:587`, TLS |
| Let's Encrypt | SSL (server-managed) | Certbot webroot |
| Docker Hub | Images de base (`python:3.10-slim`, `postgres:16-alpine`, etc.) | Pull au build |

---

## 11. Résumé décisions architecturales

| Décision | Choisi | Alternative possible |
|----------|--------|---------------------|
| Base de données | PostgreSQL + fallback SQLite | PostgreSQL uniquement |
| Auth | JWT simplejwt (15min/7d) | Session + JWT, ou OAuth2 |
| Frontend state | Context API (useReducer) | Redux, Zustand, Jotai |
| UI Framework | Bootstrap 5 (raw classes) | Tailwind, MUI, Chakra |
| API documentation | Aucune | drf-spectacular → Swagger |
| CI/CD | SSH deploy (pas encore implémenté) | GH Actions build & push registry |
| Infrastructure | Docker Compose + Nginx proxy | Kubernetes, Cloud Run, Railway |
| Env vars | Build-time (frontend), python-decouple (backend) | Runtime endpoint, Vercel env |
