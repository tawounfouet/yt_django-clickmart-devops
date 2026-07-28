# RECOMMANDATIONS.md — Plan d'action ClickMart

> Basé sur `ANALYSE_CRITIQUE.md` — 22 juillet 2026
> Objectif : rendre le projet production-ready

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Phase 1 — Sécurité immédiate (Jour 1-2)](#2-phase-1--sécurité-immédiate-jour-1-2)
3. [Phase 2 — Fiabilité backend (Jour 3-5)](#3-phase-2--fiabilité-backend-jour-3-5)
4. [Phase 3 — CI/CD robuste (Jour 6-8)](#4-phase-3--cicd-robuste-jour-6-8)
5. [Phase 4 — DevOps & Observabilité (Jour 9-10)](#5-phase-4--devops--observabilité-jour-9-10)
6. [Phase 5 — Qualité frontend (Semaine 3)](#6-phase-5--qualité-frontend-semaine-3)
7. [Phase 6 — Améliorations continues](#7-phase-6--améliorations-continues)
8. [Checklist de déploiement](#8-checklist-de-déploiement)

---

## 1. Vue d'ensemble

| Phase | Priorité | Effort | Impact |
|---|---|---|---|
| Phase 1 — Sécurité | 🔴 Critique | 1-2 jours | Élimine les failles de sécurité bloquantes |
| Phase 2 — Fiabilité | 🔴 Critique | 3-5 jours | Empêche les pertes de données |
| Phase 3 — CI/CD | 🟠 Majeur | 2-3 jours | Empêche les déploiements cassés |
| Phase 4 — DevOps | 🟠 Majeur | 1-2 jours | Ajoute visibilité et résilience |
| Phase 5 — Frontend | 🟡 Important | 1 semaine | Améliore l'UX et la maintenabilité |
| Phase 6 — Continu | 🟢 Mineur | Continu | Dette technique résiduelle |

---

## 2. Phase 1 — Sécurité immédiate (Jour 1-2)

### 2.1 Ajouter rate limiting sur les endpoints auth

**Pourquoi** : `/token/` et `/register/` sont exposés au brute force sans limitation.

**Fichier** : `backend/config/settings.py`

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '60/minute',
    },
}
```

**Endpoints sensibles à throttler individuellement** :

```python
# backend/api/urls.py — ajouter throttle_scope sur les vues auth
path('token/', TokenObtainPairView.as_view(
    throttle_scope='auth'
), name='token_obtain_pair'),
```

```python
# settings.py
REST_FRAMEWORK = {
    ...
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '60/minute',
        'auth': '5/minute',  # Login : 5 tentatives par minute
    },
}
```

### 2.2 Configurer les headers de sécurité Django

**Fichier** : `backend/config/settings.py` — ajouter en bas du fichier

```python
# Security settings
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

**Attention** : `SECURE_SSL_REDIRECT = True` nécessite que Nginx transmette les headers `X-Forwarded-Proto`. Ajouter dans la config Nginx :

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
```

### 2.3 Corriger ALLOWED_HOSTS

**Fichier** : `backend/config/settings.py`

```python
# Remplacer la ligne 30
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
```

**Fichier** : `backend/.env.docker` — ajouter

```
ALLOWED_HOSTS=localhost,127.0.0.1,backend
```

**Fichier** : `backend/.env.production` — ajouter

```
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
```

### 2.4 Retirer `is_active` du ProductSerializer

**Pourquoi** : Le client peut voir les produits inactifs via l'API détail.

**Fichier** : `backend/products/serializers.py`

```python
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'image', 'price',
                  'stock', 'tax_percent', 'created_at', 'updated_at']
        # is_active exclu volontairement
```

### 2.5 Ajouter la validation de mot de passe côté serializer

**Pourquoi** : Les validateurs Django ne sont pas appliqués when le serializer utilise `create()` directement.

**Fichier** : `backend/users/serializers.py` — vérifier et ajouter

```python
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'password']

    def validate_password(self, value):
        validate_password(value)  # Applique les validateurs Django
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
```

**Test à ajouter** : `backend/users/tests.py`

```python
def test_register_weak_password_rejected(self):
    data = {
        "email": "weak@example.com",
        "username": "weakuser",
        "password": "123",  # Trop court, trop simple
    }
    response = self.client.post(self.url, data, format="json")
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
```

---

## 3. Phase 2 — Fiabilité backend (Jour 3-5)

### 3.1 Transaction atomique dans PlaceOrderView

**Pourquoi** : Si `product.save()` échoue après déduction du stock, la base est corrompue.

**Fichier** : `backend/orders/views.py`

```python
from django.db import transaction

class PlaceOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = Cart.objects.get(user=request.user)
        shipping_address = request.data.get("shippingAddress")

        if not cart or cart.items.count() == 0:
            return Response({'error': 'Cart is empty'},
                          status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # 1. Créer la commande
            order = Order.objects.create(
                user=request.user,
                subtotal=cart.subtotal,
                tax_amount=cart.tax_amount,
                grand_total=cart.grand_total,
                address=shipping_address.get("address"),
                phone=shipping_address.get("phone"),
                city=shipping_address.get("city"),
                state=shipping_address.get("state"),
                zip_code=shipping_address.get("zipCode"),
            )

            # 2. Déduire le stock + créer les OrderItems
            for item in cart.items.all():
                product = item.product

                # Utiliser select_for_update pour éviter les courses
                product = Product.objects.select_for_update().get(pk=product.pk)

                if product.stock < item.quantity:
                    raise ValueError(
                        f'Stock insuffisant pour {product.name}'
                    )

                product.stock -= item.quantity
                product.save()

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=product.price,
                    total_price=item.total_price
                )

            # 3. Vider le panier
            cart.items.all().delete()

        # Envoi email HORS transaction (pas critique)
        try:
            send_order_notification(order)
        except Exception:
            pass  # Log l'erreur mais ne casse pas la commande

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

### 3.2 Gestion des erreurs dans les vues cart

**Fichier** : `backend/carts/views.py`

```python
class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Valider quantity
        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {'error': 'quantity must be a positive integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product = get_object_or_404(Product, id=product_id, is_active=True)
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Vérifier le stock total (item existant + nouvelle quantité)
        existing_qty = 0
        try:
            item = CartItem.objects.get(cart=cart, product=product)
            existing_qty = item.quantity
        except CartItem.DoesNotExist:
            item = None

        if existing_qty + quantity > product.stock:
            return Response(
                {'error': f'Stock insuffisant. Disponible : {product.stock}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if item:
            item.quantity += quantity
            item.save()
        else:
            item = CartItem.objects.create(
                cart=cart, product=product, quantity=quantity
            )

        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
```

### 3.3 Gestion de l'email non critique

**Fichier** : `backend/orders/utils.py`

```python
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

def send_order_notification(order):
    try:
        send_mail(
            subject=f'Order #{order.id} is received',
            message=f"""
                Hi {order.user.first_name},

                Your order #{order.id} has been placed successfully.

                Total: {order.grand_total}

                Thank you for shopping with us.
            """,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[order.user.email],
            fail_silently=True  # Ne pas crasher si email échoue
        )
    except Exception as e:
        logger.error(f"Failed to send order notification for order #{order.id}: {e}")
```

### 3.4 Nettoyer les imports inutilisés

**Fichiers concernés** : Tous les `views.py` du backend

```bash
# Trouver les imports inutilisés
cd backend
python -m py_compile products/views.py  # Vérifie la syntaxe
# Ou utiliser ruff :
pip install ruff
ruff check --select F401 backend/
```

Fichiers à nettoyer :
- `products/views.py:1` — `from django.shortcuts import render` (inutilisé)
- `orders/views.py:1` — `from django.shortcuts import get_object_or_404, render` (`render` inutilisé)
- `carts/views.py:1` — `from django.shortcuts import render, get_object_or_404` (`render` inutilisé)

### 3.5 Ajouter la contrainte d'unicité sur CartItem

**Fichier** : `backend/carts/models.py`

```python
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')  # Un produit par panier

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
```

Puis :
```bash
python manage.py makemigrations carts
python manage.py migrate
```

### 3.6 Ajouter la validation Address obligatoire

**Fichier** : `backend/orders/models.py`

```python
class Order(models.Model):
    ...
    address = models.CharField(max_length=200)  # Plus de blank=True
    phone = models.CharField(max_length=15)      # Plus de blank=True
    city = models.CharField(max_length=20)        # Plus de blank=True
    state = models.CharField(max_length=20)       # Plus de blank=True
    zip_code = models.CharField(max_length=10)    # Plus de blank=True
```

⚠️ **Attention** : Nécessite une migration. Vérifier qu'aucune migration existante ne casse.

---

## 4. Phase 3 — CI/CD robuste (Jour 6-8)

### 4.1 Pipeline complet avec tests

**Fichier** : `.github/workflows/automate.yml` — remplacer le contenu

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # ─── Job 1 : Tests backend ───
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_clickmart
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install ruff pytest-django coverage

      - name: Lint with ruff
        run: |
          cd backend
          ruff check .

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/test_clickmart
          SECRET_KEY: ci-test-secret-key
          DEBUG: 'True'
          EMAIL_HOST_USER: test@test.com
          EMAIL_HOST_PASSWORD: test
        run: |
          cd backend
          coverage run --source='.' manage.py test --verbosity=2
          coverage report --fail-under=70
          coverage xml

      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: backend/coverage.xml

  # ─── Job 2 : Tests frontend ───
  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: frontend

      - name: Lint
        run: npm run lint
        working-directory: frontend

      - name: Test
        run: npm run test
        working-directory: frontend

      - name: Build
        run: npm run build
        working-directory: frontend

  # ─── Job 3 : Deploy (uniquement si tests passent) ───
  deploy:
    needs: [test-backend, test-frontend]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest

    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.LINODE_HOST }}
          username: ${{ secrets.LINODE_USER }}
          key: ${{ secrets.LINODE_SSH_KEY }}
          script: |
            cd /opt/clickmart
            git pull origin main
            docker compose down
            docker compose up --build -d
            sleep 10
            docker compose ps
            # Health check
            curl -sf http://localhost:80 || (echo "Frontend failed" && exit 1)
            curl -sf http://localhost:8000/api/v1/products/ || (echo "Backend failed" && exit 1)
            echo "Deployment successful"
```

### 4.2 Créer un user SSH dédié (pas root)

**Sur le serveur Linode** :

```bash
# Créer l'utilisateur deploy
adduser deploy
usermod -aG docker deploy
usermod -aG sudo deploy

# Configurer SSH
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Permissions sur /opt/clickmart
chown -R deploy:deploy /opt/clickmart
```

**Mettre à jour GitHub Secrets** :
- `LINODE_USER` → `deploy` (au lieu de `root`)
- `LINODE_SSH_KEY` → clé privée correspondante

### 4.3 Ajouter ruff pour le linting backend

**Fichier** : `backend/pyproject.toml` (nouveau)

```toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by formatter)
]

[tool.ruff.lint.isort]
known-first-party = ["config", "users", "products", "carts", "orders", "api"]
```

**Fichier** : `backend/requirements.txt` — ajouter

```
ruff==0.5.0
pytest-django==4.8.0
coverage==7.6.0
```

### 4.4 Ajouter un .dockerignore

**Fichier** : `backend/.dockerignore` (nouveau)

```
__pycache__
*.pyc
*.pyo
.env
.env.*
.venv
venv
db.sqlite3
.git
.gitignore
*.md
media/
static/
.pytest_cache
.coverage
htmlcov/
```

**Fichier** : `frontend/.dockerignore` (nouveau)

```
node_modules
dist
.git
.gitignore
*.md
.env
.env.*
```

---

## 5. Phase 4 — DevOps & Observabilité (Jour 9-10)

### 5.1 Ajouter healthchecks Docker

**Fichier** : `backend/Dockerfile` — ajouter

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/products/')" || exit 1
```

**Fichier** : `docker-compose.yml` — ajouter healthchecks

```yaml
services:
  db:
    image: postgres:16-alpine
    env_file:
      - ./backend/.env.production
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file:
      - ./backend/.env.docker
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend/static:/app/static
      - ./backend/media:/app/media
    command: >
      sh -c "python manage.py collectstatic --noinput &&
             python manage.py migrate &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/products/')\" || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

  frontend:
    build:
      context: ./frontend
      args:
        VITE_SERVER_BASE_URL: "/api/v1"
    depends_on:
      backend:
        condition: service_healthy

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./certbot/www:/var/www/certbot
      - ./certbot/conf:/etc/letsencrypt
      - ./backend/media:/media
    depends_on:
      - frontend
      - backend
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:80 || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  postgres_data:
```

### 5.2 Cron de renouvellement SSL

**Sur le serveur Linode** :

```bash
# Créer le cron
crontab -e

# Ajouter cette ligne (renouvellement 2x par jour)
0 3,15 * * * cd /opt/clickmart && docker compose exec -T nginx certbot renew --quiet && docker compose restart nginx >> /var/log/certbot-renew.log 2>&1
```

### 5.3 Backup automatique de la base

**Fichier** : `scripts/backup-db.sh` (nouveau, sur le serveur)

```bash
#!/bin/bash
BACKUP_DIR="/opt/clickmart/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker compose exec -T db pg_dump -U postgres clickmart | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# Garder seulement les 7 derniers jours
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_$TIMESTAMP.sql.gz"
```

```bash
# Cron quotidien
0 2 * * * /opt/clickmart/scripts/backup-db.sh >> /var/log/db-backup.log 2>&1
```

### 5.4 Logging structuré

**Fichier** : `backend/config/settings.py` — ajouter

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': config('LOG_LEVEL', default='INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'orders': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

---

## 6. Phase 5 — Qualité frontend (Semaine 3)

### 6.1 Error Boundary global

**Fichier** : `frontend/src/components/ErrorBoundary.jsx` (nouveau)

```jsx
import { Component } from "react";

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="container mt-5 text-center">
          <h2>Une erreur est survenue</h2>
          <p className="text-muted">{this.state.error?.message}</p>
          <button
            className="btn btn-primary"
            onClick={() => window.location.reload()}
          >
            Recharger la page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
```

**Fichier** : `frontend/src/main.jsx` — wrapper

```jsx
import ErrorBoundary from "./components/ErrorBoundary";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
```

### 6.2 Axios interceptor pour les erreurs

**Fichier** : `frontend/src/api/index.js` — remplacer

```javascript
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_SERVER_BASE_URL || "http://localhost:8000/api/v1",
});

// Request interceptor — ajouter le token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — gérer les erreurs globalement
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expiré → rediriger vers login
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    }

    if (error.response?.status >= 500) {
      // Erreur serveur → notification
      console.error("Server error:", error.response.data);
    }

    return Promise.reject(error);
  }
);

export default api;
```

### 6.3 Lazy loading des routes

**Fichier** : `frontend/src/App.jsx`

```jsx
import { lazy, Suspense } from "react";
import { Route, BrowserRouter as Router, Routes } from "react-router-dom";
import Header from "./components/Navbar";
import Footer from "./components/Footer";

// Lazy loading — le code est chargé à la demande
const Home = lazy(() => import("./pages/Home"));
const ProductDetail = lazy(() => import("./pages/ProductDetails"));
const Cart = lazy(() => import("./pages/Cart"));
const Checkout = lazy(() => import("./pages/Checkout"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const DashboardHome = lazy(() => import("./pages/DashboardHome"));
const ProfileSettings = lazy(() => import("./pages/ProfileSetting"));
const Orders = lazy(() => import("./pages/Orders"));
const OrderSuccess = lazy(() => import("./pages/OrderSuccess"));
const PrivateRoute = lazy(() => import("./pages/PrivateRoute"));

function App() {
  return (
    <Router>
      <Header />
      <Suspense fallback={<div className="text-center mt-5">Chargement...</div>}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/product/:id" element={<ProductDetail />} />
          <Route path="/cart" element={<Cart />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Register />} />
          <Route element={<PrivateRoute />}>
            <Route path="/dashboard" element={<Dashboard />}>
              <Route index element={<DashboardHome />} />
              <Route path="profile" element={<ProfileSettings />} />
              <Route path="orders" element={<Orders />} />
            </Route>
          </Route>
          <Route path="/order/success/:id" element={<OrderSuccess />} />
        </Routes>
      </Suspense>
      <Footer />
    </Router>
  );
}

export default App;
```

### 6.4 Pagination côté backend

**Fichier** : `backend/config/settings.py`

```python
REST_FRAMEWORK = {
    ...
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

Ou pagination spécifique par vue :

```python
# backend/products/views.py
from rest_framework.pagination import PageNumberPagination

class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    pagination_class = ProductPagination
```

---

## 7. Phase 6 — Améliorations continues

### 7.1 Nettoyage du code

| Action | Fichier | Détail |
|---|---|---|
| Supprimer `backend/static/` du git | `.gitignore` | Ajouter `backend/static/` et faire `git rm -r --cached backend/static/` |
| Supprimer fichiers inutiles dans `api/` | `api/models.py`, `api/admin.py`, `api/tests.py` | Ces fichiers sont vides/inutiles dans un router |
| Supprimer `apple.jpg` de `products/` | `products/apple.jpg` | Image de test dans le code source |
| Vérifier `.gitignore` | Root `.gitignore` | Ajouter `backend/static/`, `*.sqlite3` (déjà fait), `backups/` |

### 7.2 Pre-commit hooks

**Fichier** : `.pre-commit-config.yaml` (nouveau)

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: detect-private-key
```

```bash
pip install pre-commit
pre-commit install
```

### 7.3 API Documentation (DRF Spectacular)

```bash
pip install drf-spectacular
```

**Fichier** : `backend/config/settings.py`

```python
INSTALLED_APPS = [
    ...
    'drf_spectacular',
]

REST_FRAMEWORK = {
    ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'ClickMart API',
    'DESCRIPTION': 'API e-commerce ClickMart',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
```

**Fichier** : `backend/config/urls.py`

```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

### 7.4 Variables d'environnement manquantes

**Fichier** : `backend/.env.example` — mettre à jour

```env
# Django
SECRET_KEY=change-me-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (laisser vide pour SQLite en local)
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

# Email
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Logging
LOG_LEVEL=INFO
```

---

## 8. Checklist de déploiement

Avant de déployer en production, vérifier :

### Sécurité
- [ ] `SECRET_KEY` différent de la clé de dev
- [ ] `DEBUG=False` dans `.env.production`
- [ ] `ALLOWED_HOSTS` configuré avec le domaine
- [ ] Rate limiting activé
- [ ] SSL redirect activé
- [ ] HSTS configuré
- [ ] Cookies sécurisés activés
- [ ] User SSH dédié (pas root)
- [ ] `.env` files non versionnés
- [ ] `.dockerignore` en place

### Backend
- [ ] Tous les tests passent (`python manage.py test`)
- [ ] Linting passe (`ruff check .`)
- [ ] Pas de `runserver` en production
- [ ] `collectstatic` fonctionne
- [ ] Migrations à jour
- [ ] Gunicorn configuré avec les bons workers

### CI/CD
- [ ] Pipeline exécute les tests avant deploy
- [ ] Pipeline vérifie le build frontend
- [ ] Health check post-deploy
- [ ] Rollback possible

### DevOps
- [ ] Healthchecks Docker configurés
- [ ] Backup DB automatisé
- [ ] Cron SSL configuré
- [ ] Logs structurés
- [ ] Monitoring en place (optionnel)

### Frontend
- [ ] `npm run build` fonctionne
- [ ] `npm run lint` passe
- [ ] `npm run test` passe
- [ ] `VITE_SERVER_BASE_URL` configuré pour le domaine

---

*Ce document est unliving document — mettre à jour au fur et à mesure de l'avancement.*
