# PLAN_IMPLEMMENTATION.md — ClickMart Production-Ready

> Basé sur `ANALYSE_CRITIQUE.md` et `RECOMMANDATIONS.md`
> Durée estimée : **3 semaines** (15 jours ouvrés)
> Approche : incrémentele, chaque livrable est testable et déployable

---

## Table des matières

1. [Vue d'ensemble du planning](#1-vue-densemble-du-planning)
2. [Semaine 1 — Sécurité & Fiabilité (J1-J5)](#2-semaine-1--sécurité--fiabilité-j1-j5)
3. [Semaine 2 — CI/CD & DevOps (J6-J10)](#3-semaine-2--cicd--devops-j6-j10)
4. [Semaine 3 — Frontend & Polish (J11-J15)](#4-semaine-3--frontend--polish-j11-j15)
5. [Matrice de dépendances](#5-matrice-de-dépendances)
6. [Critères d'acceptation globaux](#6-critères-dacceptation-globaux)
7. [Risques et mitigation](#7-risques-et-mitigation)

---

## 1. Vue d'ensemble du planning

```
Semaine 1                    Semaine 2                    Semaine 3
J1   J2   J3   J4   J5      J6   J7   J8   J9   J10     J11  J12  J13  J14  J15
├────┼────┼────┼────┤         ├────┼────┼────┼────┤         ├────┼────┼────┼────┤
Sécurité    Fiabilité        CI/CD       DevOps           Frontend     Polish
■■■■■■■■■■  ■■■■■■■■■■       ■■■■■■■■■■   ■■■■■■           ■■■■■■■■■■   ■■■■■■■■■■
```

| Phase | Jours | Livrable | Peut paralléliser |
|---|---|---|---|
| S1-J1-2 | Sécurité backend | Rate limiting, headers SSL, ALLOWED_HOSTS | Non |
| S1-J3-5 | Fiabilité backend | Transactions, validation, nettoyage | Non |
| S2-J6-8 | CI/CD | Pipeline GitHub Actions complet | Oui avec J9-10 |
| S2-J9-10 | DevOps | Healthchecks, backups, logging | Oui avec J6-8 |
| S3-J11-13 | Frontend | ErrorBoundary, lazy loading, pagination | Non |
| S3-J14-15 | Polish | Pre-commit, docs, .dockerignore, nettoyage | Non |

---

## 2. Semaine 1 — Sécurité & Fiabilité (J1-J5)

### J1 — Rate limiting & Headers de sécurité

**Objectif** : Protéger les endpoints auth contre le brute force et forcer HTTPS.

#### Tâche 1.1 — Throttling DRF

| Élément | Détail |
|---|---|
| Fichier | `backend/config/settings.py` |
| Action | Modifier `REST_FRAMEWORK` (ligne 198-202) |
| Avant | `'DEFAULT_AUTHENTICATION_CLASSES': (...)` seul |
| Après | Ajouter `DEFAULT_THROTTLE_CLASSES` et `DEFAULT_THROTTLE_RATES` |

```python
# REMPLACER les lignes 198-208
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
        'auth': '5/minute',
    },
}
```

**Vérification** :
```bash
cd backend
python manage.py test users.tests.RegisterViewTests --verbosity=2
python -c "from config.settings import REST_FRAMEWORK; print(REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'])"
```

#### Tâche 1.2 — ALLOWED_HOSTS dynamique

| Élément | Détail |
|---|---|
| Fichier | `backend/config/settings.py` |
| Action | Remplacer la ligne 30 |
| Avant | `ALLOWED_HOSTS = []` |
| Après | `ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')` |

**Fichiers `.env` à mettre à jour** :

```env
# backend/.env.docker — ajouter
ALLOWED_HOSTS=localhost,127.0.0.1,backend

# backend/.env.production — ajouter
ALLOWED_HOSTS=localhost,127.0.0.1
```

**Vérification** :
```bash
cd backend
python -c "from config.settings import ALLOWED_HOSTS; print(ALLOWED_HOSTS)"
```

---

### J2 — Headers SSL/HSTS & Nettoyage serializer

**Objectif** : Sécuriser les communications et exposer uniquement les champs nécessaires.

#### Tâche 2.1 — Security settings Django

| Élément | Détail |
|---|---|
| Fichier | `backend/config/settings.py` |
| Action | Ajouter en bas du fichier (après la ligne 223) |

```python
# ── Security ──
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
```

**Vérification** :
```bash
cd backend
python -c "
from config.settings import DEBUG, SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS
print(f'DEBUG={DEBUG}')
print(f'SSL_REDIRECT={SECURE_SSL_REDIRECT}')
print(f'HSTS={SECURE_HSTS_SECONDS}')
"
```

#### Tâche 2.2 — ProductSerializer : exclure is_active

| Élément | Détail |
|---|---|
| Fichier | `backend/products/serializers.py` |
| Action | Remplacer le contenu |

```python
from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'image', 'price',
                  'stock', 'tax_percent', 'created_at', 'updated_at']
```

**Vérification** :
```bash
cd backend
python manage.py test products.tests.ProductDetailTests.test_detail_includes_all_fields --verbosity=2
# Le test doit échouer si is_active est encore exposé (à adapter)
```

#### Tâche 2.3 — Validation mot de passe dans RegisterSerializer

| Élément | Détail |
|---|---|
| Fichier | `backend/users/serializers.py` |
| Action | Ajouter `validate_password` |

```python
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "username", "password"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name']
        read_only_fields = ["id", "email"]
```

**Test à ajouter** dans `backend/users/tests.py` :

```python
def test_register_weak_password_rejected(self):
    data = {
        "email": "weak@example.com",
        "username": "weakuser",
        "password": "123",
    }
    response = self.client.post(self.url, data, format="json")
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

def test_register_strong_password_accepted(self):
    data = {
        "email": "strong@example.com",
        "username": "stronguser",
        "password": "C0mpl3x!P@ssw0rd#2024",
    }
    response = self.client.post(self.url, data, format="json")
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
```

**Vérification** :
```bash
cd backend
python manage.py test users.tests --verbosity=2
```

---

### J3 — Transaction atomique PlaceOrderView

**Objectif** : Éviter la corruption de données en cas d'échec partiel.

#### Tâche 3.1 — Refactorer PlaceOrderView

| Élément | Détail |
|---|---|
| Fichier | `backend/orders/views.py` |
| Action | Remplacer la classe `PlaceOrderView` |

```python
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView

from carts.models import Cart
from products.models import Product
from .models import Order, OrderItem
from .serializers import OrderSerializer
from .utils import send_order_notification


class PlaceOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {'error': 'No cart found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if cart.items.count() == 0:
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )

        shipping_address = request.data.get("shippingAddress")
        if not shipping_address:
            return Response(
                {'error': 'Shipping address is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
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

            for item in cart.items.select_related('product').all():
                product = Product.objects.select_for_update().get(
                    pk=item.product.pk
                )

                if product.stock < item.quantity:
                    raise ValueError(
                        f'Stock insuffisant pour {product.name}. '
                        f'Disponible : {product.stock}'
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

            cart.items.all().delete()

        try:
            send_order_notification(order)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Email notification failed for order #{order.id}: {e}"
            )

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyOrdersView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Order, pk=pk, user=self.request.user)
```

**Vérification** :
```bash
cd backend
python manage.py test orders.tests --verbosity=2
```

---

### J4 — Validation dans les vues cart

**Objectif** : Empêcher les crashes 500 sur les inputs invalides.

#### Tâche 4.1 — AddToCartView avec validation

| Élément | Détail |
|---|---|
| Fichier | `backend/carts/views.py` |
| Action | Remplacer `AddToCartView` |

```python
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from products.models import Product


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


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


class ManageCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        if 'change' not in request.data:
            return Response(
                {"error": "Provide 'change' field"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            change = int(request.data.get('change'))
        except (TypeError, ValueError):
            return Response(
                {"error": "'change' must be an integer"},
                status=status.HTTP_400_BAD_REQUEST
            )

        item = get_object_or_404(
            CartItem, pk=item_id, cart__user=request.user
        )
        product = item.product

        if change > 0 and item.quantity + change > product.stock:
            return Response(
                {'error': 'Not enough stock'},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_qty = item.quantity + change

        if new_qty <= 0:
            item.delete()
            return Response({'success': 'Item removed'})

        item.quantity = new_qty
        item.save()
        serializer = CartItemSerializer(item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, item_id):
        item = get_object_or_404(
            CartItem, pk=item_id, cart__user=request.user
        )
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

**Vérification** :
```bash
cd backend
python manage.py test carts.tests --verbosity=2
```

---

### J5 — Nettoyage email, imports, Contrainte CartItem

**Objectif** : Stabiliser le code backend avant de construire le pipeline CI.

#### Tâche 5.1 — Email non critique

| Élément | Détail |
|---|---|
| Fichier | `backend/orders/utils.py` |
| Action | Remplacer le contenu |

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
            fail_silently=True
        )
    except Exception as e:
        logger.error(
            f"Failed to send order notification for order #{order.id}: {e}"
        )
```

#### Tâche 5.2 — Contrainte d'unicité CartItem

| Élément | Détail |
|---|---|
| Fichier | `backend/carts/models.py` |
| Action | Ajouter `class Meta` dans `CartItem` |

```python
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.product.price * self.quantity
```

```bash
cd backend
python manage.py makemigrations carts
python manage.py migrate
```

#### Tâche 5.3 — Nettoyer les imports inutilisés

```bash
cd backend
pip install ruff
ruff check --select F401 products/views.py orders/views.py carts/views.py
# Puis supprimer les imports inutilisés manuellement
```

Fichiers à nettoyer :
- `products/views.py` — supprimer `from django.shortcuts import render`
- `orders/views.py` — supprimer `render` de l'import
- `carts/views.py` — supprimer `render` de l'import

**Vérification globale S1** :
```bash
cd backend
python manage.py test --verbosity=2
# Tous les tests doivent passer
```

---

## 3. Semaine 2 — CI/CD & DevOps (J6-J10)

### J6 — Pipeline CI : tests backend

**Objectif** : Le pipeline exécute les tests avant de déployer.

#### Tâche 6.1 — Configurer ruff + pytest-django

| Élément | Détail |
|---|---|
| Fichier | `backend/pyproject.toml` (nouveau) |
| Fichier | `backend/requirements.txt` (ajouter) |

`backend/pyproject.toml` :
```toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["config", "users", "products", "carts", "orders", "api"]
```

`backend/requirements.txt` — ajouter :
```
ruff==0.5.0
coverage==7.6.0
```

#### Tâche 6.2 — Pipeline GitHub Actions

| Élément | Détail |
|---|---|
| Fichier | `.github/workflows/automate.yml` |
| Action | Remplacer le contenu complet |

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
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
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Lint with ruff
        run: |
          cd backend
          ruff check .

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/test_clickmart
          SECRET_KEY: ci-test-secret-key-not-for-prod
          DEBUG: 'True'
          EMAIL_HOST_USER: test@test.com
          EMAIL_HOST_PASSWORD: test
          ALLOWED_HOSTS: localhost
        run: |
          cd backend
          coverage run --source='.' manage.py test --verbosity=2
          coverage report --fail-under=70

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
        run: npm run test -- --run
        working-directory: frontend

      - name: Build
        run: npm run build
        working-directory: frontend
        env:
          VITE_SERVER_BASE_URL: http://localhost:8000/api/v1

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
            sleep 15
            docker compose ps
            curl -sf http://localhost:80 || (echo "Frontend healthcheck failed" && exit 1)
            curl -sf http://localhost:8000/api/v1/products/ || (echo "Backend healthcheck failed" && exit 1)
            echo "✅ Deployment successful"
```

**Vérification** :
```bash
# Tester le workflow localement avec act (optionnel)
brew install act
act -j test-backend
```

---

### J7 — .dockerignore & Backend healthcheck

**Objectif** : Réduire la taille des images Docker et ajouter des healthchecks.

#### Tâche 7.1 — .dockerignore backend

| Élément | Détail |
|---|---|
| Fichier | `backend/.dockerignore` (nouveau) |

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
ruff.toml
```

#### Tâche 7.2 — .dockerignore frontend

| Élément | Détail |
|---|---|
| Fichier | `frontend/.dockerignore` (nouveau) |

```
node_modules
dist
.git
.gitignore
*.md
.env
.env.*
```

#### Tâche 7.3 — Healthcheck backend Dockerfile

| Élément | Détail |
|---|---|
| Fichier | `backend/Dockerfile` |
| Action | Ajouter HEALTHCHECK avant CMD |

```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/products/ || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "180"]
```

**Note** : Python version bump de `3.10` à `3.11` (cohérent avec `setup-python` dans le CI).

**Vérification** :
```bash
cd backend
docker build -t clickmart-backend-test .
docker run -d --name test-health clickmart-backend-test
sleep 20
docker inspect --format='{{.State.Health.Status}}' test-health
docker rm -f test-health
```

---

### J8 — Docker Compose healthchecks

**Objectif** : Les services dépendent de la santé des autres.

| Élément | Détail |
|---|---|
| Fichier | `docker-compose.yml` |
| Action | Remplacer le contenu |

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
      test: ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/products/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s

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

**Vérification** :
```bash
docker compose down -v
docker compose up --build -d
sleep 30
docker compose ps
# Tous les services doivent être "healthy"
```

---

### J9 — User SSH dédié & Backup DB

**Objectif** : Ne plus déployer en root, ajouter la résilience données.

#### Tâche 9.1 — User deploy (sur le serveur)

```bash
# SSH sur le serveur en root
ssh root@<LINODE_IP>

# Créer l'utilisateur
adduser deploy
usermod -aG docker deploy
usermod -aG sudo deploy

# Copier les clés SSH
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Permissions sur le projet
chown -R deploy:deploy /opt/clickmart
```

Mettre à jour GitHub Secret `LINODE_USER` → `deploy`.

#### Tâche 9.2 — Script de backup

| Élément | Détail |
|---|---|
| Fichier | `scripts/backup-db.sh` (nouveau, sur le serveur) |

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/clickmart/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

# Backup
docker compose -f /opt/clickmart/docker-compose.yml exec -T db \
  pg_dump -U postgres clickmart | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# Rotation
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +"$RETENTION_DAYS" -delete

echo "[$(date)] Backup completed: db_$TIMESTAMP.sql.gz"
```

```bash
# Sur le serveur
chmod +x /opt/clickmart/scripts/backup-db.sh
crontab -e
# Ajouter :
0 2 * * * /opt/clickmart/scripts/backup-db.sh >> /var/log/db-backup.log 2>&1
```

**Vérification** :
```bash
# Tester manuellement
/opt/clickmart/scripts/backup-db.sh
ls -la /opt/clickmart/backups/
```

---

### J10 — Logging structuré & Cron SSL

**Objectif** : Tracer les erreurs et maintenir le certificat SSL.

#### Tâche 10.1 — Logging Django

| Élément | Détail |
|---|---|
| Fichier | `backend/config/settings.py` |
| Action | Ajouter après `CORS_ALLOWED_ORIGINS` (ligne 223) |

```python
# ── Logging ──
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

#### Tâche 10.2 — Cron SSL (sur le serveur)

```bash
crontab -e
# Ajouter :
0 3,15 * * * cd /opt/clickmart && docker compose exec -T nginx certbot renew --quiet && docker compose restart nginx >> /var/log/certbot-renew.log 2>&1
```

**Vérification S2** :
```bash
# Vérifier que le pipeline passe sur GitHub
# Vérifier le deploy
curl -I https://votre-domaine.com
# Les headers HSTS doivent apparaître
```

---

## 4. Semaine 3 — Frontend & Polish (J11-J15)

### J11 — ErrorBoundary & Axios interceptor

**Objectif** : Gérer les erreurs côté client proprement.

#### Tâche 11.1 — ErrorBoundary

| Élément | Détail |
|---|---|
| Fichier | `frontend/src/components/ErrorBoundary.jsx` (nouveau) |

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
    console.error("ErrorBoundary:", error, errorInfo);
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
            Recharger
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
```

| Élément | Détail |
|---|---|
| Fichier | `frontend/src/main.jsx` |
| Action | Wrapper avec ErrorBoundary |

```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./index.css";
import CartProvider from "./Provider/CartProvider.jsx";
import AuthProvider from "./Provider/AuthProvider.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <CartProvider>
          <App />
        </CartProvider>
      </AuthProvider>
    </ErrorBoundary>
  </StrictMode>
);
```

#### Tâche 11.2 — Améliorer l'axios instance

| Élément | Détail |
|---|---|
| Fichier | `frontend/src/api/index.js` |
| Action | Remplacer le contenu |

```javascript
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_SERVER_BASE_URL || "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("accessToken");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export { api };
```

**Vérification** :
```bash
cd frontend
npm run lint
npm run test -- --run
```

---

### J12 — Lazy loading & Pagination backend

**Objectif** : performances frontend + backend.

#### Tâche 12.1 — Lazy loading des routes

| Élément | Détail |
|---|---|
| Fichier | `frontend/src/App.jsx` |
| Action | Remplacer le contenu |

```jsx
import { lazy, Suspense } from "react";
import { Route, BrowserRouter as Router, Routes } from "react-router-dom";
import Header from "./components/Navbar";
import Footer from "./components/Footer";

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

const Loading = () => (
  <div className="d-flex justify-content-center align-items-center" style={{ minHeight: "50vh" }}>
    <div className="spinner-border text-primary" role="status">
      <span className="visually-hidden">Chargement...</span>
    </div>
  </div>
);

function App() {
  return (
    <Router>
      <Header />
      <Suspense fallback={<Loading />}>
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

#### Tâche 12.2 — Pagination backend

| Élément | Détail |
|---|---|
| Fichier | `backend/products/views.py` |
| Action | Ajouter pagination |

```python
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from .models import Product
from .serializers import ProductSerializer


class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    pagination_class = ProductPagination


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
```

**Vérification** :
```bash
cd backend
python manage.py test products.tests --verbosity=2
# Vérifier que la pagination fonctionne
python manage.py shell -c "
from rest_framework.test import APIClient
client = APIClient()
resp = client.get('/api/v1/products/')
print(resp.data.keys())  # doit contenir 'results', 'count', 'next'
"
```

---

### J13 — Pre-commit hooks & .env.example

**Objectif** : Qualité de code automatisée.

#### Tâche 13.1 — Pre-commit

| Élément | Détail |
|---|---|
| Fichier | `.pre-commit-config.yaml` (nouveau) |

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
pre-commit run --all-files
```

#### Tâche 13.2 — .env.example backend (mise à jour)

| Élément | Détail |
|---|---|
| Fichier | `backend/.env.example` |

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

#### Tâche 13.3 — .env.example frontend (nouveau)

| Élément | Détail |
|---|---|
| Fichier | `frontend/.env.example` (nouveau) |

```env
VITE_SERVER_BASE_URL=http://localhost:8000/api/v1
```

**Vérification** :
```bash
pre-commit run --all-files
cd backend && python manage.py test --verbosity=2
cd frontend && npm run lint && npm run test -- --run
```

---

### J14 — Nettoyage git (static/, fichiers inutiles)

**Objectif** : Réduire le poids du repo et supprimer les artefacts.

#### Tâche 14.1 — Retirer backend/static/ du git

```bash
# Ajouter au .gitignore root
echo "backend/static/" >> .gitignore

# Retirer du tracking (sans supprimer le dossier local)
git rm -r --cached backend/static/
git commit -m "chore: remove backend/static/ from tracking (generated at build)"
```

**Vérification** :
```bash
git ls-files -- "backend/static/" | wc -l  # doit être 0
du -sh backend/static/                     # dossier toujours présent localement
```

#### Tâche 14.2 — Supprimer api/tests.py vide

```bash
git rm backend/api/tests.py
git rm backend/api/__pycache__/*  # si tracké
```

Ou le vider proprement :
```python
# backend/api/tests.py — laisser vide
# (supprimé car le dossier api/ est un router, pas une app)
```

#### Tâche 14.3 — Supprimer apple.jpg de products/

```bash
git rm backend/products/apple.jpg
```

**Vérification** :
```bash
git status
git diff --stat HEAD
# Vérifier que rien de critique n'a été supprimé
```

---

### J15 — Tests additionnels & Documentation API

**Objectif** : Compléter les tests et documenter l'API.

#### Tâche 15.1 — Test d'intégration backend

| Élément | Détail |
|---|---|
| Fichier | `backend/api/tests.py` (recréer) |

```python
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch

from products.models import Product
from carts.models import Cart, CartItem
from orders.models import Order, OrderItem

User = get_user_model()


class FullOrderFlowTest(APITestCase):
    """Test du flux complet : register → login → add to cart → place order"""

    def setUp(self):
        self.register_url = reverse("register")
        self.login_url = reverse("token_obtain_pair")
        self.product = Product.objects.create(
            name="Integration Item",
            price=Decimal("25.00"),
            stock=10,
            tax_percent=Decimal("10.00"),
        )

    @patch("orders.views.send_order_notification")
    def test_full_flow(self, mock_notify):
        # 1. Register
        reg_data = {
            "email": "flow@example.com",
            "username": "flowuser",
            "password": "SecurePass123!",
        }
        response = self.client.post(self.register_url, reg_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 2. Login
        login_data = {"email": "flow@example.com", "password": "SecurePass123!"}
        response = self.client.post(self.login_url, login_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # 3. Add to cart
        cart_url = reverse("cart-add")
        response = self.client.post(
            cart_url, {"product_id": self.product.id, "quantity": 2}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 1)

        # 4. Place order
        order_url = reverse("order-place")
        shipping = {
            "shippingAddress": {
                "address": "123 Test St",
                "phone": "555-0100",
                "city": "Testville",
                "state": "TS",
                "zipCode": "12345",
            }
        }
        response = self.client.post(order_url, shipping, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 5. Verify order
        order = Order.objects.first()
        self.assertEqual(order.grand_total, Decimal("55.00"))
        self.assertEqual(order.items.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

        # 6. Cart is empty
        cart = Cart.objects.get(user__email="flow@example.com")
        self.assertEqual(cart.items.count(), 0)

        mock_notify.assert_called_once()
```

#### Tâche 15.2 — DRF Spectacular (documentation API)

```bash
pip install drf-spectacular
```

| Élément | Détail |
|---|---|
| Fichier | `backend/config/settings.py` — INSTALLED_APPS |

```python
INSTALLED_APPS = [
    ...
    'drf_spectacular',
]
```

```python
# Ajouter dans REST_FRAMEWORK
'REST_FRAMEWORK': {
    ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
},

# Ajouter en bas de settings.py
SPECTACULAR_SETTINGS = {
    'TITLE': 'ClickMart API',
    'DESCRIPTION': 'API e-commerce ClickMart',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
```

| Élément | Détail |
|---|---|
| Fichier | `backend/config/urls.py` |

```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

**Vérification finale** :
```bash
cd backend
python manage.py test --verbosity=2
# Tous les tests doivent passer

cd ../frontend
npm run lint
npm run test -- --run
npm run build

# Vérifier le pipeline sur GitHub
git push origin main
# Surveiller le workflow : https://github.com/tawounfouet/yt_django-clickmart-devops/actions
```

---

## 5. Matrice de dépendances

```
J1  J2  J3  J4  J5  J6  J7  J8  J9  J10 J11 J12 J13 J14 J15
 │   │   │   │   │   │   │   │   │   │   │   │   │   │   │
 ├─►─┤   │   │   │   │   │   │   │   │   │   │   │   │   │   1.1 → 1.2 (sécurité)
 │   ├─►─┤   │   │   │   │   │   │   │   │   │   │   │   │   1.2 → 1.3 (ALLOWED_HOSTS → serializers)
 │   │   ├─►─┤   │   │   │   │   │   │   │   │   │   │   │   1.3 → 1.4 (transactions)
 │   │   │   ├─►─┤   │   │   │   │   │   │   │   │   │   │   1.4 → 1.5 (validation cart)
 │   │   │   │   └─►─┼─►─┤   │   │   │   │   │   │   │   │   1.5 → 2.1 (nettoyage → CI)
 │   │   │   │   │   │   ├─►─┤   │   │   │   │   │   │   │   2.1 → 2.2 (CI → Docker health)
 │   │   │   │   │   │   │   └─►─┼─►─┤   │   │   │   │   │   2.2 → 2.3 (Docker → DevOps)
 │   │   │   │   │   │   │   │   │   └─►─┼─►─┤   │   │   │   2.3 → 3.1 (DevOps → Frontend)
 │   │   │   │   │   │   │   │   │   │   │   └─►─┼─►─┤   │   3.1 → 3.2 (Frontend → Polish)
```

**Tâches parallélisables** :
- J6-J7 (CI + Docker) peuvent être faits en parallèle par 2 personnes
- J9-J10 (DevOps) peuvent être faits en parallèle avec J6-J8
- J11-J12 (Frontend) peuvent être faits en parallèle avec J13-J14 (Polish)

---

## 6. Critères d'acceptation globaux

Le projet est **production-ready** quand :

### Sécurité
- [ ] `ruff check .` passe sans erreur
- [ ] Rate limiting fonctionne (tester avec `curl` en boucle)
- [ ] `curl -I http://votre-domaine.com` retourne `Strict-Transport-Security`
- [ ] Un mot de passe "123" est rejeté à l'inscription
- [ ] Le champ `is_active` n'apparaît pas dans l'API produits

### Fiabilité
- [ ] `python manage.py test` : 100% des tests passent
- [ ] Coverage ≥ 70% (`coverage report --fail-under=70`)
- [ ] Une commande avec panier vide retourne 400 (pas 500)
- [ ] Un stock insuffisant retourne 400 (pas de déduction partielle)

### CI/CD
- [ ] Le pipeline GitHub Actions affiche ✅ sur main
- [ ] Le deploy ne se fait qu'après succès des tests
- [ ] Le health check post-deploy passe

### DevOps
- [ ] `docker compose ps` montre tous les services "healthy"
- [ ] Le backup DB fonctionne (`/opt/clickmart/backups/` contient des fichiers)
- [ ] Le certificat SSL se renouvelle automatiquement
- [ ] Les logs Django sont structurés et visibles (`docker compose logs backend`)

### Frontend
- [ ] `npm run lint` passe
- [ ] `npm run test -- --run` passe
- [ ] `npm run build` produit un `dist/` valide
- [ ] Les routes sont lazy-loaded (vérifier dans Network tab du navigateur)

---

## 7. Risques et mitigation

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Migration CartItem `unique_together` casse les données existantes | Moyenne | Élevé | Vérifier l'absence de doublons avant migration : `SELECT cart_id, product_id, COUNT(*) FROM carts_cartitem GROUP BY cart_id, product_id HAVING COUNT(*) > 1` |
| `SECURE_SSL_REDIRECT` empêche l'accès HTTP local | Élevée | Moyen | Seulement activé quand `DEBUG=False`. Tester d'abord avec `DEBUG=True` |
| Le pipeline CI échoue à cause de l'absence de `.env` | Moyenne | Faible | Le workflow définit toutes les vars d'env nécessaires dans `env:` |
| Les healthchecks Docker ralentissent le démarrage | Faible | Faible | `start_period: 20s` donne le temps au backend de démarrer |
| Le lazy loading casse les imports existants | Moyenne | Moyen | Vérifier que tous les exports sont `default` (pas de named exports pour les pages) |
| ruff flag du code existant comme erreurs | Élevée | Faible | `ruff check --fix` corrige automatiquement la plupart des erreurs |

---

*Ce plan est un living document. Mettre à jour les cases à cocher au fur et à mesure de l'avancement.*
