> **⚠️ DOCUMENT HISTORIQUE — État au 28 juillet 2026. Pour l'état actuel, voir DRY_RUN_REPORT.md à la racine du projet.**

# Analyse de faisabilité — Agent de déploiement Fullstack

> **Objectif** : créer un agent autonome capable de déployer un projet Django + React
> sur n'importe quel VPS vierge (Linode, IONOS, DigitalOcean, OVH, AWS, Azure…)
> 
> **Base** : leçons apprises du projet ClickMart (sessions 2026-07-02 → 2026-07-29)

---

## Table des matières

1. [Résumé décisionnel](#1-résumé-décisionnel)
2. [Ce qui est automatisable](#2-ce-qui-est-automatisable)
3. [Ce qui ne l'est pas (ou partiellement)](#3-ce-qui-ne-lest-pas-ou-partiellement)
4. [Périmètre de l'agent](#4-périmètre-de-lagent)
5. [Architecture de l'agent](#5-architecture-de-lagent)
6. [Compétences nécessaires (skills)](#6-compétences-nécessaires-skills)
7. [Instructions pour l'agent](#7-instructions-pour-lagent)
8. [Prérequis projet cible](#8-prérequis-projet-cible)
9. [Risques et limitations](#9-risques-et-limitations)
10. [Recommandation finale](#10-recommandation-finale)

---

## 1. Résumé décisionnel

| Critère | Évaluation |
|---|---|
| Faisabilité technique | ✅ **Faisable** — 80% des étapes sont automatisables |
| Complexité | 🟡 **Moyenne** — ~30 étapes, plusieurs points de friction |
| Fiabilité | 🟡 **Moyenne** — dépend du fournisseur VPS et de l'état initial |
| Maintenance | 🟡 **Moyenne** — le script doit être maintenu à jour |
| Gain de temps | ✅ **Élevé** — passage de ~4h manuelles à ~15 min supervisées |

**Verdict** : l'agent est viable. Le déploiement initial (sans domaine/SSL) est entièrement automatisable. Le domaine + SSL nécessite des tokens API fournisseur ou reste semi-manuel.

---

## 2. Ce qui est automatisable

### 2.1 Phase 1 — Préparation du serveur (100% automatisable)

```
┌──────────────────────────────────────────────────────────────────┐
│ Étape                    │ Automatisable │ Comment              │
├───────────────────────────┼───────────────┼─────────────────────┤
│ SSH connection           │ ✅ Oui        │ Clé fournie par user │
│ apt update && upgrade    │ ✅ Oui        │ Commande standard    │
│ Installer Docker         │ ✅ Oui        │ get.docker.com       │
│ Installer Docker Compose │ ✅ Oui        │ apt install plugin   │
│ Installer Git            │ ✅ Oui        │ apt install git      │
│ Ouvrir ports firewall    │ ⚠️ Partiel    │ Dépend du cloud      │
│ Créer /opt/<projet>      │ ✅ Oui        │ mkdir                │
└───────────────────────────┴───────────────┴─────────────────────┘
```

### 2.2 Phase 2 — Déploiement du code (100% automatisable)

```
┌──────────────────────────────────────────────────────────────────┐
│ Étape                    │ Automatisable │ Comment              │
├───────────────────────────┼───────────────┼─────────────────────┤
│ Cloner le repo           │ ✅ Oui        │ git clone            │
│ Copier Dockerfiles       │ ✅ Oui        │ SCP ou git trackés   │
│ Créer .env.docker        │ ✅ Oui        │ Template + variables  │
│ Créer .env.production    │ ✅ Oui        │ Template + variables  │
│ docker compose up        │ ✅ Oui        │ --build -d           │
│ Health check             │ ✅ Oui        │ curl sur les endpoints│
│ Créer superuser          │ ✅ Oui        │ docker compose exec   │
└───────────────────────────┴───────────────┴─────────────────────┘
```

### 2.3 Phase 3 — CI/CD (100% automatisable)

```
┌──────────────────────────────────────────────────────────────────┐
│ Étape                    │ Automatisable │ Comment              │
├───────────────────────────┼───────────────┼─────────────────────┤
│ Créer .github/workflows  │ ✅ Oui        │ Template YAML        │
│ Configurer secrets GH    │ ⚠️ Partiel    │ gh secret set        │
│ Vérifier pipeline        │ ✅ Oui        │ gh run watch         │
└───────────────────────────┴───────────────┴─────────────────────┘
```

---

## 3. Ce qui ne l'est pas (ou partiellement)

### 3.1 Ouverture des ports firewall cloud

```
┌──────────────────────────────────────────────────────────────────┐
│ Fournisseur   │ Méthode              │ Automatisable             │
├───────────────┼──────────────────────┼───────────────────────────┤
│ Linode        │ API REST             │ ✅ Avec token API         │
│ DigitalOcean  │ API REST / doctl     │ ✅ Avec token API         │
│ AWS EC2       │ Security groups (API)│ ✅ Avec aws-cli           │
│ IONOS         │ Cloud Panel (web)    │ ❌ Pas d'API publique     │
│ OVH           │ API REST             │ ✅ Avec token (complexe)  │
│ Hetzner       │ API REST / hcloud    │ ✅ Avec token             │
│ Azure         │ az-cli               │ ✅ Avec az login          │
└───────────────┴──────────────────────┴───────────────────────────┘
```

**Leçon ClickMart** : On a ouvert les ports manuellement via le dashboard Linode (pas de token API configuré). Pour IONOS, même situation (panel web uniquement).

**Recommandation** : l'agent détecte l'impossibilité et demande à l'utilisateur d'ouvrir les ports manuellement, avec des instructions précises.

### 3.2 Configuration DNS

```
┌──────────────────────────────────────────────────────────────────┐
│ Action              │ Automatisable     │ Condition              │
├─────────────────────┼───────────────────┼────────────────────────┤
│ Acheter un domaine  │ ❌ Non            │ Paiement + humain      │
│ Configurer DNS A    │ ⚠️ Via API        │ Token registrar        │
│ Vérifier propagation│ ✅ Oui            │ dig + timeout          │
└─────────────────────┴───────────────────┴────────────────────────┘
```

**Leçon ClickMart** : DNS configuré manuellement dans le panel IONOS (enregistrements A pour @ et www → IP).

**Recommandation** : l'agent peut configurer les DNS si un token API est fourni, sinon il génère les instructions exactes à copier-coller.

### 3.3 SSL (Let's Encrypt)

```
┌──────────────────────────────────────────────────────────────────┐
│ Étape                 │ Automatisable │ Condition                │
├───────────────────────┼───────────────┼──────────────────────────┤
│ Certbot certonly      │ ✅ Oui        │ Domaine doit résoudre    │
│ Config HTTPS Nginx    │ ✅ Oui        │ Template                 │
│ Renouvellement        │ ✅ Oui        │ Service Docker           │
│ Service Docker certbot │ ✅ Oui       │ docker-compose           │
└───────────────────────┴───────────────┴──────────────────────────┘
```

**Leçon ClickMart** : L'approche Docker certbot (service dans docker-compose, pas de cron host) est la plus portable. Le script `infra/scripts/setup-ssl.sh` automatise toute la chaîne.

---

## 4. Périmètre de l'agent

### V1 — Périmètre minimal viable

```
✅ Déploiement rapide (HTTP uniquement, pas de domaine)     → ~15 min
✅ CI/CD GitHub Actions basique (pas de tests)              → ~5 min
✅ Choix par défaut judicieux (ports, configs, .env)
✅ Détection d'erreurs et rollback
✅ Rapport de déploiement (ce qui a été fait, URLs)
```

Exclu de la V1 :
- ❌ Domaine + DNS (nécessite tokens API)
- ❌ SSL (nécessite domaine)
- ❌ CI/CD complet (tests backend/frontend spécifiques au projet)

### V2 — Périmètre étendu

```
✅ Domaine (si token API registrar fourni)
✅ SSL Let's Encrypt
✅ CI/CD complet avec tests
✅ Support multi-fournisseurs (Linode, DO, AWS, OVH…)
✅ Détection automatique de l'OS (Ubuntu, Debian, CentOS)
```

---

## 5. Architecture de l'agent

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   .github/agents/deploy-fullstack.yml  ← Définition de l'agent      │
│                                                                      │
│   .github/instructions/                                             │
│   ├── deploy-fullstack.md              ← Instructions principales    │
│   ├── phase-1-server-setup.md          ← Préparation serveur        │
│   ├── phase-2-code-deploy.md           ← Déploiement code           │
│   ├── phase-3-cicd.md                  ← Configuration CI/CD        │
│   └── phase-4-ssl.md                   ← SSL + domaine (optionnel)  │
│                                                                      │
│   .github/skills/                                                    │
│   ├── ssh-vps-connect.md               ← Connexion SSH au VPS       │
│   ├── docker-install.md                ← Installation Docker        │
│   ├── firewall-config.md               ← Ouverture ports            │
│   ├── env-file-generator.md            ← Génération .env            │
│   ├── nginx-configurator.md            ← Configuration Nginx        │
│   ├── certbot-setup.md                 ← Setup SSL                  │
│   ├── health-check.md                  │ Vérification déploiement   │
│   └── github-secrets.md                ← Configuration CI/CD        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Compétences nécessaires (skills)

Chaque skill est une procédure autonome avec :
- **Prérequis** : ce qui doit être vrai avant d'exécuter le skill
- **Entrées** : paramètres requis
- **Étapes** : commandes à exécuter
- **Vérification** : comment valider le succès
- **Fallback** : que faire en cas d'échec

### Skills proposés

| Skill | Rôle | Complexité | Critique |
|---|---|---|---|
| `ssh-connect` | Se connecter en SSH, vérifier l'OS | Basse | 🔴 |
| `docker-install` | Installer Docker + Compose sur Ubuntu/Debian | Basse | 🔴 |
| `firewall-open` | Ouvrir les ports 80/443/22 | Moyenne | 🔴 |
| `env-generator` | Générer `.env.docker` et `.env.production` | Basse | 🔴 |
| `project-clone` | Cloner le repo + copier les fichiers infra | Basse | 🔴 |
| `docker-deploy` | `docker compose up --build -d` | Basse | 🔴 |
| `health-check` | Vérifier que tous les endpoints répondent | Basse | 🔴 |
| `github-cicd` | Créer workflow + configurer secrets | Moyenne | 🟠 |
| `dns-config` | Configurer les enregistrements DNS A | Haute | 🟡 |
| `ssl-setup` | Certbot + Nginx HTTPS + renouvellement | Moyenne | 🟡 |
| `superuser-create` | Créer un superuser Django | Basse | 🟢 |
| `rollback` | Revenir à l'état précédent en cas d'échec | Moyenne | 🟠 |

---

## 7. Instructions pour l'agent

### Principe général

L'agent doit suivre une **checklist linéaire** avec des **points d'arrêt** où il demande confirmation à l'utilisateur avant de continuer.

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  PHASE 1 : Préparation serveur                                   │
│  ─────────────────────────                                       │
│  [ ] 1.1  Vérifier connexion SSH                                 │
│  [ ] 1.2  Détecter l'OS et la version                            │
│  [ ] 1.3  Mettre à jour les paquets (apt update)                 │
│  [ ] 1.4  Installer Docker                                       │
│  [ ] 1.5  Installer Docker Compose                               │
│  [ ] 1.6  Installer Git                                          │
│  ⏸️  POINT D'ARRÊT : demander à l'utilisateur d'ouvrir          │
│      les ports 80 et 443 dans le firewall cloud                   │
│                                                                  │
│  PHASE 2 : Déploiement du code                                   │
│  ──────────────────────────                                      │
│  [ ] 2.1  Créer /opt/<projet>                                    │
│  [ ] 2.2  Cloner le repo Git                                     │
│  [ ] 2.3  Copier les fichiers Docker (si gitignorés)             │
│  [ ] 2.4  Générer .env.docker                                    │
│  [ ] 2.5  Générer .env.production                                │
│  [ ] 2.6  docker compose up --build -d                           │
│  [ ] 2.7  Vérifier que les containers tournent                    │
│  [ ] 2.8  Health check : curl sur tous les endpoints             │
│                                                                  │
│  PHASE 3 : CI/CD                                                 │
│  ─────────────                                                   │
│  [ ] 3.1  Créer .github/workflows/deploy.yml                     │
│  [ ] 3.2  Configurer les secrets GitHub (SSH)                    │
│  [ ] 3.3  Vérifier le pipeline                                   │
│                                                                  │
│  PHASE 4 : Domaine + SSL (optionnel)                             │
│  ─────────────────────────────────                               │
│  [ ] 4.1  Configurer les enregistrements DNS                     │
│  [ ] 4.2  Mettre à jour ALLOWED_HOSTS                            │
│  [ ] 4.3  Mettre à jour server_name Nginx                        │
│  [ ] 4.4  Obtenir certificat Let's Encrypt                       │
│  [ ] 4.5  Activer HTTPS dans Nginx                               │
│  [ ] 4.6  Configurer renouvellement auto                         │
│  [ ] 4.7  Vérifier HTTPS                                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Règles de l'agent

1. **Ne jamais supposer** — toujours vérifier l'état avant d'agir
2. **Idempotence** — chaque étape peut être rejouée sans effet de bord
3. **Points d'arrêt** — ne pas continuer si une étape critique échoue
4. **Rapport** — après chaque phase, résumer ce qui a été fait
5. **Rollback** — en cas d'échec, proposer de revenir en arrière

---

## 8. Prérequis projet cible

Pour que l'agent puisse déployer un projet, celui-ci doit respecter une structure minimale :

```
mon-projet/
├── backend/
│   ├── Dockerfile            ← Ou présent dans le repo
│   ├── requirements.txt      ← Dépendances Python
│   ├── config/settings.py    ← ALLOWED_HOSTS dynamique (config())
│   └── .env.example          ← Template pour .env.docker
├── frontend/
│   ├── Dockerfile            ← Multi-stage (Node build → nginx)
│   └── package.json
├── infra/
│   ├── nginx/default.conf    ← Template reverse proxy
│   ├── certbot/conf/.gitkeep
│   ├── certbot/www/.gitkeep
│   └── scripts/setup-ssl.sh
├── docker-compose.yml        ← 5 services (db, backend, frontend, nginx, certbot)
├── .env.production.example   ← Template pour PostgreSQL
└── .github/workflows/        ← (généré par l'agent)
```

Si le projet ne respecte pas cette structure, l'agent doit :
1. Le détecter
2. Proposer de générer les fichiers manquants
3. Ou signaler ce qui doit être ajouté manuellement

---

## 9. Risques et limitations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| OS non supporté (pas Ubuntu/Debian) | Faible | Élevé | Détection + fallback manuel |
| Docker déjà installé (conflit de version) | Moyenne | Faible | Vérifier avant d'installer |
| Port 80/443 déjà utilisés | Faible | Élevé | Détecter + proposer ports alternatifs |
| DNS non propagé au moment du SSL | Élevée | Moyen | Timeout + retry avec instructions |
| git clone échoue (repo privé) | Moyenne | Élevé | Demander les credentials |
| Permissions fichiers (root vs user) | Élevée | Faible | chown après déploiement |
| Firewall cloud non configurable via API | Élevée | Moyen | Instructions manuelles |
| Espace disque insuffisant | Faible | Élevé | Vérifier avant docker build |
| Rate limiting Let's Encrypt (5/semaine) | Faible | Moyen | Utiliser --dry-run d'abord |

---

## 10. Recommandation finale

### Approche recommandée : MVP itératif

```
V1 (maintenant) :
  ✅ Déploiement HTTP sans domaine
  ✅ CI/CD basique
  → Livrable en ~2h de développement
  → Couvre 80% des cas d'usage

V2 (semaine suivante) :
  ✅ SSL + domaine
  ✅ Support multi-fournisseurs
  → Livrable en ~4h supplémentaires

V3 (futur) :
  ✅ Interface interactive (choix du fournisseur, options)
  ✅ Détection et correction automatique des problèmes courants
  → Amélioration continue
```

### Prochaines actions

1. [ ] Créer `deploy-fullstack` agent definition (`.github/agents/`)
2. [ ] Créer les 4 instructions de phase (`.github/instructions/`)
3. [ ] Créer les 8-12 skills atomiques (`.github/skills/`)
4. [ ] Tester sur un VPS vierge (Linode ou DigitalOcean)
5. [ ] Itérer sur les retours

---

*Analyse produite le 29 juillet 2026 — basée sur 3 sessions et 42 commits du projet ClickMart.*
