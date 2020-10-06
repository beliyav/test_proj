import uuid

import pytest

from conftest import decimal_to_str


async def test_create_account_success(cli):
    email = f'test_account_{str(uuid.uuid4())}@test.com'

    resp = await cli.post('/account', json={'email': email})
    assert resp.status == 200

    response = await resp.json()
    assert response['success'] is True
    assert response['data']['email'] == email


async def test_duplicate_email(cli, account_factory):
    email = 'test_account@test.com'

    await account_factory(email)

    resp = await cli.post('/account', json={'email': email})
    assert resp.status == 422

    response = await resp.json()
    assert response['success'] is False
    assert 'email' in response['error']


async def test_account_payment_success(cli, account_factory):
    email = 'test_account@test.com'
    amount = 1
    account_data = await account_factory(email)
    resp = await cli.post(f"/account/{account_data['id']}/payment", json={'amount': amount})

    assert resp.status == 200

    response = await resp.json()
    assert response['success'] is True
    assert response['data']['balance'] == decimal_to_str(amount)


@pytest.mark.parametrize("account_id,http_status", [(0, 404), (-1, 422), ('test', 422)])
async def test_account_payment_not_found(cli, account_id, http_status):
    resp = await cli.post(f"/account/{account_id}/payment", json={'amount': 1})
    assert resp.status == http_status

    response = await resp.json()
    assert response['success'] is False
    assert 'account_id' in response['error']


@pytest.mark.parametrize("amount", [-1, 0, 0.001, 999999999999999999999999])
async def test_account_payment_invalid_amount(cli, account_factory, amount):
    account_data = await account_factory()
    resp = await cli.post(f"/account/{account_data['id']}/payment", json={'amount': amount})
    assert resp.status == 422

    response = await resp.json()
    assert response['success'] is False
    assert 'amount' in response['error']


async def test_account_payment_too_big(cli, account_factory):
    account_data = await account_factory(initial_balance=999999)
    resp = await cli.post(f"/account/{account_data['id']}/payment", json={'amount': 1})
    assert resp.status == 422

    response = await resp.json()
    assert response['success'] is False
    assert 'amount' in response['error']


async def test_get_account_success(cli, account_factory):
    account_data = await account_factory()

    resp = await cli.get(f"/account/{account_data['id']}")
    assert resp.status == 200

    response = await resp.json()
    assert response['success'] is True
    assert response['data']['id'] == account_data['id']


@pytest.mark.parametrize("account_id,http_status", [(0, 422), (-1, 422), ('test', 422), (9999999, 404)])
async def test_get_account_fail(cli, account_factory, account_id, http_status):
    resp = await cli.get(f"/account/{account_id}")
    assert resp.status == http_status

    response = await resp.json()
    assert response['success'] is False
    assert 'id' in response['error']
