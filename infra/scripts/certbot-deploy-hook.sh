#!/bin/sh
# Appelé par certbot après un renouvellement réussi
# Redémarre le container nginx pour charger les nouveaux certificats
NGINX_ID=$(docker ps -q --filter name=nginx 2>/dev/null | head -1)
if [ -n "$NGINX_ID" ]; then
    docker restart "$NGINX_ID"
    echo "$(date): nginx restarted after certificate renewal"
fi
