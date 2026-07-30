# Documentation Ansible — ClickMart

> Mise à jour : 30 juillet 2026
> Playbook from-scratch validé sur Linode Ubuntu 24.04

---

## Index

| N° | Fichier | Contenu |
|---|---|---|
| 1 | [01_PRESENTATION.md](01_PRESENTATION.md) | Objectif, périmètre, architecture du playbook |
| 2 | [02_INSTALLATION.md](02_INSTALLATION.md) | Prérequis, installation Ansible, dépendances |
| 3 | [03_CONFIGURATION.md](03_CONFIGURATION.md) | Inventory, variables all.yml, secrets, vault |
| 4 | [04_DEPLOIEMENT.md](04_DEPLOIEMENT.md) | Tags, premier run, re-déploiement, check mode |
| 5 | [05_ROLE_DOCKER.md](05_ROLE_DOCKER.md) | Installation Docker + Compose + UFW + deploy user |
| 6 | [06_ROLE_APP.md](06_ROLE_APP.md) | Clone, template .env, docker compose up |
| 7 | [07_ROLE_SSL.md](07_ROLE_SSL.md) | Bootstrap HTTP → Certbot → HTTPS |
| 8 | [08_ROLE_CICD.md](08_ROLE_CICD.md) | Secrets GitHub Actions |
| 9 | [09_DEPANNAGE.md](09_DEPANNAGE.md) | Problèmes connus, diagnostic, logs |
| 10 | [10_REFERENCE.md](10_REFERENCE.md) | Cheat sheet, fichiers, checklist, variables |

---

## Démarrage rapide

```bash
cd infra/ansible

# 1. Configurer
cp group_vars/secrets.yml.example group_vars/secrets.yml
vim inventory.yml          # → IP + ansible_user: root (VPS vierge)

# 2. Lancer
ansible-playbook deploy.yml -i inventory.yml

# 3. Après premier run
#    inventory.yml → ansible_user: deploy
```

Plus de détails → [04_DEPLOIEMENT.md](04_DEPLOIEMENT.md)

---

## Fichiers du projet

```
infra/ansible/
├── inventory.yml
├── deploy.yml
├── group_vars/
│   ├── all.yml
│   └── secrets.yml
├── roles/
│   ├── docker/
│   ├── clickmart_app/
│   ├── ssl_certbot/
│   └── github_actions/
└── README.md
```

Voir aussi : [Plan d'implémentation](../../plans/PLAN_ANSIBLE.md)
