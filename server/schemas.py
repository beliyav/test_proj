
from decimal import Decimal

from server.constants import ValidationErrors


def gt_zero(field, value, error):
    if (isinstance(value, Decimal) and value.quantize(Decimal('.00')) <= 0) or value <= 0:
        error(field, ValidationErrors.MUST_BE_GREATER_0)


CREATE_ACCOUNT = {
    'email': dict(type='string', required=True, regex=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
}

ACCOUNT_PAYMENT = {
    'amount': dict(type='decimal', required=True, coerce=Decimal, check_with=gt_zero)
}

CREATE_TRANSACTION = {
    'source_account_id': dict(type='integer', required=True),
    'target_account_id': dict(type='integer', required=True),
    'amount': dict(type='decimal', required=True, coerce=Decimal, check_with=gt_zero)
}

GET_OBJECT_BY_ID = {
    'id': dict(type='integer', coerce=int, check_with=gt_zero)
}
