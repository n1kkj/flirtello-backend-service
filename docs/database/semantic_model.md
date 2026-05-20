# Cемантическая модель: Flirtello: Аналитика чатов и биллинга

**Версия:** 1.0
**Статус:** В разработке
**Владелец:** cto
**Последнее обновление:** 2024-07-26

Этот документ описывает универсальную семантическую модель для анализа пользовательской активности, биллинга и маркетинга в проекте Flirtello. Он служит единым источником правды для всех аналитических запросов.

## Раздел 1: Физический слой (Base Layer)

_Описание: Здесь определены подключения к хранилищу данных и базовые таблицы/витрины, которые использует модель._

```yaml
base_layer:
  # Тип подключения: postgres_prod - основная база данных приложения
  connection: postgres_prod

  # Базовые модели (таблицы и представления)
  models:
    # --- Схема `auth` ---
    - name: auth_users
      description: "Пользователи из системы аутентификации Supabase. Содержит email, пароль, статусы подтверждения. Важно: таблица содержит флаг is_anonymous. Для аналитики следует использовать только пользователей с is_anonymous = false."
      source_table: "auth.users"

    # --- Схема `public` ---
    - name: public_channels
      description: "Каналы (чаты) между пользователями и персонажами."
      source_table: "public.channels"
    - name: public_messages
      description: "Сообщения в чатах. Содержит текст и вложения (attachments)."
      source_table: "public.messages"
    - name: public_users
      description: "Профили пользователей, расширяющие auth.users. Содержат дополнительные данные, включая настройки (settings)."
      source_table: "public.users"

    # --- Схема `content` ---
    - name: content_characters
      description: "Конфигурация и данные о персонажах."
      source_table: "content.content_characters"
    - name: content_character_configs
      description: "Конфигурация 'сюжетных' чатов. Ссылка на историю стоит в канале (чате)."
      source_table: "content.character_configs"
    - name: content_images
      description: "Данные об изображениях (фотографиях), которые могут быть отправлены в чат."
      source_table: "content.content_images"
    - name: content_invoices
      description: "Счета, выставляемые пользователям за услуги."
      source_table: "content.invoices"
    - name: content_transactions
      description: "Финансовые транзакции, связанные со счетами и балансами."
      source_table: "content.transactions"
    - name: content_tariff_plans
      description: "Подписки (тарифные планы), доступные для покупки."
      source_table: "content.tariff_plans"
    - name: content_token_packs
      description: "Пакеты токенов, доступные для покупки."
      source_table: "content.token_packs"
    - name: content_gift_codes
      description: "Промокоды, которые пользователи могут активировать для получения токенов."
      source_table: "content.gift_codes"
    - name: content_gift_codes_users
      description: "Записи об активации промокодов пользователями."
      source_table: "content.gift_codes_users"

    # --- Схема `mktdata` ---
    - name: mktdata_mktdata_raw
      description: "Сырые данные о событиях из рекламных кампаний, в основном о первом запуске бота."
      source_table: "mktdata.mktdata_raw"

    # --- Схема `translator` ---
    - name: translator_translations
      description: "Содержит переводы текстов на разные языки, используемые в приложении."
      source_table: "translator.translations"
```

## Раздел 2: Концептуальный слой (Conceptual Layer)

_Инструкция: Это ключевой раздел. Определены основные бизнес-сущности домена, их атрибуты и связи._

```yaml
conceptual_layer:
  entities:
    - name: User
      model_ref: auth_users
      primary_key: id

    - name: Channel
      model_ref: public_channels
      primary_key: id

    - name: Message
      model_ref: public_messages
      primary_key: id

    - name: Invoice
      model_ref: content_invoices
      primary_key: id

    - name: Transaction
      model_ref: content_transactions
      primary_key: id

    - name: Character
      model_ref: content_characters
      primary_key: id

    - name: Story
      model_ref: content_character_configs
      primary_key: id

    - name: Photo
      model_ref: content_images
      primary_key: id

    - name: TariffPlan
      model_ref: content_tariff_plans
      primary_key: id

    - name: TokenPack
      model_ref: content_token_packs
      primary_key: id

    - name: GiftCode
      model_ref: content_gift_codes
      primary_key: id

    - name: GiftCodeUserLink
      model_ref: content_gift_codes_users
      primary_key: id

    - name: AdEvent
      model_ref: mktdata_mktdata_raw
      primary_key: id # Примечание: в `mktdata_raw` нет явного PK, используем id, если он будет добавлен, или конкатенацию для уникальности.

    - name: UserProfile
      model_ref: public_users
      primary_key: id

    - name: Translation
      model_ref: translator_translations
      primary_key: id

  dimensions:
    # --- Измерения времени ---
    - name: registration_date
      entity: User
      type: date
      sql: "CAST(created_at AS DATE)"
    - name: message_date
      entity: Message
      type: date
      sql: "CAST(inserted_at AS DATE)"
    - name: ad_event_date
      entity: AdEvent
      type: date
      sql: "CAST(created_at AS DATE)"
    - name: transaction_date
      entity: Transaction
      type: date
      sql: "CAST(created_at AS DATE)"
    - name: gift_code_created_date
      entity: GiftCode
      type: date
      sql: "CAST(created_at AS DATE)"
    - name: gift_code_activation_date
      entity: GiftCodeUserLink
      type: date
      sql: "CAST(activated_at AS DATE)"
    - name: translation_created_date
      entity: Translation
      type: date
      sql: "CAST(created_at AS DATE)"

    # --- Категориальные измерения ---
    - name: user_id
      entity: User
      type: string
      sql: id
    - name: user_email
      entity: User
      type: string
      sql: email
    - name: user_role
      entity: User
      type: string
      sql: role
    - name: user_last_sign_in
      entity: User
      type: timestamp
      sql: last_sign_in_at
    - name: is_telegram_user
      entity: User
      type: boolean
      sql: "email LIKE '%@tg.flirtello.com'"
    - name: is_anonymous
      entity: User
      type: boolean
      sql: "is_anonymous"
      description: "Флаг, показывающий, является ли пользователь анонимным ('true') или зарегистрированным ('false'). В аналитике следует использовать is_anonymous = false."
    - name: current_telegram_character_id
      entity: User
      type: number
      sql: "CAST(public_users.settings -> 'angel_char_id' AS INTEGER)"
      description: "ID текущего персонажа, с которым пользователь общается в Telegram. Извлекается из поля 'settings' (тип hstore) таблицы public_users и приводится к числу."
    - name: current_telegram_config_id
      entity: User
      type: uuid
      sql: "CAST(public_users.settings -> 'config_id' AS UUID)"
      description: "ID конфигурации истории, который может быть сохранен в настройках пользователя. Извлекается из поля 'settings' (тип hstore). Может отсутствовать."
    - name: channel_id
      entity: Channel
      type: string
      sql: id
    - name: channel_config_id
      entity: Channel
      type: number
      sql: config_id
      description: "ID конфигурации 'сюжетной' истории, связанной с каналом. Определяет сценарий общения."
    - name: character_id
      entity: Character
      type: number
      sql: id
    - name: character_name
      entity: Character
      type: string
      sql: name
    - name: story_name
      entity: Story
      type: string
      sql: public_name
    - name: message_id
      entity: Message
      type: string
      sql: id
    - name: message_sender
      entity: Message
      type: string
      sql: "CASE WHEN user_id IS NULL THEN 'character' ELSE 'user' END"
      description: "Определяет отправителя сообщения. 'user' если user_id не NULL, 'character' если NULL."
    - name: message_type
      entity: Message
      type: string
      sql: message_type # 'user_message', 'character_message', 'photo_message' и т.д.
    - name: invoice_id
      entity: Invoice
      type: string
      sql: id
    - name: invoice_status
      entity: Invoice
      type: string
      sql: status # 'paid', 'pending', 'failed'
    - name: invoice_service_id
      entity: Invoice
      type: string
      sql: service_id
    - name: transaction_id
      entity: Transaction
      type: string
      sql: id
    - name: transaction_service_id
      entity: Transaction
      type: string
      sql: service_id
    - name: transaction_type
      entity: Transaction
      type: string
      sql: transaction_type
    - name: transaction_character_id
      entity: Transaction
      type: number
      sql: "(additional_data::jsonb ->> 'char_id')::int"
      description: "ID персонажа, связанного с транзакцией. Извлекается из поля additional_data. Позволяет напрямую атрибутировать списание токенов."
    - name: tariff_plan_name
      entity: TariffPlan
      type: string
      sql: name
    - name: token_pack_name
      entity: TokenPack
      type: string
      sql: name
    - name: token_pack_amount
      entity: TokenPack
      type: number
      sql: amount
    - name: token_pack_price
      entity: TokenPack
      type: number
      sql: price
    - name: token_pack_lifetime_days
      entity: TokenPack
      type: number
      sql: lifetime_days
    - name: is_token_pack_archived
      entity: TokenPack
      type: boolean
      sql: is_archived
    - name: is_token_pack_highlighted
      entity: TokenPack
      type: boolean
      sql: is_highlighted
    - name: token_pack_order
      entity: TokenPack
      type: number
      sql: "order"
    - name: gift_code_id
      entity: GiftCode
      type: string
      sql: id
    - name: gift_code_code
      entity: GiftCode
      type: string
      sql: code
    - name: gift_code_type
      entity: GiftCode
      type: string
      sql: code_type
    - name: gift_code_token_amount
      entity: GiftCode
      type: number
      sql: token_amount
    - name: gift_code_is_active
      entity: GiftCode
      type: boolean
      sql: is_active
    - name: gift_code_tokens_lifetime_hours
      entity: GiftCode
      type: number
      sql: tokens_lifetime_hours
    - name: gift_code_activation_id
      entity: GiftCodeUserLink
      type: string
      sql: id
    - name: traffic_source
      entity: AdEvent
      type: string
      sql: "COALESCE(params->>'utm_source', params->>'source')"
      description: "Источник трафика. Для веб-трафика используется 'utm_source', для Telegram — 'source'."
    - name: ad_campaign
      entity: AdEvent
      type: string
      sql: "params->>'utm_campaign'"
      description: "Рекламная кампания. Как правило, используется только для веб-трафика (наличие 'utm_campaign')."
    - name: traffic_channel
      entity: AdEvent
      type: string
      sql: "CASE WHEN params::jsonb ? 'utm_source' THEN 'web' ELSE 'telegram' END"
      description: "Канал привлечения: 'web' для событий с UTM-метками, 'telegram' для событий из Telegram."
    - name: action_type
      entity: AdEvent
      type: string
      sql: "action"
      description: "Тип маркетингового события. Возможные значения: 'lead', 'tg_ad_start', 'tg_kicked', 'tg_post_sent'. Примечание: записи с пустым значением ('') следует считать как 'lead', так как это, вероятно, ошибка в логировании."
    - name: translation_id
      entity: Translation
      type: number
      sql: id
    - name: translation_key
      entity: Translation
      type: string
      sql: "key"
    - name: translation_language
      entity: Translation
      type: string
      sql: "language"
    - name: is_human_verified
      entity: Translation
      type: boolean
      sql: is_verified_by_human

  measures:
    # --- Метрики Пользователей ---
    - name: total_users
      entity: User
      agg_function: count_distinct
      sql: id
      format: number
    - name: new_users
      description: "Количество новых пользователей за период (по дате регистрации)."
      entity: User
      agg_function: count_distinct
      sql: id
      format: number

    # --- Метрики активации промокодов ---
    - name: total_gift_codes_activated
      entity: GiftCodeUserLink
      agg_function: count_distinct
      sql: id
      description: "Общее количество активаций промокодов."
      format: number

    # --- Метрики переводов ---
    - name: total_translations
      entity: Translation
      agg_function: count
      sql: id
      description: "Общее количество сделанных переводов."
      format: number

    # --- Метрики Сообщений и Вовлеченности ---
    - name: total_messages
      entity_ref: Message
      description: "Общее количество отправленных сообщений."
      calculation: "COUNT(id)"
      type: count
    - name: total_messages_by_user
      entity_ref: Message
      description: "Общее количество отправленных пользователем сообщений"
      calculation: "COUNT(id) where user_id = {user_id}"
      type: count

    - name: total_character_images
      entity_ref: Message
      description: "Общее количество картинок, отправленных персонажами. Считается по наличию 'image' в 'attachments'."
      agg_function: count
      sql: "id"
      filter: 'user_id IS NULL AND attachments @> ''[{"type": "image"}]'''
      type: count
    - name: total_sessions
      entity_ref: Message
      description: "Общее количество пользовательских сессий. Сессия - это последовательность сообщений от пользователя в одном канале, где время между двумя последовательными сообщениями не превышает 15 минут."
      calculation: "Требуется оконная функция для определения начала новой сессии (когда `created_at - LAG(created_at) > 15 минут`), с последующим подсчетом уникальных сессий."
      type: count

    # --- Финансовые метрики (источник - content.transactions) ---
    - name: total_revenue
      description: "Общий доход. Суммируются транзакции поступления на счет компании EUR_COMPANY_BALANCE_ID. Важно: `amount` в таких транзакциях отрицательный, поэтому для расчета дохода используется `-amount`."
      entity: Transaction
      agg_function: sum
      sql: "-amount"
      filter: "balance_id_to = '981206493'"
      format: currency
    - name: total_payments
      description: "Общее количество успешных транзакций пополнения (поступлений на счет компании)."
      entity: Transaction
      agg_function: count_distinct
      sql: "id"
      filter: "balance_id_to = '981206493'"
      format: number
    - name: arpu
      description: "Средний доход на пользователя (считается по платящим пользователям)."
      entity: Transaction
      calculation: "[Transaction.total_revenue] / [Transaction.paying_users]" # Требует создания метрики paying_users
      format: currency
    - name: daily_revenue_eur
      description: "Сумма полученных EUR за день на баланс EUR_COMPANY_BALANCE_ID (981206493). Важно: `amount` в таких транзакциях отрицательный, поэтому для расчета используется `-amount`."
      entity: Transaction
      agg_function: sum
      sql: "-amount"
      filter: "balance_id_to = '981206493'"
      format: currency

  relationships:
    - name: user_has_channels
      from_entity: User
      to_entity: Channel
      type: one_to_many
      on: User.id = Channel.user_id
    - name: user_sends_messages
      from_entity: User
      to_entity: Message
      type: one_to_many
      on: User.id = Message.user_id
    - name: channel_has_messages
      from_entity: Channel
      to_entity: Message
      type: one_to_many
      on: Channel.id = Message.channel_id
    - name: character_in_channel
      from_entity: Character
      to_entity: Channel
      type: one_to_many
      on: Character.id = Channel.char_id
    - name: story_in_channel
      from_entity: Story
      to_entity: Channel
      type: one_to_one
      on: Story.id = Channel.config_id
    - name: user_makes_invoices
      from_entity: User
      to_entity: Invoice
      type: one_to_many
      on: User.id = Invoice.customer_id
    - name: user_makes_transactions
      from_entity: User
      to_entity: Transaction
      type: one_to_many
      on: User.id = Transaction.user_id
    - name: user_from_ad_event
      from_entity: User
      to_entity: AdEvent
      type: one_to_many
      on: User.id = AdEvent.user_id
    - name: user_activates_gift_code
      from_entity: User
      to_entity: GiftCodeUserLink
      type: one_to_many
      on: User.id = GiftCodeUserLink.user_id
    - name: gift_code_is_activated
      from_entity: GiftCode
      to_entity: GiftCodeUserLink
      type: one_to_many
      on: GiftCode.id = GiftCodeUserLink.gift_code_id
    - name: user_has_profile
      from_entity: User
      to_entity: UserProfile
      type: one_to_one
      on: User.id = UserProfile.id
    - name: user_has_current_character
      description: "Связывает пользователя с его текущим выбранным персонажем в Telegram."
      from_entity: User
      to_entity: Character
      type: many_to_one
      on: User.current_telegram_character_id = Character.character_id

  actions:
    - name: lead
      description: "Пользователь оставил свои контактные данные или проявил явный интерес (например, нажал кнопку 'Связаться'). Основное событие для оценки конверсии."
      entity: AdEvent
      filter: "action = 'lead'"

    - name: tg_ad_start
      description: "Пользователь запустил бота через рекламную ссылку в Telegram (start=...)."
      entity: AdEvent
      filter: "action = 'tg_ad_start'"

    - name: tg_kicked
      description: "Пользователь был удален или заблокировал бота в Telegram. Важно для отслеживания оттока."
      entity: AdEvent
      filter: "action = 'tg_kicked'"

    - name: tg_post_sent
      description: "Пользователю было отправлено сообщение в рамках рассылки или автоворонки в Telegram."
      entity: AdEvent
      filter: "action = 'tg_post_sent'"

    - name: legacy_action
      description: "Событие из устаревшей системы. Используется для поддержки исторических данных."
      entity: AdEvent
      filter: "action = 'legacy_action'"
```

## Раздел 3: Слой ускорения (Acceleration Layer)

_Инструкция: Опишите предагрегированные витрины для ускорения частых запросов. Этот раздел будет заполнен позже по мере выявления узких мест в производительности._

```yaml
acceleration_layer:
  pre_aggregations:
    # - name: daily_revenue_by_source
    #   description: "Ежедневная выручка в разрезе источников трафика."
    #   measures:
    #     - Invoice.total_revenue
    #   dimensions:
    #     - Invoice.invoice_date
    #     - AdEvent.traffic_source
    #   refresh_policy: "every 1 hour"
    - name: agg_daily_user_stats
      description: "Предварительно агрегированная таблица с ежедневной статистикой по пользователям."
      materialization: table
      refresh_schedule: "every 1 day"
      sql: "SELECT ... GROUP BY date"
```

## Раздел 4: Контекстный / Презентационный слой (Business Context Layer)

_Инструкция: Добавьте бизнес-контекст: понятные названия, синонимы, формулы KPI. Это поможет AI лучше понимать ваш бизнес-язык._

```yaml
business_context_layer:
  metrics:
    - name: CPA
      description: "Cost Per Acquisition - Стоимость привлечения одного пользователя."
      formula: "[AdSpend.total_cost] / [User.new_users]"
      format: currency
      owner: "cto"
      status: "draft"
    - name: ROI
      description: "Return On Investment - Окупаемость инвестиций в рекламу."
      formula: "([Invoice.total_revenue] - [AdSpend.total_cost]) / [AdSpend.total_cost]"
      format: percentage
      owner: "cto"
      status: "draft"
    - name: Conversion_to_Payment
      description: "Конверсия из нового пользователя в платящего."
      formula: "[User.paying_users] / [User.new_users]" # Примечание: требует создания метрики paying_users
      format: percentage
      owner: "cto"
      status: "draft"
    - name: Retention_Day_1
      description: "Процент пользователей, вернувшихся в приложение на следующий день после регистрации."
      formula: "Когортный анализ: (вернувшиеся на день 1) / (новые пользователи в когорте)"
      format: percentage
      owner: "cto"
      status: "draft"
    - name: Avg_Sessions_Per_User
      description: "Среднее количество сессий на одного активного пользователя за период. Сессия - это блок сообщений с интервалом менее 15 минут между ними."
      formula: "[Message.total_sessions] / [User.total_users]"
      format: number
      owner: "cto"
      status: "draft"

  context:
    - asset: User
      synonyms: ["Пользователь", "Клиент", "Юзер"]
    - asset: Invoice.total_revenue
      synonyms: ["Доход", "Выручка", "Заработок", "Деньги"]
    - asset: AdEvent.traffic_source
      synonyms: ["Источник трафика", "Канал привлечения", "UTM Source"]
    - asset: AdEvent.ad_campaign
      synonyms: ["Рекламная кампания", "Кампания"]

  constants:
    - name: BalanceIDs
      description: "Системные ID балансов компании для различных операций."
      items:
        - name: TRUEVO_PAYMENT_SYSTEM_BALANCE_ID
          value: 7361852548
          description: "Баланс, представляющий платежную систему Truevo. Основной источник поступления EUR при оплате."
        - name: TELEGRAM_STARS_PAYMENT_SYSTEM_BALANCE_ID
          value: 290520168
          description: "Баланс, представляющий платежную систему Telegram Stars. Источник поступления средств."
        - name: EUR_COMPANY_BALANCE_ID
          value: 981206493
          description: "Основной счет компании для учета выручки в EUR. Средства поступают сюда с балансов пользователей после оплаты."
        - name: TOKEN_COMPANY_BALANCE_ID
          value: 50805419
          description: "Счет компании для эмиссии платных токенов и сбора токенов, потраченных на платные действия."
        - name: SERVICE_COMPANY_BALANCE_ID
          value: 62811734
          description: "Счет компании для эмиссии 'сервисных' токенов (символизируют подписку или выполненное платное действие)."
        - name: TRIAL_TOKEN_COMPANY_BALANCE_ID
          value: 572450034
          description: "Счет для сбора неиспользованных триальных токенов при переходе пользователя на платный тариф."
        - name: EXPIRED_TOKEN_COMPANY_BALANCE_ID
          value: 331924282
          description: "Счет для сбора токенов с истекшим сроком действия с балансов пользователей."
        - name: InternalUserEmails
          description: "Список email-адресов внутренних/тестовых аккаунтов, которые следует исключать из аналитики."
          items:
            - "183901411@tg.flirtello.com"
            - "126464893@tg.flirtello.com"
            - "644920251@tg.flirtello.com"
            - "umaxfun@gmail.com"
            - "flirtello2024@gmail.com"
            - "novozhilovge@gmail.com"
            - "yurgenich++++++++++++++++++++++++++@gmail.com"
```

## Раздел 4.5: План счетов и финансовые потоки (Chart of Accounts & Financial Flows)

_Инструкция: Этот раздел описывает основные финансовые операции в системе в виде бухгалтерских проводок по системным и пользовательским счетам. Это помогает понять логику, лежащую в основе транзакций._

### 1. Покупка услуги (Тарифный план или Пакет токенов)

Этот процесс состоит из двух основных этапов, связанных общим `correlation_id`.

**Этап 1: Поступление средств от платежной системы**
Пользователь платит через Truevo или Telegram. Средства зачисляются на временный баланс пользователя.

- **Дт (Куда):** Баланс пользователя (EUR)
- **Кт (Откуда):** `TRUEVO_PAYMENT_SYSTEM_BALANCE_ID` или `TELEGRAM_STARS_PAYMENT_SYSTEM_BALANCE_ID`
- **Сумма:** Стоимость услуги в EUR
- **Тип транзакции:** `TopUpWithdrawTransactionTypes`

**Этап 2: Списание средств в пользу компании и выдача ценности**
Сразу после зачисления средства списываются с баланса пользователя на счет выручки компании. Одновременно пользователю начисляется купленная ценность (токены или сервисная подписка).

**Проводка 2.1: Учет выручки**

- **Дт (Куда):** `EUR_COMPANY_BALANCE_ID`
- **Кт (Откуда):** Баланс пользователя (EUR)
- **Сумма:** Стоимость услуги в EUR
- **Тип транзакции:** `TopUpWithdrawTransactionTypes`

**Проводка 2.2: Выдача ценности (зависит от услуги)**

- **Если куплен пакет токенов:**
  - **Дт (Куда):** Баланс пользователя (TOKEN)
  - **Кт (Откуда):** `TOKEN_COMPANY_BALANCE_ID`
  - **Сумма:** Количество токенов в пакете
  - **Тип транзакции:** `TopUpWithdrawTransactionTypes`
- **Если куплен тарифный план (подписка):**
  - **Дт (Куда):** Баланс пользователя (SERVICE)
  - **Кт (Откуда):** `SERVICE_COMPANY_BALANCE_ID`
  - **Сумма:** 1 (одна подписка)
  - **Тип транзакции:** `PurchaseSaleTransactionTypes`

---

### 2. Использование платной услуги (Трата токенов)

Когда пользователь совершает платное действие (например, открывает фото), с его баланса списываются токены.

- **Дт (Куда):** `TOKEN_COMPANY_BALANCE_ID`
- **Кт (Откуда):** Баланс пользователя (TOKEN)
- **Сумма:** Стоимость действия в токенах
- **Тип транзакции:** `TopUpWithdrawTransactionTypes`
- **Примечание:** Каждое платное действие также выдает пользователю "сервисный" токен (`SERVICE_COMPANY_BALANCE_ID` -> `Баланс пользователя (SERVICE)`), что отражает факт получения услуги.

---

### 3. Клиринг (Системные операции)

Эти операции выполняются периодически.

**Проводка 3.1: Списание просроченных токенов**

- **Дт (Куда):** `EXPIRED_TOKEN_COMPANY_BALANCE_ID`
- **Кт (Откуда):** Баланс пользователя (TOKEN)
- **Сумма:** Количество списанных просроченных токенов
- **Тип транзакции:** `TopUpWithdrawTransactionTypes`

**Проводка 3.2: Возврат неиспользованных триальных токенов**
При переходе с триального на платный тариф остаток триальных токенов возвращается компании.

- **Дт (Куда):** `TRIAL_TOKEN_COMPANY_BALANCE_ID`
- **Кт (Откуда):** Баланс пользователя (TOKEN)
- **Сумма:** Остаток триальных токенов
- **Тип транзакции:** `TopUpWithdrawTransactionTypes`

---

### 4. Активация промокода (Gift Code)

Когда пользователь активирует промокод, ему начисляются токены со счета компании. Эта операция не включает поступление реальных денег.

- **Дт (Куда):** Баланс пользователя (TOKEN)
- **Кт (Откуда):** `TOKEN_COMPANY_BALANCE_ID`
- **Сумма:** Количество токенов, указанное в промокоде (`token_amount`).
- **Тип транзакции:** `TopUpWithdrawTransactionTypes`
- **Примечание:** `service_id` в транзакции будет равен `id` активированного промокода (`gift_codes.id`).

---

### 5. Структура транзакций и пары транзакций

**ВАЖНО:** Все финансовые операции в системе создаются парами транзакций через функцию `trace_transactions()`. Это необходимо для двойной записи (double-entry bookkeeping) и обеспечения целостности данных.

#### 5.1. Пара транзакций

Каждая финансовая операция создает **две связанные транзакции**:

1. **Первая транзакция:**
   - `balance_id_from` = источник средств (откуда списывается)
   - `balance_id_to` = получатель средств (куда зачисляется)
   - `amount` = сумма операции (может быть положительной или отрицательной)
   - `correlation_id` = UUID второй транзакции в паре

2. **Вторая транзакция:**
   - `balance_id_from` = получатель средств из первой транзакции (`balance_id_to` первой)
   - `balance_id_to` = источник средств из первой транзакции (`balance_id_from` первой)
   - `amount` = противоположная сумма первой транзакции
   - `correlation_id` = UUID первой транзакции в паре

**Пример пары транзакций при пополнении токенов (например, при покупке или корректировке баланса):**

Транзакция 1 (зачисление на баланс пользователя):
```sql
id: '3f73fd79-6923-4f74-a405-cadc2c7c0ce9'
balance_id_from: 50805419   -- TOKEN_COMPANY_BALANCE_ID (компания)
balance_id_to: 230376       -- баланс пользователя (TOKEN)
amount: 1.5
correlation_id: '0faa6295-8e9c-4fcf-80af-b6027986db79'  -- ссылка на транзакцию 2
transaction_type: 'BALANCE_TOP_UP'
```

Транзакция 2 (списание с баланса компании):
```sql
id: '0faa6295-8e9c-4fcf-80af-b6027986db79'
balance_id_from: 230376      -- баланс пользователя (TOKEN)
balance_id_to: 50805419      -- TOKEN_COMPANY_BALANCE_ID (компания)
amount: -1.5
correlation_id: '3f73fd79-6923-4f74-a405-cadc2c7c0ce9'  -- ссылка на транзакцию 1
transaction_type: 'BALANCE_WITHDRAW'
```

**Примечание:** Обратите внимание, что `amount` во второй транзакции противоположен первой (отрицательный), а `balance_id_from` и `balance_id_to` поменяны местами. Это обеспечивает двойную запись: если токены зачисляются на баланс пользователя, они одновременно списываются с баланса компании.

#### 5.2. Определение направления транзакции с точки зрения пользователя

Для отображения транзакций пользователю важно определить направление операции:

- **Пополнение (Top-up):** `balance_id_to == user_balance_id`
  - Пользователь получает средства (токены, EUR и т.д.)
  - Пример: покупка токенов, активация промокода

- **Списание (Withdraw/Payment):** `balance_id_from == user_balance_id`
  - Пользователь отдает средства (токены, EUR и т.д.)
  - Пример: оплата сообщения, оплата фото

**ВАЖНО:** Не полагайтесь на `transaction_type` для определения направления! Тип транзакции (`BALANCE_TOP_UP`, `BALANCE_WITHDRAW`, `PURCHASE`, `SALE`) может быть одинаковым для обеих транзакций в паре, но направление определяется по `balance_id_from` и `balance_id_to`.

#### 5.3. Фильтрация транзакций для отображения пользователю

При отображении истории транзакций пользователю:

1. **Фильтруйте по участию пользователя:**
   ```sql
   WHERE (balance_id_from = user_balance_id OR balance_id_to = user_balance_id)
   ```

2. **Убирайте дубликаты пар:**
   - Каждая пара транзакций должна отображаться только один раз
   - Используйте `correlation_id` для группировки пар
   - Показывайте только одну транзакцию из каждой пары (обычно ту, где пользователь участвует напрямую)

3. **Определяйте тип операции:**
   - Проверяйте `additional_data.reason` для системных операций (например, `test_balance_correction`)
   - Проверяйте `service_id`:
     - Если указывает на `paid_actions` → платное действие (Message, Photo и т.д.)
     - Если указывает на `token_packs` → покупка токенов
     - Если указывает на `gift_codes` → активация промокода
   - Используйте `transaction_type` как fallback

4. **Выбирайте правильную транзакцию из пары для отображения:**
   - Для **списаний** (платные действия): показывайте транзакцию, где `balance_id_from == user_balance_id` (FROM_USER)
   - Для **пополнений** (покупка токенов, корректировка баланса): показывайте транзакцию, где `balance_id_to == user_balance_id` (TO_USER)
   - Для корректировок баланса (`additional_data.reason == "test_balance_correction"`): всегда показывайте TO_USER
   - Для платных действий (есть `service_id` и `transaction_type` содержит "WITHDRAW"): всегда показывайте FROM_USER

**Примечание:** Структура таблиц `content.transactions` и `content.balances` описана в разделе 1 (Base Layer). Список системных балансов компании находится в разделе 4 (Business Context Layer, constants).

---

## Раздел 5: Слой доступа (Security Layer)

_Инструкция: Определите роли и правила доступа к данным. Этот раздел будет сконфигурирован позже._

```yaml
security_layer:
  access_grants:
    # - name: Admin
    #   description: "Полный доступ ко всем данным."
    # - name: Marketing
    #   description: "Доступ только к маркетинговым и финансовым данным, без персональных данных пользователей."

  row_level_security:
    # - name: marketing_can_see_own_campaigns
    #   grant: Marketing
    #   applies_to: [AdEvent, User, Invoice]
    #   condition: "AdEvent.owner_id = {{ security_context.user_id }}"

  column_level_security:
    # - name: hide_user_email_from_marketing
    #   grant: Marketing
    #   applies_to: [User.email]
    #   action: hide
    - name: PII_access_policy
```
