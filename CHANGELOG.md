# Changelog — ClickMart

Toutes les modifications notables de ce projet.

Format basé sur [Keep a Changelog](https://keepachangelog.com/),
versioning sémantique [SemVer](https://semver.org/).

---

## [0.1.0] — 2025-12-24

### Projet initial

- Mise en place du projet Django avec structure modulaire (users, products, carts, orders)
- Installation de Django REST Framework + SimpleJWT
- Configuration PostgreSQL avec fallback SQLite
- Custom User model (email-based auth)
- Modèle Product (name, description, image, price, stock)
- Modèle Cart + CartItem (OneToOne User, ForeignKey Product)
- Modèle Order + OrderItem (status PENDING/CONFIRMED/DELIVERED)
- Vue RegisterView + ProfileView
- Vue ProductListView + ProductDetailView (filtre is_active)
- Vue CartView + AddToCartView + ManageCartItemView
- Vue PlaceOrderView avec email notification
- Vue MyOrdersView + OrderDetailView
- Tous les sérialiseurs (avec `fields = "__all__"`)
- Personnalisation admin (UserAdmin, OrderAdmin avec inline)
- Endpoint `/api/v1/register/`, `/api/v1/token/`, `/api/v1/profile/`

### Frontend

- Initialisation React + Vite
- Mise en place AuthProvider (localStorage JWT) + CartProvider (useReducer)
- Hook useAuth + useAxios avec intercepteurs et refresh token
- Pages : Home, Products, ProductDetails, Cart, Login, Register
- Routes : `/`, `/product/:id`, `/cart`, `/login`, `/signup`
- Navbar avec badge panier + dropdown profil
- Intégration Bootstrap 5 + Bootstrap Icons

---

## [0.2.0] — 2025-12-26

### Backend

- Ajout `tax_percent` sur Product (migration `0002_product_tax_percent`)
- Ajout `related_name='items'` sur CartItem.cart (migration `0002_alter_cartitem_cart`)
- Ajout valeur par défaut `PENDING` sur Order.status (migration `0002_alter_order_status`)
- Ajout champs adresse sur Order : address, phone, city, state, zip_code (migration `0003_address_fields`)

### Frontend

- Page Checkout (2 étapes : Shipping → Review/Place)
- Page OrderSuccess (confirmation post-achat)
- Page Register avec validation mot de passe
- Composant Sidebar (dashboard navigation)
- Dashboard layout + DashboardHome (profile + commandes récentes)
- Page Orders (liste avec modal OrderDetail)
- Composant QuantitySelector
- Gestion des erreurs Register (affichage des champs DRF)

---

## [0.3.0] — 2025-12-27

### Frontend

- Page ProfileSetting (skeleton — non fonctionnel)
- PrivateRoute (protection des routes `/dashboard/*`)
- Gestion auth complète : login/logout/refresh
- Badge panier dynamique dans Navbar
- Récupération cart au mount de Home

---

## [0.4.0] — 2025-12-28

### Documentation

- README.md détaillé avec tutoriel déploiement complet
- Architecture : Docker, Nginx reverse proxy, Gunicorn, PostgreSQL
- CI/CD : GitHub Actions + appleboy/ssh-action

---

## [0.5.0] — 2025-12-30 — 2026-01-03

### Documentation (suite)

- README.md : section Linode, captures d'écran, étapes déploiement VPS
- README.md : configuration SSL Let's Encrypt, certbot
- README.md : déploiement automatisé CI/CD

---

## [0.6.0] — 2026-04-07

### Maintenance

- Mise à jour lien compte Linode dans README

### Infrastructure

- Restructuration : `backend-drf/` → `backend/` (migration en cours)
- Dockerfiles + docker-compose.yml ajoutés (gitignorés, server-managed)
- `nginx/default.conf` : reverse proxy HTTP (HTTPS server-managed)

### Outillage

- Ajout `AGENTS.md` (instructions OpenCode)
- Ajout `ANALYSE_CODECOMPLETE.md` (analyse exhaustive)
- Ajout `ARCHITECTURE.md` (documentation architecture)
- Ajout `INDEX.md` (index de navigation)
- Ajout `CHANGELOG.md` (ce fichier)

---

## Travail à venir (projets identifiés)

Voir le détail dans `ANALYSE_CODECOMPLETE.md` sections 10 et 11.

### Bloquant

- [ ] Ajouter `gunicorn` à `requirements.txt`
- [ ] Rendre `ALLOWED_HOSTS` et `CORS_ALLOWED_ORIGINS` dynamiques via variables d'env
- [ ] Créer le workflow GitHub Actions `.github/workflows/deploy.yml`
- [ ] Retirer les Dockerfiles du `.gitignore`

### High

- [ ] Corriger l'Order créée avant validation stock (orphan order) + wrapper dans `transaction.atomic()`
- [ ] Wrapper `int()` dans `carts/views.py` (crash 500 sur input non-numérique)
- [ ] Wrapper `Cart.objects.get()` dans `orders/views.py` (crash 500 si pas de panier)
- [ ] Console email backend en dev (`EmailBackend`)
- [ ] Corriger typo `eject` dans `useAxios.js`
- [ ] Singleton pattern pour `useAxios` (intercepteurs dupliqués)

### Medium

- [ ] Pagination DRF sur listing produits
- [ ] Healthcheck endpoint + Docker HEALTHCHECK
- [ ] Champs explicites dans les sérialiseurs (remplacer `__all__`)
- [ ] Compléter ProfileSettings
- [ ] Afficher erreurs Checkout à l'utilisateur
- [ ] Rate limiting
- [ ] Nettoyer dépendances npm inutilisées

### Low

- [ ] Migrer Python 3.10 → 3.12+
- [ ] Service layer pour logique métier
- [ ] Caching propriétés Cart
- [ ] Swagger/OpenAPI
- [ ] Pre-commit + ruff + black
- [ ] User non-root Docker

---

Les versions suivies dans ce fichier commencent à la création du dépôt.
