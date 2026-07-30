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
    │                             │  clickmart_app   ────────────▶ Clone + .env + up
    │                             │  ssl_certbot     ────────────▶ Certificats HTTPS
    │                             │  github_actions  ────────────▶ Secrets CI/CD
    │                             │                                │
    │  4. Site dispo ────────────▶│                                │
```

---

## Environnement cible

| Élément | Détail |
|---|---|
| OS serveur | Ubuntu 24.04 (≥ 22.04 accepté) |
| RAM minimum | 960 MB |
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
