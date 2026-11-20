"""Readiness probes for trusted control-plane dependencies."""

import os
from dataclasses import dataclass

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError


@dataclass
class Dependencies:
    database: Engine
    redis: Redis

    @classmethod
    def from_environment(cls) -> "Dependencies":
        return cls(
            create_engine(
                os.environ["DATABASE_URL"],
                pool_pre_ping=True,
                pool_timeout=2,
                connect_args={"connect_timeout": 2, "options": "-c statement_timeout=2000"},
            ),
            Redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=2, socket_timeout=2),
        )

    def ready(self) -> bool:
        try:
            with self.database.connect() as connection:
                # Reading the first platform table also checks that migrations ran.
                connection.execute(text("SELECT 1 FROM assessment_versions LIMIT 0"))
            return bool(self.redis.ping())
        except (SQLAlchemyError, RedisError):
            return False

    def close(self) -> None:
        self.redis.close()
        self.database.dispose()
