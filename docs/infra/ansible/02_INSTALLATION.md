# 2. Installation — Ansible ClickMart

> **Mise à jour** : 30 juillet 2026

---

## Poste de contrôle

### macOS (homebrew)

```bash
brew install ansible
ansible --version
# → ansible [core 2.20.x]
```

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install -y ansible
ansible --version
```

### Python pip (tous OS)

```bash
python3 -m pip install --user ansible ansible-lint
```

---

## Dépendances Ansible Galaxy

La collection `community.docker` est requise pour tous les modules Docker :

```bash
ansible-galaxy collection install community.docker
```

Vérification :

```bash
ansible-galaxy collection list | grep docker
# → community.docker  3.14.x
```

---

## Outils requis sur le poste de contrôle

| Outil | Rôle | Vérification |
|---|---|---|
| Python ≥ 3.10 | Runtime Ansible | `python3 --version` |
| Ansible ≥ 2.15 | Playbook | `ansible --version` |
| OpenSSH | Connexion serveur | `ssh -V` |
| Git | (optionnel) pour ghcr.io | `git --version` |
| `gh` CLI | (optionnel) secrets GitHub | `gh --version` |
| `dig` | Vérification DNS | `dig -v` |

---

## Serveur cible

Le VPS doit être :

- **Ubuntu 24.04** (recommandé) ou ≥ 22.04
- **1 GB RAM minimum** (960 MB testé)
- **25 GB disque minimum**
- **Clé SSH publique** du poste de contrôle ajoutée à la création
- **Ports 22, 80, 443** ouverts dans le firewall cloud

Aucun logiciel pré-installé nécessaire sur le serveur — Ansible installe tout.
