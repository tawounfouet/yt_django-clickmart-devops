# Skill: firewall-config

## Rôle

Ouvrir automatiquement les ports 80 (HTTP) et 443 (HTTPS) via l'API du fournisseur cloud,
quand un token/CLI est disponible. Sinon, déléguer au skill `firewall-guide`.

## Prérequis

- Fournisseur détecté (skill `provider-detect`)
- Token API ou CLI configurée pour le fournisseur
- `VPS_IP` connue

## Procédure

### 1. Vérifier si l'API est disponible

```bash
case "${PROVIDER}" in
    digitalocean) which doctl >/dev/null 2>&1 && API_READY=true ;;
    linode)       which linode-cli >/dev/null 2>&1 && API_READY=true ;;
    aws)          which aws >/dev/null 2>&1 && API_READY=true ;;
    gcp)          which gcloud >/dev/null 2>&1 && API_READY=true ;;
    azure)        which az >/dev/null 2>&1 && API_READY=true ;;
    hetzner)      which hcloud >/dev/null 2>&1 && API_READY=true ;;
    *)            API_READY=false ;;
esac

if [ "$API_READY" = false ]; then
    echo "⚠️  CLI non configurée pour ${PROVIDER}"
    echo "   → Délégation au skill firewall-guide (instructions manuelles)"
    exit 0
fi
```

### 2. DigitalOcean

```bash
# Récupérer l'ID du droplet
DROPLET_ID=$(doctl compute droplet list --format ID,PublicIPv4 --no-header | grep ${VPS_IP} | awk '{print $1}')

# Créer ou modifier le firewall
doctl compute firewall create \
    --name "web-${PROJECT_NAME}" \
    --inbound-rules "protocol:tcp,ports:22,address:0.0.0.0/0 protocol:tcp,ports:80,address:0.0.0.0/0 protocol:tcp,ports:443,address:0.0.0.0/0" \
    --droplet-ids ${DROPLET_ID}
```

### 3. Linode

```bash
# Lister les firewalls
FIREWALL_ID=$(linode-cli firewalls list --json | jq -r '.[] | select(.label=="web-firewall") | .id')

if [ -z "$FIREWALL_ID" ]; then
    # Créer un nouveau firewall
    FIREWALL_ID=$(linode-cli firewalls create \
        --label "web-firewall" \
        --rules.inbound "[{\"action\":\"ACCEPT\",\"protocol\":\"TCP\",\"ports\":\"22\",\"addresses\":{\"ipv4\":[\"0.0.0.0/0\"]}},{\"action\":\"ACCEPT\",\"protocol\":\"TCP\",\"ports\":\"80\",\"addresses\":{\"ipv4\":[\"0.0.0.0/0\"]}},{\"action\":\"ACCEPT\",\"protocol\":\"TCP\",\"ports\":\"443\",\"addresses\":{\"ipv4\":[\"0.0.0.0/0\"]}}]" \
        --rules.outbound "[{\"action\":\"ACCEPT\",\"protocol\":\"TCP\",\"ports\":\"1-65535\",\"addresses\":{\"ipv4\":[\"0.0.0.0/0\"]}}]" \
        --json | jq -r '.[].id')
fi

# Associer au Linode
LINODE_ID=$(linode-cli linodes list --json | jq -r ".[] | select(.ipv4[]==\"${VPS_IP}\") | .id")
linode-cli firewalls device-create $FIREWALL_ID --id $LINODE_ID --type linode
```

### 4. AWS EC2

```bash
# Récupérer le security group de l'instance
INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=ip-address,Values=${VPS_IP}" --query 'Reservations[0].Instances[0].InstanceId' --output text)
SG_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)

# Ajouter les règles entrantes
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0
```

### 5. Google Cloud

```bash
# Créer une règle de firewall
gcloud compute firewall-rules create "allow-http-${PROJECT_NAME}" \
    --allow tcp:80,tcp:443 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server

# Ajouter le tag à l'instance
INSTANCE_NAME=$(gcloud compute instances list --filter="EXTERNAL_IP=${VPS_IP}" --format="value(name)")
gcloud compute instances add-tags $INSTANCE_NAME --tags http-server
```

### 6. Azure

```bash
# Récupérer le NSG
NIC_ID=$(az vm show -g <RESOURCE_GROUP> -n <VM_NAME> --query 'networkProfile.networkInterfaces[0].id' -o tsv)
NSG_ID=$(az network nic show --ids $NIC_ID --query 'networkSecurityGroup.id' -o tsv)
NSG_NAME=$(az network nsg show --ids $NSG_ID --query 'name' -o tsv)
RG=$(az network nsg show --ids $NSG_ID --query 'resourceGroup' -o tsv)

# Ajouter les règles
az network nsg rule create --resource-group $RG --nsg-name $NSG_NAME \
    --name AllowHTTP --priority 100 --protocol Tcp --destination-port-range 80
az network nsg rule create --resource-group $RG --nsg-name $NSG_NAME \
    --name AllowHTTPS --priority 101 --protocol Tcp --destination-port-range 443
```

### 7. Hetzner

```bash
# Récupérer le serveur
SERVER_ID=$(hcloud server list -o noheader -o columns=id,name,ipv4 | grep ${VPS_IP} | awk '{print $1}')

# Créer un firewall
FIREWALL_ID=$(hcloud firewall create --name "web-${PROJECT_NAME}" -o noheader -o columns=id)
hcloud firewall add-rule $FIREWALL_ID --direction in --protocol tcp --port 80 --source-ips 0.0.0.0/0
hcloud firewall add-rule $FIREWALL_ID --direction in --protocol tcp --port 443 --source-ips 0.0.0.0/0
hcloud firewall add-rule $FIREWALL_ID --direction in --protocol tcp --port 22 --source-ips 0.0.0.0/0

# Appliquer au serveur
hcloud firewall apply-to-resource $FIREWALL_ID --server $SERVER_ID
```

### 8. Vérifier l'ouverture des ports

```bash
sleep 5
curl -s --connect-timeout 5 -o /dev/null -w "%{http_code}" http://${VPS_IP}/ 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Port 80 ouvert et répondant"
else
    echo "⚠️  Port 80 ne répond pas encore (peut prendre quelques secondes)"
fi
```

## Vérification

```
✅ Fournisseur : <NOM>
✅ CLI configurée : <outil>
✅ Ports 80, 443, 22 ajoutés au firewall
✅ curl http://<IP>/ répond (ou en attente)
```

## Fallback

| Problème | Action |
|---|---|
| CLI non installée | Déléguer à `firewall-guide` |
| Token expiré | Demander de reconfigurer la CLI |
| Permission denied (API) | Vérifier les scopes du token |
| Firewall déjà existant | Ajouter les règles au lieu de créer |
| Fournisseur sans API (IONOS) | Déléguer à `firewall-guide` automatiquement |

## Leçons ClickMart

- Le firewall Linode était vide → créé manuellement via le dashboard (pas de token API)
- `linode-cli` nécessite un token avec scope `firewalls:read_write`
- Pour IONOS, aucune API firewall → instructions manuelles obligatoires
- Dans 80% des cas, les utilisateurs n'ont pas la CLI configurée → fallback manuel
- Le message "ports ouverts" est trompeur : le firewall peut accepter mais Docker pas encore prêt
