# Session: Agent deploy-fullstack — amélioration + déploiement IONOS from-scratch

**Date**: 2026-07-29
**Agent(s)**: build, deploy-fullstack
**Phase**: deploy

---

## Intent

Améliorer l'agent OpenCode `deploy-fullstack` (.opencode/agents/) avec : preflight-check, ssh-bootstrap (phase 0), création d'un user de déploiement dédié. Tester le cycle complet (preflight → phase 0 → 1 → 2) sur un VPS IONOS tout neuf (87.106.222.62).

## Outcome

Agent enrichi avec 5 phases + preflight-check contextuel. Déploiement réussi sur IONOS (Django + React + Docker Compose, 5 conteneurs healthy), user `deploy` créé et fonctionnel (groupe docker, plus besoin de root). App accessible sur http://87.106.222.62.

---

## Decisions

| # | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 1 | Format `.yml` → `.md` avec frontmatter YAML | OpenCode ne supporte que `.md` pour les agents locaux | Garder le `.yml` (pas détecté par opencode) |
| 2 | Ajouter une phase `preflight-check` avant toute action | Éviter de démarrer un déploiement sans les prérequis | Lancer directement (échec en milieu de process) |
| 3 | Ajouter une phase `0. ssh-bootstrap` | Le user fournit IP + mdp root, pas de clé SSH configurée | Passer le mdp en param à chaque commande SSH (risqué) |
| 4 | Trois niveaux de criticité (bloquant/conditionnel/non-bloquant) | Permet de ne pas bloquer inutilement | Binaire bloquant/non (trop rigide) |
| 5 | Créer un user `deploy` dans la phase 1 | Ne plus utiliser root après le setup, sécurité | Continuer en root (faille de sécu) |
| 6 | Utiliser rsync plutôt que git clone sur le serveur | Pas de clé SSH GitHub sur le VPS neuf | Générer une clé sur le serveur (complexe via SSH) |
| 7 | Nginx IP-only HTTP (sans SSL) en attendant phase 4 | Pas de domaine pointant vers l'IP IONOS | Config domain + SSL immédiate (pas de domaine) |

## Files Created

| File | Purpose |
|---|---|
| `.opencode/agents/deploy-fullstack.md` | Agent de déploiement au format reconnu par OpenCode (176 lignes) |

## Files Modified

| File | Change summary |
|---|---|
| `.opencode/agents/deploy-fullstack.yml` | Supprimé — remplacé par le `.md` (format .yml non supporté par OpenCode) |

## Files modifiés sur le serveur

| File | Change summary |
|---|---|
| `/opt/clickmart/infra/nginx/default.conf` | Config HTTP simple (IP 87.106.222.62, sans SSL) au lieu de webtech-dev.info avec HTTPS |
| `/opt/clickmart/backend/.env.docker` | Ajout ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS avec l'IP du VPS |

---

## Key Context

- **Agent non détecté** : le fichier `.yml` n'est pas reconnu par OpenCode, seuls les `.md` avec frontmatter YAML sont supportés dans `.opencode/agents/`
- **IONOS mot de passe** : caractères alphanumériques, échappés avec single quotes dans sshpass
- **Host key changed** : après reset du VPS, nécessité de `ssh-keygen -R 87.106.222.62`
- **Serveur** : Ubuntu 24.04.4 LTS, x86_64, 116 Go disque, ports 22/80/443 configurés
- **Docker** : installé via le script officiel Docker (pas snap), Docker Compose v5.3.1
- **Dépôt** : git@github.com:tawounfouet/yt_django-clickmart-devops.git

## Commands Run

| Command | Purpose | Result |
|---|---|---|
| `opencode agent list` | Vérifier la détection de l'agent | deploy-fullstack listé comme subagent |
| `sshpass -p '...' ssh-copy-id -i ~/.ssh/id_ed25519.pub root@IP` | Copier clé SSH sur le serveur | 1 key added |
| `ssh root@IP "echo 'KEY AUTH OK'"` | Vérifier auth par clé | KEY AUTH OK |
| `curl -fsSL https://get.docker.com \| sh` | Installer Docker sur le serveur | Docker 29.6.2 installé |
| `ufw allow 22,80,443/tcp && ufw --force enable` | Configurer firewall | UFW actif |
| `rsync -avz . root@IP:/opt/clickmart/` | Transférer le code | 61 MB transférés |
| `docker compose up -d --build` | Lancer l'app | 5 conteneurs UP, HTTP 200 |
| `useradd -m -s /bin/bash deploy && usermod -aG docker deploy` | Créer user de déploiement | User deploy OK, docker sans sudo |

## Patterns Established

- **Preflight-check en 3 niveaux** : `✅ bloquant` / `✅ si phase X` (conditionnel) / `⚠️ WARN` / `❌ NON` (bonus)
- **Table de détection** : l'agent détermine la phase de départ selon ce que le user fournit
- **Phase 0 ssh-bootstrap** : install sshpass → check/création clé → ssh-copy-id → vérification
- **Phase 1 server-setup** : inclut création user `deploy` avec groupe docker, sudo NOPASSWD, même clé SSH
- **Bannissement de root** : après phase 1, toutes les commandes passent par `ssh deploy@IP`
- **Validation explicite** : l'agent demande toujours confirmation avant de passer à la phase suivante
- **Nginx HTTP-only temporaire** : quand pas de domaine, config IP avec proxy HTTP simple

## Agent deploy-fullstack — Structure finale

```
preflight-check   →  vérifications locales + distantes, rapport, validation
phase 0           →  ssh-bootstrap (sshpass, clé SSH)
phase 1           →  server-setup (Docker, UFW, user deploy)
phase 2           →  code-deploy (rsync, .env, docker compose)
phase 3           →  cicd (GitHub Actions)
phase 4           →  ssl (Let's Encrypt)
```

## Issues & Workarounds

| Issue | Workaround | Status |
|---|---|---|
| Agent `.yml` non détecté par OpenCode | Converti en `.md` avec frontmatter YAML | resolved |
| `{file:./.github/instructions/deploy-fullstack.md}` inexistant | Instructions inline dans l'agent | resolved |
| Host key changed après reset VPS | `ssh-keygen -R 87.106.222.62` | resolved |
| `git clone` sur serveur échoue (pas de clé GitHub) | Utilisé `rsync` depuis le poste local | resolved |
| `TERM not set` pendant apt install (conteneur Docker) | Avertissement sans conséquence, installation OK | ignored |

## Action Items

- [ ] Phase 3 : configurer CI/CD GitHub Actions pour le serveur IONOS
- [ ] Phase 4 : configurer SSL avec Certbot (une fois le domaine pointé vers l'IP)
- [ ] Ajouter la création de clé GitHub sur le serveur pour permettre `git pull` en CI/CD
- [ ] Durcir SSH serveur (`PasswordAuthentication no`, `PermitRootLogin prohibit-password`)

## Related Sessions

- `archives/chats/2026-07-29_session_finalisation-clickmart.md` — finalisation du projet ClickMart
- `archives/chats/2026-07-28_session_deploiement-linode-clickmart.md` — premier déploiement Linode
- `archives/chats/2026-07-28_session_ameliorations-clickmart.md` — améliorations ClickMart

---

## Full Conversation Summary

1. User signale que l'agent `.opencode/agents/deploy-fullstack.yml` n'est pas détecté
2. Diagnostic : OpenCode ne supporte que les `.md` avec frontmatter YAML pour les agents locaux
3. Conversion du `.yml` en `.md`, remplacement de `{file:...}` inexistant par instructions inline
4. User demande d'ajouter une phase 0 pour le ssh-bootstrap (user fournit IP + user + mdp)
5. Ajout de la phase 0 + table de détection du point de départ
6. User souhaite un preflight-check complet avant tout déploiement
7. Ajout du preflight avec 3 niveaux de criticité, vérifications locales et distantes
8. Déploiement from-scratch sur IONOS (87.106.222.62) : preflight → phase 0 (ssh-copy-id) → phase 1 (Docker/UFW) → phase 2 (rsync + docker compose up)
9. Problème : git clone échoue (pas de clé SSH GitHub sur serveur) → résolu avec rsync
10. User demande d'ajouter un user `deploy` pour ne plus utiliser root → ajouté dans l'agent + appliqué
11. User `deploy` créé : groupe docker, sudo NOPASSWD, même clé SSH, propriétaire de /opt/clickmart
12. Demande d'archivage de session
