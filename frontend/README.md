# Интерфейс Python-приложения

Основа — [Front-end-, ветка develop](https://github.com/Ostatochniye-znaniya/Front-end-/tree/develop),
commit `89086c3d6e743c7075ebbf718eeaeeb96366eedd`. Перенесены общие стили, ресурсы,
Navbar, Table, Dropdown, Modal, Dropzone и другие UI-компоненты. Страницы используют
реальные данные FastAPI вместо демонстрационных массивов и адресов C# API.

```powershell
pnpm install --frozen-lockfile
pnpm dev
```

Адрес: http://localhost:3000/csh/login. Backend должен работать на 8001.
Для другого адреса задайте `BACKEND_URL` перед запуском или сборкой: rewrites
Next.js формируются при сборке. Cookie проксируется в одном origin через `/csh/api`.

| Роль | Основные страницы |
| --- | --- |
| ЛПР / администратор | `/lpr/statistics`, `/lpr/order`, `/lpr/list`, `/lpr/report`, `/access-rights`, `/lpr/settings` |
| Декан | `/dof/documents` |
| Заведующий кафедрой | `/hod/groups`, `/hod/disciplines`, `/hod/teachers`, `/hod/statistics` |
| Ответственный факультета | `/rod/schedule` |
| Преподаватель | `/teacher/dates`, `/teacher/report` |
| Гость | `/guest` |

Все страницы используют Page/AppShell и единый `--shell-gap: 8px` в
`app/unified.css`. Раздела «Рабочие процессы» в основной навигации нет.
Старая статическая версия сохранена в `../legacy/frontend-static`.

Права и принадлежность к факультету проверяются сервером. В интерфейсе нет
константы с факультетом декана. Численность, доля участия и булевый порог 50%
приходят вычисленными из `/api/reports/overview`. Настройка бумажных версий
сохраняется по семестру через `/api/periods/{id}/report-policy`.

```powershell
pnpm exec eslint . --max-warnings=0
pnpm exec tsc --noEmit
pnpm build
```

Сквозная проверка: `tests/browser/check_frontend.py` из корня проекта после сборки.
Она использует временную БД, свободный порт frontend и backend на 8001.
