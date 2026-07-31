# Analyse — Intégration Ansible dans l'agent deploy-fullstack

> **Date** : 2026-07-30
> **Fichiers analysés** : `.opencode/agents/deploy-fullstack.md`, `.github/agents/deploy-fullstack.yml`, `docs/reports/AGENT_DEPLOY_FULLSTACK.md`, `infra/ansible/`

---

## État des lieux

### Agent deploy-fullstack (v3.0)

| Phase | Ce que fait l'agent aujourd'hui | Via |
|---|---|---|
| 0 — ssh-bootstrap | Configure l'auth SSH par clé | `sshpass` + `ssh-copy-id` (manuel) |
| 1 — server-setup | Docker, Compose, Git, UFW, user deploy | Commandes SSH inline (~50 commandes) |
| 2 — code-deploy | Clone, .env, docker compose up | Commandes SSH inline |
| 3 — cicd (optionnel) | Secrets GitHub Actions | `gh secret set` inline |
| 4 — ssl (optionnel) | Certbot + Nginx HTTPS | Commandes SSH inline |

**Problèmes de l'approche manuelle :**
- Commandes SSH inline fragiles (prouvé aujourd'hui : raw SSH → `Permission denied`)
- Pas idempotent sans vérifications manuelles
- Pas de gestion des conflits (Docker signed-by, SSL bootstrap)
- Duplication de logique entre l'agent et Ansible

### Ansible ClickMart (validé from-scratch)

| Rôle | Tags | Équivalent agent |
|---|---|---|
| `docker` | `--tags docker` | Phase 1 (server-setup) |
| `clickmart_app` | `--tags app` | Phase 2 (code-deploy) |
| `ssl_certbot` | `--tags ssl` | Phase 4 (ssl) |
| `github_actions` | `--tags cicd` | Phase 3 (cicd) |

**Forces d'Ansible :**
- Idempotent (relançable sans effet de bord)
- Gère les cas complexes (bootstrap HTTP → HTTPS, conflits apt signed-by)
- 100% from-scratch validé (VPS vierge → HTTPS < 3 min)
- Documenté (10 fichiers dans `docs/infra/ansible/`)

---

## Stratégies d'intégration

### Option A — Conserver les deux (mode hybride)

```
Agent détecte le contexte
├── Si Ansible configuré → utilise Ansible
└── Sinon → fallback manuel (actuel)
```

**Avantages** : rétrocompatible, transition progressive
**Inconvénients** : deux chemins de code à maintenir

### Option B — Ansible remplace les phases manuelles

```
Agent → toujours via Ansible
├── Phase 0 : ssh-bootstrap (manuel, prérequis pour Ansible)
├── Phase 1 : ansible-playbook --tags docker
├── Phase 2 : ansible-playbook --tags app
├── Phase 3 : ansible-playbook --tags cicd
└── Phase 4 : ansible-playbook --tags ssl
```

**Avantages** : un seul chemin, plus fiable, zéro duplication
**Inconvénients** : Ansible doit être installé en local, secrets.yml doit exister

### Option C — Nouvelle commande séparée

```
@deploy-fullstack ansible  → utilise Ansible
@deploy-fullstack manuel   → utilise l'approche actuelle
```

**Avantages** : explicite, pas de changement de comportement
**Inconvénients** : fragmentation, confusion utilisateur

### Recommandation : Option B avec fallback progressif

**Stratégie retenue** : Ansible devient le chemin par défaut. Le chemin manuel est conservé comme fallback en cas d'absence d'Ansible, mais clairement marqué comme déprécié.

---

## Modifications nécessaires

### 1. Fichier principal : `.opencode/agents/deploy-fullstack.md`

#### Preflight-check — nouveau prérequis

| Prérequis | Bloquant ? | Comment vérifier |
|---|---|---|
| `ansible` installé | ⚠️ WARN (fallback manuel) | `ansible --version` |
| `community.docker` collection | ⚠️ si ansible | `ansible-galaxy collection list \| grep docker` |
| `infra/ansible/inventory.yml` configuré | ⚠️ si ansible | Vérifier `ansible_host` non vide |
| `infra/ansible/group_vars/secrets.yml` présent | ✅ si ansible | `test -f` |

#### Table de détection — nouveau point d'entrée

```markdown
| Le user fournit... | Commencer par... |
|---|---|
| `ansible` | **Mode Ansible** : déploie via le playbook |
| `inventory` | Générer/mettre à jour inventory.yml |
| ... (existant) | ... |
```

#### Nouvelles phases Ansible

Chaque phase de l'agent est remplacée par un appel au playbook avec le tag correspondant :

```yaml
### Phase 1 — server-setup (Ansible)

ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --tags docker

### Phase 2 — code-deploy (Ansible)

ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --tags app

### Phase 3 — cicd (Ansible, optionnel)

ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --tags cicd

### Phase 4 — ssl (Ansible, optionnel)

ansible-playbook infra/ansible/deploy.yml -i infra/ansible/inventory.yml --tags ssl
```

### 2. Playbook : support du déploiement partiel

Le playbook actuel exécute **tous** les rôles (`docker` + `app` + `ssl` + `cicd`). Pour l'agent, on veut pouvoir exécuter **un seul rôle** :

```bash
# Déjà supporté via les tags (--tags docker, --tags app, etc.)
ansible-playbook deploy.yml -i inventory.yml --tags docker    # Phase 1
ansible-playbook deploy.yml -i inventory.yml --tags app      # Phase 2
ansible-playbook deploy.yml -i inventory.yml --tags ssl      # Phase 4
```

✅ Les tags sont déjà en place — aucun changement nécessaire dans le playbook.

### 3. Agent : gestion de `secrets.yml`

Le fichier `secrets.yml` (gitignoré) doit être créé avant le premier déploiement. L'agent doit :

1. Vérifier si `secrets.yml` existe
2. Si absent, demander les secrets au user (ou générer depuis `.env.example`)
3. Proposer `ansible-vault encrypt` (optionnel)

```markdown
### Préparation des secrets

1. Vérifier `infra/ansible/group_vars/secrets.yml`
2. Si absent :
   - Demander les valeurs (SECRET_KEY, DB_PASSWORD, etc.)
   - Générer le fichier
   - Proposer le chiffrement vault
3. Si présent : continuer
```

### 4. Inventory : détection de l'état serveur

L'agent doit pouvoir détecter si le serveur est vierge ou déjà provisionné :

```bash
# Vérifier si Docker est installé
ansible all -i inventory.yml -m shell -a "docker --version"

# Vérifier si l'app est déployée
ansible all -i inventory.yml -m shell -a "docker compose -p clickmart ps"
```

Selon le résultat, l'agent saute les phases déjà faites (idempotence Ansible).

---

## Plan d'implémentation

### Étape 1 — Mise à jour du preflight-check (15 min)

Ajouter les prérequis Ansible dans la table de vérification :
- `ansible` installé
- `community.docker` collection
- `inventory.yml` configuré
- `secrets.yml` présent

### Étape 2 — Ajout des phases Ansible (20 min)

Dans `.opencode/agents/deploy-fullstack.md`, remplacer les sections Phase 1-4 par les appels Ansible :

| Phase | Commande Ansible |
|---|---|
| server-setup | `ansible-playbook deploy.yml --tags docker` |
| code-deploy | `ansible-playbook deploy.yml --tags app` |
| cicd | `ansible-playbook deploy.yml --tags cicd` |
| ssl | `ansible-playbook deploy.yml --tags ssl` |

### Étape 3 — Gestion des secrets (15 min)

Ajouter une section "Préparation Ansible" qui gère `secrets.yml` :
- Détection
- Génération interactive
- Proposition vault

### Étape 4 — Table de décision enrichie (10 min)

Ajouter `ansible` et `inventory` comme points d'entrée.

### Étape 5 — Mise à jour des docs (15 min)

- `docs/reports/AGENT_DEPLOY_FULLSTACK.md` → v4.0
- `docs/plans/2026-07-29_PLAN_AGENT_DEPLOIEMENT.md` → ajouter section Ansible

---

## Effort estimé

| Étape | Durée |
|---|---|
| 1. Preflight Ansible | 15 min |
| 2. Phases Ansible | 20 min |
| 3. Gestion secrets | 15 min |
| 4. Table décision | 10 min |
| 5. Mise à jour docs | 15 min |
| **Total** | **~1h15** |

---

## Conclusion

**L'intégration est simple et naturelle** : le playbook Ansible a déjà les tags correspondant à chaque phase de l'agent. Le mapping est 1:1.

Le chemin manuel (commandes SSH inline) est conservé comme fallback pour les utilisateurs sans Ansible, mais la recommandation est claire : utiliser Ansible par défaut.

L'agent gagne en fiabilité (idempotence), en maintenabilité (zéro duplication) et en couverture (cas edge gérés par les rôles). La seule dépendance supplémentaire est `ansible` + `community.docker` en local.
