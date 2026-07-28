#!/bin/bash
set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: ./scripts/setup-ssl.sh <domain> <email>"
    echo "Example: ./scripts/setup-ssl.sh webtech-dev.info admin@webtech-dev.info"
    exit 1
fi

DOMAIN="$1"
EMAIL="$2"

echo "=== 1. Vérification DNS ==="
if ! dig +short "$DOMAIN" | grep -q .; then
    echo "❌ $DOMAIN ne résout pas. Vérifiez les DNS."
    exit 1
fi
echo "✅ $DOMAIN → $(dig +short "$DOMAIN")"

echo ""
echo "=== 2. Obtention du certificat SSL ==="
echo "    (Certbot via Docker Compose — volumes partagés avec Nginx)"
docker compose run --rm certbot certonly --webroot \
    -w /var/www/certbot \
    -d "$DOMAIN" \
    -d "www.$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email
echo "✅ Certificat obtenu"

echo ""
echo "=== 3. Mise à jour Nginx ==="
sed -i '' "s/server_name .*/server_name $DOMAIN www.$DOMAIN;/" nginx/default.conf
echo "✅ nginx/default.conf → server_name $DOMAIN"

echo ""
echo "=== 4. Activation HTTPS ==="
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

echo ""
echo "=== 5. Mise à jour ALLOWED_HOSTS (.env.docker) ==="
if grep -q "^ALLOWED_HOSTS=" backend/.env.docker 2>/dev/null; then
    if ! grep -q "$DOMAIN" backend/.env.docker 2>/dev/null; then
        sed -i '' "s/^ALLOWED_HOSTS=.*/&,$DOMAIN,www.$DOMAIN/" backend/.env.docker
        echo "✅ $DOMAIN ajouté à ALLOWED_HOSTS"
    else
        echo "✅ $DOMAIN déjà dans ALLOWED_HOSTS"
    fi
else
    echo "⚠️  backend/.env.docker non trouvé — à faire manuellement"
fi

echo ""
echo "=== 6. Redémarrage des services ==="
docker compose stop backend
docker compose up -d --force-recreate backend
docker compose restart nginx certbot
sleep 5

echo ""
echo "=== 7. Vérification ==="
echo -n "HTTP  → " && curl -s -o /dev/null -w "%{http_code}\n" "http://$DOMAIN/"
echo -n "HTTPS → " && curl -sk -o /dev/null -w "%{http_code}\n" "https://$DOMAIN/"

echo ""
echo "══════════════════════════════════════════════"
echo "  🎉 SSL activé pour https://$DOMAIN"
echo ""
echo "  Services Docker :"
echo "    certbot — renouvellement auto (toutes les 12h)"
echo "    nginx  — sert HTTPS + redirige HTTP"
echo ""
echo "  Prochaine étape : committer nginx/default.conf"
echo "  $ git add nginx/default.conf && git commit -m 'feat(ssl): enable HTTPS for $DOMAIN'"
echo "══════════════════════════════════════════════"
