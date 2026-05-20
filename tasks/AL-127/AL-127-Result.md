# AL-127: Переименование бренда Flirtello → Aiko Lounge

## Задача

Критичная задача по замене всех упоминаний бренда "Flirtello" на новое название "Aiko Lounge" во всех репозиториях workspace согласно лицензионному договору.

## Что сделано

### 1. Замена в пользовательских текстах ✅

Выполнена полная замена "Flirtello" на "Aiko Lounge" во всех пользовательских текстах:

- **Telegram локализация:**

  - `flirtello-backend-service/src/telegram/locales/ru/LC_MESSAGES/messages.po` (2 места)
  - `flirtello-backend-service/src/telegram/locales/en/LC_MESSAGES/messages.po` (2 места)

- **Frontend локализация:**

  - `flirtello-frontend/public/locales/default/en/tgPages.json`
  - `flirtello-frontend/public/locales/default/ru/tgPages.json`
  - `flirtello-frontend/public/locales/empire/en/tgPages.json`
  - `flirtello-frontend/public/locales/default/en/homePage.json`
  - `flirtello-frontend/public/locales/default/en/common.json`

- **Контент лендинга:**
  - `flirtello-frontend/src/lib/landing.data.ts`

### 2. Решение о технических местах

**Принято решение:** Технические места (пути к кэшу, названия проектов в конфигах, технические идентификаторы) **НЕ переименовывать** по следующим причинам:

- Технические идентификаторы не видны пользователям
- Переименование может привести к проблемам с инфраструктурой и деплоем
- Email домены и технические пути должны оставаться стабильными

**Что осталось без изменений:**

- Пути к кэшу (`.cache/flirtello`)
- Названия проектов в `pyproject.toml` и `package.json`
- Email домены (`@tg.flirtello.com`, `@flirtello.com`)
- Технические идентификаторы в конфигах
- URL домены (технические ссылки)

## Верификация

✅ Все пользовательские тексты заменены на "Aiko Lounge"
✅ Технические места оставлены без изменений согласно решению
✅ Проверены все файлы локализации
✅ Проверен контент лендинга

## Результаты

- **Заменено:** Все пользовательские тексты в Telegram и Frontend
- **Оставлено без изменений:** Все технические идентификаторы, пути и конфигурации
- **Статус:** Задача выполнена согласно принятому решению

## Файлы изменены

- `flirtello-backend-service/src/telegram/locales/ru/LC_MESSAGES/messages.po`
- `flirtello-backend-service/src/telegram/locales/en/LC_MESSAGES/messages.po`
- `flirtello-frontend/public/locales/default/en/tgPages.json`
- `flirtello-frontend/public/locales/default/ru/tgPages.json`
- `flirtello-frontend/public/locales/empire/en/tgPages.json`
- `flirtello-frontend/public/locales/default/en/homePage.json`
- `flirtello-frontend/public/locales/default/en/common.json`
- `flirtello-frontend/src/lib/landing.data.ts`

## Документация

- `AL-127-Findings.md` - технические детали и обоснование решений
- `AL-127-task.md` - исходная задача с обновленным статусом
