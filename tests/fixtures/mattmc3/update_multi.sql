UPDATE products SET list_price = list_price * 1.05, modified_date = now() WHERE sell_end_date IS NULL AND sell_start_date IS NOT NULL
