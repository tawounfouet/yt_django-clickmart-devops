# 6. Rôle `clickmart_app` — Ansible ClickMart

> **Mise à jour** : 30 juillet 2026

---

## Responsabilité

Cloner le dépôt, générer le fichier `.env.prod` à partir d'un template Jinja2, lancer Docker Compose.

---

## Tâches (62 lignes)

### Clone du dépôt

```yaml
- git:
    repo: https://github.com/tawounfouet/yt_django-clickmart-devops.git
    dest: /opt/clickmart
    version: main
    force: yes
  become_user: deploy
```

`force: yes` écrase les modifications locales — utile pour un re-déploiement (équivalent `git reset --hard` + `git pull`).

Le répertoire `/opt/clickmart` est créé en amont (owner `deploy:deploy`, mode `0755`).

### Template Jinja2 `.env.prod`

```yaml
- template:
    src: .env.prod.j2
    dest: /opt/clickmart/backend/.envs/.prod
    owner: deploy
    group: deploy
    mode: 0600
```

Le fichier source `roles/clickmart_app/templates/.env.prod.j2` :

```jinja2
SECRET_KEY={{ secret_key }}
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS={{ domain }},www.{{ domain }},{{ ansible_facts.default_ipv4.address }},localhost
CORS_ALLOWED_ORIGINS=https://{{ domain }},https://www.{{ domain }}

DATABASE_URL=postgres://{{ db_user }}:{{ db_password }}@{{ db_host }}:{{ db_port }}/{{ db_name }}?sslmode=require

CELERY_BROKER_URL=redis://:{{ redis_password }}@{{ redis_host }}:6379/0
CELERY_RESULT_BACKEND=redis://:{{ redis_password }}@{{ redis_host }}:6379/1

MEDIA_STORAGE_BACKEND={{ media_storage }}
{% if media_storage == 'cloudinary' %}
CLOUDINARY_CLOUD_NAME={{ cloudinary_cloud }}
CLOUDINARY_API_KEY={{ cloudinary_api_key }}
CLOUDINARY_API_SECRET={{ cloudinary_api_secret }}
{% endif %}

EMAIL_BACKEND_TYPE={{ email_backend }}
{% if email_backend == 'resend' %}
RESEND_API_KEY={{ resend_api_key }}
{% endif %}
DEFAULT_FROM_EMAIL=hello@{{ domain }}
```

**Rendu** (exemple) :

```
SECRET_KEY=SECRET_KEY_PLACEHOLDER
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS=webtech-dev.info,www.webtech-dev.info,172.239.20.14,localhost
CORS_ALLOWED_ORIGINS=https://webtech-dev.info,https://www.webtech-dev.info

DATABASE_URL=postgres://postgres:DB_PASSWORD_PLACEHOLDER

CELERY_BROKER_URL=redis://:REDIS_PASSWORD_PLACEHOLDER
CELERY_RESULT_BACKEND=redis://:REDIS_PASSWORD_PLACEHOLDER

MEDIA_STORAGE_BACKEND=cloudinary
CLOUDINARY_CLOUD_NAME=dsrbll7qc
CLOUDINARY_API_KEY=CLOUDINARY_KEY_PLACEHOLDER
CLOUDINARY_API_SECRET=4LbtgrinmMk...

EMAIL_BACKEND_TYPE=resend
RESEND_API_KEY=RESEND_KEY_PLACEHOLDER
DEFAULT_FROM_EMAIL=hello@webtech-dev.info
```

### Docker Compose

```yaml
- community.docker.docker_compose_v2:
    project_src: /opt/clickmart
    files:
      - docker-compose.yml
      - docker-compose.prod.yml
    state: present
    pull: always
    build: never
  become_user: deploy
```

- `pull: always` : tire les dernières images depuis ghcr.io à chaque run
- `build: never` : ne build pas localement (les images viennent du registry)
- `files` : utilise les fichiers de base + override prod (pas de staging)

### Vérification

```yaml
- pause: 15 seconds (attente stabilisation)
- docker_compose_v2 (check statut)
- debug: affiche les noms des conteneurs actifs
```

---

## Chemins créés sur le serveur

| Chemin | Contenu |
|---|---|
| `/opt/clickmart/` | Dépôt cloné |
| `/opt/clickmart/backend/.envs/` | Répertoire envs (mode 0700) |
| `/opt/clickmart/backend/.envs/.prod` | Variables d'environnement de production |
