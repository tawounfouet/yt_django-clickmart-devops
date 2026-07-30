# 7. Rôle `ssl_certbot` — Ansible ClickMart

> **Mise à jour** : 30 juillet 2026

---

## Responsabilité

Obtenir les certificats Let's Encrypt et configurer Nginx en HTTPS, y compris le bootstrap initial sur un serveur sans certificats.

---

## Le problème du bootstrap SSL

Sur un VPS vierge, les certificats Let's Encrypt n'existent pas. Or, le fichier `infra/nginx/prod.conf` (config Nginx) référence des certificats aux chemins `/etc/letsencrypt/live/...` — ce qui fait planter Nginx au démarrage s'ils n'existent pas.

**Solution** : bootstrap en deux phases.

```
Phase 1 : HTTP-only
  ─ Déploiement de prod.bootstrap.conf (sans SSL)
  ─ Démarrage de Nginx
  ─ Certbot écrit les challenges ACME

Phase 2 : HTTPS
  ─ Restauration de prod.conf depuis git
  ─ Redémarrage de Nginx
  ─ Certbot en mode renouvellement (service)
```

---

## Tâches (100 lignes)

### Vérification DNS

```yaml
- dig +short {{ domain }}
  delegate_to: localhost
  become: no
  failed_when: dns_result.stdout != ansible_facts.default_ipv4.address
```

Vérifie que le domaine pointe bien vers le serveur cible. Si non, le rôle échoue immédiatement.

### Vérification certificats existants

```yaml
- stat:
    path: /opt/clickmart/infra/certbot/conf/live/{{ domain }}/fullchain.pem
  register: cert_file
```

Toutes les tâches suivantes sont conditionnées par `when: not cert_file.stat.exists`. Si les certificats existent déjà, le rôle passe directement aux étapes de restauration HTTPS.

### Phase 1 : Bootstrap HTTP

```yaml
# 1. Déploie le template HTTP-only
- template:
    src: prod.bootstrap.conf.j2
    dest: /opt/clickmart/infra/nginx/prod.conf

# 2. Crée le webroot
- file: /opt/clickmart/infra/certbot/www (mode 0755)

# 3. Démarre Nginx avec la config bootstrap
- docker_compose_v2:
    services: [nginx]
    pull: never
```

Le template `prod.bootstrap.conf.j2` :

```nginx
server {
    listen 80;
    server_name {{ domain }} www.{{ domain }};

    resolver 127.0.0.11 valid=30s;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://frontend:80;
        ...
    }

    location /api/ {
        set $backend_upstream backend:8000;
        proxy_pass http://$backend_upstream;
        ...
    }

    location /static/  { alias /static/; }
    location /uploads/ { alias /uploads/; }
}
```

C'est un serveur HTTP seul (port 80) qui :
- Sert les challenges ACME depuis `/var/www/certbot`
- Fait le proxy vers le frontend et l'API normalement
- Utilise le resolver DNS Docker interne (`127.0.0.11`)

### Attente de Nginx

```yaml
- uri:
    url: "http://{{ domain }}/"
    status_code: 200
  retries: 10
  delay: 3
  until: nginx_ready.status == 200
```

Boucle de polling avec `retries × delay = 30s` max jusqu'à ce que Nginx réponde.

### Obtention certificat

```yaml
- docker_container:
    name: certbot-tmp
    image: certbot/certbot
    network_mode: host
    command: >
      certonly --webroot -w /var/www/certbot
      -d {{ domain }} -d www.{{ domain }}
      --email {{ admin_email }}
      --agree-tos --no-eff-email
    volumes:
      - /opt/clickmart/infra/certbot/conf:/etc/letsencrypt
      - /opt/clickmart/infra/certbot/www:/var/www/certbot
    cleanup: yes
    detach: no
```

- `network_mode: host` : accède directement aux ports du serveur
- `cleanup: yes` : supprime le conteneur après exécution
- `detach: no` : le playbook attend la fin de la commande

### Phase 2 : Passage en HTTPS

```yaml
# Restaure la config HTTPS depuis git
- command: git -C /opt/clickmart checkout -- infra/nginx/prod.conf
  become_user: deploy

# Redémarre Nginx avec la config HTTPS
- docker_compose_v2:
    services: [nginx]
    state: restarted

# Lance certbot en mode renouvellement
- docker_compose_v2:
    services: [certbot]
    state: present
```

---

## Comportement idempotent

- Si les certificats existent déjà (`cert_file.stat.exists` = true) → les tâches de bootstrap sont ignorées, le rôle se contente de restaurer HTTPS et redémarrer Nginx.
- Si les certificats n'existent pas → bootstrap complet (HTTP → Certbot → HTTPS).

---

## Renouvellement automatique

Le service `certbot` du `docker-compose.prod.yml` lance un renouvellement toutes les 12 heures. Les certificats Let's Encrypt ont une validité de 90 jours.
