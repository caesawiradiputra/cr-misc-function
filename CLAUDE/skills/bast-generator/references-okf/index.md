---
okf_version: "0.2"
---

# BAST generator knowledge bundle

Pilot conversion of `../references/template-map.md` and `../references/deployment-types.md` into an OKF bundle. Content is the same as the originals; only the structure differs. Read only the concepts the current step needs.

Locate each template cell in the **copy** by its anchor text, then take the `data-local-id` from the copy you just read. Never reuse ids from memory or from the template read.

## Template cells (which cell is filled from what)

- [Description requirement](/template/description-requirement.md): Bahasa summary plus "Perubahan pada deployment" list.
- [Epic key](/template/epic-key.md): inline-card links to the DA ticket and its IN clone.
- [People and classification](/template/people-and-classification.md): requester, engineer, user, directorate, department, type, scope.
- [CAB fields](/template/cab-fields.md): Deployment Methods PIC and the source-code reference in checklist item 4.
- [DDCL Production](/template/ddcl-production.md): one row per deployment action.
- [Scenario test](/template/scenario-test.md): inferred scenarios, PIC is the user.
- [Left untouched](/template/left-untouched.md): cells owned by Data Ops, the user, CAB and IT.
- [Prompts that must disappear](/template/prompts-to-remove.md): the sweep list.

## Deployment rows (how an action becomes a DDCL row)

- [Row format](/deployment/row-format.md): layout, label choice and counting rules.
- [Capture Screen](/deployment/capture-screen.md): placeholder rules per row kind.
- [Skip backups by default](/deployment/skip-backups.md): when a backup step is left out.
- [Per-repo mapping](/deployment/per-repo-mapping.md): what follows an image release in each repo.
- [postgres-script](/deployment/types/postgres-script.md)
- [image-release](/deployment/types/image-release.md)
- [kubernetes-deploy](/deployment/types/kubernetes-deploy.md)
- [airflow-image-variable](/deployment/types/airflow-image-variable.md)
- [out-of-repo](/deployment/types/out-of-repo.md)

To support a new deployment type, add a concept under `deployment/types/` and list it here. `SKILL.md` needs no change.
