# 4. Déploiement — Ansible ClickMart

> **Mise à jour** : 30 juillet 2026

---

## 4.1 Tags disponibles

| Tag | Rôle concerné | Couverture |
|---|---|---|
| `docker` | docker | Installation Docker + Compose + UFW |
| `app` | clickmart_app | Clone + .env + docker compose up |
| `ssl` | ssl_certbot | Certificats Let's Encrypt |
| `cicd` | github_actions | Secrets GitHub Actions |
| `always` | docker, app | Inclus même si `--tags` spécifié |

---

## 4.2 Premier déploiement (VPS vierge)

```bash
# 1. Éditer inventory.yml
#    - Renseigner ansible_host (IP du VPS)
#    - Décommenter ansible_user: root
#    - Commenter ansible_user: deploy

# 2. Vérifier la configuration
ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --syntax-check

# 3. Dry-run (optionnel)
ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --check

# 4. Lancer
ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml

# 5. Après succès
#    - inventory.yml : commenter root, décommenter deploy
#    - (Optionnel) ansible-vault encrypt group_vars/secrets.yml
```

**Durée** : ~3 minutes (Docker + pull images + Certbot).

**Ordre d'exécution** : `pre_tasks` → `docker` → `clickmart_app` → `ssl_certbot` → `github_actions` → `post_tasks`.

---

## 4.3 Re-déploiement (serveur existant)

```bash
# Production
ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --limit clickmart-prod

# Staging
ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --limit clickmart-staging
```

Le playbook est **idempotent** : si tout est à jour, rien n'est modifié. Le `--limit` permet de cibler un environnement spécifique.

---

## 4.4 Déploiement partiel par tags

```bash
# Mise à jour de l'application uniquement (production)
ansible-playbook deploy.yml -i inventory.yml --limit clickmart-prod --tags app

# Déployer staging
ansible-playbook deploy.yml -i inventory.yml --limit clickmart-staging --tags docker,app

# Ajouter SSL (production uniquement, ignoré en staging)
ansible-playbook deploy.yml -i inventory.yml --limit clickmart-prod --tags ssl
```

---

## 4.5 Déploiement avec vault

```bash
ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --ask-vault-pass
```

---

## 4.6 Simulation (check mode)

```bash
ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --check
ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --check --diff
```

---

## 4.7 Santé post-déploiement

Le playbook exécute automatiquement deux health-checks après le déploiement :

```yaml
post_tasks:
  - name: Health check — frontend
    uri:
      url: "https://{{ domain }}/"
      status_code: [200, 301, 302]

  - name: Health check — API
    uri:
      url: "https://{{ domain }}/api/v1/products/"
      status_code: [200, 301, 302]
```

Les résultats s'affichent en fin de run :

```
Frontend: OK
API:      OK
Domaine:  https://webtech-dev.info
```

Vérification manuelle complémentaire :

```bash
ssh deploy@172.239.20.14 "docker compose -p clickmart ps"
ssh deploy@172.239.20.14 "docker compose -p clickmart logs --tail 10"
curl -I https://webtech-dev.info/
```

---

## 4.8 Checklist from-scratch

- [ ] VPS créé chez le fournisseur
- [ ] Clé SSH ajoutée (`~/.ssh/id_rsa.pub`)
- [ ] Ports 22, 80, 443 ouverts dans le firewall cloud
- [ ] `inventory.yml` : `ansible_host` = IP, `ansible_user: root`
- [ ] `secrets.yml` : valeurs renseignées
- [ ] Token GitHub valide (si ghcr.io privé)
- [ ] Collection docker installée
- [ ] Lancer `deploy.yml` → vérifier le health-check
- [ ] Passer à `ansible_user: deploy` dans l'inventory
