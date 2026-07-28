# Skill: provider-detect

## Rôle

Détecter automatiquement le fournisseur VPS (Linode, DigitalOcean, AWS, OVH, IONOS, Hetzner)
pour adapter la configuration (firewall, DNS, instructions spécifiques).

## Prérequis

- SSH fonctionnel sur le serveur
- `curl` disponible localement

## Procédure

### 1. Tenter la détection via metadata endpoints

Chaque fournisseur cloud expose une API metadata accessible uniquement depuis le serveur.
On interroge ces endpoints en SSH :

```bash
# DigitalOcean
ssh ${VPS_USER}@${VPS_IP} "curl -s --connect-timeout 2 http://169.254.169.254/metadata/v1.json 2>/dev/null | grep -q 'digitalocean' && echo 'digitalocean' || true"

# AWS EC2
ssh ${VPS_USER}@${VPS_IP} "curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null | grep -q 'i-' && echo 'aws' || true"

# Google Cloud
ssh ${VPS_USER}@${VPS_IP} "curl -s --connect-timeout 2 -H 'Metadata-Flavor: Google' http://169.254.169.254/computeMetadata/v1/instance/id 2>/dev/null | grep -q '^[0-9]' && echo 'gcp' || true"

# Azure
ssh ${VPS_USER}@${VPS_IP} "curl -s --connect-timeout 2 -H 'Metadata: true' http://169.254.169.254/metadata/instance?api-version=2021-02-01 2>/dev/null | grep -q 'azure' && echo 'azure' || true"

# OVH / OpenStack
ssh ${VPS_USER}@${VPS_IP} "curl -s --connect-timeout 2 http://169.254.169.254/openstack/latest/meta_data.json 2>/dev/null | grep -q 'uuid' && echo 'ovh' || true"
```

### 2. Détection heuristique (si pas de metadata)

Si aucun endpoint ne répond, utiliser des méthodes indirectes :

```bash
# Vérifier le reverse DNS
RDNS=$(dig +short -x ${VPS_IP} 2>/dev/null | tail -1)

# Vérifier le hostname
HOSTNAME=$(ssh ${VPS_USER}@${VPS_IP} "hostnamectl --static 2>/dev/null || hostname")

# Vérifier les infos système
SYSINFO=$(ssh ${VPS_USER}@${VPS_IP} "cat /sys/class/dmi/id/product_name 2>/dev/null || echo 'unknown'")
```

### 3. Table de correspondance

```
┌──────────────────────────────────────────────────────────────────────┐
│ Indice                          │ Fournisseur probable               │
├─────────────────────────────────┼────────────────────────────────────┤
│ *.digitalocean.com (RDNS)       │ DigitalOcean                       │
│ *.compute.amazonaws.com (RDNS)  │ AWS EC2                            │
│ *.bc.googleusercontent.com      │ Google Cloud                       │
│ *.cloudapp.azure.com (RDNS)     │ Azure                              │
│ *.linode.com (RDNS)             │ Linode                             │
│ members.linode.com (RDNS)       │ Linode                             │
│ localhost / pas de RDNS         │ IONOS / OVH / Hetzner              │
│ *.ovh.net (RDNS)                │ OVH                                │
│ *.your-server.de (RDNS)         │ Hetzner                            │
│ KVM / QEMU (product_name)       │ VPS générique (Linode, OVH, etc.)  │
│ VMware Virtual Platform         │ VPS générique                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4. Logique de décision

```bash
detect_provider() {
    # Méthode 1 : Metadata endpoints
    PROVIDER=$(ssh ${VPS_USER}@${VPS_IP} "
        curl -s --connect-timeout 2 http://169.254.169.254/metadata/v1.json 2>/dev/null | grep -q 'digitalocean' && echo 'digitalocean' && exit 0
        curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null | grep -q 'i-' && echo 'aws' && exit 0
        curl -s --connect-timeout 2 -H 'Metadata-Flavor: Google' http://169.254.169.254/computeMetadata/v1/instance/id 2>/dev/null | grep -q '^[0-9]' && echo 'gcp' && exit 0
        curl -s --connect-timeout 2 -H 'Metadata: true' http://169.254.169.254/metadata/instance?api-version=2021-02-01 2>/dev/null | grep -q 'azure' && echo 'azure' && exit 0
        curl -s --connect-timeout 2 http://169.254.169.254/openstack/latest/meta_data.json 2>/dev/null | grep -q 'uuid' && echo 'ovh' && exit 0
    " 2>/dev/null)

    if [ -n "$PROVIDER" ]; then
        echo "$PROVIDER"
        return
    fi

    # Méthode 2 : Reverse DNS
    RDNS=$(dig +short -x ${VPS_IP} 2>/dev/null)
    case "$RDNS" in
        *digitalocean*) echo "digitalocean" ;;
        *amazonaws*)    echo "aws" ;;
        *google*)       echo "gcp" ;;
        *cloudapp*)     echo "azure" ;;
        *linode*)       echo "linode" ;;
        *ovh*)          echo "ovh" ;;
        *your-server*)  echo "hetzner" ;;
        *)              echo "unknown" ;;
    esac
}
```

## Résultat

```
Fournisseur : <digitalocean|linode|aws|gcp|azure|ovh|hetzner|ionos|unknown>
Méthode     : <metadata|rdns|default>
```

## Comportement selon le fournisseur

| Fournisseur | Firewall API | Metadata | Spécificités |
|---|---|---|---|
| DigitalOcean | ✅ `doctl` | ✅ | `doctl compute firewall` |
| Linode | ✅ `linode-cli` | ❌ | RDNS `*.linode.com` |
| AWS | ✅ `aws-cli` | ✅ | Security groups |
| GCP | ✅ `gcloud` | ✅ | Firewall rules |
| Azure | ✅ `az-cli` | ✅ | Network security groups |
| OVH | ⚠️ API complexe | ✅ OpenStack | Portail web recommandé |
| IONOS | ❌ Pas d'API | ❌ | Portail web uniquement |
| Hetzner | ✅ `hcloud` | ❌ | RDNS `*.your-server.de` |
| Inconnu | ❌ | ❌ | Instructions manuelles |

## Fallback

| Problème | Action |
|---|---|
| Aucun endpoint ne répond | Tenter la détection par RDNS |
| RDNS ne donne rien | Demander à l'utilisateur → "unknown" |
| Fournisseur "unknown" | Utiliser les instructions génériques (firewall-guide.md) |

## Leçons ClickMart

- Linode : pas de metadata endpoint, détecté via RDNS (`*.linode.com`)
- Le firewall Linode est au niveau hyperviseur (pas accessible en SSH)
- IONOS : pas d'API, tout se fait via le portail web
- La détection est fiable à ~90% (les 10% restants = instructions manuelles)
