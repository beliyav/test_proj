import asyncio
from decimal import Decimal

import asyncpg
from aiohttp import web
import asyncpg.exceptions

from server.constants import ValidationErrors
from server.utils import custom_json_dumps, validate
from server.schemas import CREATE_ACCOUNT, ACCOUNT_PAYMENT, CREATE_TRANSACTION, GET_OBJECT_BY_ID
from server.exceptions import (
    DuplicateAccountEmail, AccountNotFound, AccountBalanceExceededMaximum, AccountNotEnoughtMoney, TransactionNotFound
)


class DBHandler:
    # в этом классе собраны методы для работы с базой, тут нет бизнес-логики как таковой

    def __init__(self, config):
        _loop = asyncio.get_event_loop()
        self.db_pool = _loop.run_until_complete(self._create_db_pool(config))

    async def _create_db_pool(self, config):
        return await asyncpg.create_pool(config['database']['dsn'])

    async def create_account(self, email, initial_balance=None):
        if not initial_balance:
            initial_balance = Decimal(0)

        async with self.db_pool.acquire() as conn:
            try:
                account_row = await conn.fetchrow(
                    'INSERT INTO accounts(email, balance) VALUES ($1, $2) RETURNING *',
                    email, initial_balance
                )
            except asyncpg.exceptions.UniqueViolationError:
                raise DuplicateAccountEmail from None

        return dict(account_row)

    async def drop_account(self, account_id):
        # используется только для фабрики акаунтов в тестах
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    'DELETE FROM transactions WHERE source_account_id = $1 OR target_account_id = $1', account_id
                )
                await conn.execute(
                    'DELETE FROM accounts WHERE id = $1', account_id
                )

    async def get_account(self, account_id):
        async with self.db_pool.acquire() as conn:
            account_data = await conn.fetchrow('SELECT * FROM accounts WHERE id = $1', account_id)
            if not account_data:
                raise AccountNotFound
        return dict(account_data)

    async def create_account_payment(self, account_id, amount):
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                try:
                    account_row = await conn.fetchrow(
                        'UPDATE accounts SET balance = balance + $1 WHERE id = $2 RETURNING *',
                        amount, account_id
                    )
                except asyncpg.exceptions.NumericValueOutOfRangeError:
                    raise AccountBalanceExceededMaximum from None

                if not account_row:
                    raise AccountNotFound

                await conn.execute(
                    'INSERT INTO transactions(target_account_id, amount) VALUES ($1, $2)',
                    account_id, amount
                )
        return dict(account_row)

    async def create_transaction(self, source_account_id, target_account_id, amount):
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # ORDER BY нам важен, что бы правильно смапить результаты из базы на переменные
                accounts = await conn.fetch(
                    'SELECT * FROM accounts WHERE id = ANY($1) ORDER BY CASE WHEN id = $2 THEN 1 ELSE 2 END FOR UPDATE',
                    (source_account_id, target_account_id), source_account_id
                )

                if len(accounts) < 2:
                    # если пришло меньше 2 строк, то значит что либо один, либо оба аккаунта не существуют.
                    # определяем какой именно не существует и сохраняем это в Exception
                    exists_account_ids = [a['id'] for a in accounts]
                    _map = {'source_account_id': source_account_id, 'target_account_id': target_account_id}
                    exc_extra_info = [k for k, v in _map.items() if v not in exists_account_ids]
                    raise AccountNotFound(extra_info=exc_extra_info)

                source_account, target_account = accounts

                if source_account['balance'] < amount:
                    raise AccountNotEnoughtMoney

                try:
                    transaction_row = await conn.fetchrow(
                        '''INSERT INTO transactions(source_account_id, target_account_id, amount) VALUES ($1, $2, $3)
                        RETURNING *''',
                        source_account_id, target_account_id, amount
                    )

                    await conn.execute(
                        'UPDATE accounts SET balance = balance + $1 WHERE id = $2', amount, target_account_id
                    )
                except asyncpg.exceptions.NumericValueOutOfRangeError:
                    raise AccountBalanceExceededMaximum from None

                await conn.execute(
                        'UPDATE accounts SET balance = balance - $1 WHERE id = $2', amount, source_account_id
                    )

        return dict(transaction_row)

    async def get_transaction(self, transaction_id):
        async with self.db_pool.acquire() as conn:
            transaction_data = await conn.fetchrow('SELECT * FROM transactions WHERE id = $1', transaction_id)
            if not transaction_data:
                raise TransactionNotFound
        return dict(transaction_data)


class AppHandlers:
    # в этом классе собраны хэндлеры для апи (эндпоинты).

    def __init__(self, config):
        self.db_handler = DBHandler(config)

    @staticmethod
    def success_response(data, status=200):
        return web.json_response(
            {'success': True, 'data': data},
            status=status, dumps=custom_json_dumps
        )

    @staticmethod
    def error_response(error, status=422):
        return web.json_response(
            {'success': False, 'error': error},
            status=status, dumps=custom_json_dumps
        )

    @validate(CREATE_ACCOUNT)
    async def create_account(self, request, data):
        try:
            account_data = await self.db_handler.create_account(
                data['email'], initial_balance=data.get('initial_balance')
            )
        except DuplicateAccountEmail:
            return self.error_response({'email': ValidationErrors.NOT_UNIQUE})

        return self.success_response(account_data)

    @validate(GET_OBJECT_BY_ID)
    async def get_account(self, request, data):
        try:
            return self.success_response(await self.db_handler.get_account(data['id']))
        except AccountNotFound:
            return self.error_response({'id': ValidationErrors.NOT_FOUND}, status=404)

    @validate(ACCOUNT_PAYMENT)
    async def account_payment(self, request, data):
        raw_account_id = request.match_info['id']

        if not raw_account_id.isdigit():
            return self.error_response({'account_id': ValidationErrors.MUST_BE_INT})

        account_id = int(raw_account_id)

        try:
            account_data = await self.db_handler.create_account_payment(account_id, data['amount'])
        except AccountNotFound:
            return self.error_response({'account_id': ValidationErrors.NOT_FOUND}, status=404)
        except AccountBalanceExceededMaximum:
            return self.error_response({'amount': ValidationErrors.TOO_BIG})

        return self.success_response(account_data)

    @validate(CREATE_TRANSACTION)
    async def create_transaction(self, request, data):
        if data['source_account_id'] == data['target_account_id']:
            return self.error_response({'target_account': ValidationErrors.SAME_AS_SOURCE_ACCOUNT})

        try:
            transaction_data = await self.db_handler.create_transaction(
                data['source_account_id'], data['target_account_id'], data['amount']
            )
        except AccountNotFound as exc:
            return self.error_response({field_name: ValidationErrors.NOT_FOUND for field_name in exc.extra_info})
        except AccountNotEnoughtMoney:
            return self.error_response({'source_account_id': ValidationErrors.NOT_ENOUGHT_MONEY})
        except AccountBalanceExceededMaximum:
            return self.error_response({'amount': ValidationErrors.TOO_BIG})

        return self.success_response(transaction_data)

    @validate(GET_OBJECT_BY_ID)
    async def get_transaction(self, request, data):
        try:
            return self.success_response(await self.db_handler.get_transaction(data['id']))
        except TransactionNotFound:
            return self.error_response({'id': ValidationErrors.NOT_FOUND}, status=404)
