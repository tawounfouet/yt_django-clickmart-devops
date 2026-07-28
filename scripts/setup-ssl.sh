#!/bin/bash
set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: ./setup-ssl.sh <domain> <email>"
    echo "Example: ./setup-ssl.sh webtech-dev.info admin@webtech-dev.info"
    exit 1
fi

DOMAIN="$1"
EMAIL="$2"
SERVER_DIR="/opt/clickmart"

echo "=== 1. Vérification DNS ==="
if ! dig +short "$DOMAIN" | grep -q .; then
    echo "❌ $DOMAIN ne résout pas encore. Vérifiez les DNS."
    exit 1
fi
echo "✅ $DOMAIN → $(dig +short "$DOMAIN")"

echo "=== 2. Mise à jour ALLOWED_HOSTS ==="
ssh "$SERVER_USER@$SERVER_HOST" "grep -q '$DOMAIN' $SERVER_DIR/backend/.env.docker || sed -i \"s/ALLOWED_HOSTS=.*/&,$DOMAIN,www.$DOMAIN/\" $SERVER_DIR/backend/.env.docker"
echo "✅ ALLOWED_HOSTS mis à jour"

echo "=== 3. Mise à jour Nginx (server_name) ==="
sed -i '' "s/server_name .*/server_name $DOMAIN www.$DOMAIN;/" nginx/default.conf
echo "✅ nginx/default.conf mis à jour"

echo "=== 4. Obtention du certificat SSL ==="
echo "   (Certbot via Docker pour utiliser les volumes partagés)"
ssh "$SERVER_USER@$SERVER_HOST" "docker run --rm \
    -v $SERVER_DIR/certbot/www:/var/www/certbot \
    -v $SERVER_DIR/certbot/conf:/etc/letsencrypt \
    certbot/certbot certonly --webroot \
    -w /var/www/certbot \
    -d $DOMAIN \
    -d www.$DOMAIN \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email"
echo "✅ Certificat obtenu"

echo "=== 5. Activation HTTPS dans Nginx ==="
cat > nginx/default.conf << NGINX
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /admin/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias /static/;
    }

    location /media/ {
        alias /media/;
    }
}
NGINX

echo "=== 6. Déploiement de la config Nginx + redémarrage ==="
scp nginx/default.conf "$SERVER_USER@$SERVER_HOST:$SERVER_DIR/nginx/default.conf"
ssh "$SERVER_USER@$SERVER_HOST" "\
    cd $SERVER_DIR && \
    docker compose stop backend && \
    docker compose up -d --force-recreate backend && \
    docker compose restart nginx && \
    sleep 3 && \
    echo '=== Test HTTP ===' && \
    curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://$DOMAIN/ && \
    echo '=== Test HTTPS ===' && \
    curl -sk -o /dev/null -w 'HTTP %{http_code}\n' https://$DOMAIN/ && \
    echo '✅ SSL activé'"

echo ""
echo "🎉 Configuration SSL terminée pour https://$DOMAIN"
echo "   Renouvellement auto : déjà configuré (cron 2×/jour)"
echo "   Expiration : dans 90 jours"
