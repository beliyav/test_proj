import json
import datetime
from decimal import Decimal

import yaml
from cerberus import Validator, TypeDefinition


def load_conf(path):
    with open(path) as file:
        conf = yaml.safe_load(file)
    return conf


class CustomValidator(Validator):
    # добавляем кастомный тип
    # https://docs.python-cerberus.org/en/stable/customize.html#custom-data-types
    types_mapping = Validator.types_mapping.copy()
    types_mapping['decimal'] = TypeDefinition('decimal', (Decimal,), ())


def validate(schema):
    def wrapper(fn):
        async def deco(_self, request):
            # для исключение рекурсивного импорта
            from server.handlers import AppHandlers

            if request.method == 'GET':
                data = dict(request.query)
                data.update(request.match_info)
            else:
                try:
                    data = await request.json()
                except json.decoder.JSONDecodeError:
                    data = {}

            v = CustomValidator(schema)
            is_valid = v.validate(data)

            if is_valid:
                result = await fn(_self, request, v.document)
                return result
            else:
                return AppHandlers.error_response(v.errors, status=422)
        return deco
    return wrapper


def json_defaults(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    else:
        return str(obj)


def custom_json_dumps(*args, **kwargs):
    kwargs['default'] = json_defaults
    return json.dumps(*args, **kwargs)
