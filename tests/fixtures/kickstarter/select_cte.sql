WITH backings_per_category AS (SELECT category_id, deadline FROM app.backings), backers AS (SELECT backer_id, COUNT(id) AS projects_backed FROM app.backings GROUP BY backer_id) SELECT * FROM backers
