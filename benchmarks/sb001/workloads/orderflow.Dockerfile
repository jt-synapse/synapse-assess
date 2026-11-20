FROM python:3.12-bookworm@sha256:4209fae09a3e20afd863e528bfddc235da5fd5977983e1996cd54cc9a72e6267 AS python_runtime
FROM postgres:16-bookworm@sha256:ce3efec6bc404f6b15ebf5d9bed6b45a9d4655aea238d7dacc3467ccb05a1175

COPY --from=python_runtime /usr/local/ /usr/local/
COPY --from=python_runtime /usr/bin/git /usr/bin/git
COPY --from=python_runtime /usr/lib/git-core/ /usr/lib/git-core/
COPY --from=python_runtime /usr/share/git-core/templates/ /usr/share/git-core/templates/
RUN useradd --create-home --uid 10001 candidate \
    && install -d -m 0755 /opt/sb001 \
    && install -d -m 0755 -o candidate -g candidate /workspace \
    && install -d -m 0755 -o postgres -g postgres /run/postgresql \
    && printf 'orderflow\n' > /opt/sb001/profile
COPY --chmod=0555 ready.py /opt/sb001/ready
COPY --chmod=0555 postgres_service.py /opt/sb001/postgres-service
ADD --chown=candidate:candidate candidate.tar /workspace/
RUN chown -R candidate:candidate /workspace \
    && python -m pip install --no-cache-dir --require-hashes -r /workspace/requirements.txt \
    && install -m 0444 /workspace/migrations/001_reservations.sql /opt/sb001/schema.sql \
    && install -m 0444 /workspace/seed.sql /opt/sb001/seed.sql \
    && git --version && python -c 'import psycopg, uvicorn, fastapi, httpx' \
    && /usr/lib/postgresql/16/bin/postgres --version
ENV ORDERFLOW_DATABASE_URL="host=/run/postgresql dbname=orderflow user=candidate application_name=orderflow-api" \
    PGDATA=/var/lib/postgresql/data/sb001
WORKDIR /workspace
USER postgres
ENTRYPOINT ["/opt/sb001/postgres-service"]
CMD []
