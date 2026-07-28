# Skill: dns-guide

## Rôle

Guider l'utilisateur pour configurer les enregistrements DNS (A records)
pointant vers l'IP du serveur. L'agent ne peut pas le faire automatiquement
sans token API du registrar.

## Prérequis

- `VPS_IP` connue
- `DOMAIN` acheté chez un registrar
- Accès au panneau d'administration DNS du registrar

## Procédure

### 1. Lister les enregistrements DNS à créer

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   📋 ENREGISTREMENTS DNS À CONFIGURER                      │
│                                                             │
│   Domaine : ${DOMAIN}                                        │
│   IP      : ${VPS_IP}                                       │
│                                                             │
│   ┌──────┬────────┬──────────────────┬─────────┐            │
│   │ Type │ Host   │ Value            │ TTL     │            │
│   ├──────┼────────┼──────────────────┼─────────┤            │
│   │ A    │ @      │ ${VPS_IP}        │ 3600    │            │
│   │ A    │ www    │ ${VPS_IP}        │ 3600    │            │
│   └──────┴────────┴──────────────────┴─────────┘            │
│                                                             │
│   • @  = domaine racine (${DOMAIN})                         │
│   • www = sous-domaine (www.${DOMAIN})                      │
│   • TTL = 3600 secondes (1 heure) — réduire à 300           │
│           pendant la configuration, remonter après          │
│                                                             │
│   ⚠️  Ne pas supprimer les enregistrements MX/TXT           │
│   si vous utilisez les emails du registrar.                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Instructions par registrar

#### Namecheap

```
Domain List → ${DOMAIN} → Manage → Advanced DNS

→ Supprimer ou modifier l'enregistrement A @ existant
→ Add New Record :
    Type : A Record
    Host : @
    Value : ${VPS_IP}
    TTL : Automatic

→ Add New Record :
    Type : A Record
    Host : www
    Value : ${VPS_IP}
    TTL : Automatic
```

#### GoDaddy

```
My Products → ${DOMAIN} → DNS → Manage Records

→ Edit l'enregistrement A @ → ${VPS_IP}
→ Add : Type A, Name www, Value ${VPS_IP}
```

#### IONOS

```
Domaines & SSL → ${DOMAIN} → DNS

→ Modifier l'enregistrement A @ → ${VPS_IP}
→ Ajouter un enregistrement :
    Type : A
    Nom d'hôte : www
    Pointe vers : ${VPS_IP}

⚠️  Si un service "Default Site" est actif, IONOS demande
    confirmation pour le désactiver. Accepter.
    Les enregistrements mail (MX, TXT) ne seront PAS touchés.
```

#### OVH

```
Web Cloud → Domaines → ${DOMAIN} → Zone DNS

→ Modifier l'entrée A → ${VPS_IP}
→ Ajouter une entrée :
    Type : A
    Sous-domaine : www
    Cible : ${VPS_IP}
```

#### Cloudflare

```
${DOMAIN} → DNS → Records

→ Edit l'enregistrement A @ → ${VPS_IP}
→ Add Record :
    Type : A
    Name : www
    IPv4 : ${VPS_IP}
    Proxy : Désactivé (DNS only) pendant la config SSL
```

#### Linode DNS Manager

```
Domains → ${DOMAIN} → A/AAAA Records

→ Edit l'enregistrement A → ${VPS_IP}
→ Add A Record :
    Hostname : www
    Value : ${VPS_IP}
```

### 3. Vérifier la propagation DNS

```bash
echo "⏳ Attente de la propagation DNS (5-30 minutes)..."
for i in $(seq 1 12); do
    IP=$(dig +short ${DOMAIN} | tail -1)
    if [ "$IP" = "${VPS_IP}" ]; then
        echo "✅ DNS propagé après $((i * 10)) secondes"
        break
    fi
    echo "   Essai $i/12 : ${DOMAIN} → ${IP:-non résolu}"
    sleep 10
done
```

### 4. Vérifier aussi www

```bash
WWW_IP=$(dig +short www.${DOMAIN} | tail -1)
if [ "$WWW_IP" = "${VPS_IP}" ]; then
    echo "✅ www.${DOMAIN} → ${VPS_IP}"
else
    echo "⚠️  www.${DOMAIN} → ${WWW_IP:-non résolu} — vérifier l'enregistrement A www"
fi
```

## Vérification

```
✅ ${DOMAIN} → ${VPS_IP}
✅ www.${DOMAIN} → ${VPS_IP}
```

## Fallback

| Problème | Action |
|---|---|
| DNS ne propage pas après 30 min | Vérifier les nameservers (NS) du domaine |
| Nameservers pointent vers l'ancien hébergeur | Changer les NS vers le registrar ou Linode |
| AAAA (IPv6) interfère | Supprimer l'enregistrement AAAA si pas d'IPv6 |
| "Default Site" sur IONOS | Accepter la désactivation, les mails sont préservés |
| Conflit avec des enregistrements existants | Ne supprimer que les A/AAAA, garder MX/TXT/CNAME |

## Conseils

- **Réduire le TTL à 300** (5 min) avant de changer les DNS pour accélérer la propagation
- **Vérifier avec plusieurs résolveurs** : `dig @8.8.8.8`, `dig @1.1.1.1`
- **whatsmydns.net** : outil en ligne pour vérifier la propagation mondiale
- **Attendre 5 min** entre la config DNS et le setup SSL (Let's Encrypt vérifie le DNS)

## Leçons ClickMart

- Domaine acheté chez IONOS → DNS configuré en 2 minutes (A @ + A www → IP)
- Le "Default Site" IONOS bloquait la modification → accepter la désactivation
- Propagation quasi-instantanée (IONOS → 30 secondes)
- Les enregistrements mail (MX, SPF, DKIM) n'ont PAS été touchés
- `dig +short webtech-dev.info` a retourné la bonne IP immédiatement
