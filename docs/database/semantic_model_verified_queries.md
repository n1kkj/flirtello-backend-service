## Раздел 6: Примеры запросов (Query Examples)

### `mktg_stats_daily_users_by_source`
**Описание:** Запрос для подсчета количества уникальных пользователей за каждый день в разрезе их последнего известного источника трафика.
```sql mktg_stats_daily_users_by_source
WITH last_source AS (
    SELECT user_id,
        created_at,
        params->>'source' AS traffic_source,
        ROW_NUMBER() OVER (
            PARTITION BY user_id
            ORDER BY created_at DESC
        ) as rn
    FROM mktdata.mktdata_raw
    WHERE action = 'tg_ad_start'
)
SELECT date_trunc('day', created_at AT TIME ZONE 'Europe/Moscow') AS date_bucket,
    traffic_source,
    COUNT(DISTINCT user_id) AS user_count
FROM last_source
WHERE rn = 1
GROUP BY date_bucket,
    traffic_source
ORDER BY date_bucket DESC,
    user_count DESC;
```
**Пример результата:**
```json
[
  {
    "date_bucket": "2025-06-28T00:00:00+00:00",
    "traffic_source": "bresciehill700aiko",
    "user_count": 5
  },
  {
    "date_bucket": "2025-06-28T00:00:00+00:00",
    "traffic_source": "realhardxxx170aiko",
    "user_count": 2
  },
  {
    "date_bucket": "2025-06-27T00:00:00+00:00",
    "traffic_source": "bresciehill700aiko",
    "user_count": 15
  }
]
```

### `user_satisfaction_and_content_quality`
**Описание:** Запрос для подсчета пользовательских отзывов (лайков/дизлайков) и агрегации категорий обратной связи. Примечание: Гарантирует, что каждое сообщение считается только один раз, даже если у него несколько категорий.
```sql user_satisfaction_and_content_quality
-- Запрос для подсчета пользовательских отзывов (лайков/дизлайков)
-- и агрегации категорий обратной связи.
-- Примечание: Гарантирует, что каждое сообщение считается только один раз,
-- даже если у него несколько категорий.
SELECT
    -- Дата отзыва
    CAST(m.inserted_at AS DATE) AS review_date,
    -- Статус отзыва (LIKE/DISLIKE)
    m.review_status,
    -- Общее количество уникальных сообщений с отзывом
    COUNT(DISTINCT m.id) AS total_reviews,
    -- Список уникальных категорий, перечисленных через запятую
    STRING_AGG(DISTINCT category_name, ', ') AS top_review_categories
FROM
    public.messages m,
    -- "Разворачиваем" массив категорий для обработки каждой в отдельности
    unnest(m.review_categories) AS category_name
WHERE
    m.review_status IS NOT NULL AND m.review_status != 'NEUTRAL'
GROUP BY
    review_date,
    m.review_status
ORDER BY
    review_date DESC;
```

### `character_popularity_and_engagement`
**Описание:** Рассчитывает популярность и вовлеченность персонажей. Связывает сообщения пользователей с персонажами через `channel_id`. `total_tokens_spent` — это расход в токенах, а не в валюте.
```sql character_popularity_and_engagement
-- Map channel to character to correctly attribute user messages
WITH channel_to_character_map AS (
    SELECT DISTINCT
        channel_id,
        char_id
    FROM
        public.messages
    WHERE
        char_id IS NOT NULL AND channel_id IS NOT NULL
),
-- Calculate engagement stats using the channel-character map
engagement_stats AS (
    SELECT
        m.char_id AS character_id,
        COUNT(u_msg.id) AS total_messages,
        COUNT(DISTINCT u_msg.user_id) AS total_users_engaged,
        COUNT(DISTINCT u_msg.channel_id) AS total_channels_engaged
    FROM
        channel_to_character_map AS m
    JOIN
        public.messages AS u_msg ON m.channel_id = u_msg.channel_id
    WHERE
        u_msg.user_id IS NOT NULL
    GROUP BY
        m.char_id
),
-- Calculate token spending stats
revenue_stats AS (
    WITH valid_transactions AS (
      SELECT
        (additional_data::jsonb ->> 'char_id') as char_id_str,
        amount
      FROM
        content.transactions
      WHERE
        additional_data::jsonb ? 'char_id'
        AND additional_data::jsonb ->> 'char_id' ~ '^[0-9]+$'
        AND balance_id_from = '50805419' -- User token balance
    )
    SELECT
      t.char_id_str::int AS character_id,
      SUM(t.amount) AS total_tokens_spent
    FROM
      valid_transactions AS t
    GROUP BY
      t.char_id_str::int
)
-- Final SELECT to join all stats for published characters
SELECT
    c.id AS character_id,
    c.name AS character_name,
    COALESCE(e.total_messages, 0) AS total_messages,
    COALESCE(e.total_users_engaged, 0) AS total_users_engaged,
    COALESCE(e.total_channels_engaged, 0) AS total_channels_engaged,
    COALESCE(r.total_tokens_spent, 0) AS total_tokens_spent
FROM
    content.content_characters c
LEFT JOIN engagement_stats e ON c.id = e.character_id
LEFT JOIN revenue_stats r ON c.id = r.character_id
WHERE
    c.status = 'published'
    AND (e.character_id IS NOT NULL OR r.character_id IS NOT NULL) 
ORDER BY
    total_tokens_spent DESC, total_messages DESC;
```

### `average_user_lifetime_value_ltv`
**Описание:** Рассчитывает средний LTV по когортам пользователей. Когорта определяется датой первой покупки. Доход рассчитывается как транзакции на счет компании.
```sql average_user_lifetime_value_ltv
WITH paid_users AS (
    -- 1. Находим всех пользователей, у которых есть хотя бы один оплаченный счет
    SELECT DISTINCT customer_id
    FROM content.invoices
    WHERE status = 'PAID' AND customer_id IS NOT NULL
),
revenue_transactions AS (
    -- 2. Выбираем только транзакции дохода для этих пользователей
    SELECT
        user_id,
        -amount AS amount, -- Инвертируем сумму для получения положительного дохода
        created_at
    FROM content.transactions
    WHERE user_id IN (SELECT customer_id FROM paid_users)
      AND balance_id_to = 981206493 -- Фильтруем по ID счета компании
),
user_first_purchase AS (
    -- 3. Определяем дату первой покупки для каждой когорты
    SELECT
        user_id,
        MIN(created_at) AS first_purchase_date
    FROM revenue_transactions
    GROUP BY user_id
),
user_ltv AS (
    -- 4. Считаем LTV для каждого пользователя
    SELECT
        user_id,
        SUM(amount) AS total_spent
    FROM revenue_transactions
    GROUP BY user_id
)
-- 5. Агрегируем LTV по когортам
SELECT
    CAST(ufp.first_purchase_date AS DATE) AS cohort_date,
    AVG(ul.total_spent) AS average_ltv
FROM user_first_purchase ufp
JOIN user_ltv ul ON ufp.user_id = ul.user_id
GROUP BY 1
ORDER BY 1;
```
**Пример результата:**
```json
[
  {
    "cohort_date": "2024-10-16",
    "average_ltv": 47.5
  },
  {
    "cohort_date": "2024-10-17",
    "average_ltv": 40.0
  },
  {
    "cohort_date": "2024-10-19",
    "average_ltv": 15.0
  }
]
```

### `funnel_and_retention_analysis`
**Описание:** SQL-запрос для анализа основной воронки пользователей: Регистрация -> Активация -> Оплата.
```sql funnel_and_retention_analysis
WITH user_cohorts AS (
    -- Шаг 1: Собираем всех не-анонимных пользователей
    SELECT 
        id as user_id,
        CAST(created_at AS DATE) as registration_date
    FROM auth.users
    WHERE is_anonymous = false
),
user_first_message AS (
    -- Шаг 2: Находим дату первого сообщения для каждого пользователя
    SELECT
        c.user_id,
        MIN(CAST(m.inserted_at AS DATE)) as first_message_date
    FROM public.channels c
    JOIN public.messages m ON c.id = m.channel_id
    GROUP BY c.user_id
),
user_first_payment AS (
    -- Шаг 3: Находим дату первого платежа, используя дату транзакции
    SELECT
        i.customer_id AS user_id,
        MIN(CAST(t.created_at AS DATE)) AS first_payment_date
    FROM content.invoices i
    JOIN content.transactions t ON i.service_id = t.service_id AND i.customer_id = t.user_id
    WHERE i.status = 'PAID' 
      AND t.balance_id_to = 981206493 -- EUR_COMPANY_BALANCE_ID
      AND t.transaction_type = 'BALANCE_WITHDRAW'
    GROUP BY i.customer_id
),
funnel_data AS (
    -- Соединяем все данные вместе
    SELECT
        u.user_id,
        u.registration_date,
        fm.first_message_date,
        fp.first_payment_date
    FROM user_cohorts u
    LEFT JOIN user_first_message fm ON u.user_id = fm.user_id
    LEFT JOIN user_first_payment fp ON u.user_id = fp.user_id
)
-- Агрегируем данные по когортам (месяцам регистрации)
SELECT
    TO_CHAR(registration_date, 'YYYY-MM') AS cohort_month,
    COUNT(DISTINCT user_id) AS total_registered,
    COUNT(DISTINCT CASE WHEN first_message_date IS NOT NULL THEN user_id END) AS total_activated,
    COUNT(DISTINCT CASE WHEN first_payment_date IS NOT NULL THEN user_id END) AS total_paid
FROM funnel_data
GROUP BY 1
ORDER BY 1;
```
**Пример результата:**
```json
[
  {
    "cohort_month": "2024-10",
    "total_registered": 62,
    "total_activated": 59,
    "total_paid": 13
  }
]
```

### `daily_character_interactions`
**Описание:** Проверить корректность работы запроса. Если данных нет, выяснить причину: возможно, выбран слишком малый период, или сам запрос содержит ошибку.
```sql
SELECT
  t.char_id as c_id,
  c.name as c_name,
  count(*) as interactions_times,
  DATE(t.inserted_at) as interaction_date
FROM
  content.message_archive t
INNER JOIN
  content.content_characters as c ON c.id = t.char_id
GROUP BY
  c.name, t.char_id, DATE(t.inserted_at)
ORDER BY
  interaction_date DESC, interactions_times DESC;
```
**Пример результата:**
```json
[
  {"c_id": 12, "c_name": "Rachel", "interactions_times": 15, "interaction_date": "2025-06-29"},
  {"c_id": 24, "c_name": "Aiko", "interactions_times": 12, "interaction_date": "2025-06-28"},
  {"c_id": 38, "c_name": "Holly", "interactions_times": 4, "interaction_date": "2025-06-28"},
  {"c_id": 34, "c_name": "Zoe", "interactions_times": 4, "interaction_date": "2025-06-28"},
  {"c_id": 24, "c_name": "Aiko", "interactions_times": 28, "interaction_date": "2025-06-27"},
  {"c_id": 10, "c_name": "Jessica", "interactions_times": 24, "interaction_date": "2025-06-27"},
  {"c_id": 34, "c_name": "Zoe", "interactions_times": 12, "interaction_date": "2025-06-27"},
  {"c_id": 16, "c_name": "Ellie", "interactions_times": 6, "interaction_date": "2025-06-27"},
  {"c_id": 8, "c_name": "Anna", "interactions_times": 6, "interaction_date": "2025-06-27"},
  {"c_id": 38, "c_name": "Holly", "interactions_times": 4, "interaction_date": "2025-06-27"}
]
```

### `mktg_stats_sources_of_truth`
**Описание:** Запрос для подсчета количества уникальных пользователей по источнику и кампании.
```sql mktg_stats_sources_of_truth
SELECT
  params->>'source' as "source",
  params->>'campaign' as campaign,
  COUNT(DISTINCT user_id) AS total_users
FROM mktdata.mktdata_raw
GROUP BY 1, 2
ORDER BY 1 DESC;
```
**Пример результата:**
```json
[
  {
    "source": "video",
    "campaign": null,
    "total_users": 151
  },
  {
    "source": "tvshow",
    "campaign": null,
    "total_users": 7
  }
]
```

### `user_engagement_and_retention_by_cohort`
**Описание:** Рассчитывает удержание пользователей по когортам, основываясь на дате их регистрации и последующей активности (отправке сообщений).
```sql user_engagement_and_retention_by_cohort
WITH user_cohorts AS (
    SELECT
        id AS user_id,
        CAST(created_at AS DATE) AS cohort_date
    FROM auth.users
    WHERE is_anonymous = false
),
user_daily_activity AS (
    SELECT
        c.user_id,
        CAST(m.inserted_at AS DATE) AS activity_date
    FROM public.channels c
    JOIN public.messages m ON c.id = m.channel_id
    GROUP BY 1, 2
)
SELECT
    uc.cohort_date,
    (uda.activity_date - uc.cohort_date) AS days_since_registration,
    COUNT(DISTINCT uda.user_id) AS retained_users
FROM user_cohorts uc
JOIN user_daily_activity uda ON uc.user_id = uda.user_id
WHERE uda.activity_date >= uc.cohort_date
GROUP BY 1, 2
ORDER BY 1, 2;
```
**Пример результата:**
```json
[
  {
    "cohort_date": "2024-10-16",
    "days_since_registration": 0,
    "retained_users": 3
  },
  {
    "cohort_date": "2024-10-16",
    "days_since_registration": 1,
    "retained_users": 3
  }
]
```

### `user_engagement_by_traffic_source`
**Описание:** Рассчитывает вовлеченность пользователей (среднее количество просмотренных изображений на пользователя) в разрезе источников трафика.
```sql user_engagement_by_traffic_source
WITH user_image_counts AS (
  SELECT
    c.user_id,
    COUNT(m.id) as image_count
  FROM public.messages m
  JOIN public.channels c ON m.channel_id = c.id
  WHERE
    m.user_id IS NULL -- Сообщения от персонажа
    AND m.attachments @> '[{"type": "image"}]'
  GROUP BY c.user_id
),
user_traffic_source AS (
  SELECT
    user_id,
    params->>'source' AS traffic_source,
    ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY created_at DESC) as rn
  FROM mktdata.mktdata_raw
  WHERE action = 'tg_ad_start'
)
SELECT
  COALESCE(uts.traffic_source, 'Direct/Unknown') AS traffic_source,
  COUNT(DISTINCT uic.user_id) AS total_users,
  SUM(uic.image_count) AS total_images_viewed,
  (SUM(uic.image_count) / COUNT(DISTINCT uic.user_id)) AS avg_images_per_user
FROM user_image_counts uic
LEFT JOIN user_traffic_source uts ON uic.user_id = uts.user_id AND uts.rn = 1
JOIN auth.users u ON uic.user_id = u.id
WHERE 
  u.email NOT IN ('183901411@tg.flirtello.com', '126464893@tg.flirtello.com', '644920251@tg.flirtello.com', 'umaxfun@gmail.com', 'flirtello2024@gmail.com', 'novozhilovge@gmail.com', 'yurgenich++++++++++++++++++++++++++@gmail.com')
GROUP BY COALESCE(uts.traffic_source, 'Direct/Unknown')
ORDER BY avg_images_per_user DESC;
```
**Пример результата:**
```json
[
  {
    "traffic_source": "heat30aiko",
    "total_users": 1,
    "total_images_viewed": "20",
    "avg_images_per_user": "20.00"
  },
  {
    "traffic_source": "Direct/Unknown",
    "total_users": 2833,
    "total_images_viewed": "18500",
    "avg_images_per_user": "6.53"
  }
]
```

### `registered_telegram_users`
**Описание:** Запрос для получения списка зарегистрированных пользователей Telegram с подтвержденным email.
```sql registered_telegram_users
SELECT
  email,
  DATE(created_at) as registration_date
FROM
  auth.users
WHERE
  email_confirmed_at IS NOT NULL
  AND email LIKE '%@tg.flirtello.com'
ORDER BY
  registration_date DESC;
```
**Пример результата:**
```json
[
  {
    "email": "7512254394@tg.flirtello.com",
    "registration_date": "2025-06-28"
  },
  {
    "email": "5698255752@tg.flirtello.com",
    "registration_date": "2025-06-28"
  },
  {
    "email": "1626323876@tg.flirtello.com",
    "registration_date": "2025-06-28"
  }
]
```

### `registered_web_users`
**Описание:** Запрос для получения списка зарегистрированных пользователей, которые пришли не через Telegram.
```sql registered_web_users
SELECT
  email,
  DATE(created_at) as registration_date
FROM
  auth.users
WHERE
  email_confirmed_at IS NOT NULL
  AND email NOT LIKE '%@tg.flirtello.com'
ORDER BY
  registration_date DESC;
```
**Пример результата:**
```json
[
  {
    "email": "test.user@example.com",
    "registration_date": "2025-06-27"
  },
  {
    "email": "another.user@example.com",
    "registration_date": "2025-06-27"
  }
]
```

### `daily_payments_from_gateways`
**Описание:** Запрос для отслеживания ежедневных платежей через разные платежные шлюзы, включая подсчет уникальных платящих пользователей и общей суммы дохода.
```sql daily_payments_from_gateways
SELECT
  DATE(t.created_at) AS transaction_date,
  CASE
    WHEN t.balance_id_from = '7361852548' THEN 'Main Payment System'
    WHEN t.balance_id_from = '290520168' THEN 'Telegram Stars'
    ELSE 'Unknown'
  END AS payment_gateway,
  COUNT(DISTINCT t.user_id) AS paying_users,
  SUM(-t.amount) AS total_amount
FROM
  content.transactions AS t
WHERE
  t.balance_id_from IN ('7361852548', '290520168') -- PAYMENT_SYSTEM_BALANCE_ID, TELEGRAM_STARS_PAYMENT_SYSTEM_BALANCE_ID
GROUP BY
  transaction_date, payment_gateway
ORDER BY
  transaction_date DESC, total_amount DESC;
```
**Пример результата:**
```json
[
  {
    "transaction_date": "2025-06-23",
    "payment_gateway": "Telegram Stars",
    "paying_users": 1,
    "total_amount": 9.98
  },
  {
    "transaction_date": "2025-05-30",
    "payment_gateway": "Main Payment System",
    "paying_users": 4,
    "total_amount": 65.93
  }
]
```

### `daily_eur_flow`
**Описание:** Запрос для отслеживания ежедневных поступлений в EUR на счет компании от пользователей.
```sql daily_eur_flow
SELECT
  t.user_id AS user_id,
  u.email AS email,
  DATE(t.created_at) AS transaction_date,
  SUM(-t.amount) AS eur_received -- Инвертировано для наглядности
FROM
  content.transactions AS t
JOIN -- INNER JOIN является корректным, т.к. транзакция не может существовать без пользователя
  auth.users AS u
ON
  t.user_id = u.id
WHERE
  t.balance_id_to = '981206493' -- EUR_COMPANY_BALANCE_ID
GROUP BY
  t.user_id, u.email, transaction_date
ORDER BY
  eur_received DESC;
```
**Пример результата:**
```json
[
  {
    "user_id": "9cdea35f-a1fa-4bfe-b2b8-7037bef1f181",
    "email": "justinwang0987@gmail.com",
    "transaction_date": "2025-01-11",
    "eur_received": 200.00
  },
  {
    "user_id": "efb3e6c3-0b0a-42cb-8991-1d8eb561e3a5",
    "email": "aidenpearce2001@gmail.com",
    "transaction_date": "2024-12-05",
    "eur_received": 65.00
  }
]
```

### `daily_paid_token_distribution`
**Описание:** Запрос для анализа распределения токенов, выданных по промокодам. Он агрегирует данные по пользователям и дням, основываясь на фактических транзакциях пополнения баланса.
```sql daily_paid_token_distribution
-- Запрос для анализа распределения токенов, выданных по промокодам.
-- Он агрегирует данные по пользователям и дням, основываясь на фактических
-- транзакциях пополнения баланса.
SELECT
    -- ID пользователя
    t.user_id,
    -- Email пользователя для идентификации
    u.email,
    -- Дата начисления токенов
    CAST(t.created_at AS DATE) AS distribution_date,
    -- Суммарное количество токенов, полученных по промокодам за день
    SUM(t.amount) AS tokens_from_gift_codes
FROM
    -- Основная таблица с транзакциями
    content.transactions AS t
JOIN
    -- Присоединяем пользователей для получения email
    auth.users AS u ON t.user_id = u.id
WHERE
    -- Фильтруем только транзакции пополнения баланса
    t.transaction_type = 'BALANCE_TOP_UP'
    -- И оставляем только те, что связаны с промокодами
    AND t.service_id IN (SELECT id FROM content.gift_codes)
GROUP BY
    t.user_id,
    u.email,
    distribution_date
ORDER BY
    distribution_date DESC;
```
**Пример результата:**
```json
[
  {
    "user_id": "74ee65ee-2a7d-49cb-a0a8-a43c6789c0cb",
    "email": "1626323876@tg.flirtello.com",
    "distribution_date": "2025-06-28",
    "tokens_from_gift_codes": 10
  },
  {
    "user_id": "b583bd42-0c9d-4269-b880-8f30d8660881",
    "email": "7512254394@tg.flirtello.com",
    "distribution_date": "2025-06-28",
    "tokens_from_gift_codes": 10
  },
  {
    "user_id": "088a2c2d-3153-4209-9aa6-1a545f9f01bb",
    "email": "6984231305@tg.flirtello.com",
    "distribution_date": "2025-06-27",
    "tokens_from_gift_codes": 30
  }
]
```

### `daily_user_spending_eur`
**Описание:** Запрос для подсчета ежедневных трат пользователей в EUR. Он суммирует все транзакции, где получателем является счет компании в EUR.
```sql daily_user_spending_eur
-- Запрос для подсчета ежедневных трат пользователей в EUR.
-- Он суммирует все транзакции, где получателем является счет компании в EUR.
SELECT
  -- ID пользователя
  t.user_id,
  -- Email пользователя для идентификации
  u.email,
  -- Дата транзакции
  DATE(t.created_at) AS transaction_date,
  -- Сумма потраченных EUR (в абсолютном значении)
  ABS(SUM(t.amount)) AS spent_eur
FROM
  content.transactions AS t
JOIN
  auth.users AS u
ON
  t.user_id = u.id
WHERE
  -- Фильтруем транзакции, где получатель - счет компании в EUR
  t.balance_id_to = '981206493' -- EUR_COMPANY_BALANCE_ID
GROUP BY
  t.user_id,
  u.email,
  transaction_date
ORDER BY
  spent_eur DESC;
```
**Пример результата:**
```json
[
  {
    "user_id": "9cdea35f-a1fa-4bfe-b2b8-7037bef1f181",
    "email": "justinwang0987@gmail.com",
    "transaction_date": "2025-01-11",
    "spent_eur": 200
  },
  {
    "user_id": "efb3e6c3-0b0a-42cb-8991-1d8eb561e3a5",
    "email": "aidenpearce2001@gmail.com",
    "transaction_date": "2024-12-05",
    "spent_eur": 65
  },
  {
    "user_id": "9eb13562-c769-45fe-ab61-62237704ef53",
    "email": "kayley.france8966@gmail.com",
    "transaction_date": "2025-01-05",
    "spent_eur": 55
  }
]
```

### `new_telegram_users_with_character_and_config`
**Описание:** Запрос для получения новых пользователей из Telegram за последний месяц. Включает информацию о выбранном персонаже и `config_id` чата, если они существуют. Корректно обрабатывает случаи, когда у пользователя нет персонажа или чата, отображая `NULL`.
```sql new_telegram_users_with_character_and_config
WITH user_base AS (
  SELECT
    u.id,
    u.email,
    u.created_at,
    CASE
      WHEN pu.settings ? 'angel_char_id' AND pu.settings -> 'angel_char_id' ~ '^[0-9]+$'
      THEN (pu.settings -> 'angel_char_id')::integer
      ELSE NULL
    END AS angel_char_id
  FROM
    auth.users AS u
    LEFT JOIN public.users AS pu ON u.id = pu.id
  WHERE
    u.created_at >= NOW() - INTERVAL '1 month'
    AND u.email LIKE '%@tg.flirtello.com'
)
SELECT
  split_part(ub.email, '@', 1) AS telegram_id,
  ub.id AS user_id,
  cc.name AS character_name,
  ch.config_id,
  ub.email,
  ub.created_at,
  cc.id AS character_id
FROM
  user_base ub
  LEFT JOIN content.content_characters AS cc ON ub.angel_char_id = cc.id
  LEFT JOIN public.channels AS ch ON ub.id = ch.user_id AND cc.id = ch.char_id
ORDER BY
  ub.created_at DESC;
```

### `translator_weekly_translations_by_language`
**Описание:** Запрос для подсчета количества переводов для каждого языка за последние 7 дней. Полезно для отслеживания активности по локализации.
```sql translator_weekly_translations_by_language
SELECT
    "language",
    COUNT(id) as translation_count
FROM
    translator.translations
WHERE
    created_at >= NOW() - INTERVAL '7 days'
GROUP BY
    "language"
ORDER BY
    translation_count DESC;
```
**Пример результата:**
```json
[
  {
    "language": "en",
    "translation_count": 1513
  },
  {
    "language": "ru",
    "translation_count": 1218
  },
  {
    "language": "es",
    "translation_count": 152
  }
]
```
