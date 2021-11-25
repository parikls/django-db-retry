import logging
import sys
from functools import wraps
from typing import Callable

import backoff
import django.db.backends.utils
from MySQLdb import (
    OperationalError as MySQLOperationalError,
    DatabaseError as MySQLDatabaseError
)
from backoff import random_jitter
from django.db import (
    OperationalError as DjangoOperationalError,
    DatabaseError as DjangoDatabaseError
)
from django.db import connection
from django.db.backends.mysql.base import DatabaseWrapper

__all__ = ('install', 'uninstall', 'with_query_retry', 'QueryRetry')

logger = logging.getLogger('django-db-retry')

DEFAULT_MAX_TRIES = 5

MYSQL_RETRY_PATTERNS = {
    '1040',  # Too many connections
    '1205',  # Lock wait timeout exceeded; try restarting transaction
    '1213',  # Deadlock found when trying to get lock; try restarting transaction
    '2006',  # MySQL server has gone away
    '2013',  # Lost connection to MySQL server during query
    'deadlock detected'  # other deadlocks
}

# keep a reference to an original django database methods
original_ensure_connection = DatabaseWrapper.ensure_connection
original_execute_with_wrappers = django.db.backends.utils.CursorWrapper._execute_with_wrappers  # noqa


class DBRetry(Exception):
    """
    Conditional exception. By raising this one we initiate the execution retry.
    Additionally, keeps a reference to an original exception raised
    """
    def __init__(self, orig: Exception):
        self.orig = orig


def on_back_off(details):
    """ Log retry attempt on back-off """
    wait, tries, target = details['wait'], details['tries'], details['target']
    logger.debug(f'django-db-retry: Going to call {target} in {wait} seconds after {tries} tries')


def on_give_up(*_):
    """ No luck in retry - re-raise originally raised exception """
    _, exc_raised, _ = sys.exc_info()
    exc_raised: DBRetry
    raise exc_raised.orig


def configure_retry_rule(max_tries: int) -> Callable:
    return backoff.on_exception(
        wait_gen=backoff.expo,  # exponential wait
        jitter=random_jitter,
        exception=DBRetry,
        max_tries=max_tries,
        on_backoff=(on_back_off,),  # back-off callback
        on_giveup=(on_give_up,)  # give-up callback
    )


def install(max_tries: int = DEFAULT_MAX_TRIES):
    """
    Main entry-point for monkey-patching of django db-related methods.
    We do patch two of them:
    - `ensure_connection` is being used to connect to a DB when connection was not established
      previously. Therefore, it can fail if DB is not accessible at that moment.
    - `_execute_with_wrappers` is being called by all django ORM methods, e.g. all CRUD ops
      including `bulk` ones. Since connection can be dropped exactly during the execution -
      we also patch this one
    """
    retry_rule = configure_retry_rule(max_tries=max_tries)
    # actual monkey-patch
    DatabaseWrapper.ensure_connection = retry_rule(ensure_connection)
    django.db.backends.utils.CursorWrapper._execute_with_wrappers = retry_rule(
        execute_with_wrappers
    )


def uninstall():
    """ Replace patched methods back to original ones """
    DatabaseWrapper.ensure_connection = original_ensure_connection
    django.db.backends.utils.CursorWrapper._execute_with_wrappers = original_execute_with_wrappers


def ensure_connection(self: DatabaseWrapper):
    """
    For `ensure_connection` method we need to only check if retry pattern
    exists in the raised exception. If it's true - we do a retry
    """
    try:
        return original_ensure_connection(self)
    except (DjangoOperationalError, MySQLOperationalError) as exc:
        ensure_retryable(db_wrapper=self, exc=exc)
        raise DBRetry(orig=exc)


def execute_with_wrappers(self: django.db.backends.utils.CursorWrapper, *args, **kwargs):
    """
    For `_execute_with_wrappers` call we have several possible cases:
    - database becomes not accessible. in this case we need to re-establish the connection
    - deadlocks, etc. we need to do a retry with the interval
    """
    try:
        return original_execute_with_wrappers(self, *args, **kwargs)
    except (DjangoOperationalError, MySQLOperationalError) as exc:
        ensure_retryable(db_wrapper=self.db, exc=exc)
        retry_error = DBRetry(orig=exc)

        if not connection.connection:
            # connection was lost during the execution - need to reconnect
            logger.debug('django-db-retry: connection lost. reconnecting')
            try:
                connection.connect()
            except (MySQLDatabaseError, DjangoDatabaseError):
                raise retry_error  # db is still not accessible - let's wait and retry

        # we have a connection object - let's ping a db to ensure that connection is alive
        try:
            logger.debug('django-db-retry: db ping')
            connection.connection.ping()
        except (MySQLDatabaseError, DjangoDatabaseError):
            logger.debug('django-db-retry: db ping failed')
            # connection died or was closed by a previous attempt - need to re-connect in this case
            try:
                connection.close()
                connection.connect()
            except (MySQLDatabaseError, DjangoDatabaseError):
                logger.debug('django-db-retry: cant connect to a database')
                raise retry_error  # db is still not available, let's retry

        logger.debug('django-db-retry: db ping succeed')
        # db is accessible, and we have a connection object -
        # let's spawn a new cursor and update a reference
        self.cursor = connection.cursor()
        raise retry_error


def ensure_retryable(db_wrapper: DatabaseWrapper, exc: Exception):
    """
    Ensures that query is retryable based on provided exception and the
    current state of database wrapper (e.g. is this atomic tx or no).
    If it's not - we raise an original exception
    """
    if not any(retry_pattern in str(exc) for retry_pattern in MYSQL_RETRY_PATTERNS):
        logger.debug('django-db-retry: unable to retry. retryable pattern was not found')
        raise exc

    if db_wrapper.in_atomic_block is True:
        # we can't blindly retry a transaction which was in atomic block
        # because we don't know what objects were already affected. Also
        # support of nested atomic transactions will bring much more complexity.
        # Retrying of such blocks should be handled on a top-level with the
        # @with_query_retry decorator. Maybe this will be handled in a future
        logger.debug('django-db-retry: unable to retry atomic transaction')
        raise exc


class QueryRetry:
    """ Decorator for query retries. RN should be used for wrapping atomic transactions """
    def __init__(self, max_tries: int = DEFAULT_MAX_TRIES):
        self.retry_rule = configure_retry_rule(max_tries)

    def __call__(self, func):
        @self.retry_rule
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (DjangoOperationalError, MySQLOperationalError) as exc:
                if any(retry_pattern in str(exc) for retry_pattern in MYSQL_RETRY_PATTERNS):
                    raise DBRetry(orig=exc)
                raise exc

        return wrapper


with_query_retry = QueryRetry()  # alias for default behaviour with 5 reties
