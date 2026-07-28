# Skill: ssl-setup

## Rôle

Configurer HTTPS avec Let's Encrypt via le service Docker certbot.
Activer le renouvellement automatique. Mettre à jour Nginx pour le HTTPS.

## Prérequis

- Application déployée et fonctionnelle en HTTP
- Domaine configuré (DNS A → IP du serveur)
- `DOMAIN` et `EMAIL` fournis
- `docker-compose.yml` avec service certbot et volumes configurés
- `infra/nginx/default.conf` avec le bloc `/.well-known/acme-challenge/`

## Procédure

### 1. Vérifier la propagation DNS

```bash
echo "Vérification DNS pour ${DOMAIN}..."
REAL_IP=$(dig +short ${DOMAIN} | tail -1)
if [ "$REAL_IP" != "${VPS_IP}" ]; then
    echo "❌ ${DOMAIN} → ${REAL_IP} (attendu : ${VPS_IP})"
    echo "   Attendez la propagation DNS (5-30 min) et réessayez."
    exit 1
fi
echo "✅ ${DOMAIN} → ${VPS_IP}"
```

### 2. Mettre à jour ALLOWED_HOSTS

```bash
ssh ${VPS_USER}@${VPS_IP} "\
    cd /opt/${PROJECT_NAME} && \
    if ! grep -q '${DOMAIN}' backend/.env.docker; then \
        sed -i 's/^ALLOWED_HOSTS=.*/&,${DOMAIN},www.${DOMAIN}/' backend/.env.docker && \
        echo '✅ ALLOWED_HOSTS mis à jour'; \
    else \
        echo '✅ ${DOMAIN} déjà dans ALLOWED_HOSTS'; \
    fi"
```

### 3. Mettre à jour le server_name Nginx (HTTP d'abord)

```bash
ssh ${VPS_USER}@${VPS_IP} "\
    cd /opt/${PROJECT_NAME} && \
    sed -i 's/server_name .*/server_name ${DOMAIN} www.${DOMAIN};/' infra/nginx/default.conf && \
    docker compose restart nginx && \
    echo '✅ Nginx server_name mis à jour'"
```

### 4. Redémarrer le backend (forcer rechargement ALLOWED_HOSTS)

```bash
ssh ${VPS_USER}@${VPS_IP} "\
    cd /opt/${PROJECT_NAME} && \
    docker compose up -d --force-recreate backend && \
    sleep 5 && \
    echo '✅ Backend redémarré'"
```

> **Leçon ClickMart** : un simple `restart` ne recharge pas les variables d'environnement. Il faut `--force-recreate` ou `down && up`.

### 5. Obtenir le certificat SSL

```bash
ssh ${VPS_USER}@${VPS_IP} "\
    cd /opt/${PROJECT_NAME} && \
    docker compose run --rm certbot certonly --webroot \
        -w /var/www/certbot \
        -d ${DOMAIN} \
        -d www.${DOMAIN} \
        --email ${EMAIL} \
        --agree-tos \
        --no-eff-email"
```

> **Pourquoi Docker et pas `apt install certbot` ?**
> - Zéro installation sur l'hôte
> - Volumes partagés directement avec nginx (pas de `cp`)
> - Reproductible : fonctionne sur n'importe quel serveur avec Docker

### 6. Activer HTTPS dans Nginx

```bash
ssh ${VPS_USER}@${VPS_IP} "cat > /opt/${PROJECT_NAME}/infra/nginx/default.conf << 'NGINX'
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\\\$host\\\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name ${DOMAIN} www.${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }

    location /admin/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }

    location /static/ {
        alias /static/;
    }

    location /media/ {
        alias /media/;
    }
}
NGINX"
```

### 7. Redémarrer Nginx

```bash
ssh ${VPS_USER}@${VPS_IP} "cd /opt/${PROJECT_NAME} && docker compose restart nginx"
sleep 3
```

### 8. Démarrer le service certbot (renouvellement auto)

```bash
ssh ${VPS_USER}@${VPS_IP} "cd /opt/${PROJECT_NAME} && docker compose up -d certbot"
```

Le service certbot tourne en continu :
- Toutes les 12h : `certbot renew --quiet`
- Si renouvellement : `--deploy-hook` → `docker restart nginx`
- `restart: unless-stopped` → survit aux reboots

### 9. Vérification finale

```bash
echo "=== Tests HTTPS ==="
echo -n "HTTP  → " && curl -s -o /dev/null -w "%{http_code}" http://${DOMAIN}/
echo " (attendu : 301)"
echo -n "HTTPS → " && curl -sk -o /dev/null -w "%{http_code}" https://${DOMAIN}/
echo " (attendu : 200)"
echo -n "WWW   → " && curl -sk -o /dev/null -w "%{http_code}" https://www.${DOMAIN}/
echo " (attendu : 200)"
echo -n "API   → " && curl -sk -o /dev/null -w "%{http_code}" https://${DOMAIN}/api/v1/products/
echo " (attendu : 200)"
```

## Vérification

```
✅ DNS propagé : ${DOMAIN} → ${VPS_IP}
✅ ALLOWED_HOSTS mis à jour
✅ Certificat Let's Encrypt obtenu
✅ Nginx configuré pour HTTPS
✅ HTTP → 301 redirect vers HTTPS
✅ HTTPS → 200
✅ Certbot service Docker running (renouvellement auto)
✅ Expiration : 90 jours
```

## Fallback

| Problème | Action |
|---|---|
| DNS pas propagé | Attendre 5-30 min, `dig +short ${DOMAIN}` |
| Certbot: "too many requests" | Rate limiting Let's Encrypt (5/semaine/domaine). Utiliser `--dry-run` d'abord |
| Certbot: connection refused | Nginx pas lancé ou port 80 pas ouvert |
| Certbot: unauthorized | Le défi ACME n'est pas servi. Vérifier `/.well-known/` dans nginx |
| Nginx: certificate not found | Certbot a écrit dans `/etc/letsencrypt` (hôte) au lieu du volume Docker. Relancer avec `docker compose run` |
| Certbot container restart loop | Vérifier les volumes, `docker compose logs certbot` |
| HTTPS 502 | Backend pas prêt, attendre 30s |

## Leçons ClickMart

- `certbot` installé sur l'hôte → certificat dans `/etc/letsencrypt` (hôte) PAS dans le volume Docker → nginx crash
  - **Solution** : utiliser `docker compose run certbot` pour que le volume soit monté
- `docker compose restart backend` ne recharge pas les variables d'environnement
  - **Solution** : `docker compose up -d --force-recreate backend`
- `server_name` nginx doit être mis à jour AVANT le certificat (sinon le défi ACME échoue)
- Le service certbot Docker gère le renouvellement : plus besoin de cron host
- `infra/scripts/certbot-deploy-hook.sh` restart nginx après renouvellement
