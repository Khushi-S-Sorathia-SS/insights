-- Seed chart templates into semantic_definitions
-- These templates instruct the AI agent on the exact JSON schema to produce for each chart type.

INSERT INTO semantic_definitions (id, definition_type, name, definition_json, version) VALUES
(gen_random_uuid(), 'chart_template', 'bar', '{"type":"bar","description":"Bar chart for comparing categories","required_fields":{"type":"bar","title":"string - descriptive title","data":"array of objects with category and value keys","xAxis":"string - key name for category axis","yAxis":"string - key name for value axis"},"example":{"type":"bar","title":"Sales by Region","data":[{"region":"North","sales":100},{"region":"South","sales":200}],"xAxis":"region","yAxis":"sales"}}', 1),

(gen_random_uuid(), 'chart_template', 'pie', '{"type":"pie","description":"Pie chart for showing proportions","required_fields":{"type":"pie","title":"string - descriptive title","data":"array of objects with name and value keys","xAxis":"string - key name for label","yAxis":"string - key name for value"},"example":{"type":"pie","title":"Distribution","data":[{"name":"A","value":30},{"name":"B","value":70}],"xAxis":"name","yAxis":"value"}}', 1),

(gen_random_uuid(), 'chart_template', 'line', '{"type":"line","description":"Line chart for trends over time","required_fields":{"type":"line","title":"string - descriptive title","data":"array of objects with x and y keys","xAxis":"string - key for x axis","yAxis":"string - key for y axis"},"example":{"type":"line","title":"Trend","data":[{"month":"Jan","count":10},{"month":"Feb","count":20}],"xAxis":"month","yAxis":"count"}}', 1),

(gen_random_uuid(), 'chart_template', 'area', '{"type":"area","description":"Area chart for cumulative trends","required_fields":{"type":"area","title":"string - descriptive title","data":"array of objects","xAxis":"string - key for x axis","yAxis":"string - key for y axis"},"example":{"type":"area","title":"Growth","data":[{"year":"2020","revenue":100},{"year":"2021","revenue":150}],"xAxis":"year","yAxis":"revenue"}}', 1),

(gen_random_uuid(), 'chart_template', 'scatter', '{"type":"scatter","description":"Scatter plot for correlations","required_fields":{"type":"scatter","title":"string - descriptive title","data":"array of objects with x and y keys","xAxis":"string - key for x axis","yAxis":"string - key for y axis"},"example":{"type":"scatter","title":"Correlation","data":[{"x":5,"y":85000},{"x":3,"y":72000}],"xAxis":"x","yAxis":"y"}}', 1),

(gen_random_uuid(), 'chart_template', 'radar', '{"type":"radar","description":"Radar chart for multi-dimensional comparison","required_fields":{"type":"radar","title":"string - descriptive title","data":"array of objects with dimension and value keys","xAxis":"string - key for dimension","yAxis":"string - key for value"},"example":{"type":"radar","title":"Skill Comparison","data":[{"skill":"Python","score":90},{"skill":"SQL","score":80}],"xAxis":"skill","yAxis":"score"}}', 1)

ON CONFLICT (name) DO NOTHING;
