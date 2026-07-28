# Utiliser l'agent de déploiement

## Méthode 1 — Via OpenCode (recommandé)

Depuis le répertoire du projet à déployer :

```bash
# Charger l'agent
@deploy-fullstack

# L'agent va demander :
# 1. L'IP du VPS
# 2. L'utilisateur SSH (root par défaut)
# 3. La clé SSH (~/.ssh/id_rsa par défaut)

# Puis exécuter les phases automatiquement
```

L'agent s'arrête à chaque checkpoint pour demander confirmation.

## Méthode 2 — Manuellement, en suivant les skills

Ouvrir les fichiers dans l'ordre et exécuter les commandes :

```bash
# Phase 1
cat .github/instructions/phase-1-server-setup.md
# → Suivre les étapes : ssh-connect → docker-install → firewall

# Phase 2
cat .github/instructions/phase-2-code-deploy.md
# → Suivre les étapes : env-generator → project-deploy → health-check

# Phase 3 (optionnelle)
cat .github/instructions/phase-3-cicd.md

# Phase 4 (optionnelle, nécessite un domaine)
cat .github/instructions/phase-4-ssl.md
```

## Ce dont l'agent a besoin

| Entrée | Obligatoire | Par défaut |
|---|---|---|
| IP du VPS | ✅ Oui | — |
| Utilisateur SSH | Non | `root` |
| Clé SSH | Non | `~/.ssh/id_rsa` |
| URL du repo Git | Non | Détectée automatiquement |
| Domaine (pour SSL) | Non | — |
| Email (pour SSL) | Non | — |

## Ce que l'agent fait

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  PHASE 1 : Préparation (~3 min)                             │
│  ├── Connexion SSH                                          │
│  ├── Détection OS + fournisseur                             │
│  ├── Installation Docker + Compose + Git                    │
│  └── Ouverture ports firewall (API ou instructions)         │
│                                                             │
│  PHASE 2 : Déploiement (~3 min)                             │
│  ├── Génération .env.docker + .env.production               │
│  ├── Clone du repo → /opt/<projet>                          │
│  ├── SCP des fichiers gitignorés                            │
│  └── docker compose up --build -d                           │
│                                                             │
│  PHASE 3 : CI/CD (~2 min, optionnelle)                      │
│  ├── Création .github/workflows/deploy.yml                  │
│  └── Configuration secrets GitHub                           │
│                                                             │
│  PHASE 4 : SSL (~3 min, optionnelle)                        │
│  ├── Configuration DNS                                      │
│  ├── Obtention certificat Let's Encrypt                     │
│  ├── Activation HTTPS Nginx                                 │
│  └── Renouvellement automatique                             │
│                                                             │
│  TOTAL : ~8-15 min (selon options)                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Exemple concret

```bash
# Tu es dans ton projet Django + React
$ pwd
/home/moi/mon-super-projet

# Tu as acheté un VPS chez DigitalOcean
# IP : 146.190.xxx.xxx
# Tu as la clé SSH configurée

$ @deploy-fullstack

🤖 Agent: Je vais déployer mon-super-projet sur 146.190.xxx.xxx
🤖 Phase 1 : Préparation du serveur...
   ✅ SSH OK (Ubuntu 24.04, 2GB RAM)
   ✅ Fournisseur : DigitalOcean
   ✅ Docker 29.x installé
   ✅ Ports 80/443 configurés via doctl

🤖 Phase 2 : Déploiement...
   ✅ .env générés
   ✅ Repo cloné dans /opt/mon-super-projet
   ✅ docker compose up --build -d
   ✅ Frontend : HTTP 200
   ✅ API : HTTP 200

🤖 Phase 3 : CI/CD ? (o/n)
   n

🤖 Phase 4 : SSL ? (o/n)
   n

✅ Déploiement terminé !
   http://146.190.xxx.xxx/
```

## Pour un NOUVEAU projet

Si tu crées un nouveau projet Django + React, il doit avoir cette structure pour être compatible :

```
mon-projet/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config/settings.py    ← ALLOWED_HOSTS dynamique via config()
│   └── .env.example
├── frontend/
│   ├── Dockerfile
│   └── package.json
├── infra/
│   ├── nginx/default.conf
│   ├── certbot/conf/.gitkeep
│   ├── certbot/www/.gitkeep
│   └── scripts/setup-ssl.sh
└── docker-compose.yml        ← services : db, backend, frontend, nginx, certbot
```

Si la structure est différente, l'agent le détecte et s'adapte ou propose de générer les fichiers manquants.
