from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.database import initialize_database


def test_initialize_database_adds_refresh_token_column_to_legacy_databases(tmp_path: Path) -> None:
    legacy_engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE access_tokens ("
                "token_hash VARCHAR(64) PRIMARY KEY, "
                "user_id VARCHAR(50), "
                "expires_at BIGINT NOT NULL, "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )
        )

    initialize_database(legacy_engine)

    columns = {column["name"] for column in inspect(legacy_engine).get_columns("access_tokens")}
    assert "refresh_token_hash" in columns

    # 迁移后，签发令牌对所需的含新列 INSERT 不再报错
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO access_tokens (token_hash, user_id, expires_at, refresh_token_hash) "
                "VALUES ('hash', 'user', 1, 'refresh-hash')"
            )
        )
    legacy_engine.dispose()
