# AGENTS.md — yt_django-clickmart-devops

> Mis à jour le 29 juillet 2026 — projet fonctionnel, CI/CD actif, SSL configuré

## État du projet

- **Production** : `https://webtech-dev.info` (Linode 172.239.20.14)
- **CI/CD** : GitHub Actions → 78 tests (67 backend + 11 frontend) → déploiement auto
- **Stack** : Django 5.2 + DRF + React 19 + Vite 7 + Docker + Nginx + PostgreSQL 16 + Certbot

## Structure

```
├── backend/          # Django 5.2 (users, products, carts, orders)
│   └── */api/        # API routes par app (urls + views + serializers)
├── frontend/         # React 19 + Vite 7
├── infra/            # Docker/SSL (nginx, certbot, scripts)
│   ├── nginx/        # Reverse proxy HTTP/HTTPS
│   ├── certbot/      # Volumes SSL (conf + www)
│   └── scripts/      # setup-ssl.sh, backup-db.sh, certbot-deploy-hook.sh
├── docs/
│   ├── analyse/      # 6 fichiers d'analyse
│   └── deploy/       # 7 guides opérationnels
└── .github/
    ├── agents/       # Agent de déploiement fullstack
    ├── instructions/ # Instructions par phase
    └── skills/       # 11 skills atomiques
```

## Commandes essentielles

| Commande | Contexte |
|---|---|
| `docker compose up` | Lancer l'app en local |
| `python manage.py test` | 67 tests Django (SQLite en CI) |
| `npm run dev` | Frontend Vite (port 5173) |
| `npm run test` | 11 tests React (vitest) |
| `npm run build` | Build production (dist/) |

## Agent de déploiement

```
@deploy-fullstack
```

Déploie un projet Django + React sur n'importe quel VPS vierge.
Phases : préparation serveur → déploiement → CI/CD (optionnel) → SSL (optionnel).
Documentation : `.github/agents/HOWTO.md`

## Notes importantes

- `ALLOWED_HOSTS` et `CORS_ALLOWED_ORIGINS` sont dynamiques via `config()` + `split(',')`
- Les statics sont servis par Nginx via `alias /static/` (volume partagé), pas par Django
- Certbot est un service Docker (pas de cron host), renouvellement automatique toutes les 12h
- `docker compose restart backend` ne recharge pas les variables d'env → utiliser `--force-recreate`
- `git reset --hard origin/main` dans le CI (pas `git pull`) pour éviter les conflits
- Le user SSH du CI doit avoir les permissions sur `/opt/clickmart` (`chown -R`)
