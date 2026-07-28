# Phase 1 — Préparation du serveur

## Objectif

Prendre un VPS vierge et le rendre prêt à recevoir l'application :
- SSH fonctionnel
- Docker + Compose + Git installés
- Ports 80 et 443 ouverts (firewall cloud)

## Skills à charger

1. `ssh-connect` — Se connecter, détecter l'OS, vérifier les ressources
2. `docker-install` — Installer Docker, Compose, Git
3. `firewall-guide` — Guider l'utilisateur pour ouvrir les ports

## Déroulement

```
1. ssh-connect
   ├── Tester la connexion SSH
   ├── Détecter l'OS (doit être Ubuntu/Debian)
   └── Vérifier RAM ≥ 1GB, disque ≥ 10GB

2. docker-install
   ├── apt update && apt upgrade
   ├── Installer Git si absent
   ├── curl -fsSL https://get.docker.com | sh
   ├── apt install docker-compose-plugin
   └── Vérifier docker --version, docker compose version

3. firewall-guide
   ├── Détecter le fournisseur VPS
   ├── Afficher les ports à ouvrir (80, 443)
   └── ⏸️ Attendre confirmation utilisateur
```

## Checkpoint

```
✅ SSH : OK
✅ OS : Ubuntu 24.04
✅ Docker : 29.x.x
✅ Docker Compose : v2.x.x
✅ Git : 2.x.x
✅ Ports 80/443 : ouverts (confirmé par l'utilisateur)
```

→ Passer à la Phase 2
