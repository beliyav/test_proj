from aiohttp import web
from loguru import logger

from server.handlers import AppHandlers


class Application:
    def __init__(self, config):
        self.config = config
        self.webapp = self._create_webapp(config)

    @staticmethod
    @web.middleware
    async def error_middleware(request, handler):
        # что бы не показывать пользователю реальных ошибок, если они случаются
        try:
            response = await handler(request)
        except Exception as exc:
            if isinstance(exc, web.HTTPException):
                message, status = exc.reason,  exc.status_code
            else:
                logger.exception('Uncatched exception: ')
                message, status = 'server error', 500

            response = AppHandlers.error_response(message, status=status)

        return response

    def _create_webapp(self, config):
        webapp = web.Application(middlewares=[self.error_middleware])

        _handlers = AppHandlers(config)
        webapp.add_routes([
            web.post('/account', _handlers.create_account),
            web.get('/account/{id}', _handlers.get_account),
            web.post('/account/{id}/payment', _handlers.account_payment),
            web.post('/transaction', _handlers.create_transaction),
            web.get('/transaction/{id}', _handlers.get_transaction)
        ])
        return webapp

    def run(self):
        logger.info('Starting application')
        web.run_app(
            self.webapp,
            host=self.config['http']['host'],
            port=self.config['http']['port']
        )
