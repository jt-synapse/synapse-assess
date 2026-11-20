INSERT INTO inventory (sku, available) VALUES ('DEMO-BOOK', 8), ('DEMO-LAST', 1)
ON CONFLICT (sku) DO NOTHING;
