# Phase 4 — SSL + Domaine (optionnelle)

## Objectif

Activer HTTPS avec Let's Encrypt et configurer le renouvellement automatique.

## Prérequis

- Phase 1 et 2 terminées (app fonctionnelle en HTTP)
- `DOMAIN` acheté chez un registrar
- `EMAIL` pour Let's Encrypt

## Skills à charger

1. `dns-guide` — Guider la configuration DNS
2. `ssl-setup` — Certbot + Nginx HTTPS + renouvellement

## Déroulement

```
1. dns-guide
   ├── Afficher les enregistrements DNS à créer
   │   A @     → <VPS_IP>
   │   A www   → <VPS_IP>
   ├── Instructions spécifiques au registrar
   └── ⏸️ Attendre propagation DNS
       → dig +short <DOMAIN> doit retourner <VPS_IP>

2. ssl-setup
   ├── Vérifier propagation DNS
   ├── Mettre à jour ALLOWED_HOSTS (.env.docker)
   ├── Mettre à jour server_name Nginx (HTTP)
   ├── Redémarrer backend (--force-recreate)
   ├── docker compose run certbot certonly --webroot
   │   → Certificat dans certbot/conf/live/<DOMAIN>/
   ├── Activer HTTPS dans Nginx
   │   HTTP → redirect 301 vers HTTPS
   │   HTTPS → proxy_pass vers frontend/backend
   ├── docker compose restart nginx
   ├── docker compose up -d certbot (renouvellement auto)
   └── Vérifier HTTP 301 + HTTPS 200
```

## Checkpoint

```
✅ DNS propagé : <DOMAIN> → <VPS_IP>
✅ Certificat Let's Encrypt obtenu
✅ Nginx HTTPS configuré
✅ HTTP → 301 redirect vers HTTPS
✅ HTTPS → 200
✅ Renouvellement auto : certbot service Docker
✅ Expiration : 90 jours
```

## Résultat final

```
🔒 https://<DOMAIN>/
🔒 https://www.<DOMAIN>/

Frontend : https://<DOMAIN>/
API      : https://<DOMAIN>/api/v1/products/
Admin    : https://<DOMAIN>/admin/
Docs     : https://<DOMAIN>/api/docs/
```

## Notes importantes

- **Certbot service Docker** : renouvelle automatiquement (vérification toutes les 12h)
- **Pas de cron host** : tout est géré par le service Docker `certbot`
- **Pas de `apt install certbot`** : l'image Docker contient tout
- **Certificats dans `certbot/conf/`** : volume partagé avec nginx
- **Redémarrage nginx automatique** : `certbot-deploy-hook.sh` après renouvellement
