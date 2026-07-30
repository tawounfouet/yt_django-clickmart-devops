# 3. Configuration — Ansible ClickMart

> **Mise à jour** : 30 juillet 2026

---

## 3.1 Inventory (`inventory.yml`)

```yaml
all:
  hosts:
    clickmart-prod:
      ansible_host: 172.239.20.14
      # ── VPS vierge → root ──
      # ansible_user: root
      # ── Après déploiement → deploy ──
      ansible_user: deploy
      ansible_ssh_private_key_file: ~/.ssh/id_rsa
      ansible_ssh_common_args: -o StrictHostKeyChecking=accept-new
  vars:
    env: production
    domain: webtech-dev.info
```

| Paramètre | Description |
|---|---|
| `ansible_host` | IP publique du VPS |
| `ansible_user` | `root` pour premier run, `deploy` après |
| `ansible_ssh_private_key_file` | Chemin vers la clé SSH privée |
| `ansible_ssh_common_args` | Évite le prompt interactive `known_hosts` |

---

## 3.2 Variables non-sensibles (`group_vars/all.yml`)

```yaml
---
env: production
domain: webtech-dev.info
admin_email: thomas.awounfouet@yahoo.com

db_host: 49.13.239.42
db_port: 5432
db_name: clickmart
db_user: postgres

redis_host: 49.13.239.42
redis_port: 6379

media_storage: cloudinary
email_backend: resend

# ─── Valeurs par défaut (remplacées par secrets.yml) ───
secret_key: "changeme-generate-with-python-secrets"
db_password: "changeme"
redis_password: "changeme"
cloudinary_cloud: "dsrbll7qc"
cloudinary_api_key: "changeme"
cloudinary_api_secret: "changeme"
resend_api_key: "changeme"
github_user: "tawounfouet"
github_token: "changeme"
```

### Signification des variables

| Variable | Rôle |
|---|---|
| `env` | Environnement (`production`, `staging`) |
| `domain` | Nom de domaine pour Nginx et Certbot |
| `admin_email` | Email Certbot (renouvellement, alertes) |
| `db_*` | Connexion PostgreSQL |
| `redis_*` | Connexion Redis |
| `media_storage` | Backend de médias (`cloudinary`, `s3`, `local`) |
| `email_backend` | Backend d'email (`resend`, `smtp`, `console`) |

Les valeurs sensibles (`secret_key`, `db_password`, `redis_password`, `cloudinary_*`, `resend_api_key`, `github_token`) ont des valeurs par défaut inoffensives dans `all.yml`. Elles sont **remplacées** par les valeurs réelles de `secrets.yml`.

---

## 3.3 Secrets (`group_vars/secrets.yml`)

Fichier **gitignoré**, chargé conditionnellement par le playbook :

```yaml
---
secret_key: "changeme-generate-with-django-secret"
db_password: "changeme"
redis_password: "changeme"
cloudinary_api_key: "changeme"
cloudinary_api_secret: "changeme"
resend_api_key: "changeme"
github_user: "tawounfouet"
github_token: "changeme"
```

### Chiffrement avec ansible-vault (optionnel mais recommandé)

```bash
ansible-vault encrypt infra/ansible/group_vars/secrets.yml
# → Saisir le mot de passe vault

ansible-vault decrypt infra/ansible/group_vars/secrets.yml
# → Déchiffrer pour édition

ansible-vault view infra/ansible/group_vars/secrets.yml
# → Lire sans déchiffrer
```

Avec vault chiffré, le déploiement nécessite `--ask-vault-pass` :

```bash
ansible-playbook deploy.yml -i inventory.yml --ask-vault-pass
```

---

## 3.4 Chargement conditionnel des secrets

Le playbook vérifie la présence de `secrets.yml` **sur le poste de contrôle** via `delegate_to: localhost` :

```yaml
pre_tasks:
  - name: Check if vault secrets file exists locally
    stat:
      path: "{{ playbook_dir }}/group_vars/secrets.yml"
    register: secrets_file
    delegate_to: localhost
    become: no

  - name: Load vault secrets
    include_vars:
      file: group_vars/secrets.yml
    when: secrets_file.stat.exists
```

**Particularité** : `become: no` est nécessaire sur les tâches déléguées à `localhost` pour éviter l'erreur `sudo: a password is required` sur macOS.

Si `secrets.yml` n'existe pas, le playbook utilise les valeurs par défaut de `all.yml` et continue — utile pour un test en environnement non sensible.
