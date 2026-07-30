# 8. Rôle `github_actions` — Ansible ClickMart

> **Mise à jour** : 30 juillet 2026

---

## Responsabilité

Configurer les secrets GitHub nécessaires au CI/CD (optionnel, désactivé par défaut).

---

## Activation

Le rôle est désactivé par défaut dans le playbook :

```yaml
- role: github_actions
  tags: [cicd, optional]
  when: cicd_enabled | default(false)
```

Pour l'activer : `--tags cicd` suffit :

```bash
ansible-playbook deploy.yml -i inventory.yml --tags cicd
```

---

## Tâches (38 lignes)

### Vérification de `gh` CLI

```yaml
- which gh
  delegate_to: localhost
  failed_when: no
```

### Vérification de l'authentification

```yaml
- gh auth status
  delegate_to: localhost
  failed_when: no
  when: gh_check.rc == 0
```

### Configuration des secrets

```yaml
- gh secret set VPS_HOST  --body "172.239.20.14"
- gh secret set VPS_USER  --body "deploy"
- gh secret set VPS_SSH_KEY --body "{{ lookup('file', '~/.ssh/id_ed25519') }}"
  repo: tawounfouet/yt_django-clickmart-devops
  when: gh_check.rc == 0 and gh_auth.rc == 0
  no_log: yes
```

`no_log: yes` empêche l'affichage de la clé SSH privée dans les logs.

### Instructions de fallback

Si `gh` n'est pas disponible, le rôle affiche les commandes à exécuter manuellement :

```
GitHub Actions configuré si gh CLI était disponible.
Sinon, ajouter manuellement les secrets :
  gh secret set VPS_HOST --body '172.239.20.14'
  gh secret set VPS_USER --body 'deploy'
  gh secret set VPS_SSH_KEY --body '$(cat ~/.ssh/id_ed25519)'
  Repo: tawounfouet/yt_django-clickmart-devops
```

---

## Secrets créés

| Secret | Valeur | Usage CI/CD |
|---|---|---|
| `VPS_HOST` | IP du serveur | `ssh deploy@VPS_HOST` |
| `VPS_USER` | `deploy` | Utilisateur SSH |
| `VPS_SSH_KEY` | Clé privée (multiline) | Authentification SSH |

---

## Prérequis

- `gh` CLI installé sur le poste de contrôle
- `gh auth login` déjà effectué
- Token GitHub avec le scope `repo` ou `admin:org`
