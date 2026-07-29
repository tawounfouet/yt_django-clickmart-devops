# SDLC — ClickMart

> Software Development Life Cycle — workflow et outils par phase
> Dernière mise à jour : 2026-07-29

---

## Cycle complet

```
┌───●───●───●───●───●───●───●───┐
│ 1   2   3   4   5   6   7      │
│ Pla  Dev  Tes  Rev  Rel  Dep  Mai │
└───────────────────────────────┘
```

---

## Phase 1 — Planification & Conception

**Objectif** : comprendre le système, planifier l'architecture, définir les specs.

| Outil | Commande |
|---|---|
| Mode architect | `ctrl+a` — explorer la structure |
| Agent plan | `@plan` — analyse sans modifier |
| Agent docs-writer | `@docs-writer` — documenter les décisions |
| Dry-run | `@deploy-fullstack dry-run` — analyser l'infra |

**Livrables** : analyses (`docs/analyse/`), ADR, specs

---

## Phase 2 — Développement

**Objectif** : implémenter des features, corriger des bugs, refactorer.

| Outil | Commande |
|---|---|
| Agent build | (défaut) — développement standard |
| Agent refactor-assistant | `@refactor-assistant` — refactoring sécurisé |
| Commande refactor | `/refactor` — planifier et exécuter |
| Git hygiene | `@git-hygiene` — commits atomiques |

**Conventions** :
- Branches : `dev` → `stg` → `main`
- Commits : [Conventional Commits](https://www.conventionalcommits.org/)
- Feature branch : `git checkout -b feat/xxx` depuis `dev`

**Checklist avant merge** :
```
git checkout dev
git merge feat/xxx
git push origin dev     → CI : 78 tests
git checkout stg && git merge dev → CI : tests + deploy staging
git checkout main && git merge stg → CI : tests + deploy production
```

---

## Phase 3 — Testing

**Objectif** : vérifier le comportement, couvrir les cas limites.

| Outil | Commande |
|---|---|
| Tests backend | `cd backend && python manage.py test` (67 tests) |
| Tests frontend | `cd frontend && npx vitest run` (11 tests) |
| Agent test-scaffolder | `@test-scaffolder` — générer des tests |
| Lint | `ruff check backend/` + `npm run lint` |

**CI** : les tests tournent automatiquement sur chaque push.

---

## Phase 4 — Review

**Objectif** : valider la qualité, vérifier la sécurité, préparer le merge.

| Outil | Commande |
|---|---|
| Commande review | `/review` — revue de code |
| Commande pr-review | `/pr-review` — revue de branche vs main |
| Agent code-reviewer | `@code-reviewer` — revue structurée |
| Mode security-audit | `ctrl+s` — scan vulnérabilités |

**Checklist** :
- [ ] Tous les tests passent en CI
- [ ] Pas de régression (dry-run OK)
- [ ] Revue de code approuvée
- [ ] Secrets non exposés

---

## Phase 5 — Release

**Objectif** : préparer la version, générer le changelog, tagger.

| Outil | Commande |
|---|---|
| Commande release | `/release` — préparation complète |
| Agent release-prep | `@release-prep` — analyse git, semver, changelog |

**Checklist** :
- [ ] Version bump dans `CHANGELOG.md`
- [ ] Tag git : `git tag v1.x.x`
- [ ] Tous les commits sont conventionnels

---

## Phase 6 — Déploiement

**Objectif** : commit propre, push, déploiement automatique.

| Outil | Commande |
|---|---|
| Agent deploy | `@deploy-fullstack production` |
| Commande commit | `/commit` — format conventionnel |

**Pipeline automatique** :
```
git push main → CI/CD Pipeline
  ├── test-backend (67 tests)
  ├── test-frontend (11 tests)
  ├── build-and-push (ghcr.io)
  └── deploy-production (Linode pull + up)
```

**Vérification** :
```bash
curl -s https://webtech-dev.info/          → 200
curl -s https://webtech-dev.info/api/v1/products/ → 200
ssh deploy@172.239.20.14 "docker compose -p clickmart ps"
```

---

## Phase 7 — Maintenance

**Objectif** : documentation, dette technique, support continu.

| Outil | Commande |
|---|---|
| Commande docs | `/docs` — générer/maj la documentation |
| Agent docs-writer | `@docs-writer` — documentation technique |
| find-todos | `rg -n "TODO\|FIXME\|HACK" --type py --type js` |
| Agent archive | `/archive` — archiver la session |

**Livrables** : rapports, architecture, README, TODO à jour

**Checklist** :
- [ ] Documentation à jour (README, ARCHITECTURE, rapports)
- [ ] TODO.md reflète les items restants
- [ ] Session archivée
- [ ] Dry-run final (`@deploy-fullstack dry-run`)

---

## État actuel

| Phase | Statut | Dernière action |
|---|---|---|
| 1. Planification | ✅ | Analyses (Celery, Terraform/Ansible) |
| 2. Développement | ✅ | 12 features (CI/CD, email, storage, apps media) |
| 3. Testing | ✅ | Dry-run ×2, email Resend testé, API validée |
| 4. Review | ✅ | Dry-run final (17/17 problèmes résolus) |
| 5. Release | ✅ | Commits atomiques tout au long |
| 6. Déploiement | ✅ | Production stable (6 conteneurs, 200 OK) |
| **7. Maintenance** | **🔄 Actif** | Documentation, TODO, SDLC |

---

## Prochain cycle

1. **Plan** → Phase 1 : spec pour les items TODO restants (django-celery-beat, Flower, Sentry)
2. **Dev** → Phase 2 : implémenter les items P1/P2
3. **Test** → Phase 3 : `python manage.py test` + `npx vitest run`
4. **Review** → Phase 4 : `@code-reviewer` + dry-run
5. **Release** → Phase 5 : changelog + tag
6. **Deploy** → Phase 6 : `git push main` → CI/CD
7. **Maintain** → Phase 7 : docs + archive

> `@sdlc-orchestrator` pour naviguer entre les phases.
