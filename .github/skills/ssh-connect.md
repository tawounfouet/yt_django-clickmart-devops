# Skill: ssh-connect

## Rôle

Se connecter en SSH au serveur, détecter l'OS, vérifier les ressources minimales.

## Prérequis

- `VPS_IP` : adresse IP du serveur
- `VPS_USER` : utilisateur SSH (root par défaut)
- `SSH_KEY` : chemin vers la clé privée (~/.ssh/id_rsa par défaut, optionnel)

## Procédure

### 1. Tester la connexion SSH

```bash
SSH_CMD="ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no"
[ -n "$SSH_KEY" ] && SSH_CMD="$SSH_CMD -i $SSH_KEY"
$SSH_CMD ${VPS_USER}@${VPS_IP} "echo SSH_OK"
```

Si la commande ne retourne pas `SSH_OK` → **ARRÊT**. Vérifier l'IP, le user, la clé.

### 2. Détecter l'OS et la version

```bash
$SSH_CMD ${VPS_USER}@${VPS_IP} "cat /etc/os-release | grep -E '^NAME=|^VERSION_ID='"
```

Résultat attendu :
```
NAME="Ubuntu"
VERSION_ID="24.04"
```

Si l'OS n'est pas Ubuntu/Debian → avertir que le déploiement peut échouer, proposer de continuer.

### 3. Vérifier les ressources

```bash
$SSH_CMD ${VPS_USER}@${VPS_IP} "echo '=== RAM ===' && free -h | grep Mem && echo '=== DISK ===' && df -h / | tail -1 && echo '=== CPU ===' && nproc"
```

Minimum requis :
- RAM ≥ 1 Go
- Disque ≥ 10 Go disponibles
- CPU ≥ 1 core

Si insuffisant → avertir, le build Docker peut échouer.

### 4. Vérifier l'état du système

```bash
$SSH_CMD ${VPS_USER}@${VPS_IP} "echo '=== Uptime ===' && uptime && echo '=== Deja installe ===' && which docker git 2>/dev/null || echo 'Serveur vierge'"
```

## Vérification

```
✅ SSH fonctionnel
✅ OS : Ubuntu 24.04
✅ RAM : >1GB, DISK : >10GB
✅ Serveur vierge ou outils détectés
```

## Fallback

| Problème | Action |
|---|---|
| SSH timeout | Vérifier que l'IP est correcte, que le serveur est allumé |
| Permission denied | Vérifier la clé SSH, proposer `ssh-copy-id` |
| OS non supporté | Lister les OS supportés (Ubuntu 22.04/24.04, Debian 11/12) |
| Ressources insuffisantes | Proposer un VPS avec plus de RAM/disque |

## Leçons ClickMart

- Le serveur Linode était Ubuntu 24.04 vierge → ssh-connect OK en 2 secondes
- Le firewall cloud était INACTIF au départ → firewall-guide nécessaire
- La clé était `~/.ssh/id_rsa` (détectée automatiquement)
