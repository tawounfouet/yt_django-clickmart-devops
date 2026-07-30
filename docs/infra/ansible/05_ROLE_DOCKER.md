# 5. Rôle `docker` — Ansible ClickMart

> **Mise à jour** : 30 juillet 2026

---

## Responsabilité

Installer Docker, Docker Compose, Git, créer l'utilisateur `deploy`, configurer UFW, authentifier ghcr.io.

---

## Tâches (126 lignes)

### Nettoyage préalable

```yaml
- name: Remove any existing Docker repo files
  file:
    path: "{{ item }}"
    state: absent
  loop:
    - /etc/apt/sources.list.d/docker.list
    - /etc/apt/sources.list.d/download_docker_com_linux_ubuntu.list
```

Évite le conflit `signed-by` entre un ancien repo Docker et le nouveau. Ces fichiers sont souvent un `docker.list` standard ou un `download_docker_com_linux_ubuntu.list` qui utilisent `signed-by=/usr/share/keyrings/docker-archive-keyring.gpg` (ancien emplacement) alors que nous utilisons `/etc/apt/keyrings/docker.asc`.

### Installation Docker

```yaml
# Prérequis système
apt: ca-certificates, curl, git, ufw

# Keyrings
mkdir /etc/apt/keyrings (mode 0755)
get_url → /etc/apt/keyrings/docker.asc (mode 0644)

# Repo avec signed-by
apt_repository:
  repo: "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc]
         https://download.docker.com/linux/ubuntu {{ ansible_facts.distribution_release }} stable"
  filename: docker

# Paquets
apt: docker-ce, docker-ce-cli, containerd.io, docker-compose-plugin

# Service
docker started + enabled
```

**Pourquoi `get_url` plutôt que `apt_key`** : le module `apt_key` ajoute la clé dans `/etc/apt/trusted.gpg.d/` (déprécié). `get_url` place la clé dans `/etc/apt/keyrings/` puis `apt_repository` la référence avec `signed-by=` (méthode moderne).

### Utilisateur `deploy`

```yaml
user: deploy, groups=docker, shell=/bin/bash
authorized_key: ~/.ssh/id_ed25519.pub (depuis le contrôleur)
sudoers: /etc/sudoers.d/deploy → "deploy ALL=(ALL) NOPASSWD:ALL"
```

La clé SSH est chargée depuis le poste de contrôle via `lookup('file', ...)`. Le `validate: /usr/sbin/visudo -cf %s` prévient une écriture cassée de `/etc/sudoers.d`.

### GHCR.io login

```yaml
community.docker.docker_login:
  registry_url: https://ghcr.io
  username: "{{ github_user }}"
  password: "{{ github_token }}"
  reauthorize: yes
become_user: deploy
no_log: yes
```

`reauthorize: yes` force la mise à jour du token même si un token précédent existe. Sans cela, un token expiré n'est pas remplacé.

`become_user: deploy` exécute le login Docker en tant que `deploy` (car `docker login` stocke les credentials dans `~/.docker/config.json`).

`no_log: yes` masque le token des logs Ansible.

### UFW / Firewall

```yaml
ufw allow: 22/tcp, 80/tcp, 443/tcp
ufw enable: outgoing=allow
policy: allow (sortant)
```

---

## Problèmes résolus

| Problème | Cause | Solution |
|---|---|---|
| `NO_PUBKEY 7EA0A9C3F273FCD8` | Clé GPG Docker absente | `get_url` dans `/etc/apt/keyrings/` avec `signed-by` |
| `Conflicting values for Signed-By` | Deux repos Docker avec/sans `signed-by` | Nettoyage préalable des fichiers `.list` |
| `docker login` ne met pas à jour | Token expiré, `reauthorize` non spécifié | `reauthorize: yes` |
| `sudo: a password is required` | `deploy` sans sudo NOPASSWD | Fichier `/etc/sudoers.d/deploy` créé avec visudo |
