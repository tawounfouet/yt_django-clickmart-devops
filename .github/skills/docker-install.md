# Skill: docker-install

## Rôle

Installer Docker, Docker Compose (plugin), et Git sur un serveur Ubuntu/Debian vierge.

## Prérequis

- SSH fonctionnel (skill ssh-connect exécuté)
- OS Ubuntu 22.04+ ou Debian 11+

## Procédure

### 1. Mettre à jour les paquets système

```bash
ssh ${VPS_USER}@${VPS_IP} "apt update && apt upgrade -y"
```

### 2. Installer Git (si absent)

```bash
ssh ${VPS_USER}@${VPS_IP} "which git || apt install -y git"
```

### 3. Installer Docker via le script officiel

```bash
ssh ${VPS_USER}@${VPS_IP} "curl -fsSL https://get.docker.com | sh"
```

Ce script :
- Détecte l'OS automatiquement
- Ajoute le dépôt Docker officiel
- Installe docker-ce, docker-ce-cli, containerd.io
- Active et démarre le service Docker

### 4. Installer le plugin Docker Compose

```bash
ssh ${VPS_USER}@${VPS_IP} "apt install -y docker-compose-plugin"
```

> **Note** : on utilise le **plugin** Compose (`docker compose`), pas le binaire standalone (`docker-compose`). Le plugin est maintenu par Docker et intégré à la CLI.

### 5. Vérifier les versions

```bash
ssh ${VPS_USER}@${VPS_IP} "docker --version && docker compose version && git --version"
```

Résultat attendu :
```
Docker version 2x.x.x
Docker Compose version v2.x.x
git version 2.x.x
```

### 6. (Optionnel) Ajouter l'utilisateur au groupe docker

Si l'utilisateur n'est pas root :
```bash
ssh ${VPS_USER}@${VPS_IP} "usermod -aG docker ${VPS_USER}"
# L'utilisateur doit se reconnecter pour que le groupe prenne effet
```

## Vérification

```
✅ Docker <version> installé
✅ Docker Compose v<version> installé
✅ Git <version> installé
```

## Fallback

| Problème | Action |
|---|---|
| `curl` non trouvé | `apt install -y curl` |
| get.docker.com inaccessible | Installation manuelle via apt (étapes détaillées) |
| Docker déjà installé | Vérifier la version, proposer de continuer sans réinstaller |
| `docker compose` plante | Vérifier que le plugin est bien installé (`docker compose version`) |
| Permission denied (docker) | Ajouter l'utilisateur au groupe docker OU utiliser sudo |

## Leçons ClickMart

- Sur Ubuntu 24.04, Git était déjà installé → l'étape `which git` évite une réinstallation inutile
- Le script `get.docker.com` a installé Docker + Compose + plugins en une seule commande (~30s)
- `docker compose version` (avec espace) = plugin. `docker-compose version` (avec tiret) = standalone. On utilise le plugin.
