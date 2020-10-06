class ApiException(Exception):
    def __init__(self, extra_info=None):
        self.extra_info = extra_info


class DuplicateAccountEmail(ApiException):
    pass


class AccountNotFound(ApiException):
    pass


class AccountBalanceExceededMaximum(ApiException):
    pass


class AccountNotEnoughtMoney(ApiException):
    pass


class TransactionNotFound(ApiException):
    pass
