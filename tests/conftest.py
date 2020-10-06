import os
import os.path
from uuid import uuid4
from decimal import Decimal

import pytest

from server.app import Application
from server.handlers import DBHandler
from server.utils import load_conf


@pytest.fixture
def cli(loop, aiohttp_client):
    conf = load_conf(os.path.join(os.getcwd(), 'config.yml'))
    app = Application(conf).webapp
    return loop.run_until_complete(aiohttp_client(app))


@pytest.fixture(scope="function")
def account_factory(loop):
    conf = load_conf(os.path.join(os.getcwd(), 'config.yml'))
    db_handler = DBHandler(conf)

    account_ids = []

    async def _account_factory(email=None, initial_balance=None):

        if not email:
            email = f'test_account_{str(uuid4())}@test.com'

        account_data = await db_handler.create_account(email, initial_balance)
        account_ids.append(account_data['id'])
        return account_data

    yield _account_factory

    async def _drop_all_accounts():
        for account_id in account_ids:
            await db_handler.drop_account(account_id)

    loop.run_until_complete(_drop_all_accounts())


def decimal_to_str(d):
    if not isinstance(d, Decimal):
        d = Decimal(d)
    return str(d.quantize(Decimal('.00')))
