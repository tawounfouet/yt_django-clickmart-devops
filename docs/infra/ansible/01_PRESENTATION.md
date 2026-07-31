# 1. Présentation — Ansible ClickMart

> **Mise à jour** : 30 juillet 2026

---

## Objectif

Provisionner un VPS vierge → application ClickMart fonctionnelle en HTTPS, **sans intervention manuelle**, via un playbook Ansible unique.

---

## Périmètre

| Fait par Ansible | Pas fait par Ansible |
|---|---|
| Configuration du serveur (Docker, app, SSL, CI/CD) | Provisionnement du VPS (Linode, IONOS, AWS, etc.) |
| Installation Docker + Compose + Git + UFW | Création du serveur / réservation d'IP |
| Déploiement de l'application (clone, .env, up) | Configuration DNS |
| Certificats Let's Encrypt | Firewall cloud (ports 22, 80, 443) |
| Secrets GitHub Actions pour CI/CD | |
| Multi-environnement (production + staging, même VPS) | |

---

## Principe

```
Utilisateur                    Ansible                         Serveur cible
    │                             │                                │
    │  1. Crée le VPS             │                                │
    │     (clé SSH ajoutée)       │                                │
    │                             │                                │
    │  2. Renseigne l'IP          │                                │
    │     dans inventory.yml      │                                │
    │                             │                                │
    │  3. ansible-playbook ──────▶│  docker          ────────────▶ Docker + Compose + Git
    │     --limit clickmart-prod  │  clickmart_app   ────────────▶ Clone + .env + up
    │     --limit clickmart-stg   │  ssl_certbot     ────────────▶ Certificats HTTPS (prod only)
    │                             │  github_actions  ────────────▶ Secrets CI/CD
    │                             │                                │
    │  4. Site dispo ────────────▶│  https://webtech-dev.info     │
    │                             │  http://staging:8080          │
```

---

## Environnements

| Environnement | Host | Domaine | Port | SSL |
|---|---|---|---|---|
| Production | `clickmart-prod` | `webtech-dev.info` | 80/443 | ✅ |
| Staging | `clickmart-staging` | `staging.webtech-dev.info` | 8080 | ❌ |

Même playbook, variables différentes par host (`app_dir`, `compose_files`, `project_name`, `branch`, `ssl_enabled`). Déploiement ciblé via `--limit`.

---

## Environnement cible

| Élément | Détail |
|---|---|
| OS serveur | Ubuntu 24.04 (≥ 22.04 accepté) |
| RAM minimum | 960 MB (2 Go recommandé pour prod + staging) |
| Disque minimum | 25 GB |
| Services | Docker 28.x, Compose v2, PostgreSQL 16, Redis 7 |
| Domaines | `webtech-dev.info` + `www.webtech-dev.info` |
| Conteneurs | backend, celery-worker, celery-beat, frontend, nginx, certbot |

---

## Architecture du playbook

```
infra/ansible/
├── inventory.yml                    # Inventaire des serveurs
├── deploy.yml                       # Playbook principal
├── group_vars/
│   ├── all.yml                      # Variables non-sensibles (publiques)
│   └── secrets.yml                  # Variables sensibles (gitignorées, optionnel chiffré)
├── roles/
│   ├── docker/                      # Installation et configuration Docker
│   ├── clickmart_app/               # Déploiement de l'application
│   ├── ssl_certbot/                 # Certificats Let's Encrypt
│   └── github_actions/              # Configuration CI/CD
└── README.md
```
