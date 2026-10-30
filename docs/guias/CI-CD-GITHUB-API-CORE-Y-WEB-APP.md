---
tipo: guia
fecha: 2026-10-30
tags: [harness, guia]
---

# CI/CD en GitHub: api-core y web-app

> Ejemplo anonimizado de dos configuraciones. Verifica las reglas actuales en tu instalación.

Por qué un PR de api-core muestra el check y «Review required», y uno de web-app no. Los dos repos usan el mismo flujo (`develop` → `qa` → `main`), pero su configuración en GitHub no es igual. Ejemplo anonimizado verificado en la fecha de esta nota; confirma la configuración actual antes de aplicarlo.

Ver también: [[docs/guias/ESTANDAR-ENTREGA-TRELLO-Y-GITHUB|Estándar de entrega en Trello y GitHub]].

## Lo que ves en cada PR

| | api-core | web-app |
|---|---|---|
| Check de CI en el último commit | Sí (`build-test`) | Solo en el commit con el que se abrió el PR |
| «Review required» | Sí | No |
| Etiqueta «Review Dev» | Sí, si se pone a mano | Sí, si se pone a mano |
| Revisor pedido (Revisor Principal) | Sí, con `--reviewer <revisor-principal>` | Sí, con `--reviewer <revisor-principal>` |

La etiqueta y el revisor se ponen igual en los dos repos. Las diferencias son el check y el aviso de revisión.

## 1. El check de CI

**api-core** (`.github/workflows/ci.yml`):
```yaml
on:
  pull_request:
    branches: [develop, qa, main]
```
Como no declara `types`, GitHub usa los de siempre: `opened`, `synchronize` y `reopened`. El CI corre en cada push al PR, así que el último commit siempre tiene su check.

**web-app** (`.github/workflows/ci.yml`):
```yaml
on:
  pull_request:
    branches: [develop]
    types: [opened]
```
Solo corre al **abrir** el PR. Los commits que se suben después quedan sin check, y GitHub muestra el estado del último commit, así que el PR aparece sin nada. Tampoco corre al hacer `gh pr update-branch` ni al reabrir el PR.

**Decisión vigente (el responsable, 2026-09-29): el CI de web-app no se modifica.** Por eso una rama de web-app se verifica en local antes de mergear: `npx tsc -b`, `npx eslint .` y `npx vitest run` sobre el commit final (`bash .claude/scripts/verificar-pr.sh <PR>`).

**Para igualarlo a api-core** (si se decide cambiar): agregar `synchronize` y `reopened` a `types` en un PR chico propio:
```yaml
    types: [opened, synchronize, reopened]
```
Ojo: el check verde de `develop` en web-app viene de `cd-nonprod.yml` (el deploy), no de `ci.yml`. No prueba que la suite pase.

## 2. «Review required»

**api-core** tiene tres rulesets de rama: `dev` (`refs/heads/dev*`), `qa` y `main`. El de `dev` exige, para mergear a `develop`:
- 1 aprobación, que se descarta si se sube un commit nuevo (`dismiss_stale_reviews_on_push`);
- todos los hilos de conversación resueltos;
- el check `build-test` en verde y la rama al día con `develop` (`strict`);
- merge con *merge commit*; sin force push ni borrar la rama.

Con eso, GitHub muestra «Review required» y bloquea el merge hasta que Revisor Principal apruebe.

**web-app no tiene ningún ruleset.** GitHub no exige aprobación, así que no muestra el aviso y deja mergear sin revisión ni CI verde.

**Para igualarlo** (lo hace un admin del repo, en Settings › Rules › Rulesets, o con `gh api`): crear en web-app un ruleset `dev` con las mismas reglas que el de api-core. Recomendación: **sin** el check obligatorio mientras el CI siga corriendo solo al abrir el PR. Si no, ningún PR con commits después de abrirlo podría mergearse, porque su último commit nunca tendría check.

## Otros datos útiles

- El deploy no pasa por los PRs: `cd-nonprod.yml` corre con `push` a `develop` y `qa` en los dos repos.
- La etiqueta «Review Dev» («Visto bueno del responsable: pasar la tarjeta a revisión de Revisor Principal») existe en los dos repos y se pone a mano.
- Un commit nuevo en un PR de api-core descarta la aprobación que ya tenía. Hay que volver a pedírsela a Revisor Principal.
