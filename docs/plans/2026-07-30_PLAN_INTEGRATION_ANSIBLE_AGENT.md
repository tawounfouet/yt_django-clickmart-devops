# Plan d'implémentation — Intégration Ansible dans l'agent deploy-fullstack

> Basé sur l'analyse : `docs/analyse/ANALYSE_INTEGRATION_ANSIBLE_AGENT.md`
> **Objectif** : Faire d'Ansible le moteur de déploiement par défaut de l'agent
> **Version cible** : Agent v4.0
> **Durée estimée** : ~1h15

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Étape 1 — Preflight-check Ansible](#2-étape-1--preflight-check-ansible)
3. [Étape 2 — Remplacement des phases par Ansible](#3-étape-2--remplacement-des-phases-par-ansible)
4. [Étape 3 — Gestion des secrets](#4-étape-3--gestion-des-secrets)
5. [Étape 4 — Table de décision enrichie](#5-étape-4--table-de-décision-enrichie)
6. [Étape 5 — Mise à jour de la documentation](#6-étape-5--mise-à-jour-de-la-documentation)
7. [Vérification](#7-vérification)
8. [Checklist de suivi](#8-checklist-de-suivi)

---

## 1. Vue d'ensemble

```
┌─────────────────────────────────────────────────────────┐
│              Agent deploy-fullstack v4.0                 │
│                                                          │
│  Phase 0 — ssh-bootstrap (inchangé, manuel)             │
│                    ↓                                     │
│  Preflight check (nouveaux prérequis Ansible)           │
│                    ↓                                     │
│  ┌─────────────── Déploiement ───────────────┐         │
│  │                                            │         │
│  │  Chemin Ansible (par défaut)               │         │
│  │  ├── Phase 1 : playbook --tags docker      │         │
│  │  ├── Phase 2 : playbook --tags app         │         │
│  │  ├── Phase 3 : playbook --tags cicd        │         │
│  │  └── Phase 4 : playbook --tags ssl         │         │
│  │                                            │         │
│  │  Fallback manuel (si pas d'Ansible)        │         │
│  │  └── Commandes SSH inline (déprécié)       │         │
│  └────────────────────────────────────────────┘         │
│                    ↓                                     │
│  Post-deploy validation (inchangé)                      │
└─────────────────────────────────────────────────────────┘
```

**Principe** : le playbook a déjà les tags correspondant à chaque phase. Le mapping est 1:1, aucune modification du playbook n'est nécessaire.

---

## 2. Étape 1 — Preflight-check Ansible

**Fichier** : `.opencode/agents/deploy-fullstack.md`
**Section** : `### Vérifications locales`

### 2.1 Nouveaux prérequis

Ajouter ces lignes dans la table des vérifications locales :

```markdown
| `ansible` installé | ⚠️ WARN | `ansible --version` (fallback manuel si absent) |
| `community.docker` collection | ⚠️ si ansible | `ansible-galaxy collection list \| grep community.docker` |
```

### 2.2 Nouveaux prérequis distants

Ajouter dans les vérifications distantes :

```markdown
| `inventory.yml` configuré | ⚠️ si ansible | Vérifier `ansible_host` non vide dans `infra/ansible/inventory.yml` |
| `secrets.yml` présent | ✅ si ansible (bloquant) | `test -f infra/ansible/group_vars/secrets.yml` |
```

### 2.3 Règles de comportement

```markdown
- Si Ansible est **absent** → **WARN**, l'agent utilisera le chemin manuel (déprécié)
- Si Ansible est **présent** mais `secrets.yml` absent → **STOP**, proposer de le créer (étape 3)
- Si Ansible est **présent** et `secrets.yml` présent → utiliser Ansible par défaut
```

---

## 3. Étape 2 — Remplacement des phases par Ansible

**Fichier** : `.opencode/agents/deploy-fullstack.md`
**Sections** : `### 1. server-setup` et `### 2. code-deploy`

### 3.1 Phase 1 — server-setup

**Avant** (commandes SSH inline) :
```markdown
### 1. server-setup
Prépare un VPS Ubuntu 22.04/24.04 vierge (toutes les commandes en root) :
1. Mise à jour système
2. Installation de Docker
3. Installation de Docker Compose
4. Installation de Git
5. Configuration UFW
6. Création user deploy
7. Vérification
```

**Après** (Ansible) :
```markdown
### 1. server-setup (Ansible)

Prépare le serveur via le rôle `docker` du playbook Ansible :

1. **Vérifier l'inventory** : `ansible_user: root` pour un VPS vierge
2. **Lancer le playbook** :
   ```bash
   ansible-playbook infra/ansible/deploy.yml \
     -i infra/ansible/inventory.yml \
     --tags docker
   ```
3. **Après succès** : passer `ansible_user: deploy` dans l'inventory

**Ce que fait le rôle** :
- Nettoie les repos Docker existants (évite conflit signed-by)
- Installe Docker 29.x + Compose v2 + Git + UFW
- Crée l'utilisateur `deploy` (sudo NOPASSWD, groupe docker)
- Configure la clé SSH (depuis `~/.ssh/id_ed25519.pub`)
- Authentifie ghcr.io (`docker login`)
- Ouvre les ports 22, 80, 443
- Installe fail2ban (SSH jail)

⚠️ Si Ansible n'est pas disponible, utiliser le [chemin manuel](#fallback-manuel-déprécié).
```

### 3.2 Phase 2 — code-deploy

**Après** (Ansible) :
```markdown
### 2. code-deploy (Ansible)

Déploie l'application via le rôle `clickmart_app` :

1. **Vérifier l'inventory** : `ansible_user: deploy`
2. **Lancer le playbook** :
   ```bash
   ansible-playbook infra/ansible/deploy.yml \
     -i infra/ansible/inventory.yml \
     --tags app
   ```

**Ce que fait le rôle** :
- Clone le dépôt dans `/opt/clickmart`
- Génère `.env.prod` depuis le template Jinja2
- `docker compose pull` + `docker compose up -d`
- Vérifie l'état des conteneurs

Le fichier `.env.prod` est généré automatiquement depuis les variables `secrets.yml` et `all.yml`. Les templates Jinja2 gèrent les blocs conditionnels (Cloudinary, Resend, S3).

⚠️ Si Ansible n'est pas disponible, utiliser le [chemin manuel](#fallback-manuel-déprécié).
```

### 3.3 Phase 3 — cicd

```markdown
### 3. cicd (Ansible, optionnel)

Configure GitHub Actions via le rôle `github_actions` :

```bash
ansible-playbook infra/ansible/deploy.yml \
  -i infra/ansible/inventory.yml \
  --tags cicd
```

Crée les secrets `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` dans le repo GitHub.

⚠️ Nécessite `gh` CLI authentifié en local.
```

### 3.4 Phase 4 — ssl

```markdown
### 4. ssl (Ansible, optionnel)

Active HTTPS via le rôle `ssl_certbot` :

```bash
ansible-playbook infra/ansible/deploy.yml \
  -i infra/ansible/inventory.yml \
  --tags ssl
```

**Ce que fait le rôle** :
- Vérifie que le DNS pointe vers le serveur
- Bootstrap : déploie une config Nginx HTTP-only
- Obtient les certificats Let's Encrypt (certbot)
- Restaure la config Nginx HTTPS
- Lance certbot en mode renouvellement auto (12h)

Idempotent : si les certificats existent déjà, le rôle passe directement à la config HTTPS.
```

### 3.5 Fallback manuel (conservé, déprécié)

```markdown
### Fallback manuel (déprécié)

Si Ansible n'est pas disponible, utiliser les commandes SSH inline ci-dessous.
Ces étapes sont moins fiables et non idempotentes. Privilégier Ansible.

<contenu actuel des phases 1-4>
```

---

## 4. Étape 3 — Gestion des secrets

**Fichier** : `.opencode/agents/deploy-fullstack.md`
**Nouvelle section** : avant les phases de déploiement

```markdown
## Préparation Ansible (OBLIGATOIRE si mode Ansible)

Avant le premier déploiement avec Ansible, le fichier `secrets.yml` doit être créé :

### Vérification

```bash
test -f infra/ansible/group_vars/secrets.yml && echo "OK" || echo "MISSING"
```

### Si absent — création interactive

1. **Demander les valeurs au user** :
   - `SECRET_KEY` — générer avec `python -c "import secrets; print(secrets.token_urlsafe(50))"`
   - `DB_PASSWORD` — mot de passe PostgreSQL
   - `REDIS_PASSWORD` — mot de passe Redis
   - `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` (si cloudinary)
   - `RESEND_API_KEY` (si resend)
   - `GITHUB_TOKEN` — `gh auth token` (scope `read:packages`)

2. **Générer le fichier** :
   ```yaml
   ---
   secret_key: "<valeur>"
   db_password: "<valeur>"
   redis_password: "<valeur>"
   # ...
   ```

3. **Proposer le chiffrement vault** (optionnel) :
   ```bash
   ansible-vault encrypt infra/ansible/group_vars/secrets.yml
   ```
   Si chiffré, ajouter `--ask-vault-pass` aux commandes du playbook.

### Si présent

Vérifier que les valeurs sont à jour (token ghcr.io non expiré). Proposer de renouveler si nécessaire.

### Configuration de l'inventory

Vérifier que `infra/ansible/inventory.yml` est correct :
- `ansible_host` : IP du VPS
- `ansible_user` : `root` pour VPS vierge, `deploy` après
- `domain` : nom de domaine
```

---

## 5. Étape 4 — Table de décision enrichie

**Fichier** : `.opencode/agents/deploy-fullstack.md`
**Section** : `## Détection du point de départ`

### 5.1 Nouveaux points d'entrée

```markdown
| Le user fournit... | Commencer par... |
|---|---|
| `ansible` | **Mode Ansible** : déploiement complet via le playbook |
| `inventory` | Générer/mettre à jour `inventory.yml` |
| `dry-run` | Mode analyse sans déploiement |
| IP + user + mot de passe | **Phase 0** : ssh-bootstrap → puis mode Ansible |
| IP + user + clé SSH | **Préparation Ansible** → secrets + inventory → playbook |
| `ansible` + `staging` | Playbook avec `--tags app` et `--limit staging` |
```

### 5.2 Logique de décision automatisée

```markdown
Quand l'agent est invoqué sans argument explicite, il applique cette logique :

1. Vérifier si `ansible` est installé → OUI : mode Ansible, NON : mode manuel
2. Vérifier `secrets.yml` → absent : proposer création
3. Vérifier `inventory.yml` → non configuré : demander IP + user
4. Détecter l'état du serveur :
   - Docker absent → commencer Phase 1 (server-setup)
   - Docker présent, app absente → commencer Phase 2 (code-deploy)
   - App présente, pas de SSL → proposer Phase 4 (ssl)
   - Tout OK → "Serveur déjà à jour"
```

---

## 6. Étape 5 — Mise à jour de la documentation

### 6.1 `docs/reports/AGENT_DEPLOY_FULLSTACK.md`

**Version** : 3.0 → 4.0

Ajouts :
- Section "Intégration Ansible" dans l'architecture
- Mapping phases agent ↔ rôles Ansible
- Nouveaux prérequis dans le preflight
- Table de décision enrichie
- Statistiques : 12 modifications

### 6.2 `docs/plans/PLAN_AGENT_DEPLOIEMENT.md`

Ajouter une section "V4 — Intégration Ansible" avec :
- Mapping des phases
- Prérequis Ansible
- Gestion des secrets
- Fallback manuel

### 6.3 `.opencode/agents/deploy-fullstack.md`

Fichier principal modifié (étapes 1 à 4 ci-dessus).

---

## 7. Vérification

### 7.1 Test local

```bash
# Vérifier que le playbook fonctionne en mode partiel
ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --tags docker --check

# Vérifier la détection de l'état
ansible all -i infra/ansible/inventory.yml -m ping
ansible all -i infra/ansible/inventory.yml -m shell -a "docker --version"
```

### 7.2 Test from-scratch

Sur un VPS vierge (ou reset) :
1. `@deploy-fullstack` → détecte mode Ansible
2. Prépare les secrets → génère `secrets.yml`
3. Phase 1 → `--tags docker` → OK
4. Phase 2 → `--tags app` → OK
5. Phase 4 → `--tags ssl` → OK
6. Site accessible en HTTPS

### 7.3 Test fallback

Sur une machine sans Ansible :
1. `@deploy-fullstack` → détecte absence Ansible
2. Propose fallback manuel
3. Déploiement via SSH inline → OK

---

## 8. Checklist de suivi

| # | Tâche | Fichier | Effort | Statut |
|---|---|---|---|---|
| 1 | Preflight : ajouter prérequis Ansible | `.opencode/agents/deploy-fullstack.md` | 15 min | ⬜ |
| 2 | Phase 1 : remplacer par appel Ansible | `.opencode/agents/deploy-fullstack.md` | 5 min | ⬜ |
| 3 | Phase 2 : remplacer par appel Ansible | `.opencode/agents/deploy-fullstack.md` | 5 min | ⬜ |
| 4 | Phase 3 : remplacer par appel Ansible | `.opencode/agents/deploy-fullstack.md` | 5 min | ⬜ |
| 5 | Phase 4 : remplacer par appel Ansible | `.opencode/agents/deploy-fullstack.md` | 5 min | ⬜ |
| 6 | Ajouter section "Préparation Ansible" (secrets, inventory) | `.opencode/agents/deploy-fullstack.md` | 15 min | ⬜ |
| 7 | Ajouter section "Fallback manuel" | `.opencode/agents/deploy-fullstack.md` | 5 min | ⬜ |
| 8 | Table de décision : enrichir avec `ansible` | `.opencode/agents/deploy-fullstack.md` | 10 min | ⬜ |
| 9 | Mettre à jour `AGENT_DEPLOY_FULLSTACK.md` → v4.0 | `docs/reports/` | 15 min | ⬜ |
| 10 | Ajouter section V4 dans `PLAN_AGENT_DEPLOIEMENT.md` | `docs/plans/` | 10 min | ⬜ |
| 11 | Vérification : test dry-run avec `--check` | Terminal | 5 min | ⬜ |
| **Total** | | | **~1h35** | |

---

**Progression** : 0/11 tâches (0%)
