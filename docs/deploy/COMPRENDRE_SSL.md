# Comprendre les certificats SSL — Local vs Serveur

> Pourquoi `certbot/conf/` est vide dans le repo mais plein sur le serveur
> Projet ClickMart — `webtech-dev.info`

---

## Table des matières

1. [Le principe en 30 secondes](#1-le-principe-en-30-secondes)
2. [Visualisation : local vs serveur](#2-visualisation--local-vs-serveur)
3. [Pourquoi ce Design ?](#3-pourquoi-ce-design-)
4. [Cycle de vie d'un certificat](#4-cycle-de-vie-dun-certificat)
5. [Le flux Docker Compose](#5-le-flux-docker-compose)
6. [Pourquoi les certificats ne sont pas dans le repo](#6-pourquoi-les-certificats-ne-sont-pas-dans-le-repo)
7. [FAQ](#7-faq)

---

## 1. Le principe en 30 secondes

```
Le repo git contient la STRUCTURE (dossiers vides).
Le serveur contient les DONNÉES (les vrais certificats).

Jamais l'inverse. Les certificats sont des secrets comme les mots de passe.
```

---

## 2. Visualisation : local vs serveur

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   MACHINE LOCALE (repo git)               SERVEUR LINODE (172.239.20.14)     │
│   ─────────────────────────               ──────────────────────────────     │
│                                                                              │
│   certbot/                                certbot/                           │
│   ├── conf/                               ├── conf/                          │
│   │   └── .gitkeep    ◄─ vide ────────►   │   ├── accounts/                 │
│   │                    (juste la           │   │   └── acme-v02.api...       │
│   │                     structure)         │   ├── renewal/                  │
│   │                                       │   │   └── webtech-dev.info.conf │
│   ├── www/                                │   ├── live/                     │
│   │   └── .gitkeep    ◄─ vide ────────►   │   │   └── webtech-dev.info/     │
│   │                    (juste la           │   │       ├── fullchain.pem  🔒 │
│   │                     structure)         │   │       ├── privkey.pem    🔑 │
│   │                                       │   │       ├── cert.pem           │
│   │                                       │   │       ├── chain.pem          │
│   │                                       │   │       └── README             │
│   │                                       │   ├── archive/                  │
│   │                                       │   └── keys/                     │
│   │                                       └── www/                          │
│   │                                           └── .well-known/              │
│   │                                               └── acme-challenge/       │
│   │                                                   └── (fichiers temp)   │
│                                                                              │
│   ✅ Commitée dans git                     ❌ JAMAIS commitée                │
│   C'est la coquille vide.                  C'est le contenu réel.            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Pourquoi ce Design ?

### 3.1 Les `.gitkeep` dans le repo

```
certbot/conf/.gitkeep   →  Le dossier est créé sur le serveur au clone
certbot/www/.gitkeep    →  Les volumes Docker peuvent être montés
```

Sans ces fichiers, le dossier `certbot/conf/` n'existerait pas dans le repo. Au `git clone`, le dossier ne serait pas créé. Docker créerait le dossier vide, mais sans les bonnes permissions.

### 3.2 Les vrais certificats sur le serveur

```
/etc/letsencrypt/live/webtech-dev.info/fullchain.pem   ←  Sur le serveur
/opt/clickmart/certbot/conf/live/...                   ←  Monté dans Docker
```

Les certificats sont dans un **volume Docker** (`certbot/conf` → `/etc/letsencrypt`). Nginx y accède en lecture seule.

### 3.3 Ce qui est dans `.gitignore`

```
certbot/conf/*     ← Ignore tout SAUF .gitkeep
certbot/www/*      ← Ignore tout SAUF .gitkeep
```

Le `.gitkeep` force Git à tracker le dossier. Tout le reste est ignoré.

---

## 4. Cycle de vie d'un certificat

```
ÉTAPE 1 : CRÉATION (une seule fois)
─────────────────────────────────────
$ ./scripts/setup-ssl.sh webtech-dev.info admin@webtech-dev.info

  ┌──────────────────────────────────────────────┐
  │ Docker lance certbot/certbot                  │
  │ → Place un fichier défi dans certbot/www/     │
  │ → Let's Encrypt vérifie via le domaine        │
  │ → Certificat stocké dans certbot/conf/live/   │
  │ → Nginx lit le certificat                     │
  │ → HTTPS activé                                │
  └──────────────────────────────────────────────┘


ÉTAPE 2 : RENOUVELLEMENT (automatique, tous les 90 jours)
────────────────────────────────────────────────────────────
Cron 2×/jour sur le serveur :

  ┌──────────────────────────────────────────────┐
  │ certbot renew --quiet                         │
  │ → Vérifie si expiration < 30 jours           │
  │ → Si oui : nouveau certificat                │
  │ → Sinon : ne fait rien                        │
  │ → docker compose restart nginx               │
  └──────────────────────────────────────────────┘


ÉTAPE 3 : DÉPLOIEMENT (à chaque git push via CI/CD)
─────────────────────────────────────────────────────
  ┌──────────────────────────────────────────────┐
  │ git pull → docker compose up --build         │
  │ → Le nouveau code est déployé                │
  │ → Les certificats existants RESTENT          │
  │   (ils sont dans un volume, pas dans l'image) │
  └──────────────────────────────────────────────┘
```

---

## 5. Le flux Docker Compose

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           docker-compose.yml                               │
│                                                                            │
│  services:                                                                 │
│                                                                            │
│    nginx:                                                                  │
│      ports:                                                                │
│        - "80:80"     ← HTTP (entrée)                                        │
│        - "443:443"   ← HTTPS (entrée)                                       │
│      volumes:                                                               │
│        - ./nginx/default.conf:/etc/nginx/conf.d/default.conf               │
│                        ↑                                                   │
│                        │ Le fichier de config Nginx est dans le repo       │
│                        │ (contient les chemins vers les certificats)        │
│                                                                            │
│        - ./certbot/conf:/etc/letsencrypt                                   │
│              ↑                 ↑                                           │
│              │                 │                                            │
│    ┌─────────┘                 └──────────┐                                │
│    │                                      │                                │
│    │  Dossier sur l'HÔTE                  │  Dossier dans le CONTAINER     │
│    │  /opt/clickmart/certbot/conf/        │  /etc/letsencrypt/             │
│    │  └── live/webtech-dev.info/          │  └── live/webtech-dev.info/    │
│    │      ├── fullchain.pem               │      ├── fullchain.pem   ← lu  │
│    │      └── privkey.pem                 │      └── privkey.pem     ← lu  │
│    │                                      │                                │
│    │  Certbot écrit ICI                   │  Nginx lit ICI                 │
│    │  (via le même volume)                │  (via le même volume)          │
│    │                                      │                                │
│        - ./certbot/www:/var/www/certbot                                     │
│              ↑              ↑                                              │
│              │              │                                               │
│    ┌─────────┘              └──────────┐                                   │
│    │  Certbot place des     │  Nginx sert les fichiers    │                │
│    │  fichiers défi ICI     │  via /.well-known/         │                │
│    └────────────────────────┴────────────────────────────┘                │
│                                                                            │
│        - ./backend/media:/media                                            │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Résumé des volumes

| Volume hôte | Volume container | Qui écrit ? | Qui lit ? | Contenu |
|---|---|---|---|---|
| `./certbot/conf/` | `/etc/letsencrypt` | Certbot | Nginx | Certificats SSL |
| `./certbot/www/` | `/var/www/certbot` | Certbot | Nginx (via ACME) | Fichiers de défi |
| `./nginx/default.conf` | `/etc/nginx/conf.d/default.conf` | Développeur (git) | Nginx | Configuration |
| `./backend/media/` | `/media` | Django | Nginx | Uploads |

---

## 6. Pourquoi les certificats ne sont pas dans le repo

### Raison 1 : Sécurité

```
❌ MAUVAIS : git add certbot/conf/
   → La clé privée serait sur GitHub
   → N'importe qui pourrait usurper le domaine
   → GitHub scanne et révoque automatiquement les clés exposées

✅ BON : les certificats sont uniquement sur le serveur
   → La clé privée ne quitte jamais le serveur
   → Même si le repo est public, le HTTPS reste sécurisé
```

### Raison 2 : Spécificité

```
Un certificat SSL est lié à :
  - Un nom de domaine (webtech-dev.info)
  - Une autorité (Let's Encrypt)
  - Une date d'expiration (90 jours)

Si on commitait les certificats :
  - Chaque déploiement écraserait les certificats du serveur
  - Impossible d'avoir des certificats différents par environnement
  - Le renouvellement automatique serait inutile
```

### Raison 3 : Séparation des responsabilités

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│   CODE SOURCE (git)              INFRASTRUCTURE (serveur)     │
│   ─────────────                  ──────────────────────       │
│                                                              │
│   • Django / React               • Certificats SSL           │
│   • Tests                        • Base de données           │
│   • CI/CD                        • Logs                      │
│   • Dockerfiles                  • Secrets (.env)            │
│   • Nginx config                 • Volumes Docker            │
│                                                              │
│   Peut être partagé, cloné,      Spécifique à ce serveur,    │
│   versionné, revu en PR          ne quitte jamais la machine  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. FAQ

### « Comment recréer les certificats si le serveur est détruit ? »

```bash
# 1. Cloner le repo sur le nouveau serveur
git clone ... /opt/clickmart

# 2. Lancer l'app
cd /opt/clickmart && docker compose up -d

# 3. Régénérer les certificats
./scripts/setup-ssl.sh webtech-dev.info admin@webtech-dev.info

# → Nouveau certificat émis, stocké dans certbot/conf/
```

### « Comment ça se synchronise au git pull ? »

```
Ça ne se synchronise PAS. Et c'est voulu.

git pull → met à jour le code source
certbot renew → met à jour les certificats (cron)

Deux mécanismes indépendants, zéro conflit.
```

### « Que se passe-t-il si le certificat expire ? »

```
Le cron vérifie 2×/jour. Si le certificat expire dans < 30 jours,
certbot le renouvelle automatiquement. Aucune action humaine nécessaire.

Vérifier l'état :
$ certbot certificates
$ docker compose logs nginx | grep SSL
```

### « Pourquoi ne pas mettre les certificats dans l'image Docker ? »

```
❌ L'image Docker est reconstruite à chaque déploiement
   → Le certificat serait perdu à chaque mise à jour
   → Il faudrait le regénérer à chaque build (interdit par Let's Encrypt)

✅ Avec un volume :
   → Le certificat survit aux rebuilds
   → Le renouvellement est indépendant du déploiement
```

---

*Document créé le 28 juillet 2026.*
