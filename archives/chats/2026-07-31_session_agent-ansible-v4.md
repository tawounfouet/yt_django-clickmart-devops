# Session: Agent Ansible v4.0 — Multi-env & Provision CI

**Date**: 2026-07-31
**Agent(s)**: opencode, deploy-fullstack
**Phase**: maintain (agent evolution + ops)

---

## Intent

Intégrer Ansible comme moteur de déploiement par défaut dans l'agent deploy-fullstack, ajouter le support multi-environnement (staging), et créer un job CI/CD `workflow_dispatch` pour le provisionnement.

## Outcome

Agent v4.0 finalisé. Déploiement from-scratch validé (4 bugs production corrigés). Multi-environnement fonctionnel (`--limit staging`). Provision manuel disponible dans GitHub Actions. 3 ajustements post-déploiement appliqués.

---

## Decisions

| # | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 1 | Ansible comme chemin par défaut, fallback manuel déprécié | Idempotence, fiabilité, cas edge gérés | Garder les deux chemins égaux |
| 2 | Variables par host dans l'inventory plutôt que playbooks séparés | Ansible natif, un seul playbook | Deux playbooks (prod/staging séparés) |
| 3 | `RemoveField`+`AddField` pour migrations UUID PostgreSQL | `AlterField` impossible sur PostgreSQL | Table temporaire (trop complexe) |
| 4 | `os.environ.get()` dans `create_admin` plutôt que `django-environ` | Commande simple, pas besoin d'import lourd | Réinstaller `python-decouple` |

## Files Created

| File | Purpose |
|---|---|
| `docs/analyse/ANALYSE_INTEGRATION_ANSIBLE_AGENT.md` | Analyse intégration Ansible → agent |
| `docs/plans/PLAN_INTEGRATION_ANSIBLE_AGENT.md` | Plan d'implémentation 11 tâches |
| `docs/debug/2026-07-30_DEPLOIEMENT_ANSIBLE_AGENT.md` | 4 bugs production documentés |

## Files Modified

| File | Change summary |
|---|---|
| `.opencode/agents/deploy-fullstack.md` | v4.0 : phases 1-4 → Ansible, préparation secrets, table enrichie |
| `infra/ansible/inventory.yml` | Ajout `clickmart-staging` (per-host vars) |
| `infra/ansible/deploy.yml` | `hosts: all`, `health_proto`, `ssl_enabled` conditionnel |
| `infra/ansible/roles/clickmart_app/tasks/main.yml` | Paramétré (`{{ app_dir }}`, `{{ compose_files }}`, `{{ project_name }}`, `{{ branch }}`) |
| `infra/ansible/README.md` | Multi-environnement, `--limit` |
| `.github/workflows/ci-cd.yml` | `workflow_dispatch` + job `provision`, forbidden imports check |
| `Makefile` | `api-test` → `python -m pytest -q` |
| `infra/scripts/deploy-app.sh` | Pre-deploy backup (production) |
| `backend/users/management/commands/create_admin.py` | `decouple` → `os.environ` |
| `infra/ansible/roles/clickmart_app/templates/.env.prod.j2` | `ADMIN_EMAIL`, `ADMIN_PASSWORD` |
| `backend/users/migrations/0002_alter_user_id.py` | `AlterField` → `RemoveField`+`AddField` |
| `backend/products/migrations/0003_alter_product_id.py` | Idem |
| `backend/carts/migrations/0004_alter_cart_id_alter_cartitem_id.py` | Idem |
| `backend/orders/migrations/0004_alter_order_id_alter_orderitem_id.py` | Idem |
| `TODO.md` | Ansible multi-env + CI/CD provision marqués faits |
| `docs/reports/AGENT_DEPLOY_FULLSTACK.md` | v3.0 → v4.0, historique + architecture Ansible |
| `docs/plans/PLAN_AGENT_DEPLOIEMENT.md` | Section V4 — Intégration Ansible |
| `docs/reports/GESTION_CICD.md` | Table provision + `workflow_dispatch` |

## Commands Run

| Command | Purpose | Result |
|---|---|---|
| `@deploy-fullstack ansible` | Déploiement via agent v4.0 | 6 conteneurs healthy, 4 bugs corrigés |
| `ansible-inventory --list --yaml` | Vérifier merge variables | staging OK (per-host vars) |
| `ansible-playbook --syntax-check` | Validation playbook | OK |
| `ansible-playbook --list-hosts` | Vérifier hosts | 2 hosts (prod + staging) |

## Issues & Workarounds

| Issue | Workaround | Status |
|---|---|---|
| UUID migrations `AlterField` casse PostgreSQL | `RemoveField`+`AddField` (2 commits) | resolved |
| `create_admin` : `ModuleNotFoundError: decouple` | `os.environ.get()` + template Ansible | resolved |
| Clé SSH `id_rsa` → `id_ed25519` inventory | Preflight check détecté, corrigé | resolved |
| DB reset en production | Documenté, backup pre-deploy ajouté | documented |
| Secrets dans l'historique Git bloquent le push | `git reset --soft` + sanitize + force push | resolved |

## Action Items

- [ ] Activer le cron de backup en production (`backup-db.sh` quotidien)
- [ ] Créer les secrets GitHub manquants (`SECRET_KEY`, `DB_PASSWORD`, etc.) pour le job `provision`
- [ ] Tester `workflow_dispatch` → `provision` depuis l'UI GitHub Actions
- [ ] Chiffrer `secrets.yml` avec `ansible-vault` (P1)

## Related Sessions

- `archives/chats/2026-07-30_session_ameliorations-cicd.md` — CI/CD v3
- `archives/chats/2026-07-30_session_ameliorations-vocalfit.md` — Phase 1-3 VocalFit
- `archives/chats/2026-07-30_session_documentation-ansible.md` — Doc Ansible

## Full Conversation Summary

1. Analyse d'intégration Ansible → agent (option B retenue : Ansible par défaut)
2. Plan d'implémentation créé (11 tâches, ~1h35)
3. Implémentation : agent v4.0 (6 modifications dans `.opencode/agents/deploy-fullstack.md`)
4. Mise à jour rapport agent + plan agent
5. `@deploy-fullstack ansible` → déploiement réussi (6 conteneurs)
6. 4 bugs production : UUID PostgreSQL, create_admin/decouple, clé SSH, DB reset
7. Debug documenté dans `docs/debug/`
8. 3 ajustements post-déploiement : Makefile pytest, backup pre-deploy, CI forbidden imports
9. Multi-environnement Ansible : staging ajouté à l'inventory, playbook `hosts: all`, rôle paramétré
10. CI/CD : job `provision` avec `workflow_dispatch` (target + tags inputs)
11. Pipeline vert
12. Archivage
