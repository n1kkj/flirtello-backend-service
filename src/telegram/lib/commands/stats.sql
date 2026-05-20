SELECT 
    qwe.model_id, 
    SUM(qwe.input_tokens) AS input, 
    SUM(qwe.output_tokens) AS output, 
    SUM(qwe.input_tokens) * 0.0000005 AS cost_input, 
    SUM(qwe.output_tokens) * 0.0000015 AS cost_output,
    (SUM(qwe.input_tokens) * 0.0000005) + (SUM(qwe.output_tokens) * 0.0000015) AS total_cost
FROM 
    content.llm_stats AS qwe
WHERE
    qwe.model_id != 'dummy'
GROUP BY 
    qwe.model_id

UNION ALL

SELECT 
    'Total' AS model_id,
    SUM(input) AS input,
    SUM(output) AS output,
    ROUND(SUM(cost_input), 2) AS cost_input,
    ROUND(SUM(cost_output), 2) AS cost_output,
    ROUND(SUM(total_cost), 2) AS total_cost
FROM (
    SELECT 
        qwe.model_id, 
        SUM(qwe.input_tokens) AS input, 
        SUM(qwe.output_tokens) AS output, 
        SUM(qwe.input_tokens) * 0.0000005 AS cost_input, 
        SUM(qwe.output_tokens) * 0.0000015 AS cost_output,
        (SUM(qwe.input_tokens) * 0.0000005) + (SUM(qwe.output_tokens) * 0.0000015) AS total_cost
    FROM 
        content.llm_stats AS qwe
    WHERE
        qwe.model_id != 'dummy'
    GROUP BY 
        qwe.model_id
) AS subquery