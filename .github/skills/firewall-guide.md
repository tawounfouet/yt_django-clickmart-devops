# Skill: firewall-guide

## Rôle

Guider l'utilisateur pour ouvrir les ports 80 (HTTP) et 443 (HTTPS) dans le firewall
cloud du fournisseur VPS. L'agent ne peut PAS le faire automatiquement sans token API.

## Prérequis

- Docker installé sur le serveur
- `docker-compose.yml` avec nginx exposant les ports 80:80 et 443:443

## Procédure

### 1. Détecter le fournisseur VPS

```bash
# Essayer les endpoints de metadata cloud
curl -s --connect-timeout 2 http://169.254.169.254/metadata/v1.json 2>/dev/null | grep -q 'digitalocean' && echo "DigitalOcean"
curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/ 2>/dev/null | grep -q 'ami-id' && echo "AWS EC2"
curl -s --connect-timeout 2 http://169.254.169.254/openstack/latest/meta_data.json 2>/dev/null && echo "OVH/OpenStack"

# Si pas de metadata, détection heuristique
ssh ${VPS_USER}@${VPS_IP} "hostnamectl 2>/dev/null | grep -i 'chassis\|deployment\|virtual'" || true

# Fallback : reverse DNS
dig +short -x ${VPS_IP} 2>/dev/null
```

### 2. Afficher les instructions selon le fournisseur

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   📋 PORTS À OUVRIR DANS VOTRE FIREWALL CLOUD              │
│                                                             │
│   Fournisseur : <NOM_DETECTE>                               │
│   IP serveur  : <VPS_IP>                                    │
│                                                             │
│   Règles entrantes à ajouter :                              │
│                                                             │
│   ┌──────────┬──────────┬──────────────────────┐            │
│   │ Action   │ Protocole│ Port   │ Source      │            │
│   ├──────────┼──────────┼────────┼─────────────┤            │
│   │ ACCEPT   │ TCP      │ 22     │ 0.0.0.0/0   │ (SSH)     │
│   │ ACCEPT   │ TCP      │ 80     │ 0.0.0.0/0   │ (HTTP)    │
│   │ ACCEPT   │ TCP      │ 443    │ 0.0.0.0/0   │ (HTTPS)   │
│   └──────────┴──────────┴────────┴─────────────┘            │
│                                                             │
│   ⚠️  Ne PAS ouvrir les ports 8000 et 5173.                │
│   Nginx est le seul point d'entrée (reverse proxy).         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3. Instructions par fournisseur

#### Linode
```
Cloud Manager → Firewalls → Create Firewall
→ Add inbound rules : TCP 22, 80, 443
→ Apply to Linode : <VPS_IP>
```

#### DigitalOcean
```
Networking → Firewalls → Create Firewall
→ Inbound Rules : SSH (22), HTTP (80), HTTPS (443)
→ Apply to Droplet : <VPS_IP>
```
Ou via CLI : `doctl compute firewall create --inbound-rules "..."`

#### AWS EC2
```
EC2 → Security Groups → <sg-xxxxx> → Edit inbound rules
→ Add : HTTP (80) 0.0.0.0/0, HTTPS (443) 0.0.0.0/0
```
Ou via CLI : `aws ec2 authorize-security-group-ingress --group-id <sg> --protocol tcp --port 80 --cidr 0.0.0.0/0`

#### IONOS
```
Cloud Panel → Network → Firewall Policies
→ Add rule : TCP 80, TCP 443
```

#### OVH
```
OVHcloud Control Panel → Public Cloud → Firewall
→ Add rules : 22, 80, 443
```

### 4. Attendre confirmation

```bash
echo "Une fois les ports ouverts, tapez 'ok' pour continuer."
read -r CONFIRMATION
```

### 5. Vérifier que les ports sont ouverts

```bash
# Test HTTP depuis la machine locale
curl -s --connect-timeout 5 -o /dev/null -w "%{http_code}" http://${VPS_IP}/ 2>/dev/null

# Si 000 → ports pas encore ouverts
# Si 200 → OK
```

## Pourquoi seuls les ports 80 et 443 sont nécessaires

```
Avec nginx reverse proxy :
  Internet → Nginx :80/:443 → /api/*    → backend:8000  (interne Docker)
                              → /admin/*  → backend:8000
                              → /          → frontend:80   (interne Docker)

Sans nginx (déprécié) :
  Internet → backend:8000 (exposé directement, dangereux)
  Internet → frontend:5173 (dev server, pas pour la prod)
```

## Vérification

```
✅ Instructions fournies à l'utilisateur
✅ Utilisateur a confirmé l'ouverture des ports
✅ curl http://<IP>/ → HTTP 200 (ou au moins pas timeout)
```

## Fallback

| Problème | Action |
|---|---|
| Fournisseur non détecté | Afficher les instructions génériques |
| Ports déjà ouverts | Passer à l'étape suivante directement |
| Firewall local (UFW) actif | `ufw allow 80/tcp && ufw allow 443/tcp` |

## Leçons ClickMart

- Le firewall Linode était INACTIF au départ → on a ouvert 22, 80, 443
- Les ports 8000 et 5173 du tutoriel YouTube étaient OBSOLÈTES (nginx gère tout)
- HTTP 000 depuis l'extérieur → firewall cloud, pas UFW (UFW était inactif)
- Le firewall cloud est au niveau hyperviseur (pas accessible en SSH)
- IONOS n'a pas d'API firewall publique → instructions manuelles obligatoires
