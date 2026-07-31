# Ansible — ClickMart

Provisionne un VPS vierge → ClickMart fonctionnel en HTTPS (production) ou HTTP (staging).

## Prérequis

```bash
pip install ansible
ansible-galaxy collection install community.docker
```

## Usage

```bash
cd infra/ansible

# 1. Configurer l'inventory
vim inventory.yml    # → IP + ansible_user (root pour VPS vierge, deploy ensuite)

# 2. Configurer les secrets (une seule fois pour tous les environnements)
cp group_vars/secrets.yml.example group_vars/secrets.yml
# → Éditer avec les vraies valeurs
# → Optionnel : ansible-vault encrypt group_vars/secrets.yml

# 3. Lancer — production
ansible-playbook deploy.yml -i inventory.yml --limit clickmart-prod

# 4. Lancer — staging
ansible-playbook deploy.yml -i inventory.yml --limit clickmart-staging
# Avec vault : ansible-playbook deploy.yml -i inventory.yml --ask-vault-pass --limit clickmart-staging
```

## Tags

| Tag | Rôle |
|---|---|
| `docker` | Docker + Compose + UFW + fail2ban + user deploy |
| `app` | Clone + .env + docker compose up |
| `ssl` | Certbot Let's Encrypt (prod uniquement, ignoré en staging) |
| `cicd` | Secrets GitHub Actions |

```bash
# Déployer uniquement l'app sur staging
ansible-playbook deploy.yml -i inventory.yml --limit clickmart-staging --tags app
```

## Multi-environnement

| Variable | Production | Staging |
|---|---|---|
| `domain` | `webtech-dev.info` | `staging.webtech-dev.info` |
| `app_dir` | `/opt/clickmart` | `/opt/clickmart-stg` |
| `project_name` | `clickmart` | `clickmart-stg` |
| `branch` | `main` | `stg` |
| `ssl_enabled` | `true` | `false` |
| `health_proto` | `https` | `http` |
| Port | 80/443 | 8080 |

**Isolation** : les deux stacks utilisent des noms de projet Docker distincts (`-p clickmart` vs `-p clickmart-stg`) et des répertoires séparés. Elles peuvent coexister si le VPS a assez de RAM.

## VPS vierge (premier run)

1. Créer le VPS chez Linode/IONOS/DigitalOcean
2. Ajouter la clé SSH (`~/.ssh/id_ed25519.pub`) lors de la création
3. Dans `inventory.yml` : `ansible_user: root`
4. Lancer le playbook

```bash
ansible-playbook deploy.yml -i inventory.yml --limit clickmart-prod
# → Docker + app + SSL : ~3 min
```

5. Après le premier run, repasser à `ansible_user: deploy`
