-- Earned money EUR(total)
SELECT
  SUM(t.amount) as amount,
  DATE (t.created_at) as interaction_date
FROM
  content.transactions as t
WHERE
  t.balance_id_from = 981206493
GROUP BY
  interaction_date;

-- Earned money EUR(fake)
SELECT
  SUM(t.amount) as amount,
  DATE (t.created_at) as interaction_date
FROM
  content.transactions as t
WHERE
  t.balance_id_to = 7361852548
GROUP BY
  interaction_date;

-- Earned money EUR(truevo)
SELECT
  SUM(t.amount) as amount,
  DATE (t.created_at) as interaction_date
FROM
  content.transactions as t
WHERE
  t.balance_id_to = 1129648012
GROUP BY
  interaction_date;

-- Photo rating sells statistic
SELECT
  COUNT(*) / 4 AS sells_count,
  ci.rating,
  DATE (t.created_at) as interaction_date
FROM
  content.transactions AS t
  JOIN content.content_images AS ci ON ci.id = (t.additional_data::jsonb ->> 'image_id')::uuid
WHERE
  t.additional_data::jsonb ? 'image_id'
GROUP BY
  interaction_date,
  ci.rating;

-- User's active tariff plans
SELECT
  tp.name,
  COUNT(*) as users
FROM
  content.user_plans as up
  JOIN content.tariff_plans AS tp ON up.tariff_plan_id = tp.id
WHERE
  up.expired_at > NOW() AT TIME ZONE 'UTC'
  OR up.expired_at IS NULL
GROUP BY
  tp.name
ORDER BY
  users DESC;

-- User's active tariff plans only not archived
SELECT
  tp.name,
  COUNT(*) as users
FROM
  content.user_plans as up
  JOIN content.tariff_plans AS tp ON up.tariff_plan_id = tp.id
WHERE
  (
    up.expired_at > NOW() AT TIME ZONE 'UTC'
    OR up.expired_at IS NULL
  )
  AND tp.is_archived = FALSE
GROUP BY
  tp.name
ORDER BY
  users DESC;

-- User's expired tariff plans
SELECT
  tp.name,
  COUNT(*) as users
FROM
  content.user_plans as up
  JOIN content.tariff_plans AS tp ON up.tariff_plan_id = tp.id
WHERE
  up.expired_at < NOW() AT TIME ZONE 'UTC'
GROUP BY
  tp.name
ORDER BY
  users DESC;

-- Most popular published characters 'characters/spent tokens'
SELECT
  c.id as c_id,
  c.name as c_name,
  SUM(t.amount) as spent_tokens
FROM
  content.transactions as t
  JOIN content.content_characters as c ON (t.additional_data::jsonb ->> 'char_id')::int = c.id
WHERE
  t.balance_id_from = 50805419
  AND c.status = 'published'
GROUP BY
  c_id,
  c_name
ORDER BY
  spent_tokens DESC;

-- Top users by spending tokens
SELECT
  t.user_id as user_id,
  u.email as user_email,
  SUM(amount) as spent_tokens
FROM
  content.transactions as t
JOIN auth.users as u ON user_id = u.id
WHERE
  t.balance_id_from = 50805419
  AND t.additional_data::jsonb ? 'char_id'
GROUP BY
  user_id, user_email
ORDER BY
  spent_tokens DESC;

-- Top users by spending eur
SELECT
  t.user_id as user_id,
  u.email as user_email,
  SUM(amount) as spent_eur
FROM
  content.transactions as t
JOIN auth.users as u ON user_id = u.id
WHERE
  t.balance_id_from = '981206493'
GROUP BY
  user_id, user_email
ORDER BY
  spent_eur DESC;

-- The dynamics of communication with different characters? (Number of messages by character by day)
SELECT
  c.id as c_id,
  c.name as c_name,
  DATE (t.created_at) as interaction_date,
  COUNT(*) as interactions_times
FROM
  content.transactions as t
  JOIN content.content_characters as c ON (t.additional_data::jsonb ->> 'char_id')::int = c.id
WHERE
  t.balance_id_from = 50805419
  AND c.status = 'published'
GROUP BY
  c_id,
  c_name,
  interaction_date
ORDER BY
  interaction_date,
  c_name DESC;
