# OrderFlow

OrderFlow accepts inventory reservations. Customers report that more reservations sometimes succeed than there is stock available.

During the 35-minute independent stage, investigate the reservation path, preserve the existing API, and fix concurrent stock allocation and failure recovery. Add a regression test and explain what evidence identified the cause. You can give your explanation in writing or through the assessment's consent-based microphone option.

The assessment runtime supplies Python 3.12+, dependencies, a dedicated PostgreSQL database, and `ORDERFLOW_DATABASE_URL`. To apply the migrations and seed data, run `python -m orderflow.setup`. Run the service with `python -m uvicorn orderflow.main:app` and the visible tests with `python -m pytest tests`. The starter includes a book with SKU `DEMO-BOOK` and a single-unit item with SKU `DEMO-LAST`.

See [the service contract](docs/api_contract.md) for the request format.
