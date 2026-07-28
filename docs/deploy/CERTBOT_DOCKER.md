# Certbot en service Docker — Méthode production

> Comment et pourquoi intégrer Certbot comme service Docker Compose
> Projet ClickMart — `webtech-dev.info`

---

## Table des matières

1. [Résumé de la méthode](#1-résumé-de-la-méthode)
2. [Comparaison : ancienne vs nouvelle méthode](#2-comparaison--ancienne-vs-nouvelle-méthode)
3. [Ce que ça apporte](#3-ce-que-ça-apporte)
4. [Fichiers et dossiers obligatoires](#4-fichiers-et-dossiers-obligatoires)
5. [Comment c'est configuré](#5-comment-cest-configuré)
6. [Diagramme de flux](#6-diagramme-de-flux)
7. [Comment reproduire sur un nouveau projet](#7-comment-reproduire-sur-un-nouveau-projet)

---

## 1. Résumé de la méthode

```
AVANT : certbot installé sur l'hôte, cron, copie de certificats
APRÈS  : certbot = service Docker, zéro install, zéro cron
```

| | Ancienne méthode | Nouvelle méthode |
|---|---|---|
| Certbot | Installé sur l'hôte (`apt install`) | Image Docker `certbot/certbot` |
| Renouvellement | `crontab -e` sur l'hôte | Boucle `while` dans le container |
| Certificats | `/etc/letsencrypt` → copiés vers volume | Volume Docker partagé directement |
| Redémarrage nginx | Script shell + cron | Deploy hook Docker |
| Portabilité | Spécifique au serveur | Fonctionne partout où Docker tourne |

---

## 2. Comparaison : ancienne vs nouvelle méthode

### 2.1 Ancienne méthode (avec cron host)

```
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 1 : Installation manuelle                                │
│                                                                 │
│  $ ssh root@172.239.20.14                                       │
│  $ apt install certbot -y           ← dépend du serveur         │
│                                                                 │
│  ÉTAPE 2 : Obtention du certificat                              │
│                                                                 │
│  $ certbot certonly --webroot \                                 │
│      -w /opt/clickmart/certbot/www \                            │
│      -d webtech-dev.info                                        │
│                                                                 │
│  → Certificat sauvegardé dans /etc/letsencrypt/ (hôte)          │
│  → PAS dans le volume Docker                                    │
│                                                                 │
│  ÉTAPE 3 : Copie manuelle vers le volume Docker                 │
│                                                                 │
│  $ cp -r /etc/letsencrypt/* /opt/clickmart/certbot/conf/        │
│                                                                 │
│  → ⚠️ Si on oublie cette étape, nginx crash                     │
│     "cannot load certificate: No such file or directory"        │
│                                                                 │
│  ÉTAPE 4 : Cron manuel pour le renouvellement                   │
│                                                                 │
│  $ crontab -e                                                    │
│  0 3,15 * * * /opt/clickmart/scripts/renew-ssl.sh               │
│                                                                 │
│  → Script renew-ssl.sh :                                        │
│    1. certbot renew                                              │
│    2. cp -r /etc/letsencrypt/* → certbot/conf/                  │
│    3. docker compose restart nginx                              │
│                                                                 │
│  PROBLÈMES :                                                    │
│  ❌ Repose sur certbot installé sur l'hôte                      │
│  ❌ Repose sur cron configuré manuellement                      │
│  ❌ La copie des certificats est fragile                        │
│  ❌ Si on change de serveur, il faut tout refaire               │
│  ❌ Pas versionné, pas reproductible                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Nouvelle méthode (service Docker)

```
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 1 : Rien à installer sur l'hôte                          │
│                                                                 │
│  → Certbot est une image Docker, incluse dans docker-compose    │
│                                                                 │
│  ÉTAPE 2 : Obtention du certificat                              │
│                                                                 │
│  $ docker compose run --rm certbot certonly --webroot \         │
│      -w /var/www/certbot \                                      │
│      -d webtech-dev.info                                        │
│                                                                 │
│  → Certificat directement dans certbot/conf/ (volume Docker)    │
│  → Nginx y accède immédiatement                                 │
│                                                                 │
│  ÉTAPE 3 : Aucune — le volume est déjà partagé                  │
│                                                                 │
│  → docker-compose.yml monte certbot/conf:/etc/letsencrypt       │
│  → Nginx ET Certbot utilisent le même volume                    │
│                                                                 │
│  ÉTAPE 4 : Renouvellement automatique via le service            │
│                                                                 │
│  → Le container certbot tourne en continu                        │
│  → Toutes les 12h : certbot renew --quiet                        │
│  → Si renouvellement : deploy-hook → docker restart nginx       │
│                                                                 │
│  AVANTAGES :                                                    │
│  ✅ Zéro installation sur l'hôte                                │
│  ✅ Zéro cron à configurer                                       │
│  ✅ Tout est versionné dans le repo                             │
│  ✅ Reproductible : docker compose up -d suffit                 │
│  ✅ Fonctionne sur n'importe quel serveur avec Docker           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Ce que ça apporte

### 3.1 Portabilité

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Changement de serveur :                                         │
│                                                                  │
│  $ git clone ... /opt/clickmart                                  │
│  $ docker compose up -d                                          │
│  $ ./scripts/setup-ssl.sh webtech-dev.info admin@...             │
│                                                                  │
│  → C'est tout. Aucune autre commande.                            │
│  → Pas de apt install, pas de crontab -e, pas de cp.            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Reproductibilité

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Pour un NOUVEAU projet Django :                                 │
│                                                                  │
│  1. Copier dans le nouveau repo :                                │
│     • docker-compose.yml  (service certbot)                      │
│     • scripts/setup-ssl.sh                                       │
│     • scripts/certbot-deploy-hook.sh                             │
│     • certbot/conf/.gitkeep                                      │
│     • certbot/www/.gitkeep                                       │
│     • nginx/default.conf                                         │
│                                                                  │
│  2. docker compose up -d                                         │
│  3. ./scripts/setup-ssl.sh nouveau-domaine.com email@...         │
│                                                                  │
│  → SSL fonctionnel en 2 commandes                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.3 Résilience

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Si le container certbot s'arrête :                              │
│  → restart: unless-stopped → Docker le relance automatiquement  │
│                                                                  │
│  Si le serveur redémarre :                                       │
│  → docker compose up -d (au boot) → tous les services repartent │
│  → certbot reprend sa boucle de renouvellement                   │
│                                                                  │
│  Si le certificat expire :                                       │
│  → certbot renew le détecte et renouvelle                       │
│  → deploy-hook → nginx rechargé automatiquement                 │
│                                                                  │
│  Aucune intervention humaine nécessaire.                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Fichiers et dossiers obligatoires

```
yt_django-clickmart-devops/
│
├── docker-compose.yml          ← Service certbot défini ici
│
├── certbot/                    ← Volume persistent Docker
│   ├── conf/                   ← Certificats SSL (NE PAS COMMITTER)
│   │   └── .gitkeep            ← Garde le dossier dans git (vide)
│   └── www/                    ← Défis ACME (NE PAS COMMITTER)
│       └── .gitkeep            ← Garde le dossier dans git (vide)
│
├── nginx/
│   └── default.conf            ← Config Nginx (HTTP + HTTPS)
│
├── scripts/
│   ├── setup-ssl.sh            ← Script d'initialisation SSL
│   └── certbot-deploy-hook.sh  ← Hook post-renouvellement
│
└── .gitignore                  ← Ignore certbot/conf/* et certbot/www/*
```

### 4.1 `docker-compose.yml` — Service certbot

```yaml
certbot:
  image: certbot/certbot                    # Image officielle Let's Encrypt
  volumes:
    - ./certbot/www:/var/www/certbot         # Certbot écrit, Nginx lit
    - ./certbot/conf:/etc/letsencrypt        # Certificats partagés
    - ./scripts/certbot-deploy-hook.sh:/usr/local/bin/deploy-hook.sh:ro
    - /var/run/docker.sock:/var/run/docker.sock:ro  # Pour restart nginx
  entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew --quiet --deploy-hook /usr/local/bin/deploy-hook.sh; sleep 12h; done'"
  restart: unless-stopped                    # Survit aux reboots
  depends_on:
    - nginx
```

### 4.2 `certbot/conf/` et `certbot/www/`

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  LOCAL (git)              │  SERVEUR (après certbot)         │
│                           │                                  │
│  certbot/                 │  certbot/                        │
│  ├── conf/                │  ├── conf/                       │
│  │   └── .gitkeep  (vide) │  │   ├── live/                   │
│  │                        │  │   │   └── webtech-dev.info/   │
│  │                        │  │   │       ├── fullchain.pem   │
│  │                        │  │   │       └── privkey.pem     │
│  │                        │  │   ├── archive/                │
│  │                        │  │   ├── renewal/                │
│  │                        │  │   └── accounts/               │
│  └── www/                 │  └── www/                        │
│      └── .gitkeep  (vide) │      └── .well-known/            │
│                           │          └── acme-challenge/     │
│                           │              └── (fichiers temp)  │
│                           │                                  │
│  ✅ Commitée               │  ❌ Jamais commitée              │
│  (structure vide)          │  (données sensibles)            │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 `nginx/default.conf`

```nginx
# HTTP → redirige tout vers HTTPS (sauf ACME)
server {
    listen 80;
    server_name webtech-dev.info www.webtech-dev.info;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;    # ← Monté depuis certbot/www/
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS → sert l'application
server {
    listen 443 ssl;
    server_name webtech-dev.info www.webtech-dev.info;

    ssl_certificate     /etc/letsencrypt/live/webtech-dev.info/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/webtech-dev.info/privkey.pem;
    # ↑ Monté depuis certbot/conf/

    # ... proxy_pass vers frontend:80 et backend:8000 ...
}
```

### 4.4 `scripts/certbot-deploy-hook.sh`

```bash
#!/bin/sh
# Appelé après chaque renouvellement réussi
NGINX_ID=$(docker ps -q --filter name=nginx | head -1)
if [ -n "$NGINX_ID" ]; then
    docker restart "$NGINX_ID"
fi
```

### 4.5 `scripts/setup-ssl.sh`

Script d'initialisation complet qui :
1. Vérifie la propagation DNS
2. Lance `docker compose run certbot` pour le premier certificat
3. Met à jour `nginx/default.conf` avec le domaine
4. Met à jour `ALLOWED_HOSTS`
5. Redémarre les services
6. Vérifie HTTP 301 + HTTPS 200

### 4.6 `.gitignore`

```gitignore
# Dossiers certbot : garder la structure, ignorer le contenu
certbot/conf/*
!certbot/conf/.gitkeep
certbot/www/*
!certbot/www/.gitkeep
```

---

## 5. Comment c'est configuré

### 5.1 Les volumes partagés — le cœur du système

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                     VOLUMES DOCKER PARTAGÉS                          │
│                                                                      │
│  ┌─────────────────────┐         ┌─────────────────────┐            │
│  │   CONTAINER NGINX   │         │  CONTAINER CERTBOT  │            │
│  │                     │         │                     │            │
│  │  /etc/letsencrypt ──┼────┬────┼── /etc/letsencrypt  │            │
│  │       ↑             │    │    │                     │            │
│  │  lit les certificats │    │    │  écrit les certificats          │
│  │                     │    │    │                     │            │
│  │  /var/www/certbot ──┼────┼────┼── /var/www/certbot │            │
│  │       ↑             │    │    │         ↓           │            │
│  │  sert .well-known/  │    │    │  place les défis    │            │
│  └─────────────────────┘    │    └─────────────────────┘            │
│                             │                                        │
│                    VOLUMES SUR L'HÔTE                                │
│                    ┌────────┴──────────┐                            │
│                    │ certbot/conf/     │ ← certificats persistants   │
│                    │ certbot/www/      │ ← fichiers ACME temporaires │
│                    └───────────────────┘                            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 Le cycle de renouvellement

```
T = 0h     certbot démarre, boucle infinie
T = 0h     certbot renew --quiet → rien à renouveler
T = 12h    certbot renew --quiet → rien à renouveler
T = 24h    certbot renew --quiet → rien à renouveler
   ...
T = ~60j   certbot renew --quiet → certificat renouvelé !
           → deploy-hook : docker restart nginx
           → nginx recharge les nouveaux certificats
T = 60j+12h certbot renew --quiet → rien à renouveler
   ...
```

### 5.3 Le deploy hook — redémarrage automatique de nginx

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  1. certbot renew détecte un certificat à renouveler             │
│                                                                  │
│  2. Certbot contacte Let's Encrypt                               │
│     → Nouveau certificat écrit dans certbot/conf/live/           │
│                                                                  │
│  3. Certbot exécute le deploy-hook :                             │
│     scripts/certbot-deploy-hook.sh                               │
│     → docker ps -q --filter name=nginx                           │
│     → docker restart <container_id>                              │
│                                                                  │
│  4. Nginx redémarre                                              │
│     → Lit les nouveaux certificats depuis certbot/conf/           │
│     → Zéro downtime (nginx gère le restart graceful)             │
│                                                                  │
│  ⚠️ docker.sock monté en read-only (ro) :                        │
│     certbot peut lister/restart les containers                   │
│     mais ne peut pas créer/modifier des images                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Diagramme de flux

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        VUE D'ENSEMBLE                                    │
│                                                                         │
│                                                                         │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐      │
│   │    DB    │     │ BACKEND  │     │ FRONTEND │     │  NGINX   │      │
│   │ postgres │     │ gunicorn │     │  nginx   │     │  :80:443 │      │
│   │  :5432   │     │  :8000   │     │  :80     │     │          │      │
│   └──────────┘     └──────────┘     └──────────┘     └────┬─────┘      │
│                                                           │            │
│                                              volumes partagés          │
│                                              ┌─────────┴─────────┐     │
│                                              │   certbot/conf/    │     │
│                                              │   certbot/www/     │     │
│                                              └─────────┬─────────┘     │
│                                                           │            │
│                                                    ┌──────┴──────┐     │
│                                                    │   CERTBOT   │     │
│                                                    │  certbot/   │     │
│                                                    │  certbot    │     │
│                                                    │             │     │
│                                                    │ while true: │     │
│                                                    │   renew     │     │
│                                                    │   sleep 12h │     │
│                                                    └─────────────┘     │
│                                                                         │
│   ───────────────────────────────────────────────────────────────────   │
│                                                                         │
│   FLUX DE RENOUVELLEMENT :                                              │
│                                                                         │
│   certbot ──► Let's Encrypt ──► défi ACME                               │
│                                  │                                      │
│                                  ▼                                      │
│                            http://domaine/.well-known/acme-challenge/   │
│                                  │                                      │
│                                  ▼                                      │
│                            nginx ──► certbot/www/ (fichier défi)         │
│                                  │                                      │
│                                  ▼                                      │
│                            Let's Encrypt valide                         │
│                                  │                                      │
│                                  ▼                                      │
│                            certbot ──► certbot/conf/ (nouveau certif)    │
│                                  │                                      │
│                                  ▼                                      │
│                            deploy-hook ──► docker restart nginx          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Comment reproduire sur un nouveau projet

### 7.1 Fichiers à copier

```bash
# Depuis le repo ClickMart vers le nouveau projet Django
cp docker-compose.yml                    nouveau-projet/
cp nginx/default.conf                    nouveau-projet/nginx/
cp scripts/setup-ssl.sh                  nouveau-projet/scripts/
cp scripts/certbot-deploy-hook.sh        nouveau-projet/scripts/
mkdir -p nouveau-projet/certbot/conf nouveau-projet/certbot/www
touch nouveau-projet/certbot/conf/.gitkeep
touch nouveau-projet/certbot/www/.gitkeep
```

### 7.2 Modifications à faire

```bash
# 1. Dans nginx/default.conf : remplacer le proxy_pass par le bon service
#    (si le service s'appelle autrement que frontend/backend)

# 2. Dans .gitignore : ajouter
certbot/conf/*
!certbot/conf/.gitkeep
certbot/www/*
!certbot/www/.gitkeep
```

### 7.3 Commandes à lancer

```bash
# 1. Déployer l'app
docker compose up -d --build

# 2. Configurer le DNS (A record → IP du serveur)

# 3. Lancer le setup SSL
./scripts/setup-ssl.sh nouveau-domaine.com admin@domaine.com

# 4. Committer la config nginx mise à jour
git add nginx/default.conf
git commit -m "feat(ssl): enable HTTPS for nouveau-domaine.com"
git push
```

---

*Document créé le 28 juillet 2026.*
