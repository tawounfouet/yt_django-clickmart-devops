# 10. Référence — Ansible ClickMart

> **Mise à jour** : 30 juillet 2026

---

## Fichiers créés

| Fichier | Rôle |
|---|---|
| `infra/ansible/inventory.yml` | Hosts — IP, connexion SSH, domain |
| `infra/ansible/deploy.yml` | Playbook principal (37 tasks) |
| `infra/ansible/requirements.yml` | Dépendances Ansible Galaxy |
| `infra/ansible/.gitignore` | Exclusion secrets.yml + `.retry` |
| `infra/ansible/group_vars/all.yml` | Variables non-sensibles (26 lignes) |
| `infra/ansible/group_vars/secrets.yml` | Secrets (16 lignes, gitignoré) |
| `infra/ansible/roles/docker/tasks/main.yml` | Installation Docker (126 lignes) |
| `infra/ansible/roles/clickmart_app/tasks/main.yml` | Déploiement app (62 lignes) |
| `infra/ansible/roles/clickmart_app/templates/.env.prod.j2` | Template .env (23 lignes) |
| `infra/ansible/roles/ssl_certbot/tasks/main.yml` | Certificats SSL (100 lignes) |
| `infra/ansible/roles/ssl_certbot/templates/prod.bootstrap.conf.j2` | Nginx HTTP bootstrap (44 lignes) |
| `infra/ansible/roles/github_actions/tasks/main.yml` | Secrets CI/CD (38 lignes) |
| `infra/ansible/README.md` | README opérationnel (80 lignes) |
| `docs/infra/ansible/` | **Cette documentation** (10 fichiers) |

---

## Commands cheat sheet

```bash
# === Installation ===
ansible-galaxy collection install community.docker

# === Déploiement ===
ansible-playbook deploy.yml -i inventory.yml                           # Complet
ansible-playbook deploy.yml -i inventory.yml --tags docker             # Docker seul
ansible-playbook deploy.yml -i inventory.yml --tags app                # App seule
ansible-playbook deploy.yml -i inventory.yml --tags ssl                # SSL seul
ansible-playbook deploy.yml -i inventory.yml --tags cicd               # CI/CD seul
ansible-playbook deploy.yml -i inventory.yml --ask-vault-pass          # Avec vault
ansible-playbook deploy.yml -i inventory.yml --check                   # Dry-run
ansible-playbook deploy.yml -i inventory.yml --check --diff            # Dry-run + diffs
ansible-playbook deploy.yml -i inventory.yml --syntax-check            # Syntaxe
ansible-playbook deploy.yml -i inventory.yml --limit clickmart-prod    # Un seul hôte

# === Diagnostic ===
ansible all -i inventory.yml -m ping
ansible all -i inventory.yml -m setup
ansible all -i inventory.yml -m shell -a "docker ps"
ansible all -i inventory.yml -m shell -a "free -h"
ansible all -i inventory.yml -m shell -a "df -h /"
ansible all -i inventory.yml -m shell -a "uptime"

# === Vault ===
ansible-vault encrypt group_vars/secrets.yml
ansible-vault decrypt group_vars/secrets.yml
ansible-vault view group_vars/secrets.yml
```

---

## Variables Jinja2 disponibles dans les templates

| Variable | Source | Exemple |
|---|---|---|
| `{{ domain }}` | inventory → group_vars | `webtech-dev.info` |
| `{{ ansible_facts.default_ipv4.address }}` | `setup` module | `172.239.20.14` |
| `{{ ansible_facts.distribution_release }}` | `setup` module | `noble` |
| `{{ secret_key }}` | secrets.yml → vault | `SECRET_KEY_PLACEHOLDER` |
| `{{ db_password }}` | secrets.yml → vault | `DB_PASSWORD_PLACEHOLDER` |
| `{{ redis_password }}` | secrets.yml → vault | `REDIS_PASSWORD_PLACEHOLDER` |
| `{{ cloudinary_api_key }}` | secrets.yml → vault | `CLOUDINARY_KEY_PLACEHOLDER` |
| `{{ resend_api_key }}` | secrets.yml → vault | `re_YRep...` |
| `{{ github_token }}` | secrets.yml → vault | `GITHUB_TOKEN_PLACEHOLDER` |
| `{{ admin_email }}` | all.yml | `thomas...` |

---

## Structure des conteneurs en production

```
docker compose ps (production)
┌───────────────────┬──────────────────────────────┐
│ backend           │ ghcr.io/.../clickmart-backend │
│ celery-worker     │ ghcr.io/.../clickmart-backend │
│ celery-beat       │ ghcr.io/.../clickmart-backend │
│ frontend          │ ghcr.io/.../clickmart-frontend│
│ nginx             │ nginx:alpine                  │
│ certbot           │ certbot/certbot               │
└───────────────────┴──────────────────────────────┘
```

---

## Checklist from-scratch

- [ ] VPS créé chez le fournisseur (Linode, IONOS, DigitalOcean...)
- [ ] Clé SSH ajoutée (`~/.ssh/id_rsa.pub`)
- [ ] Ports 22, 80, 443 ouverts dans le firewall cloud
- [ ] `inventory.yml` : `ansible_host` = IP, `ansible_user: root`
- [ ] `secrets.yml` : valeurs renseignées
- [ ] Token GitHub valide (si ghcr.io privé)
- [ ] Collection docker installée

```bash
cd infra/ansible
ansible-playbook deploy.yml -i inventory.yml
```

- [ ] `inventory.yml` : passer à `ansible_user: deploy`
- [ ] (Optionnel) `ansible-vault encrypt group_vars/secrets.yml`
- [ ] Vérifier https://webtech-dev.info/
- [ ] Vérifier https://webtech-dev.info/api/v1/products/

---

## Ressources externes

- [Documentation Ansible](https://docs.ansible.com/)
- [Collection community.docker](https://docs.ansible.com/ansible/latest/collections/community/docker/)
- [Jinja2 template designer](https://jinja.palletsprojects.com/)
- [Certbot documentation](https://eff-certbot.readthedocs.io/)
