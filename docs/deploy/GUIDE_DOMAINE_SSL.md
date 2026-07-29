> **⚠️ DOCUMENT HISTORIQUE — État au 28 juillet 2026. Pour l'état actuel, voir DRY_RUN_REPORT.md à la racine du projet.**

# Guide Domaine + SSL — ClickMart

> Configurer un nom de domaine et HTTPS avec Let's Encrypt
> Serveur : Linode 172.239.20.14 — `/opt/clickmart`
> Dernière mise à jour : 28 juillet 2026

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Étape 1 : Acheter un nom de domaine](#2-étape-1--acheter-un-nom-de-domaine)
3. [Étape 2 : Configurer les DNS (pointer vers Linode)](#3-étape-2--configurer-les-dns-pointer-vers-linode)
4. [Étape 3 : Mettre à jour Nginx (domaine)](#4-étape-3--mettre-à-jour-nginx-domaine)
5. [Étape 4 : Mettre à jour le `.env.docker` (ALLOWED_HOSTS)](#5-étape-4--mettre-à-jour-le-envdocker-allowed_hosts)
6. [Étape 5 : Obtenir le certificat SSL (Let's Encrypt)](#6-étape-5--obtenir-le-certificat-ssl-lets-encrypt)
7. [Étape 6 : Configurer Nginx pour HTTPS](#7-étape-6--configurer-nginx-pour-https)
8. [Étape 7 : Renouvellement automatique](#8-étape-7--renouvellement-automatique)
9. [Étape 8 : Vérification finale](#9-étape-8--vérification-finale)
10. [Résumé des commandes](#10-résumé-des-commandes)

---

## 1. Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  AVANT (HTTP seul)                    APRÈS (HTTPS + domaine)           │
│                                                                         │
│  http://172.239.20.14 ──► App    │    https://clickmart.com ──► App    │
│                            │     │                              │       │
│  Nginx écoute sur :80       │     │  Nginx écoute sur :80        │       │
│                            │     │  → redirige vers :443         │       │
│                            │     │  Nginx écoute sur :443        │       │
│                            │     │  → certificat Let's Encrypt   │       │
│                            │     │                              │       │
└─────────────────────────────────────────────────────────────────────────┘
```

**Prérequis** :
- [x] Serveur Linode opérationnel (172.239.20.14)
- [x] Docker Compose déployé dans `/opt/clickmart`
- [x] Dossiers certbot créés (`certbot/www/`, `certbot/conf/`)
- [x] Port 80 et 443 ouverts dans le firewall cloud Linode
- [ ] ~10-15€ pour le nom de domaine (prix annuel)

---

## 2. Étape 1 : Acheter un nom de domaine

### 2.1 Choisir un registrar

| Fournisseur | Prix .com/an | Prix .fr/an | Interface |
|---|---|---|---|
| [Namecheap](https://namecheap.com) | ~12€ | ~10€ | Facile, bon support DNS |
| [GoDaddy](https://godaddy.com) | ~15€ | ~10€ | Connu, beaucoup d'upsells |
| [OVH](https://ovh.com) | ~10€ | ~6€ | Bon pour .fr |
| [Google Domains](https://domains.google) | ~14€ | — | Simple, intégré Google |
| [Cloudflare Registrar](https://cloudflare.com) | ~10€ | — | Prix coûtant, oblige à utiliser leurs DNS |
| **Linode DNS Manager** | N/A | N/A | Gratuit si domaine acheté ailleurs |

### 2.2 Procédure (exemple Namecheap)

```
1. Aller sur namecheap.com
2. Chercher un nom de domaine (ex: "clickmart-store.com")
3. L'ajouter au panier
4. Créer un compte (email + mot de passe)
5. Payer (carte bancaire ou PayPal)
6. ✅ Domaine acheté
```

> **Note** : Le choix du registrar n'a pas d'impact technique. Ce qui compte, c'est la configuration DNS (étape 2).

### 2.3 Alternative : acheter via Linode

Linode vend aussi des domaines directement :

```
Linode Cloud Manager → Domains → Register Domain
```

Avantage : DNS déjà configuré sur Linode, pas besoin de l'étape 2.

---

## 3. Étape 2 : Configurer les DNS (pointer vers Linode)

Une fois le domaine acheté, il faut créer des **enregistrements DNS** pour qu'il pointe vers le serveur Linode.

### 3.1 Principe

```
┌──────────────────┐     DNS     ┌──────────────────┐
│  Utilisateur     │ ──────────► │  clickmart.com   │
│  tape l'URL      │  résolution │  172.239.20.14   │
└──────────────────┘             └──────────────────┘
```

### 3.2 Option A : DNS du registrar (Namecheap, GoDaddy, OVH...)

Dans l'interface d'administration du registrar, aller dans **DNS Management** / **Advanced DNS** et créer ces enregistrements :

```
┌──────┬────────┬──────────────────────┬─────────┐
│ Type │ Host   │ Value                │ TTL     │
├──────┼────────┼──────────────────────┼─────────┤
│ A    │ @      │ 172.239.20.14        │ 3600    │
│ A    │ www    │ 172.239.20.14        │ 3600    │
└──────┴────────┴──────────────────────┴─────────┘
```

```
Exemple visuel (Namecheap) :

Host          Type    Value              TTL
─────────────────────────────────────────────────
@             A       172.239.20.14      Automatic
www           A       172.239.20.14      Automatic
─────────────────────────────────────────────────
```

- **@** = domaine racine (`clickmart.com`)
- **www** = sous-domaine (`www.clickmart.com`)

### 3.3 Option B : Déléguer les DNS à Linode (recommandé)

Si tu veux tout gérer depuis Linode :

1. Aller dans **Linode Cloud Manager → Domains → Create Domain**
2. Entrer le nom de domaine (`clickmart.com`)
3. Linode va fournir des **serveurs de noms** (nameservers) :

```
ns1.linode.com
ns2.linode.com
ns3.linode.com
ns4.linode.com
ns5.linode.com
```

4. Dans l'interface du registrar, remplacer les nameservers par ceux de Linode
5. Les enregistrements A seront gérés dans Linode DNS Manager :

```
Linode Cloud Manager → Domains → clickmart.com → A/AAAA Records

Hostname    Type    Value
─────────────────────────────────
            A       172.239.20.14
www         A       172.239.20.14
```

### 3.4 Vérifier la propagation DNS

La propagation peut prendre de 5 minutes à 48 heures (généralement 15-30 min).

```bash
# Vérifier que le domaine résout vers l'IP
nslookup clickmart.com
# ou
dig clickmart.com +short
# ou en ligne :
# https://www.whatsmydns.net/#A/clickmart.com
```

```
Résultat attendu :
$ dig clickmart.com +short
172.239.20.14
```

Quand le domaine répond sur l'IP, on peut passer à l'étape 3.

---

## 4. Étape 3 : Mettre à jour Nginx (domaine)

### 4.1 Modifier `nginx/default.conf` sur le serveur

Ajouter `server_name` avec le nouveau domaine :

```bash
ssh root@172.239.20.14
nano /opt/clickmart/nginx/default.conf
```

Remplacer la ligne 3 par le domaine :

```nginx
server {
    listen 80;
    server_name clickmart.com www.clickmart.com;

    # Certbot ACME challenge route
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Frontend (React)
    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend (Django)
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django admin
    location /admin/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        proxy_pass http://backend:8000;
    }

    location /media/ {
        alias /media/;
    }
}
```

> **Note** : On garde uniquement le bloc `listen 80` pour l'instant. Le bloc HTTPS sera ajouté à l'étape 6, après avoir obtenu le certificat.

### 4.2 Redémarrer Nginx

```bash
cd /opt/clickmart
docker compose restart nginx
```

### 4.3 Vérifier l'accès HTTP sur le domaine

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://clickmart.com/
# Doit retourner HTTP 200
```

---

## 5. Étape 4 : Mettre à jour le `.env.docker` (ALLOWED_HOSTS)

Django doit accepter les requêtes venant du nouveau domaine.

### 5.1 Sur le serveur

```bash
ssh root@172.239.20.14
nano /opt/clickmart/backend/.env.docker
```

Modifier la ligne `ALLOWED_HOSTS` :

```env
# AVANT
ALLOWED_HOSTS=172.239.20.14,localhost,127.0.0.1,backend

# APRÈS
ALLOWED_HOSTS=clickmart.com,www.clickmart.com,172.239.20.14,localhost,127.0.0.1,backend
```

### 5.2 Redémarrer le backend

```bash
cd /opt/clickmart
docker compose restart backend
```

---

## 6. Étape 5 : Obtenir le certificat SSL (Let's Encrypt)

### 6.1 Principe

```
┌──────────────┐  1. Demande certificat  ┌─────────────────┐
│   Certbot    │ ──────────────────────► │  Let's Encrypt   │
│  (serveur)   │                        │  (autorité SSL)  │
│              │  2. Défi ACME           │                  │
│              │  "Prouve que tu         │                  │
│              │   contrôles le domaine" │                  │
│              │                        │                  │
│              │  3. Let's Encrypt       │                  │
│              │     vérifie le fichier  │                  │
│              │     dans .well-known/   │                  │
│              │     sur clickmart.com   │                  │
│              │                        │                  │
│              │  4. Certificat délivré  │                  │
│              │ ◄────────────────────── │                  │
└──────────────┘                        └─────────────────┘
```

Le défi ACME consiste à créer un fichier temporaire accessible via `http://clickmart.com/.well-known/acme-challenge/...`. Le bloc `location /.well-known/acme-challenge/` dans la config Nginx (déjà présent) permet à Certbot de répondre à ce défi.

### 6.2 Lancer Certbot

```bash
ssh root@172.239.20.14

# Créer les dossiers certbot (déjà fait normalement)
mkdir -p /opt/clickmart/certbot/www /opt/clickmart/certbot/conf

# Installer Certbot
apt update
apt install certbot -y

# Obtenir le certificat (webroot method)
certbot certonly \
  --webroot \
  -w /opt/clickmart/certbot/www \
  -d clickmart.com \
  -d www.clickmart.com \
  --email ton-email@gmail.com \
  --agree-tos \
  --no-eff-email

# Résultat :
# - Certificate saved at /etc/letsencrypt/live/clickmart.com/fullchain.pem
# - Key saved at /etc/letsencrypt/live/clickmart.com/privkey.pem
```

> **`--webroot`** : Certbot place un fichier de validation dans `/opt/clickmart/certbot/www`, et Let's Encrypt vérifie qu'il est accessible via `http://clickmart.com/.well-known/acme-challenge/...`. Pas besoin d'arrêter Nginx.

### 6.3 Résultat attendu

```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/clickmart.com/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/clickmart.com/privkey.pem
This certificate expires on 2026-10-26.
```

### 6.4 Vérifier les certificats

```bash
ls -la /etc/letsencrypt/live/clickmart.com/
# Doit contenir : fullchain.pem, privkey.pem, cert.pem, chain.pem, README
```

---

## 7. Étape 6 : Configurer Nginx pour HTTPS

### 7.1 Remplacer la config Nginx

```bash
ssh root@172.239.20.14
nano /opt/clickmart/nginx/default.conf
```

Remplacer tout le contenu par la config finale :

```nginx
# ── Redirection HTTP → HTTPS ──
server {
    listen 80;
    server_name clickmart.com www.clickmart.com;

    # Certbot ACME challenge (nécessaire pour le renouvellement)
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Tout le reste → rediriger vers HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# ── HTTPS ──
server {
    listen 443 ssl;
    server_name clickmart.com www.clickmart.com;

    ssl_certificate /etc/letsencrypt/live/clickmart.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/clickmart.com/privkey.pem;

    # Frontend (React)
    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend (Django)
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django admin
    location /admin/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /static/;
    }

    location /media/ {
        alias /media/;
    }
}
```

### 7.2 Redémarrer Nginx

```bash
cd /opt/clickmart
docker compose restart nginx
```

---

## 8. Étape 7 : Renouvellement automatique

Les certificats Let's Encrypt expirent après **90 jours**. Il faut un cron pour les renouveler automatiquement.

### 8.1 Configurer le cron sur le serveur

```bash
ssh root@172.239.20.14
crontab -e
```

Ajouter cette ligne (renouvellement 2 fois par jour) :

```
0 3,15 * * * certbot renew --quiet && cd /opt/clickmart && docker compose restart nginx >> /var/log/certbot-renew.log 2>&1
```

### 8.2 Tester le renouvellement (dry-run)

```bash
certbot renew --dry-run
```

```
Résultat attendu :
- - - - - - - - - - - - - - - - - - - - - - - - - -
** DRY RUN: simulating 'certbot renew' close to cert expiry
**          (The test certificates below have not been saved.)

Congratulations, all renewals succeeded. The following certs have been renewed:
  /etc/letsencrypt/live/clickmart.com/fullchain.pem (success)
- - - - - - - - - - - - - - - - - - - - - - - - - -
```

---

## 9. Étape 8 : Vérification finale

### 9.1 Depuis un navigateur

```
https://clickmart.com
https://www.clickmart.com
```

Doit afficher le cadenas 🔒 vert.

### 9.2 Via curl

```bash
# HTTPS doit répondre 200
curl -s -o /dev/null -w "HTTP %{http_code}\n" https://clickmart.com/

# HTTP doit rediriger (301) vers HTTPS
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://clickmart.com/

# Vérifier le certificat
curl -sI https://clickmart.com/ | grep -i "HTTP\|Strict-Transport"
```

### 9.3 Vérifier le grade SSL

Aller sur [https://www.ssllabs.com/ssltest/](https://www.ssllabs.com/ssltest/) et entrer le domaine. Viser un grade **A** ou **A+**.

### 9.4 Vérifier le renouvellement

```bash
# Voir la date d'expiration
certbot certificates

# Résultat :
# Expiry Date: 2026-10-26 (VALID: 89 days)
```

---

## 10. Résumé des commandes

```bash
# ── 1. Vérifier la propagation DNS ──
dig clickmart.com +short

# ── 2. Mettre à jour la config Nginx ──
ssh root@172.239.20.14 "nano /opt/clickmart/nginx/default.conf"
# → Modifier server_name avec le domaine
ssh root@172.239.20.14 "cd /opt/clickmart && docker compose restart nginx"

# ── 3. Mettre à jour ALLOWED_HOSTS ──
ssh root@172.239.20.14 "nano /opt/clickmart/backend/.env.docker"
# → Ajouter clickmart.com,www.clickmart.com dans ALLOWED_HOSTS
ssh root@172.239.20.14 "cd /opt/clickmart && docker compose restart backend"

# ── 4. Obtenir le certificat ──
ssh root@172.239.20.14 "certbot certonly --webroot -w /opt/clickmart/certbot/www -d clickmart.com -d www.clickmart.com --email ton-email@gmail.com --agree-tos --no-eff-email"

# ── 5. Configurer HTTPS ──
# Remplacer nginx/default.conf par la config finale (HTTPS)
ssh root@172.239.20.14 "cd /opt/clickmart && docker compose restart nginx"

# ── 6. Activer le renouvellement automatique ──
ssh root@172.239.20.14 "echo '0 3,15 * * * certbot renew --quiet && cd /opt/clickmart && docker compose restart nginx >> /var/log/certbot-renew.log 2>&1' | crontab -"

# ── 7. Vérifications ──
curl -I https://clickmart.com/
certbot certificates
certbot renew --dry-run
```

---

## Dépannage

### « DNS not yet propagated »

```
Certbot error: DNS problem: NXDOMAIN looking up A for clickmart.com
```

**Solution** : Attendre la propagation DNS (5 min à 48h). Vérifier avec `dig clickmart.com +short`.

### « Connection refused on port 443 »

```
curl: (7) Failed to connect to clickmart.com port 443: Connection refused
```

**Solution** : Vérifier que le port 443 est ouvert dans le **firewall cloud Linode** (pas seulement UFW).

### « Domain name does not resolve »

**Solution** : Vérifier les enregistrements DNS dans l'interface du registrar. S'assurer que les **nameservers** pointent vers le bon service (registrar ou Linode).

### « Certificate not trusted »

**Solution** : Si le certificat vient d'être créé, attendre 1-2 minutes. Vérifier avec `certbot certificates` que le certificat est bien présent.

---

*Guide créé le 28 juillet 2026.*
