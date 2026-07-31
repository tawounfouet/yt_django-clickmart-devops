# Plan d'implémentation — Agent de déploiement Fullstack

> Création d'un agent autonome pour déployer Django + React sur n'importe quel VPS
> Basé sur l'analyse de faisabilité : `.github/agents/ANALYSE_FAISABILITE.md`

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [MVP V1 — Déploiement HTTP (prioritaire)](#2-mvp-v1--déploiement-http-prioritaire)
3. [V2 — SSL + Domaine](#3-v2--ssl--domaine)
4. [V3 — Multi-fournisseurs](#4-v3--multi-fournisseurs)
5. [Structure finale des fichiers](#5-structure-finale-des-fichiers)

---

## 1. Vue d'ensemble

```
V1 (HTTP)          V2 (SSL)           V3 (Multi-cloud)
─────2h─────       ───1h30───          ────2h────
■■■■■■■■■■■       ■■■■■■■■■           ■■■■■■■■■■

SEMAINE 1           SEMAINE 1           SEMAINE 2
```

| Version | Livrable | Durée | Priorité |
|---|---|---|---|
| V1 | Déploiement HTTP sans domaine | ~2h | 🔴 MVP |
| V2 | SSL + domaine + DNS | ~1h30 | 🟠 Important |
| V3 | Multi-fournisseurs + détection OS | ~2h | 🟡 Confort |

---

## 2. MVP V1 — Déploiement HTTP (prioritaire)

**Objectif** : prendre un VPS vierge (IP + credentials SSH) → app fonctionnelle en HTTP

### 2.1 Fichiers à créer

| Fichier | Rôle | Temps estimé |
|---|---|---|
| `.github/agents/deploy-fullstack.yml` | Définition de l'agent | 15 min |
| `.github/instructions/deploy-fullstack.md` | Instructions principales | 20 min |
| `.github/skills/ssh-connect.md` | Connexion SSH + détection OS | 10 min |
| `.github/skills/docker-install.md` | Installation Docker + Compose + Git | 15 min |
| `.github/skills/project-deploy.md` | Clone + .env + docker compose up | 20 min |
| `.github/skills/health-check.md` | Vérification post-déploiement | 10 min |
| `.github/skills/github-cicd.md` | Configuration CI/CD basique | 15 min |
| `.github/skills/env-generator.md` | Génération des fichiers .env | 10 min |
| `.github/skills/firewall-guide.md` | Instructions firewall cloud | 10 min |

### 2.2 Contenu de chaque fichier

#### `.github/agents/deploy-fullstack.yml`

```yaml
name: deploy-fullstack
description: >
  Déploie un projet Django + React (Docker Compose) sur un VPS vierge.
  Supporte Ubuntu 22.04/24.04. Nécessite les credentials SSH du serveur.

temperature: 0.2
tools:
  - bash
  - read
  - write
  - edit
  - glob
  - grep
  - task
  - question

phases:
  - name: server-setup
    instruction: phase-1-server-setup
    skills:
      - ssh-connect
      - docker-install
    mandatory: true

  - name: code-deploy
    instruction: phase-2-code-deploy
    skills:
      - env-generator
      - project-deploy
      - health-check
    mandatory: true

  - name: cicd
    instruction: phase-3-cicd
    skills:
      - github-cicd
    mandatory: false

  - name: ssl
    instruction: phase-4-ssl
    skills:
      - ssl-setup
    mandatory: false

checkpoints:
  - after: server-setup
    action: "Vérifier que Docker est installé et que les ports sont ouverts"
  - after: code-deploy
    action: "Vérifier que l'app répond sur http://<IP>"
  - after: cicd
    action: "Vérifier que le pipeline GitHub Actions passe"
```

#### `.github/instructions/deploy-fullstack.md`

```markdown
# Instructions : Déploiement Fullstack

## Quand m'activer

L'utilisateur veut déployer un projet Django + React sur un VPS.
Il me donne une IP + des credentials SSH. J'exécute les phases dans l'ordre.

## Règles

1. **Idempotence** : chaque étape peut être rejouée sans effet de bord
2. **Points d'arrêt** : ne pas continuer si une étape critique échoue
3. **Vérification** : après chaque phase, valider le succès
4. **Phases optionnelles** : CI/CD et SSL peuvent être sautés si l'utilisateur le demande
5. **Ne jamais supposer** : toujours vérifier l'état avant d'agir

## Entrées utilisateur

- `VPS_IP` : adresse IP du serveur
- `VPS_USER` : utilisateur SSH (root par défaut)
- `SSH_KEY_PATH` : chemin vers la clé privée SSH (~/.ssh/id_rsa par défaut)
- `REPO_URL` : URL du dépôt Git à déployer (détecté automatiquement si dans un repo)
- `PROJECT_NAME` : nom du projet (détecté depuis le repo)

## Déroulement

### Phase 1 : Préparation serveur
- Charger le skill `ssh-connect`
- Charger le skill `docker-install`
- ⏸️ Point d'arrêt : faire ouvrir les ports 80/443 par l'utilisateur

### Phase 2 : Déploiement
- Charger le skill `env-generator`
- Charger le skill `project-deploy`
- Charger le skill `health-check`

### Phase 3 : CI/CD (optionnel)
- Charger le skill `github-cicd`

### Phase 4 : SSL (optionnel)
- Charger le skill `ssl-setup`
```

#### `.github/skills/ssh-connect.md`

```markdown
# Skill: ssh-connect

## Prérequis
- IP du serveur connue
- Clé SSH disponible localement

## Procédure

1. Tester la connexion SSH
   ```bash
   ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no <USER>@<IP> "echo OK"
   ```

2. Détecter l'OS
   ```bash
   ssh <USER>@<IP> "cat /etc/os-release | grep -E '^NAME=|^VERSION_ID='"
   ```

3. Vérifier les ressources
   ```bash
   ssh <USER>@<IP> "free -h && df -h / && nproc"
   ```

## Résultat attendu
```
SSH: OK
OS: Ubuntu 24.04
RAM: >1GB, DISK: >10GB, CPU: >1
```

## Fallback
Si SSH échoue : vérifier la clé, le user, l'IP. Demander à l'utilisateur.
Si OS non supporté : proposer de continuer mais avertir des risques.
Si ressources insuffisantes : avertir et demander confirmation.
```

#### `.github/skills/docker-install.md`

```markdown
# Skill: docker-install

## Prérequis
- SSH fonctionnel
- OS Ubuntu/Debian

## Procédure

1. Mettre à jour les paquets
   ```bash
   ssh <USER>@<IP> "apt update && apt upgrade -y"
   ```

2. Installer Git si absent
   ```bash
   ssh <USER>@<IP> "which git || apt install -y git"
   ```

3. Installer Docker via le script officiel
   ```bash
   ssh <USER>@<IP> "curl -fsSL https://get.docker.com | sh"
   ```

4. Installer le plugin Docker Compose
   ```bash
   ssh <USER>@<IP> "apt install -y docker-compose-plugin"
   ```

5. Vérifier les versions
   ```bash
   ssh <USER>@<IP> "docker --version && docker compose version && git --version"
   ```

## Résultat attendu
```
Docker version 2x.x.x
Docker Compose version v2.x.x
git version 2.x.x
```

## Fallback
Si Docker déjà installé : vérifier la version, proposer de continuer.
Si échec d'installation : afficher l'erreur, proposer des solutions.
```

#### `.github/skills/project-deploy.md`

```markdown
# Skill: project-deploy

## Prérequis
- Serveur prêt (Docker + Git)
- Fichiers .env générés (skill env-generator)
- Repo Git accessible

## Procédure

1. Créer le répertoire de déploiement
   ```bash
   ssh <USER>@<IP> "mkdir -p /opt/<PROJECT_NAME>"
   ```

2. Cloner le repo
   ```bash
   ssh <USER>@<IP> "git clone <REPO_URL> /opt/<PROJECT_NAME>"
   ```

3. Copier/transférer les fichiers d'infrastructure si gitignorés
   ```bash
   # Vérifier si Dockerfiles sont gitignorés
   git check-ignore backend/Dockerfile 2>/dev/null && NEED_SCP=true

   # Si oui, les copier via SCP
   [ "$NEED_SCP" = true ] && scp backend/Dockerfile <USER>@<IP>:/opt/<PROJECT_NAME>/backend/
   [ "$NEED_SCP" = true ] && scp frontend/Dockerfile <USER>@<IP>:/opt/<PROJECT_NAME>/frontend/
   [ "$NEED_SCP" = true ] && scp docker-compose.yml <USER>@<IP>:/opt/<PROJECT_NAME>/
   ```

4. Transférer les fichiers .env
   ```bash
   scp backend/.env.docker <USER>@<IP>:/opt/<PROJECT_NAME>/backend/
   scp backend/.env.production <USER>@<IP>:/opt/<PROJECT_NAME>/backend/
   ```

5. Lancer Docker Compose
   ```bash
   ssh <USER>@<IP> "cd /opt/<PROJECT_NAME> && docker compose up --build -d"
   ```

6. Vérifier que les containers tournent
   ```bash
   ssh <USER>@<IP> "cd /opt/<PROJECT_NAME> && docker compose ps"
   ```

## Résultat attendu
```
4-5 containers avec le statut "Up"
```

## Fallback
Si git clone échoue : vérifier l'URL, proposer HTTPS avec token.
Si docker compose échoue : afficher les logs, diagnostiquer.
Si containers "Exited" : afficher docker logs, proposer des corrections.
```

#### `.github/skills/health-check.md`

```markdown
# Skill: health-check

## Prérequis
- docker compose up terminé

## Procédure

1. Attendre le démarrage (15-20s)
2. Vérifier les containers
   ```bash
   ssh <USER>@<IP> "cd /opt/<PROJECT_NAME> && docker compose ps"
   ```
3. Tester le frontend
   ```bash
   curl -s -o /dev/null -w '%{http_code}' http://<IP>/
   ```
4. Tester l'API
   ```bash
   curl -s -o /dev/null -w '%{http_code}' http://<IP>/api/v1/products/
   ```
5. Tester l'admin
   ```bash
   curl -s -o /dev/null -w '%{http_code}' http://<IP>/admin/
   ```
6. Vérifier les logs backend
   ```bash
   ssh <USER>@<IP> "cd /opt/<PROJECT_NAME> && docker compose logs backend --tail=20"
   ```

## Résultat attendu
```
Frontend  : HTTP 200
API       : HTTP 200
Admin     : HTTP 200
Backend   : no errors in logs
```

## Fallback
Si 502/503 : backend pas prêt, attendre 30s et réessayer.
Si 404 : vérifier les routes, la config nginx.
Si connexion refusée : docker compose ps, vérifier les ports.
```

#### `.github/skills/env-generator.md`

```markdown
# Skill: env-generator

## Prérequis
- Repo cloné localement
- IP du serveur connue
- SECRET_KEY à générer

## Procédure

1. Détecter le .env.example du projet
   ```bash
   ls backend/.env.example 2>/dev/null || echo "Pas de .env.example"
   ```

2. Générer une SECRET_KEY
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

3. Créer backend/.env.docker
   ```
   SECRET_KEY=<généré>
   DEBUG=True
   DB_NAME=<project>_db
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_HOST=db
   DB_PORT=5432
   ALLOWED_HOSTS=<IP>,localhost,127.0.0.1,backend
   CORS_ALLOWED_ORIGINS=http://<IP>,http://localhost:5173
   EMAIL_HOST_USER=test@test.com
   EMAIL_HOST_PASSWORD=test
   ```

4. Créer backend/.env.production
   ```
   POSTGRES_DB=<project>_db
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   ```

## Résultat
Deux fichiers .env créés localement, prêts à être SCP vers le serveur.
```

#### `.github/skills/github-cicd.md`

```markdown
# Skill: github-cicd

## Prérequis
- gh CLI configuré (gh auth status)
- Application déployée et fonctionnelle
- Clé SSH privée disponible

## Procédure

1. Créer le workflow GitHub Actions
   → Fichier : .github/workflows/deploy.yml
   → Template : 3 jobs (test-backend, test-frontend, deploy)

2. Ajouter les secrets GitHub
   ```bash
   gh secret set VPS_HOST -b "<IP>" -R <REPO>
   gh secret set VPS_USER -b "<USER>" -R <REPO>
   gh secret set VPS_SSH_KEY -b "$(cat ~/.ssh/id_rsa)" -R <REPO>
   ```

3. Vérifier le workflow
   ```bash
   git add .github/workflows/deploy.yml
   git commit -m "ci: add deployment pipeline"
   git push origin main
   gh run watch -R <REPO>
   ```

## Résultat attendu
Pipeline GitHub Actions fonctionnel.
Push sur main → tests → déploiement automatique.
```

#### `.github/skills/firewall-guide.md`

```markdown
# Skill: firewall-guide

## Quand l'utiliser

Après l'installation de Docker, avant le déploiement.
L'agent ne peut pas configurer le firewall cloud sans token API.

## Procédure

1. Détecter le fournisseur VPS
   ```bash
   # Via les metadata endpoints ou le hostname
   curl -s http://169.254.169.254/metadata/v1.json 2>/dev/null  # DigitalOcean
   curl -s http://169.254.169.254/openstack/latest/meta_data.json 2>/dev/null
   ssh <USER>@<IP> "hostnamectl | grep -i 'chassis\|deployment'"
   ```

2. Afficher les instructions spécifiques
   ```
   📋 Ouvrez les ports suivants dans votre firewall cloud :

   Fournisseur détecté : <NOM>
   → Panneau de configuration : <URL>

   Ports à ouvrir :
   ✅ TCP 22  (SSH)
   ✅ TCP 80  (HTTP)
   ✅ TCP 443 (HTTPS)
   ```

3. Attendre confirmation utilisateur avant de continuer
```

---

## 3. V2 — SSL + Domaine

**Objectif** : ajouter HTTPS avec Let's Encrypt + configuration DNS

### 3.1 Fichiers à créer

| Fichier | Rôle | Temps estimé |
|---|---|---|
| `.github/skills/ssl-setup.md` | Certbot Docker + Nginx HTTPS | 20 min |
| `.github/skills/dns-guide.md` | Instructions DNS selon le registrar | 15 min |
| `.github/instructions/phase-4-ssl.md` | Instructions détaillées SSL | 10 min |

### 3.2 Contenu

#### `.github/skills/ssl-setup.md`

```markdown
# Skill: ssl-setup

## Prérequis
- Domaine configuré (DNS A → IP)
- Application déployée en HTTP
- docker-compose avec service certbot

## Procédure

1. Vérifier la propagation DNS
   ```bash
   dig +short <DOMAIN>
   # Doit retourner l'IP du serveur
   ```

2. Mettre à jour ALLOWED_HOSTS
   ```bash
   ssh <USER>@<IP> "sed -i 's/ALLOWED_HOSTS=.*/&,<DOMAIN>,www.<DOMAIN>/' /opt/<PROJECT>/backend/.env.docker"
   ```

3. Mettre à jour Nginx (server_name)
   ```bash
   ssh <USER>@<IP> "sed -i 's/server_name .*/server_name <DOMAIN> www.<DOMAIN>;/' /opt/<PROJECT>/infra/nginx/default.conf"
   ```

4. Obtenir le certificat via Docker certbot
   ```bash
   ssh <USER>@<IP> "docker compose -f /opt/<PROJECT>/docker-compose.yml run --rm certbot certonly --webroot -w /var/www/certbot -d <DOMAIN> -d www.<DOMAIN> --email <EMAIL> --agree-tos --no-eff-email"
   ```

5. Activer HTTPS dans Nginx
   → Remplacer la config Nginx par la version HTTPS (template)
   → Redémarrer nginx

6. Démarrer le service certbot (renouvellement auto)
   ```bash
   ssh <USER>@<IP> "cd /opt/<PROJECT> && docker compose up -d certbot"
   ```

7. Vérifier
   ```bash
   curl -I https://<DOMAIN>/
   # Doit retourner HTTP 200
   ```

## Résultat attendu
```
HTTP  <DOMAIN> → 301 → HTTPS
HTTPS <DOMAIN> → 200
Certificat : Let's Encrypt, expire dans 90 jours
Renouvellement : automatique (certbot service Docker)
```
```

---

## 4. V3 — Multi-fournisseurs

**Objectif** : supporter Linode, DigitalOcean, AWS, OVH, IONOS, Hetzner

### 4.1 Fichiers à créer/modifier

| Fichier | Rôle |
|---|---|
| `.github/skills/provider-detect.md` | Détection automatique du fournisseur |
| `.github/skills/firewall-config.md` | Ouverture ports via API (si token fourni) |

### 4.2 Logique de détection

```
curl metadata endpoint → nom du fournisseur → config adaptée
├── 169.254.169.254/metadata/v1.json     → DigitalOcean
├── 169.254.169.254/latest/meta-data/    → AWS
├── 169.254.169.254/openstack/           → OVH / cloud public
├── Pas de metadata                      → Linode / IONOS / Hetzner
│   └── hostnamectl + reverse DNS lookup → détection heuristique
```

---

## 5. Structure finale des fichiers

```
.github/
├── agents/
│   ├── ANALYSE_FAISABILITE.md                      ✅ Créé
│   └── deploy-fullstack.yml                         ← V1
│
├── instructions/
│   ├── deploy-fullstack.md                          ← V1
│   ├── phase-1-server-setup.md                      ← V1
│   ├── phase-2-code-deploy.md                       ← V1
│   ├── phase-3-cicd.md                              ← V1
│   └── phase-4-ssl.md                               ← V2
│
└── skills/
    ├── ssh-connect.md                               ← V1
    ├── docker-install.md                            ← V1
    ├── project-deploy.md                            ← V1
    ├── health-check.md                              ← V1
    ├── github-cicd.md                               ← V1
    ├── env-generator.md                             ← V1
    ├── firewall-guide.md                            ← V1
    ├── ssl-setup.md                                 ← V2
    ├── dns-guide.md                                 ← V2
    └── provider-detect.md                           ← V3

docs/plans/
└── PLAN_AGENT_DEPLOIEMENT.md                        ✅ Ce fichier
```

---

## 6. V4 — Intégration Ansible (30/07/2026)

**Objectif** : Remplacer les commandes SSH inline par le playbook Ansible comme moteur de déploiement par défaut.

### 6.1 Mapping phases agent ↔ rôles Ansible

| Phase agent | Rôle Ansible | Commande |
|---|---|---|
| Phase 1 — server-setup | `docker` | `ansible-playbook deploy.yml --tags docker` |
| Phase 2 — code-deploy | `clickmart_app` | `ansible-playbook deploy.yml --tags app` |
| Phase 3 — cicd | `github_actions` | `ansible-playbook deploy.yml --tags cicd` |
| Phase 4 — ssl | `ssl_certbot` | `ansible-playbook deploy.yml --tags ssl` |
| Complet from-scratch | Tous | `ansible-playbook deploy.yml` (3 min) |

### 6.2 Modifications de l'agent

- **Preflight** : nouveaux prérequis (`ansible`, `community.docker`, `secrets.yml`)
- **Phases** : remplacées par appels playbook avec `--tags`
- **Préparation** : nouvelle section "Préparation Ansible" (génération `secrets.yml`, config `inventory.yml`)
- **Fallback** : chemin manuel conservé mais déprécié (pointe vers `.github/instructions/`)
- **Décision** : table enrichie avec entrées `ansible`, `inventory`

### 6.3 Fichiers modifiés

- `.opencode/agents/deploy-fullstack.md` — agent principal (v4.0)
- `docs/reports/AGENT_DEPLOY_FULLSTACK.md` — rapport mis à jour
- `docs/plans/PLAN_AGENT_DEPLOIEMENT.md` — ce fichier

### 6.4 Résultat

L'agent utilise Ansible par défaut. Le playbook est idempotent, documenté (10 fichiers), et from-scratch validé. Le chemin manuel reste disponible en fallback.

---

*Plan créé le 29 juillet 2026, mis à jour le 30 juillet 2026.*
