# Skill: health-check

## Rôle

Vérifier que l'application déployée répond correctement sur tous les endpoints.

## Prérequis

- `docker compose up` terminé
- `VPS_IP` connue

## Procédure

### 1. Attendre le démarrage complet

```bash
echo "⏳ Attente du démarrage des services..."
sleep 10
```

Les conteneurs peuvent prendre 10-20 secondes après `docker compose up` pour être prêts
(migrations, collectstatic, gunicorn workers).

### 2. Vérifier l'état des conteneurs

```bash
ssh ${VPS_USER}@${VPS_IP} "cd /opt/${PROJECT_NAME} && docker compose ps"
```

Tous les services doivent être `Up` (pas `Restarting` ni `Exited`).

### 3. Tester les endpoints

```bash
# Frontend (React SPA)
echo -n "Frontend : "
curl -s -o /dev/null -w "%{http_code}" http://${VPS_IP}/
echo " → attendu : 200"

# API (Django DRF)
echo -n "API      : "
curl -s -o /dev/null -w "%{http_code}" http://${VPS_IP}/api/v1/products/
echo " → attendu : 200"

# Admin (Django)
echo -n "Admin    : "
curl -s -o /dev/null -w "%{http_code}" http://${VPS_IP}/admin/login/
echo " → attendu : 200"

# Docs API (DRF Spectacular)
echo -n "Docs     : "
curl -s -o /dev/null -w "%{http_code}" http://${VPS_IP}/api/docs/
echo " → attendu : 200"
```

### 4. Vérifier les logs backend (signes d'erreur)

```bash
ssh ${VPS_USER}@${VPS_IP} "cd /opt/${PROJECT_NAME} && docker compose logs backend --tail=20 | grep -i 'error\|exception\|traceback' || echo '✅ Aucune erreur'"
```

### 5. Vérifier les statics (CSS admin)

```bash
curl -s -o /dev/null -w "Static CSS : %{http_code}\n" http://${VPS_IP}/static/admin/css/login.css
```

Doit retourner 200. Si 404 → le volume `backend/static` n'est pas monté dans nginx.

## Résultat attendu

```
✅ docker compose ps → 5 services Up
✅ Frontend : 200
✅ API      : 200
✅ Admin    : 200
✅ Docs     : 200 (si DRF Spectacular installé)
✅ Static   : 200
✅ Logs     : aucune erreur
```

## Fallback

| Problème | Action |
|---|---|
| HTTP 000 (connexion refusée) | Serveur injoignable, vérifier le firewall cloud |
| HTTP 502 (Bad Gateway) | Backend pas prêt, attendre 30s et réessayer |
| HTTP 404 sur /admin/ | URL mal configurée dans nginx |
| HTTP 404 sur /static/ | Volume static non monté → `docker compose down && up -d` |
| HTTP 500 | Erreur Django → `docker compose logs backend` |
| Container `Restarting` | Crash loop → `docker compose logs <service>` |
| Container `Exited` | Erreur fatale → `docker compose logs <service>` |

## Leçons ClickMart

- Le healthcheck est crucial : après le premier deploy, les ports firewall n'étaient pas ouverts → HTTP 000
- L'admin CSS était cassée (404 sur static) → volume `backend/static:/static:ro` manquant dans nginx
- Le proxy_pass de `/static/` vers gunicorn ne marche pas en prod → utiliser `alias /static/`
- Toujours tester au moins 3 endpoints (frontend, API, admin) pour couvrir tous les services
