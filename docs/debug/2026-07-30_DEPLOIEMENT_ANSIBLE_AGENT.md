# Debug : Déploiement Ansible par l'agent deploy-fullstack — 30 juillet 2026

> - **Contexte** : Premier déploiement via l'agent v4.0 (mode Ansible) après migration massive (UUID PKs, django-environ, pytest, Sentry).
> - **Issue finale** : 4 bugs découverts en production, tous résolus.

---

## Table des bugs

| # | Bug | Impact | Statut |
|---|---|---|---|
| 1 | [UUID PKs : `AlterField` incompatible PostgreSQL](#1-uuid-pks-alterfield-incompatible-postgresql) | `docker compose up` crash | ✅ résolu |
| 2 | [`create_admin` : `from decouple import config` absent du Dockerfile](#2-create_admin-from-decouple-import-config-absent) | Backend crash au démarrage | ✅ résolu |
| 3 | [Clé SSH `id_rsa` au lieu de `id_ed25519` dans l'inventory](#3-clé-ssh-invalide-dans-linventory) | Preflight check | ✅ résolu |
| 4 | [Base de données reset en production](#4-base-de-données-reset-en-production) | Perte de données | ⚠️ documenté |

---

## 1. UUID PKs : `AlterField` incompatible PostgreSQL

### Symptôme

```
django.db.utils.ProgrammingError: cannot cast type bigint to uuid
LINE 1: ...ALTER COLUMN id TYPE uuid USING id::uuid
```

### Contexte

Les migrations générées par `makemigrations` pour passer de `BigAutoField` à `UUIDField` utilisent `AlterField`. Sur SQLite (dev local), Django émule le changement de type en recréant la table, donc ça passe. Sur PostgreSQL (production), Django génère un `ALTER COLUMN ... TYPE ... USING` qui échoue car il n'y a pas de cast natif `bigint → uuid`.

### Diagnostic

La migration générée :
```python
# backend/users/migrations/0002_alter_user_id.py (version SQLite-compatible)
migrations.AlterField(
    model_name='user',
    name='id',
    field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
)
```

Sur PostgreSQL, cela se traduit par :
```sql
ALTER COLUMN id TYPE uuid USING id::uuid
-- ERREUR : pas de cast bigint → uuid
```

### Pistes envisagées

| Option | Résultat |
|---|---|
| A. Migration manuelle avec `RunSQL` | Complexe, doit gérer FK cascade |
| B. `RemoveField` + `AddField` | Propre, mais supprime la colonne (perte de données si non vide) |
| C. Table temporaire + swap | Trop complexe |

### Solution retenue

**Option B** — `RemoveField` + `AddField`. La table est vide (base fraîchement créée), donc pas de perte de données.

```python
# backend/users/migrations/0002_alter_user_id.py (version PostgreSQL-compatible)
operations = [
    migrations.RemoveField(model_name='user', name='id'),
    migrations.AddField(
        model_name='user',
        name='id',
        field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
    ),
]
```

**Fichiers corrigés** (commit `79d885d`) :
- `users/migrations/0002_alter_user_id.py`
- `products/migrations/0003_alter_product_id.py`
- `carts/migrations/0004_alter_cart_id_alter_cartitem_id.py`
- `orders/migrations/0004_alter_order_id_alter_orderitem_id.py`

### Leçon

> Django génère des migrations compatibles SQLite mais pas toujours PostgreSQL. Toujours tester les migrations sur la base cible (PostgreSQL) avant de déployer en production. Les migrations de changement de PK sont particulièrement sensibles.

---

## 2. `create_admin` : `from decouple import config` absent

### Symptôme

```
ModuleNotFoundError: No module named 'decouple'
```

Le conteneur backend crashait au démarrage car la commande `create_admin` importait `decouple` — module retiré du `requirements.txt` pendant la migration vers `django-environ`.

### Diagnostic

```python
# backend/users/management/commands/create_admin.py (AVANT)
from decouple import config

class Command(BaseCommand):
    def handle(self, *args, **options):
        email = config('ADMIN_EMAIL', default='admin@clickmart.local')
        password = config('ADMIN_PASSWORD', default='admin123')
```

Le module `python-decouple` a été retiré de `requirements.txt` dans la session précédente (migration vers `django-environ`), mais le `Dockerfile` n'a pas été rebuildé localement — le bug n'est apparu qu'en production.

### Pistes envisagées

| Option | Résultat |
|---|---|
| A. Réinstaller `python-decouple` dans `requirements.txt` | Rétrograde la migration django-environ |
| B. Remplacer par `django-environ` (`env()`) | Nécessite l'import, lourd pour une commande simple |
| C. Remplacer par `os.environ.get()` | Simple, natif, pas de dépendance |

### Solution retenue

**Option C** — `os.environ.get()`. La commande `create_admin` n'a pas besoin de toute la puissance de django-environ, juste de lire 2 variables.

```python
# backend/users/management/commands/create_admin.py (APRÈS)
import os

class Command(BaseCommand):
    def handle(self, *args, **options):
        email = os.environ.get('ADMIN_EMAIL', 'admin@clickmart.local')
        password = os.environ.get('ADMIN_PASSWORD', 'admin123')
```

Ajout des variables dans le template Ansible `.env.prod.j2` :
```jinja2
ADMIN_EMAIL={{ admin_email }}
ADMIN_PASSWORD=admin123
```

**Fichiers corrigés** (commit `eb46afe`) :
- `backend/users/management/commands/create_admin.py`
- `infra/ansible/roles/clickmart_app/templates/.env.prod.j2`

### Leçon

> Quand on retire une dépendance (`python-decouple`), vérifier TOUS les imports dans le projet, pas seulement `settings.py`. Un `grep -r "from decouple" backend/` avant de retirer le module aurait évité ce bug.

---

## 3. Clé SSH invalide dans l'inventory

### Symptôme

```
ansible all -i infra/ansible/inventory.yml -m ping
→ UNREACHABLE
```

### Diagnostic

Le preflight check a détecté :
```yaml
# infra/ansible/inventory.yml (avant correction)
ansible_ssh_private_key_file: ~/.ssh/id_rsa
```

Mais la clé configurée sur le serveur (via le rôle Ansible `docker`) est `~/.ssh/id_ed25519.pub`. Le fichier `id_rsa` n'existe pas ou ne correspond pas.

### Solution

```yaml
ansible_ssh_private_key_file: ~/.ssh/id_ed25519
```

### Leçon

> Après un reprovisionnement Ansible qui change la clé du user `deploy` (ED25519 vs RSA), mettre à jour l'inventory. Le preflight check de l'agent v4.0 a correctement détecté cette incohérence avant le déploiement.

---

## 4. Base de données reset en production

### Symptôme

La base PostgreSQL `clickmart` sur `49.13.239.42` a été supprimée et recréée. Toutes les données de production ont été perdues.

### Diagnostic

Les migrations UUID PK ont échoué (bug #1). Après correction des migrations, la base contenait des migrations partielles (état incohérent). La solution la plus rapide était de reset la base et de réappliquer toutes les migrations.

### Impact

- **Données perdues** : utilisateurs, produits, paniers, commandes
- **Récupération** : pas de backup récent (le backup script n'a jamais été exécuté en cron)
- **Mitigation** : l'app n'est pas encore utilisée en production réelle

### Solution

```sql
DROP DATABASE clickmart;
CREATE DATABASE clickmart;
```

Puis réapplication de toutes les migrations.

### Leçon

> Avant un déploiement qui change la structure de la base (PK, FK), TOUJOURS :
> 1. Faire un backup : `pg_dump clickmart > backup_before_uuid.sql`
> 2. Tester les migrations sur une copie de la base
> 3. Avoir un plan de rollback
> 4. Activer le cron de backup (`infra/scripts/backup-db.sh`) AVANT de déployer

---

## Synthèse

### Chronologie des événements

| Étape | Action | Résultat |
|---|---|---|
| 1 | Preflight check | Clé SSH `id_rsa` → corrigée en `id_ed25519` |
| 2 | Ansible playbook `--tags docker` | ✅ Docker + UFW + fail2ban OK |
| 3 | Ansible playbook `--tags app` | ❌ Backend crash (bug #1 + #2) |
| 4 | Fix migrations UUID (commit `79d885d`) | 4 migrations corrigées |
| 5 | CI/CD pipeline #1 | ✅ Build + push OK |
| 6 | Ansible playbook `--tags app` (retry) | ❌ Backend crash (bug #2) |
| 7 | Fix create_admin (commit `eb46afe`) | Template + commande corrigés |
| 8 | CI/CD pipeline #2 | ✅ Build + push OK |
| 9 | Ansible playbook complet (retry) | ✅ Tous les conteneurs healthy |
| 10 | Health check | ✅ Frontend 200, API 200 |

### Causes racines

| Bug | Cause | Évitable ? |
|---|---|---|
| UUID migrations PostgreSQL | `makemigrations` testé uniquement sur SQLite | Oui — tester sur PostgreSQL avant |
| `create_admin` / `decouple` | `grep` sur les imports non fait après migration | Oui — `grep -r "decouple" backend/` |
| Clé SSH inventory | Non mis à jour après reprovisionnement Ansible | Oui — documenté dans le preflight |
| DB reset | Pas de backup avant migration de structure | Oui — backup systématique avant ALTER TABLE |

### Checklist anti-régression

- [ ] Avant de changer les dépendances : `grep -r "from <module>" backend/` sur tous les imports
- [ ] Avant de déployer des migrations : tester sur PostgreSQL (pas seulement SQLite)
- [ ] Avant un déploiement majeur : `pg_dump` du backup
- [ ] Après un reprovisionnement : vérifier `ansible all -m ping`
- [ ] Activer le cron de backup en production (`backup-db.sh` quotidien à 3h)
