# Roman 2050 → Team2050 — план миграции названия

Полное переименование отложено до отдельной фазы. Сначала сохраняется совместимость с существующими пользовательскими данными.

| OLD | NEW | TYPE | MIGRATION_REQUIRED | BREAKING_RISK |
|---|---|---|---|---|
| Roman 2050 | Team2050 | user-facing product title | да | низкий |
| Роман | Роман | employee identity | нет | высокий при изменении |
| `Roman2050` | `Team2050` | package/module/repository label | позже | высокий |
| `Roman 2050.spec` | `Team2050.spec` | PyInstaller/EXE | позже | средний |
| `%LOCALAPPDATA%\Roman2050` | совместимый старый путь + alias | user data path | да | высокий |
| `roman2050.sqlite3` | сохранить и мигрировать по schema version | SQLite identifier | да | высокий |
| `roman2050.log` | сохранить legacy log path | log identifier | да | средний |
| `Roman 2050` shortcuts | Team2050 label, old target | Windows shortcut | позже | средний |

## Правило миграции

Сначала добавляется display-name compatibility layer и явная версия схемы. Старый каталог, база, настройки и история читаются без потери данных. Удаление legacy paths не выполняется автоматически.

Переименование employee key `roman` запрещено: это не название продукта, а стабильная идентичность сотрудника.
