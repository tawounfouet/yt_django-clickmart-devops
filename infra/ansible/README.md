# Ansible — ClickMart

Provisionne un VPS vierge → ClickMart fonctionnel en HTTPS.

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

# 2. Configurer les secrets (une seule fois)
cp group_vars/secrets.yml.example group_vars/secrets.yml
# → Éditer avec les vraies valeurs
# → Optionnel : ansible-vault encrypt group_vars/secrets.yml

# 3. Lancer
ansible-playbook deploy.yml -i inventory.yml
# Avec vault : ansible-playbook deploy.yml -i inventory.yml --ask-vault-pass
```

## Tags

| Tag | Rôle |
|---|---|
| `docker` | Docker + Compose + UFW + user deploy |
| `app` | Clone + .env + docker compose up |
| `ssl` | Certbot Let's Encrypt |
| `cicd` | Secrets GitHub Actions |

```bash
# Exécuter un rôle spécifique
ansible-playbook deploy.yml -i inventory.yml --tags docker
ansible-playbook deploy.yml -i inventory.yml --tags ssl
```

## Structure

```
infra/ansible/
├── inventory.yml                    # Hosts
├── deploy.yml                       # Playbook principal
├── group_vars/
│   ├── all.yml                      # Variables non-sensibles
│   └── secrets.yml                  # Secrets (gitignoré)
├── roles/
│   ├── docker/                      # Installation Docker + user deploy
│   ├── clickmart_app/               # Déploiement application
│   ├── ssl_certbot/                 # Certificats Let's Encrypt
│   └── github_actions/              # Configuration CI/CD
└── README.md
```

## VPS vierge (premier run)

1. Créer le VPS chez Linode/IONOS/DigitalOcean
2. Ajouter la clé SSH (`~/.ssh/id_rsa.pub`) lors de la création
3. Dans `inventory.yml` : `ansible_user: root`
4. Lancer le playbook

```bash
ansible-playbook deploy.yml -i inventory.yml
# → Docker + app + SSL : ~3 min
```

5. Après le premier run, repasser à `ansible_user: deploy`

## VPS existant (re-déploiement)

```bash
ansible-playbook deploy.yml -i inventory.yml --tags app
```

## Maintenance

```bash
# Ping
ansible all -i inventory.yml -m ping

# Voir les facts
ansible all -i inventory.yml -m setup

# Commande ad-hoc
ansible all -i inventory.yml -m shell -a "docker ps"
```
