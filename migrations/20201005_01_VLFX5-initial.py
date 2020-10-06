"""
initial
"""

from yoyo import step

__depends__ = {}

steps = [
    step("""
        CREATE TABLE accounts (
            id BIGSERIAL NOT NULL PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            balance NUMERIC(8, 2) NOT NULL DEFAULT 0,
            ctime TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT timezone('utc', now())
        );
        CREATE TABLE transactions (
            id BIGSERIAL NOT NULL PRIMARY KEY,
            source_account_id BIGINT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
            target_account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
            amount NUMERIC(8, 2),
            ctime TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT timezone('utc', now())
        );
    """)
]
