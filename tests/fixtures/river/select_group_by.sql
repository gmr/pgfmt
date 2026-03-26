SELECT f.species_name, AVG(f.height) AS average_height FROM flora AS f WHERE f.species_name = 'Banksia' OR f.species_name = 'Sheoak' GROUP BY f.species_name, f.observation_date
