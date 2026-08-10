# Skill Qualification Model

North Star reference: `docs/product/PRODUCT_NORTH_STAR.md`.

Skill state is more important than a percentage.

Lifecycle:
- `Не назначен`;
- `Назначен`;
- `Практиковал`;
- `Показал результат`;
- `Проверен`;
- `Квалифицирован`;
- `Требует переобучения`;
- `Приостановлен`;
- `Истек`.

The current implementation derives visible states from connected evidence:
- skill record exists;
- successful runs explicitly using that skill;
- file evidence connected to that skill run;
- review runs connected to the skill.

Chat claims do not advance the lifecycle. `SkillProgressService` is the authority for skill state display.
