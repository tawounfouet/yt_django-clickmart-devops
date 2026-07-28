# Session : Déploiement ClickMart sur Linode

**Date** : 2026-07-28
**Duration** : ~2 heures
**Agent(s)** : opencode/big-pickle
**Phase** : deploy
**Serveur** : Linode 172.239.20.14 (Ubuntu 24.04)

---

## Intent

Déployer l'application ClickMart (Django + React + Docker + Nginx) sur un serveur Linode vierge, obtenir un état fonctionnel identique au local, documenter l'architecture et les choix d'infrastructure.

## Outcome

- Application déployée et fonctionnelle sur `http://172.239.20.14`
- 4 containers up : nginx, frontend, backend, db
- Frontend HTTP 200, API HTTP 200 (products), Auth HTTP 200 (token)
- 3 documents créés : état des lieux, guide de déploiement, mise à jour du README
- 1 commit sécurité : ALLOWED_HOSTS + CORS dynamiques

---

## Decisions

| # | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 1 | Corriger ALLOWED_HOSTS et CORS avant de déployer | Sinon Django rejette toutes les requêtes externes | Déployer puis corriger sur le serveur (plus risqué) |
| 2 | Garder Dockerfiles gitignorés, SCP manuel | Cohérent avec la stratégie server-managed existante | Les tracker dans git (casserait la stratégie documentée) |
| 3 | Ouvrir uniquement les ports 80 et 443 | Nginx est le seul point d'entrée, 8000/5173 sont obsolètes | Garder 8000/5173 (inutile, faille de sécurité) |
| 4 | `.env.docker` créé manuellement sur le serveur | Contient des secrets, ne doit pas être dans git | Les tracker (mauvaise pratique sécurité) |
| 5 | Firewall cloud ouvert via dashboard et non via CLI | Pas de token API Linode configuré | Attendre la config du token (retard inutile) |
| 6 | Documenter l'architecture avec diagrammes ASCII | Compréhension visuelle sans outil externe | Diagrammes Mermaid (moins lisibles en CLI) |

---

## Files Created

| File | Purpose |
|---|---|
| `ETAT_DES_LIEUX.md` | État des lieux complet du projet : chronologie, fait/non fait, dettes documentaires, matrice récapitulative |
| `docs/deploy/DEPLOIEMENT_LINODE.md` | Guide de déploiement complet avec diagrammes ASCII, explication 2 couches firewall, flux réseau, procédure pas-à-pas |
| `archives/chats/2026-07-28_session_deploiement-linode-clickmart.md` | Ce fichier d'archive |

## Files Modified

| File | Change summary |
|---|---|
| `backend/config/settings.py` | `ALLOWED_HOSTS` et `CORS_ALLOWED_ORIGINS` rendus dynamiques via `config()` + `split(',')` |
| `backend/.env.example` | Ajout des variables `ALLOWED_HOSTS` et `CORS_ALLOWED_ORIGINS` |

## Files Created on Server (172.239.20.14)

| File | Purpose |
|---|---|
| `/opt/clickmart/` (repo cloné) | Code source complet |
| `/opt/clickmart/backend/.env.docker` | Variables d'environnement Django (SECRET_KEY, DB, ALLOWED_HOSTS, CORS, EMAIL) |
| `/opt/clickmart/backend/.env.production` | Variables PostgreSQL (POSTGRES_DB, USER, PASSWORD) |
| `/opt/clickmart/backend/Dockerfile` | SCP — image backend (python:3.10-slim → gunicorn) |
| `/opt/clickmart/frontend/Dockerfile` | SCP — image frontend (node:18 build → nginx:alpine) |
| `/opt/clickmart/docker-compose.yml` | SCP — orchestration 4 services |

---

## Key Context

- Le serveur était vierge : Ubuntu 24.04 sans Docker ni Git
- Docker 29.6.2, Docker Compose v5.3.1, Git 2.43.0 installés
- Le firewall cloud Linode est distinct du firewall serveur (UFW) — expliqué avec analogie immeuble/appartement
- Les ports 8000 et 5173 du tutoriel YouTube d'origine sont obsolètes depuis l'ajout de Nginx
- `backend/static/` (163 fichiers) est tracké dans git — à nettoyer plus tard
- 3 documents non commités de la session précédente : ANALYSE_CRITIQUE.md, RECOMMANDATIONS.md, PLAN_IMPLEMMENTATION.md
- La session précédente (22 juillet) a produit l'analyse critique mais rien n'a été implémenté — cette session a fait le premier pas : déploiement fonctionnel

## Commands Run

| Command | Purpose | Result |
|---|---|---|
| `ssh root@172.239.20.14 "apt update && apt upgrade -y && apt install -y git && curl -fsSL https://get.docker.com \| sh"` | Installer Docker + Git | ✅ Docker 29.6.2 |
| `git commit -m "fix(backend): make ALLOWED_HOSTS and CORS_ALLOWED_ORIGINS dynamic from env"` | Sécurité déploiement | ✅ Push réussi |
| `git clone ... /opt/clickmart` | Cloner le code sur le serveur | ✅ |
| `scp backend/Dockerfile root@IP:/opt/clickmart/backend/` | Copier les fichiers gitignorés | ✅ 3 fichiers |
| `cat > .env.docker` + `cat > .env.production` | Créer les variables d'environnement | ✅ |
| `docker compose up --build -d` | Builder et démarrer les containers | ✅ 4 containers up |
| `curl http://172.239.20.14/` | Tester le frontend | ✅ HTTP 200 |
| `curl http://172.239.20.14/api/v1/products/` | Tester l'API | ✅ HTTP 200, `[]` |

## Patterns Established

- **Double firewall** : Cloud Linode (ports 80, 443, 22) + UFW serveur (inactif, Docker gère iptables)
- **Single entry point** : Nginx reverse proxy est le seul service exposé (80/443)
- **DNS interne Docker** : Les containers communiquent par nom de service (`backend`, `db`, `frontend`)
- **SCP pour fichiers gitignorés** : `Dockerfile` ×2 + `docker-compose.yml` copiés manuellement
- **Environnement par `.env`** : `.env.docker` (Django) + `.env.production` (PostgreSQL)

## Issues & Workarounds

| Issue | Workaround | Status |
|---|---|---|
| `git clone` dans `/opt/clickmart` déjà existant (dossiers créés avant) | `rm -rf /opt/clickmart && git clone` | resolved |
| Dockerfiles gitignorés → serveur ne les reçoit pas au clone | SCP manuel depuis la machine locale | resolved |
| Firewall cloud bloque ports 80/443 | Ouvert via dashboard Linode (pas d'API token) | resolved |
| Commits précédents pas pushés (analyse critique, reco, plan) | Pas bloquant pour le déploiement, à faire plus tard | open |
| `backend/static/` tracké par git (163 fichiers) | Pas d'impact immédiat | open |
| ALLOWED_HOSTS était `[]` en dur | Rendu dynamique via `config()` | resolved |
| CORS limité à localhost:5173 | Rendu dynamique via `config()` | resolved |

---

## Action Items

- [x] Déployer l'application sur Linode
- [x] Documenter l'architecture et la procédure
- [ ] Créer un superuser et ajouter des produits de test
- [ ] Configurer un domaine + SSL (Let's Encrypt)
- [ ] Implémenter les correctifs de sécurité du PLAN_IMPLEMMENTATION.md Phase 1
- [ ] Implémenter les correctifs de fiabilité du PLAN_IMPLEMMENTATION.md Phase 2
- [ ] Améliorer le pipeline CI/CD (tests avant deploy)
- [ ] Committer les documents non versionnés (ANALYSE_CRITIQUE.md, RECOMMANDATIONS.md, PLAN_IMPLEMMENTATION.md, ETAT_DES_LIEUX.md, docs/)

## Related Sessions

- `archives/chats/2026-07-02_session_analyse-documentation-codebase.md` — Première analyse complète de la codebase
- `archives/chats/2026-07-22_session_analyse-critique-clickmart.md` — Analyse critique + recommandations + plan d'implémentation

---

## Full Conversation Summary

1. L'utilisateur a fourni les credentials SSH du serveur Linode (172.239.20.14, root)
2. Vérification : serveur vierge, Docker et Git non installés
3. Installation de Docker 29.6.2, Docker Compose v5.3.1, Git 2.43.0
4. Analyse du README : 3 incohérences majeures identifiées (fichiers gitignorés, version sans nginx, ALLOWED_HOSTS dur)
5. Création de `ETAT_DES_LIEUX.md` : chronologie du projet, ce qui est fait/non fait, dettes documentaires
6. Choix : Option A (déploiement rapide) avant les correctifs de sécurité
7. Correction `settings.py` : ALLOWED_HOSTS et CORS dynamiques via `config()`
8. Commit + push sur GitHub
9. Clone du repo sur le serveur dans `/opt/clickmart`
10. SCP des fichiers gitignorés : `Dockerfile` ×2 + `docker-compose.yml`
11. Création des fichiers `.env.docker` et `.env.production` sur le serveur
12. `docker compose up --build -d` : 4 containers démarrés avec succès
13. Ouverture des ports 80 et 443 dans le firewall cloud Linode (dashboard)
14. Vérification : Frontend HTTP 200, API HTTP 200, Auth HTTP 200
15. Discussion : pourquoi les ports 8000/5173 du tutoriel YouTube sont obsolètes (nginx reverse proxy)
16. Explication des 2 couches de firewall (cloud vs serveur, analogie immeuble/appartement)
17. Création de `docs/deploy/DEPLOIEMENT_LINODE.md` : guide complet avec diagrammes ASCII
18. Archivage de la session
