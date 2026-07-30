# 9. Dépannage — Ansible ClickMart

> **Mise à jour** : 30 juillet 2026

---

## Problèmes connus et solutions

### Connexion SSH

| Erreur | Cause | Solution |
|---|---|---|
| `Permission denied (publickey)` | Mauvaise clé SSH ou user incorrect | Vérifier `ansible_user` (root vs deploy) et `ansible_ssh_private_key_file` |
| `UNREACHABLE: Failed to connect` | IP incorrecte ou SSH éteint | `ssh root@<IP>` manuellement, vérifier le firewall cloud |

### Docker

| Erreur | Cause | Solution |
|---|---|---|
| `NO_PUBKEY 7EA0A9C3F273FCD8` | Clé GPG Docker absente du keyring | Le rôle nettoie et télécharge la clé automatiquement |
| `Conflicting values set for option Signed-By` | Deux fichiers `.list` avec/sans `signed-by` | Le rôle supprime les fichiers en conflit avant d'ajouter le repo |
| `docker.service: Unit not found` | Docker non installé | Relancer `--tags docker` |
| `Permission denied /var/run/docker.sock` | User non membre du groupe `docker` | Le rôle ajoute `deploy` au groupe `docker`, nécessite re-login |
| `error from registry: denied` (ghcr.io) | Token expiré ou invalide | `gh auth token` sur le contrôleur, mettre à jour `secrets.yml` |

### SSL / Nginx

| Erreur | Cause | Solution |
|---|---|---|
| `cannot load certificate` (nginx container exit 1) | Certificats absents, Nginx ne démarre pas | Relancer `--tags ssl` → le bootstrap HTTP gère ce cas |
| `Connection refused` sur le port 443 | Nginx n'écoute pas | Vérifier UFW, firewall cloud, relancer `--tags ssl` |
| `Connection timed out` sur HTTP/HTTPS | Firewall cloud bloque le port | Ouvrir 22, 80, 443 dans la console du cloud provider |
| `dig +short` ne répond pas l'IP attendue | DNS non configuré ou pas propagé | `dig webtech-dev.info A`, attendre la propagation DNS |

### Application

| Erreur | Cause | Solution |
|---|---|---|
| Django 500 | .env mal configuré | Vérifier `/opt/clickmart/backend/.envs/.prod`, relancer `--tags app` |
| Database connection refused | PostgreSQL injoignable | Vérifier `db_host`, `db_password`, firewall PostgreSQL |
| Celery worker crash | Redis injoignable | Vérifier `redis_host`, `redis_password` |

### Ansible / Playbook

| Erreur | Cause | Solution |
|---|---|---|
| `sudo: a password is required` | Tâche déléguée à localhost avec `become: yes` | Ajouter `become: no` à la tâche (déjà fait dans le playbook) |
| `The task includes an option with an undefined variable` | Variable non définie | Vérifier `all.yml` et `secrets.yml` |
| `file not found: secrets.yml` | Le fichier n'existe pas sur le serveur | C'est normal — le playbook utilise `delegate_to: localhost` pour le charger |

---

## Commandes de diagnostic

### Ansible

```bash
# Ping
ansible all -i inventory.yml -m ping

# Facts (infos système)
ansible all -i inventory.yml -m setup | head -50
ansible all -i inventory.yml -m setup | grep -E 'ansible_distribution|ansible_memtotal'

# Syntaxe
ansible-playbook deploy.yml -i inventory.yml --syntax-check

# Dry-run avec diff
ansible-playbook deploy.yml -i inventory.yml --check --diff

# Limiter à un hôte
ansible-playbook deploy.yml -i inventory.yml --limit clickmart-prod

# Voir les variables compilées
ansible all -i inventory.yml -m setup -a "gather_subset=!all,!min" > /dev/null
ansible all -i inventory.yml -m debug -a "var=domain"
```

### Docker sur le serveur

```bash
ssh deploy@172.239.20.14 "

# État des conteneurs
docker compose -p clickmart ps

# Logs
docker compose -p clickmart logs --tail 30
docker logs clickmart-backend-1 --tail 50
docker logs clickmart-nginx-1 --tail 50

# Redémarrage
docker compose -p clickmart restart backend
docker compose -p clickmart up -d --force-recreate backend

# Images
docker compose -p clickmart images
docker system df
"
```

### Santé application

```bash
# HTTP
curl -I https://webtech-dev.info/
curl -I http://webtech-dev.info/

# API
curl https://webtech-dev.info/api/v1/products/

# Admin
curl -I https://webtech-dev.info/admin/
```
