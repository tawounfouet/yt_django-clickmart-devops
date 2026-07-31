# Analyse — Export de la configuration comme template Terraform/Ansible

> - **Date** : 2026-07-29
> - **Projet** : ClickMart
> - **Contexte** : Automatisation complète du provisionnement infrastructure

---

## Résumé

L'objectif est de pouvoir recréer l'intégralité de l'infrastructure ClickMart sur un nouveau fournisseur cloud en exécutant une seule commande. Actuellement, le déploiement repose sur :

- Un VPS provisionné manuellement (Linode, IONOS...)
- Docker + Docker Compose installés manuellement
- Fichiers `.env` copiés manuellement sur le serveur
- GitHub Actions configuré manuellement (secrets)

**Cible** : `terraform apply` ou `ansible-playbook deploy.yml` provisionne tout.

---

## Approche recommandée : Terraform pour l'infra, Ansible pour la config

```
┌─────────────────────────────────────────────────────────┐
│                     Terraform                            │
│  (infrastructure : VPS, réseau, DNS, firewall)          │
│                                                          │
│  resource "linode_instance" "clickmart" { ... }         │
│  resource "cloudflare_record" "webtech" { ... }         │
│  output "instance_ip" { ... }                           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                      Ansible                             │
│  (configuration : Docker, app, .env, SSL, CI/CD)        │
│                                                          │
│  - hosts: clickmart                                      │
│    roles:                                                │
│      - docker                                            │
│      - clickmart_app                                     │
│      - ssl_certbot                                       │
│      - github_actions                                    │
└─────────────────────────────────────────────────────────┘
```

| Outil | Responsabilité | Pourquoi |
|---|---|---|
| **Terraform** | Créer le VPS, configurer le DNS, ouvrir les ports | Gère l'état (state), idempotent, multi-cloud |
| **Ansible** | Installer Docker, déployer l'app, configurer SSL | Pas d'agent, YAML lisible, idempotent |

---

## Phase 1 — Terraform : Infrastructure

### Fichier : `infra/terraform/main.tf`

```hcl
terraform {
  required_providers {
    linode = { source = "linode/linode" }
  }
}

variable "linode_token" { sensitive = true }
variable "root_password" { sensitive = true }

provider "linode" {
  token = var.linode_token
}

resource "linode_instance" "clickmart" {
  label           = "clickmart-prod"
  image           = "linode/ubuntu24.04"
  region          = "us-east"
  type            = "g6-nanode-1"   # 1 GB RAM
  root_pass       = var.root_password
  authorized_keys = [file("~/.ssh/id_ed25519.pub")]
}

resource "linode_firewall" "clickmart" {
  label = "clickmart-fw"
  inbound {
    protocol = "TCP"
    ports    = "22"
    addresses = ["0.0.0.0/0"]
  }
  inbound {
    protocol = "TCP"
    ports    = "80"
    addresses = ["0.0.0.0/0"]
  }
  inbound {
    protocol = "TCP"
    ports    = "443"
    addresses = ["0.0.0.0/0"]
  }
  inbound_policy  = "DROP"
  outbound_policy = "ACCEPT"
  linodes = [linode_instance.clickmart.id]
}

output "instance_ip" {
  value = linode_instance.clickmart.ip_address
}
```

### Multi-cloud : le même Terraform pour IONOS, AWS, DigitalOcean...

```hcl
# Il suffit de changer le provider
# provider "ionoscloud" { ... }
# provider "aws" { ... }
# provider "digitalocean" { ... }

resource "cloudflare_record" "webtech" {
  zone_id = var.cloudflare_zone_id
  name    = "webtech-dev.info"
  value   = linode_instance.clickmart.ip_address
  type    = "A"
  proxied = true
}
```

### Commandes

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply -auto-approve
# → VPS créé, IP affichée, DNS configuré
```

---

## Phase 2 — Ansible : Configuration

### Structure

```
infra/ansible/
├── inventory.yml
├── deploy.yml                    # Playbook principal
├── group_vars/
│   └── all.yml                   # Variables communes
├── roles/
│   ├── docker/                   # Installation Docker + Compose
│   │   └── tasks/main.yml
│   ├── clickmart_app/            # Déploiement de l'application
│   │   ├── tasks/main.yml
│   │   └── templates/
│   │       └── .env.prod.j2      # Template Jinja2 pour .env
│   ├── ssl_certbot/              # HTTPS Let's Encrypt
│   │   └── tasks/main.yml
│   └── github_actions/           # Configuration CI/CD
│       └── tasks/main.yml
└── requirements.yml              # Dépendances Ansible Galaxy
```

### Playbook principal : `deploy.yml`

```yaml
- name: Provision ClickMart server
  hosts: clickmart
  become: yes
  vars_files:
    - group_vars/all.yml

  roles:
    - docker
    - clickmart_app
    - ssl_certbot
    - github_actions
```

### Rôle Docker : `roles/docker/tasks/main.yml`

```yaml
- name: Install Docker dependencies
  apt:
    name: [ca-certificates, curl, git]
    state: present

- name: Add Docker GPG key
  apt_key:
    url: https://download.docker.com/linux/ubuntu/gpg
    state: present

- name: Add Docker repository
  apt_repository:
    repo: "deb [arch=amd64] https://download.docker.com/linux/ubuntu noble stable"
    state: present

- name: Install Docker
  apt:
    name: [docker-ce, docker-ce-cli, containerd.io, docker-compose-plugin]
    state: present

- name: Create deploy user
  user:
    name: deploy
    groups: docker
    shell: /bin/bash

- name: Add SSH key for deploy
  authorized_key:
    user: deploy
    key: "{{ lookup('file', '~/.ssh/id_ed25519.pub') }}"
```

### Rôle ClickMart App : `roles/clickmart_app/tasks/main.yml`

```yaml
- name: Clone repository
  git:
    repo: "git@github.com:tawounfouet/yt_django-clickmart-devops.git"
    dest: /opt/clickmart
    version: main
    accept_hostkey: yes
  become_user: deploy

- name: Generate .env.prod from template
  template:
    src: .env.prod.j2
    dest: /opt/clickmart/backend/.envs/.prod
    owner: deploy
    mode: 0600

- name: Create .env.local symlink
  file:
    src: /opt/clickmart/backend/.envs/.prod
    dest: /opt/clickmart/backend/.envs/.local
    state: link
    force: yes

- name: Start application
  docker_compose:
    project_src: /opt/clickmart
    files:
      - docker-compose.yml
      - docker-compose.prod.yml
    project_name: clickmart
    state: present
    build: no
    pull: yes
  become_user: deploy
```

### Template .env.prod : `roles/clickmart_app/templates/.env.prod.j2`

```jinja2
SECRET_KEY={{ secret_key }}
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS={{ domain }},www.{{ domain }},{{ ansible_default_ipv4.address }},localhost
CORS_ALLOWED_ORIGINS=https://{{ domain }},https://www.{{ domain }}

DATABASE_URL=postgres://{{ db_user }}:{{ db_password }}@{{ db_host }}:{{ db_port }}/{{ db_name }}?sslmode=require

CELERY_BROKER_URL=redis://{{ redis_user }}:{{ redis_password }}@{{ redis_host }}:6379/0
CELERY_RESULT_BACKEND=redis://{{ redis_user }}:{{ redis_password }}@{{ redis_host }}:6379/1

MEDIA_STORAGE_BACKEND={{ media_storage }}
CLOUDINARY_CLOUD_NAME={{ cloudinary_cloud }}
CLOUDINARY_API_KEY={{ cloudinary_api_key }}
CLOUDINARY_API_SECRET={{ cloudinary_api_secret }}

EMAIL_BACKEND_TYPE=resend
RESEND_API_KEY={{ resend_api_key }}
DEFAULT_FROM_EMAIL=hello@{{ domain }}
ADMIN_EMAIL={{ admin_email }}
ADMIN_PASSWORD={{ admin_password }}
```

### Variables : `group_vars/all.yml`

```yaml
domain: webtech-dev.info
db_host: 49.13.239.42
db_port: 5432
db_name: clickmart
db_user: postgres
redis_host: 49.13.239.42
redis_user: default
media_storage: cloudinary
admin_email: thomas.awounfouet@yahoo.com
```

### Variables sensibles : `ansible-vault encrypt group_vars/secrets.yml`

```bash
ansible-vault create group_vars/secrets.yml
```

```yaml
secret_key: ZR4e5ySk2aV2Bc7fbDe...
db_password: 8U69qKIOxQ...
redis_password: 5FVFmDuc9Yo...
cloudinary_cloud: dsrbll7qc
cloudinary_api_key: changeme
cloudinary_api_secret: 4LbtgrinmMk...
resend_api_key: re_YRepoFCP...
admin_password: admin123
linode_token: xxxxx
root_password: xxxxx
```

### Commande

```bash
cd infra/ansible
ansible-playbook deploy.yml -i inventory.yml --ask-vault-pass
# → Tout est installé, configuré, l'app tourne
```

---

## Phase 3 — Intégration CI/CD

### Déclenchement depuis GitHub Actions

```yaml
# .github/workflows/automate.yml — ajouter un job optionnel
provision-infra:
  if: github.event_name == 'workflow_dispatch'
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: hashicorp/setup-terraform@v3
    - run: |
        cd infra/terraform
        terraform init
        terraform apply -auto-approve
      env:
        LINODE_TOKEN: ${{ secrets.LINODE_TOKEN }}
    - run: |
        cd infra/ansible
        ansible-playbook deploy.yml -i inventory.yml
      env:
        ANSIBLE_VAULT_PASSWORD: ${{ secrets.ANSIBLE_VAULT_PASSWORD }}
```

---

## Comparatif : avec / sans IaC

| Aspect | Actuel (manuel) | Avec Terraform + Ansible |
|---|---|---|
| Provisionner un VPS | 10 min (interface web) | `terraform apply` (2 min) |
| Installer Docker/Git/UFW | Phase 1 de l'agent | Rôle Ansible (automatique) |
| Configurer .env | Copie manuelle SSH | Template Jinja2 (automatique) |
| Déployer l'app | `docker compose up` | Rôle Ansible (automatique) |
| SSL Certbot | Script manuel | Rôle Ansible (automatique) |
| Reproduire sur un autre cloud | Tout refaire | Changer le provider Terraform |
| Secrets | Fichiers .env manuels | Ansible Vault (chiffré) |

---

## Prochaines étapes

1. **Extraire les variables** de `inventory.yml` (déjà généré par dry-run) vers les variables Ansible
2. **Créer le rôle `clickmart_app`** qui lit `docker-compose.yml` + `docker-compose.prod.yml`
3. **Tester sur un VPS vierge** : `terraform apply && ansible-playbook deploy.yml`
4. **Ajouter le job `provision-infra`** au workflow GitHub Actions
5. **Migrer les secrets** existants (LINODE_SSH_KEY, etc.) vers Ansible Vault

---

## Effort estimé

| Phase | Tâche | Effort |
|---|---|---|
| 1 | Terraform (VPS + DNS + firewall) | 2h |
| 2 | Ansible (Docker + app + SSL + CI/CD) | 4h |
| 3 | Intégration CI/CD | 1h |
| **Total** | | **~7h** |
