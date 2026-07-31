# Plan d'implémentation — Ansible : Configuration du serveur ClickMart

> Basé sur l'analyse : `docs/analyse/2026-07-29_ANALYSE_TERRAFORM_ANSIBLE.md` (Phase 2 uniquement)
> **Périmètre** : Ansible uniquement — le provisionnement de l'infrastructure (VPS, DNS, firewall) est fait manuellement par l'utilisateur chez son fournisseur de choix

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Prérequis](#2-prérequis)
3. [Structure des fichiers](#3-structure-des-fichiers)
4. [Rôle docker](#4-rôle-docker)
5. [Rôle clickmart_app](#5-rôle-clickmart_app)
6. [Rôle ssl_certbot](#6-rôle-ssl_certbot)
7. [Rôle github_actions](#7-rôle-github_actions)
8. [Variables et secrets](#8-variables-et-secrets)
9. [Playbook principal](#9-playbook-principal)
10. [Utilisation](#10-utilisation)
11. [Estimation d'effort](#11-estimation-deffort)

---

## 1. Vue d'ensemble

```
Utilisateur                    Ansible                         Serveur cible
    │                             │                                │
    │  1. Provisionne le VPS      │                                │
    │  (manuel : Linode/IONOS/    │                                │
    │   AWS/DigitalOcean/OVH)     │                                │
    │                             │                                │
    │  2. Renseigne l'IP          │                                │
    │     dans inventory.yml      │                                │
    │                             │                                │
    │  3. ansible-playbook ──────▶│  docker role ────────────────▶ Install Docker + Compose
    │                             │                                │
    │                             │  clickmart_app role ─────────▶ Clone repo + .env + up
    │                             │                                │
    │                             │  ssl_certbot role ────────────▶ Certificats Let's Encrypt
    │                             │                                │
    │                             │  github_actions role ─────────▶ Config CI/CD
    │                             │                                │
    │  4. Site dispo ────────────▶│                                │
```

| Phase | Rôle | Responsabilité | Optionnel |
|---|---|---|---|
| 1 | `docker` | Docker, Compose, Git, user deploy, UFW | Non |
| 2 | `clickmart_app` | Clone repo, génération .env, docker compose up | Non |
| 3 | `ssl_certbot` | Certificats Let's Encrypt, Nginx HTTPS | Oui |
| 4 | `github_actions` | Secrets GitHub, workflow CI/CD | Oui |

---

## 2. Prérequis

### Côté utilisateur

- Python ≥ 3.10 installé localement
- Ansible ≥ 2.15 installé : `pip install ansible`
- Clé SSH publique ajoutée au VPS (user `root` ou `deploy`)
- OpenSSH client
- `ansible-vault` pour les secrets (optionnel mais recommandé)

### Côté serveur (avant Ansible)

- VPS vierge Ubuntu 24.04 provisionné (1 GB RAM min, 25 GB disk min)
- Ports ouverts dans le firewall cloud : **22**, **80**, **443**
- Accès SSH root (ou user avec sudo)
- Swap configuré si < 2 GB RAM

---

## 3. Structure des fichiers

```
infra/ansible/
├── inventory.yml                         # Hosts + groupes
├── deploy.yml                            # Playbook principal
├── group_vars/
│   ├── all.yml                           # Variables non-sensibles
│   ├── secrets.yml                       # Variables sensibles (chiffré vault)
│   └── vault_password                    # Mot de passe vault (gitignoré)
├── roles/
│   ├── docker/
│   │   └── tasks/
│   │       └── main.yml                  # Installation Docker + Compose
│   ├── clickmart_app/
│   │   ├── tasks/
│   │   │   └── main.yml                  # Déploiement app
│   │   └── templates/
│   │       └── .env.prod.j2              # Template Jinja2 du .env
│   ├── ssl_certbot/
│   │   └── tasks/
│   │       └── main.yml                  # Certificats SSL
│   └── github_actions/
│       └── tasks/
│           └── main.yml                  # CI/CD setup
└── requirements.yml                      # Ansible Galaxy (optionnel)
```

### Fichier : `infra/ansible/inventory.yml`

```yaml
all:
  hosts:
    clickmart-prod:
      ansible_host: 172.239.20.14       # ← À remplacer par l'IP du VPS
      ansible_user: root
      ansible_ssh_private_key_file: ~/.ssh/id_ed25519
      ansible_ssh_common_args: -o StrictHostKeyChecking=accept-new
  vars:
    env: production
    domain: webtech-dev.info
```

### Fichier : `infra/ansible/requirements.yml`

```yaml
collections:
  - name: community.docker
    version: ">=3.0.0"
  - name: community.general
    version: ">=7.0.0"
```

---

## 4. Rôle docker

**Responsabilité** : installer Docker, Compose, Git, créer l'utilisateur `deploy`, configurer UFW.

### Fichier : `infra/ansible/roles/docker/tasks/main.yml`

```yaml
---
- name: Update apt cache
  apt:
    update_cache: yes
    cache_valid_time: 3600

- name: Install prerequisites
  apt:
    name:
      - ca-certificates
      - curl
      - git
      - ufw
    state: present

- name: Add Docker GPG key
  apt_key:
    url: https://download.docker.com/linux/ubuntu/gpg
    state: present

- name: Add Docker repository
  apt_repository:
    repo: "deb [arch=amd64] https://download.docker.com/linux/ubuntu {{ ansible_distribution_release }} stable"
    state: present
    update_cache: yes

- name: Install Docker packages
  apt:
    name:
      - docker-ce
      - docker-ce-cli
      - containerd.io
      - docker-compose-plugin
    state: present

- name: Start and enable Docker
  service:
    name: docker
    state: started
    enabled: yes

- name: Create deploy user
  user:
    name: deploy
    groups: docker
    shell: /bin/bash
    create_home: yes
    state: present

- name: Add SSH public key for deploy user
  authorized_key:
    user: deploy
    key: "{{ lookup('file', lookup('env','HOME') + '/.ssh/id_ed25519.pub') }}"
    state: present

- name: Configure UFW - allow SSH
  ufw:
    rule: allow
    port: 22
    proto: tcp

- name: Configure UFW - allow HTTP
  ufw:
    rule: allow
    port: 80
    proto: tcp

- name: Configure UFW - allow HTTPS
  ufw:
    rule: allow
    port: 443
    proto: tcp

- name: Enable UFW
  ufw:
    state: enabled
    policy: allow
    direction: outgoing
  # Ne pas activer 'deny incoming' ici — le firewall cloud gère ça

- name: Verify installations
  command: "{{ item }}"
  changed_when: no
  register: version_check
  loop:
    - docker --version
    - docker compose version
    - git --version

- name: Show versions
  debug:
    msg:
      - "Docker: {{ version_check.results[0].stdout }}"
      - "Compose: {{ version_check.results[1].stdout }}"
      - "Git: {{ version_check.results[2].stdout }}"
```

---

## 5. Rôle clickmart_app

**Responsabilité** : cloner le repo, générer le `.env.prod` depuis template, déployer avec Docker Compose.

### Fichier : `infra/ansible/roles/clickmart_app/tasks/main.yml`

```yaml
---
- name: Ensure /opt/clickmart directory exists
  file:
    path: /opt/clickmart
    state: directory
    owner: deploy
    group: deploy
    mode: 0755

- name: Clone repository
  git:
    repo: "https://github.com/tawounfouet/yt_django-clickmart-devops.git"
    dest: /opt/clickmart
    version: main
    force: yes
  become_user: deploy
  register: git_result

- name: Generate .env.prod from template
  template:
    src: .env.prod.j2
    dest: /opt/clickmart/backend/.envs/.prod
    owner: deploy
    group: deploy
    mode: 0600

- name: Copy docker-compose files
  copy:
    src: "{{ item }}"
    dest: "/opt/clickmart/{{ item }}"
    owner: deploy
    group: deploy
    mode: 0644
  loop:
    - docker-compose.yml
    - docker-compose.prod.yml

- name: Ensure .envs directory permissions
  file:
    path: /opt/clickmart/backend/.envs
    state: directory
    owner: deploy
    group: deploy
    mode: 0700

- name: Pull latest images
  community.docker.docker_compose_v2:
    project_src: /opt/clickmart
    files:
      - docker-compose.yml
      - docker-compose.prod.yml
    state: present
    pull: always
    build: never
  become_user: deploy
  register: compose_result

- name: Wait for containers to be healthy
  pause:
    seconds: 15

- name: Check running containers
  community.docker.docker_compose_v2:
    project_src: /opt/clickmart
    files:
      - docker-compose.yml
      - docker-compose.prod.yml
  register: compose_ps
  become_user: deploy

- name: Show container status
  debug:
    var: compose_ps.containers | map(attribute='Name') | list
```

### Fichier : `infra/ansible/roles/clickmart_app/templates/.env.prod.j2`

```jinja2
# ClickMart — Production environment
# Generated by Ansible — DO NOT EDIT MANUALLY

SECRET_KEY={{ secret_key }}
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS={{ domain }},www.{{ domain }},{{ ansible_default_ipv4.address }},localhost
CORS_ALLOWED_ORIGINS=https://{{ domain }},https://www.{{ domain }}

# Database
DATABASE_URL=postgres://{{ db_user }}:{{ db_password }}@{{ db_host }}:{{ db_port }}/{{ db_name }}?sslmode=require

# Celery (Redis)
CELERY_BROKER_URL=redis://:{{ redis_password }}@{{ redis_host }}:6379/0
CELERY_RESULT_BACKEND=redis://:{{ redis_password }}@{{ redis_host }}:6379/1

# Media storage
MEDIA_STORAGE_BACKEND={{ media_storage }}
{% if media_storage == 'cloudinary' %}
CLOUDINARY_CLOUD_NAME={{ cloudinary_cloud }}
CLOUDINARY_API_KEY={{ cloudinary_api_key }}
CLOUDINARY_API_SECRET={{ cloudinary_api_secret }}
{% endif %}

# Email
EMAIL_BACKEND_TYPE={{ email_backend }}
{% if email_backend == 'resend' %}
RESEND_API_KEY={{ resend_api_key }}
{% endif %}
DEFAULT_FROM_EMAIL=hello@{{ domain }}
ADMIN_EMAIL={{ admin_email }}
ADMIN_PASSWORD={{ admin_password }}

# Django REST Framework
CORS_ALLOW_CREDENTIALS=True
CSRF_TRUSTED_ORIGINS=https://{{ domain }},https://www.{{ domain }}
```

---

## 6. Rôle ssl_certbot

**Responsabilité** : configurer Certbot en Docker, obtenir les certificats, configurer Nginx en HTTPS.

### Fichier : `infra/ansible/roles/ssl_certbot/tasks/main.yml`

```yaml
---
- name: Verify DNS resolves to this server
  command: "dig +short {{ domain }}"
  delegate_to: localhost
  register: dns_result
  changed_when: no
  failed_when: dns_result.stdout != ansible_default_ipv4.address

- name: Check if certificates already exist
  stat:
    path: /opt/clickmart/infra/certbot/conf/live/{{ domain }}/fullchain.pem
  register: cert_file

- name: Obtain Let's Encrypt certificate
  community.docker.docker_container_exec:
    container: clickmart-certbot-1
    command: >
      certonly --webroot -w /var/www/certbot
      -d {{ domain }} -d www.{{ domain }}
      --email {{ admin_email }}
      --agree-tos --no-eff-email
  when: not cert_file.stat.exists
  register: cert_result
  ignore_errors: yes

- name: Fallback — run certbot once if container not running
  community.docker.docker_container:
    name: certbot-tmp
    image: certbot/certbot
    command: >
      certonly --webroot -w /var/www/certbot
      -d {{ domain }} -d www.{{ domain }}
      --email {{ admin_email }}
      --agree-tos --no-eff-email
    volumes:
      - /opt/clickmart/infra/certbot/conf:/etc/letsencrypt
      - /opt/clickmart/infra/certbot/www:/var/www/certbot
  when: cert_result is failed

- name: Enable HTTPS in Nginx config
  community.docker.docker_container_exec:
    container: clickmart-nginx-1
    command: nginx -s reload
  when: cert_file.stat.exists or cert_result is succeeded
```

---

## 7. Rôle github_actions

**Responsabilité** : configurer les secrets GitHub et le workflow CI/CD (optionnel).

### Fichier : `infra/ansible/roles/github_actions/tasks/main.yml`

```yaml
---
- name: Check GitHub CLI availability
  command: which gh
  delegate_to: localhost
  register: gh_check
  changed_when: no
  failed_when: no

- name: Check GitHub authentication
  command: gh auth status
  delegate_to: localhost
  register: gh_auth
  changed_when: no
  failed_when: no
  when: gh_check.rc == 0

- name: Set GitHub secrets
  command: >
    gh secret set {{ item.name }}
    --body "{{ item.value }}"
    --repo tawounfouet/yt_django-clickmart-devops
  delegate_to: localhost
  loop:
    - { name: VPS_HOST, value: "{{ ansible_host }}" }
    - { name: VPS_USER, value: "deploy" }
    - { name: VPS_SSH_KEY, value: "{{ lookup('file', lookup('env','HOME') + '/.ssh/id_ed25519') }}" }
  when: gh_check.rc == 0 and gh_auth.rc == 0

- name: Display CI/CD setup instructions
  debug:
    msg:
      - "GitHub Actions configuré si gh CLI était disponible."
      - "Sinon, ajouter manuellement les secrets :"
      - "  gh secret set VPS_HOST --body '{{ ansible_host }}'"
      - "  gh secret set VPS_USER --body 'deploy'"
      - "  gh secret set VPS_SSH_KEY --body '$(cat ~/.ssh/id_ed25519)'"
```

---

## 8. Variables et secrets

### Fichier : `infra/ansible/group_vars/all.yml` (non-sensible)

```yaml
---
# Infrastructure
ansible_user: root
env: production

# Domaine
domain: webtech-dev.info
admin_email: thomas.awounfouet@yahoo.com

# Base de données distante
db_host: 49.13.239.42
db_port: 5432
db_name: clickmart
db_user: postgres

# Redis distant
redis_host: 49.13.239.42

# Media storage
media_storage: cloudinary
email_backend: resend
```

### Fichier : `infra/ansible/group_vars/secrets.yml` (chiffré avec vault)

```yaml
---
secret_key: "SECRET_KEY_PLACEHOLDER"
db_password: "DB_PASSWORD_PLACEHOLDER"
redis_password: "REDIS_PASSWORD_PLACEHOLDER"

cloudinary_cloud: "dsrbll7qc"
cloudinary_api_key: "changeme"
cloudinary_api_secret: "4LbtgrinmMk..."

resend_api_key: "RESEND_KEY_PLACEHOLDER"
admin_password: "admin123"
```

Création :
```bash
ansible-vault create infra/ansible/group_vars/secrets.yml
ansible-vault edit infra/ansible/group_vars/secrets.yml
```

### Fichier : `infra/ansible/.gitignore`

```
group_vars/vault_password
group_vars/secrets.yml
*.retry
```

---

## 9. Playbook principal

### Fichier : `infra/ansible/deploy.yml`

```yaml
---
- name: Provision ClickMart server
  hosts: clickmart-prod
  become: yes
  vars_files:
    - group_vars/all.yml
    - group_vars/secrets.yml

  pre_tasks:
    - name: Gather facts
      setup:

    - name: Check minimum requirements
      assert:
        that:
          - ansible_memtotal_mb >= 960
          - ansible_distribution == "Ubuntu"
          - ansible_distribution_version is version("22.04", ">=")
        fail_msg: "Le serveur ne répond pas aux prérequis minimum (Ubuntu ≥ 22.04, RAM ≥ 960 MB)"

  roles:
    - role: docker
      tags: [docker, always]

    - role: clickmart_app
      tags: [app, always]

    - role: ssl_certbot
      tags: [ssl, optional]
      when: ssl_enabled | default(true)

    - role: github_actions
      tags: [cicd, optional]
      when: cicd_enabled | default(false)

  post_tasks:
    - name: Health check — frontend
      uri:
        url: "https://{{ domain }}/"
        status_code: 200
      register: health_frontend
      ignore_errors: yes

    - name: Health check — API
      uri:
        url: "https://{{ domain }}/api/v1/products/"
        status_code: 200
      register: health_api
      ignore_errors: yes

    - name: Display health results
      debug:
        msg:
          - "Frontend: {{ '✅ OK' if health_frontend.status == 200 else '❌ FAIL' }}"
          - "API:      {{ '✅ OK' if health_api.status == 200 else '❌ FAIL' }}"
          - "Domaine:  https://{{ domain }}"
```

---

## 10. Utilisation

### Installation des dépendances

```bash
pip install ansible
ansible-galaxy collection install community.docker community.general
```

### Déploiement complet

```bash
cd infra/ansible

# 1. Éditer l'inventory avec l'IP du VPS
vim inventory.yml

# 2. Créer les secrets (une seule fois)
ansible-vault create group_vars/secrets.yml

# 3. Lancer le playbook
ansible-playbook deploy.yml -i inventory.yml --ask-vault-pass
```

### Déploiement partiel (tags)

```bash
# Seulement Docker
ansible-playbook deploy.yml -i inventory.yml --tags docker

# Seulement l'application
ansible-playbook deploy.yml -i inventory.yml --tags app

# Ajouter SSL après coup
ansible-playbook deploy.yml -i inventory.yml --tags ssl

# Ajouter CI/CD après coup
ansible-playbook deploy.yml -i inventory.yml --tags cicd
```

### Sans vault (si l'utilisateur préfère)

```bash
# Copier les valeurs directement dans all.yml
ansible-playbook deploy.yml -i inventory.yml
```

---

## 11. Estimation d'effort

| Tâche | Fichiers | Effort |
|---|---|---|
| Structure + inventory + vars | `inventory.yml`, `group_vars/all.yml`, `.gitignore`, `requirements.yml` | 30 min |
| Rôle docker | `roles/docker/tasks/main.yml` | 30 min |
| Rôle clickmart_app | `roles/clickmart_app/tasks/main.yml` + `templates/.env.prod.j2` | 1h |
| Rôle ssl_certbot | `roles/ssl_certbot/tasks/main.yml` | 30 min |
| Rôle github_actions | `roles/github_actions/tasks/main.yml` | 20 min |
| Playbook principal | `deploy.yml` | 30 min |
| Secrets vault | `group_vars/secrets.yml` | 15 min |
| **Total** | **~10 fichiers** | **~3h30** |

> Comparatif avec l'analyse initiale : l'effort Terraform (2h) est supprimé car l'utilisateur provisionne lui-même. Le scope Ansible est identique à la Phase 2 de l'analyse (4h) mais réduit à ~3h30 grâce à une meilleure isolation des fichiers.

---

## A. Annexe — Documentation Ansible pour l'utilisateur

### A.1 Structure des commandes

```bash
# Ping de test
ansible all -i inventory.yml -m ping

# Afficher les facts du serveur
ansible all -i inventory.yml -m setup

# Exécuter une commande ad-hoc
ansible all -i inventory.yml -m shell -a "docker ps"
```

### A.2 Installation Ansible

```bash
# macOS
brew install ansible

# Ubuntu/Debian
sudo apt update && sudo apt install -y ansible

# pip (toute plateforme)
python3 -m pip install --user ansible ansible-lint

# Vérification
ansible --version
```

### A.3 Gestion du vault

```bash
# Créer un fichier vault
ansible-vault create group_vars/secrets.yml

# Éditer
ansible-vault edit group_vars/secrets.yml

# Voir le contenu déchiffré
ansible-vault view group_vars/secrets.yml

# Changer le mot de passe
ansible-vault rekey group_vars/secrets.yml
```

### A.4 Multi-environnements

```yaml
# inventory.yml — version complète
all:
  children:
    production:
      hosts:
        clickmart-prod:
          ansible_host: 172.239.20.14
      vars:
        env: production
        domain: webtech-dev.info
        ssl_enabled: true
        cicd_enabled: true

    staging:
      hosts:
        clickmart-staging:
          ansible_host: 203.0.113.10
      vars:
        env: staging
        domain: stg.webtech-dev.info
        ssl_enabled: false
        cicd_enabled: false
```

```bash
# Déploiement staging
ansible-playbook deploy.yml -i inventory.yml --limit staging

# Déploiement production
ansible-playbook deploy.yml -i inventory.yml --limit production
```

---

*Plan créé le 30 juillet 2026 — basé sur docs/analyse/2026-07-29_ANALYSE_TERRAFORM_ANSIBLE.md*

---

## B. Journal d'implémentation

| Date | Étape | Statut |
|---|---|---|
| 30/07/2026 | Création des 11 fichiers Ansible | ✅ |
| 30/07/2026 | Syntax check + --check mode | ✅ |
| 30/07/2026 | Test SSH + sudo sur prod | ✅ |
| 30/07/2026 | Fix conflit signed-by Docker repo | ✅ |
| 30/07/2026 | Fix include_vars (delegate_to localhost + become:no) | ✅ |
| 30/07/2026 | Ajout passwordless sudo pour deploy user | ✅ |
| 30/07/2026 | Ajout docker login ghcr.io (token via gh CLI) | ✅ |
| 30/07/2026 | Création template bootstrap SSL (prod.bootstrap.conf.j2) | ✅ |
| 30/07/2026 | Fix SSL bootstrap (HTTP → Certbot → HTTPS) | ✅ |
| 30/07/2026 | From-scratch validation (VPS vierge → HTTPS < 3 min) | ✅ |
