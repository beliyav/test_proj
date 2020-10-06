import random
from decimal import Decimal

import pytest

from conftest import decimal_to_str

@pytest.mark.parametrize("amount", [0.01, 0.1, 1, 10])
async def test_transaction_success(cli, account_factory, amount):
    initial_source_balance = 10

    source_account = await account_factory(initial_balance=initial_source_balance)
    target_account = await account_factory()

    payload = {
        'source_account_id': source_account['id'],
        'target_account_id': target_account['id'],
        'amount': amount
    }

    resp = await cli.post('/transaction', json=payload)
    assert resp.status == 200

    response = await resp.json()
    assert response['success'] is True
    assert response['data']['source_account_id'] == source_account['id']
    assert response['data']['target_account_id'] == target_account['id']
    assert response['data']['amount'] == decimal_to_str(payload['amount'])

    resp = await cli.get(f"/account/{source_account['id']}")
    response = await resp.json()
    assert response['data']['balance'] == decimal_to_str(Decimal(initial_source_balance) - Decimal(amount))


@pytest.mark.parametrize("amount", [0.001, 0, -1, 9999999999999999999])
async def test_transaction_fail(cli, account_factory, amount):
    initial_source_balance = 10

    source_account = await account_factory(initial_balance=initial_source_balance)
    target_account = await account_factory()

    payload = {
        'source_account_id': source_account['id'],
        'target_account_id': target_account['id'],
        'amount': amount
    }

    resp = await cli.post('/transaction', json=payload)
    assert resp.status == 422


async def test_transaction_overflow(cli, account_factory):
    source_account = await account_factory(initial_balance=1)
    target_account = await account_factory(initial_balance=999999)

    payload = {
        'source_account_id': source_account['id'],
        'target_account_id': target_account['id'],
        'amount': 1
    }

    resp = await cli.post('/transaction', json=payload)
    assert resp.status == 422


async def test_transaction_not_found(cli, account_factory):
    account = await account_factory(initial_balance=1)

    payload = {
        'source_account_id': account['id'],
        'target_account_id': random.randint(1111111, 9999999),
        'amount': 1
    }

    resp = await cli.post('/transaction', json=payload)
    assert resp.status == 422

    payload = {
        'source_account_id': random.randint(1111111, 9999999),
        'target_account_id': account['id'],
        'amount': 1
    }

    resp = await cli.post('/transaction', json=payload)
    assert resp.status == 422

    payload = {
        'source_account_id': random.randint(1111111, 9999999),
        'target_account_id': random.randint(1111111, 9999999),
        'amount': 1
    }

    resp = await cli.post('/transaction', json=payload)
    assert resp.status == 422


async def test_get_transaction_success(cli, account_factory):
    source_account = await account_factory(initial_balance=1)
    target_account = await account_factory()

    payload = {
        'source_account_id': source_account['id'],
        'target_account_id': target_account['id'],
        'amount': 1
    }

    resp = await cli.post('/transaction', json=payload)
    assert resp.status == 200

    response = await resp.json()
    transaction_id = response['data']['id']

    resp = await cli.get(f'/transaction/{transaction_id}')
    assert resp.status == 200
    response = await resp.json()
    assert response['data']['id'] == transaction_id


@pytest.mark.parametrize("transaction_id,http_status", [(0, 422), (-1, 422), ('test', 422), (9999999, 404)])
async def test_get_transaction_fail(cli, account_factory, transaction_id, http_status):
    resp = await cli.get(f"/transaction/{transaction_id}")
    assert resp.status == http_status

    response = await resp.json()
    assert response['success'] is False
    assert 'id' in response['error']
