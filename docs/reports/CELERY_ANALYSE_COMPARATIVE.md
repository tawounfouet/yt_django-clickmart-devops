# Analyse comparative — Celery Patterns (udemy) → ClickMart

> **Source** : `udemy_dj-celery-mastery` (Django 4.2 / Celery 5.3 / RabbitMQ / Redis / Flower)
> **Cible** : ClickMart (Django 5.2 / Celery 5.6 / Redis 7 / Docker / Linode 961 MiB)
> **Date** : 2026-07-29

---

## Résumé exécutif

Le projet `django-celery-mastery` est un bac à sable pédagogique couvrant l'ensemble des patterns Celery en production. Sur les **40+ patterns identifiés**, **12 sont directement applicables à ClickMart** avec un effort total estimé à **4-6 heures**.

---

## Recommandations priorisées

### 🔴 Priorité 1 — Critique (sécurité/résilience)

| # | Recommandation | Pourquoi | Effort | Gain |
|---|---|---|---|---|
| 1 | **Resource limits Docker** (`mem_limit`, `cpus`) | Linode 961 MiB — un worker en fuite mémoire tue tout | 10 min | Évite OOM killer |
| 2 | **`task_reject_on_worker_lost = True`** | Si le worker crashe, la tâche est perdue sinon | 2 min | Zéro perte de tâche |
| 3 | **`result_expires = 3600`** | Redis ne nettoie pas automatiquement les résultats | 2 min | Évite saturation Redis |
| 4 | **`task_time_limit = 600`** + **`task_soft_time_limit = 300`** | Protection contre les tâches bloquées | 2 min | Pas de worker bloqué |

### 🟠 Priorité 2 — Important (monitoring/observabilité)

| # | Recommandation | Pourquoi | Effort | Gain |
|---|---|---|---|---|
| 5 | **Flower monitoring** (port 5555) | Visibilité temps réel sur les tâches | 30 min | Dashboard, debug, API |
| 6 | **`retry_backoff=True` + `retry_jitter=True`** | Sur les tâches avec retry (email, commande) | 10 min | Évite thundering herd |
| 7 | **`autoretry_for`** sur tâches critiques | Retry automatique sur erreurs réseau | 5 min/tâche | Résilience |

### 🟡 Priorité 3 — Recommandé (qualité de vie)

| # | Recommandation | Pourquoi | Effort | Gain |
|---|---|---|---|---|
| 8 | **`django-celery-beat` + DatabaseScheduler** | Tâches planifiées modifiables via admin Django | 45 min | Admin UI pour les schedules |
| 9 | **Service `beat` séparé du `worker`** | Conforme aux recommandations Celery | 30 min | Un crash n'emporte pas le scheduler |
| 10 | **Dead letter queue** | Isoler les tâches échouées pour analyse | 1h | Debug post-mortem |

### 🟢 Priorité 4 — Optionnel (nice-to-have)

| # | Recommandation | Pourquoi | Effort | Gain |
|---|---|---|---|---|
| 11 | **Sentry conditionnel** | Tracking d'erreurs en production | 15 min | Alerting erreurs |
| 12 | **Réseau Docker `internal`** | Isoler Redis/Postgres du host | 10 min | Surface d'attaque réduite |

---

## Détail des recommandations

### 1. Resource limits Docker

```yaml
# docker-compose.yml — ajouter sur chaque service
services:
  redis:
    mem_limit: 128m
  db:
    mem_limit: 256m
  backend:
    mem_limit: 512m
    cpus: 1
  celery-worker:
    mem_limit: 256m
    cpus: 0.5
  celery-beat:
    mem_limit: 128m
    cpus: 0.5
```

**Justification** : avec 961 MiB de RAM, sans limits, un conteneur en fuite (ex: worker qui charge un dataset en mémoire) peut tuer l'OS hôte. Les limits garantissent que chaque service reste dans son enveloppe.

### 2-4. Configuration Celery robuste

```python
# backend/config/celery.py — ajouter
app.conf.task_acks_late = True                # Ack après exécution
app.conf.task_reject_on_worker_lost = True    # Requeue si crash
app.conf.task_default_retry_delay = 60        # 60s entre retries
app.conf.task_max_retries = 3                 # Max 3 retries
app.conf.task_soft_time_limit = 300           # Warning à 5 min
app.conf.task_time_limit = 600                # Kill à 10 min
app.conf.result_expires = 3600               # TTL résultats Redis 1h
```

Ces paramètres n'existent pas dans la config actuelle de ClickMart. Ils sont le socle minimal pour une utilisation Celery en production.

### 5. Flower

```yaml
# docker-compose.yml
flower:
  image: mher/flower
  ports:
    - "5555:5555"
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
  depends_on:
    redis:
      condition: service_healthy
  mem_limit: 128m
```

Ajouter `-E` au worker : `celery -A config worker --loglevel=info -E`

### 6-7. Retry policies

```python
# Exemple : orders/tasks.py
from celery import shared_task
from requests.exceptions import ConnectionError, Timeout

@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, Timeout),
    default_retry_delay=5,
    retry_kwargs={"max_retries": 5},
    retry_backoff=True,
    retry_jitter=True,
)
def send_order_confirmation_email(self, order_id, user_email):
    # ... logique d'envoi ...
```

### 8. django-celery-beat

```bash
pip install django-celery-beat
```

```python
# settings.py
INSTALLED_APPS += ['django_celery_beat']
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

```yaml
# docker-compose.yml — commande beat
celery-beat:
  command: celery -A config beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Les tâches périodiques sont ensuite gérables depuis `/admin/django_celery_beat/periodictask/`.

---

## Patterns NON recommandés pour ClickMart

| Pattern | Raison |
|---|---|
| RabbitMQ comme broker | Redis suffit à l'échelle ClickMart. RabbitMQ = +256 MiB RAM + complexité |
| Workers standalone (sans Django) | Pas de tâches hors Django |
| Adminer (interface DB externe) | Django admin déjà présent |
| `runserver` en prod | ClickMart utilise déjà Gunicorn ✅ |
| Bind mounts pour hot-reload en prod | Le code est dans l'image Docker ✅ |
| Double broker (RabbitMQ + Redis) | Complexité inutile |

---

## Effort total estimé

| Priorité | Items | Effort |
|---|---|---|
| 🔴 Critique | 1-4 | **20 min** |
| 🟠 Important | 5-7 | **50 min** |
| 🟡 Recommandé | 8-10 | **2h15** |
| 🟢 Optionnel | 11-12 | **25 min** |
| **Total** | **12 items** | **~4h** |

---

## Avant/Après — Configuration Celery ClickMart

| Paramètre | Avant | Après |
|---|---|---|
| `task_acks_late` | (défaut: False) | True |
| `task_reject_on_worker_lost` | (défaut: False) | True |
| `task_time_limit` | (illimité) | 600s |
| `result_expires` | (défaut: 24h) | 1h |
| Retry policy | Aucune | backoff + jitter |
| Scheduler | Fichier par défaut | DB-backed (admin) |
| Monitoring | Aucun | Flower dashboard |
| Resource limits | Aucun | mem_limit + cpus |
| Dead letter queue | Non | Oui (si implémenté) |

---

## Source

- Projet : `udemy_dj-celery-mastery`
- Documentation : 20 ADR, ANALYSIS.md, ARCHITECTURE.md, CRITICAL-REVIEW.md, IMPLEMENTATION-PLAN.md
- Docker : 10 services, 2 réseaux, healthcheck-driven startup
- Tâches : 15 exemples couvrant retry, dead letter, timeouts, groups, chains, signals, scheduling
