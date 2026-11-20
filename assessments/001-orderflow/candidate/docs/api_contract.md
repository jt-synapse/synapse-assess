# Reservations API

`POST /reservations` accepts a JSON object containing a case-sensitive SKU and a positive integer quantity. For example, submit `{"sku":"DEMO-BOOK","quantity":2}`. The SKU consists of 1–64 ASCII letters, digits, underscores or hyphens. Quantities fit a signed PostgreSQL integer. Extra fields are rejected.

A success returns HTTP 201 with the reservation's UUID, SKU and quantity. An unknown SKU returns HTTP 404 and `{"detail":"SKU_NOT_FOUND"}`. Insufficient inventory returns HTTP 409 and `{"detail":"INSUFFICIENT_STOCK"}`. Invalid input returns HTTP 422. Database failures return HTTP 503. A failed request must leave reservations and stock unchanged. Each successful reservation decreases stock by the quantity reserved.

The service uses a separate PostgreSQL connection for each request. The `inventory` and `reservations` tables are established by numbered SQL migrations.
