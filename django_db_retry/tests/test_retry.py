from unittest.mock import patch

import pytest
from django.db import OperationalError

from django_db_retry import with_query_retry, QueryRetry, on_back_off, on_give_up


RETRYABLE_ERRORS = {
    OperationalError('1040: Too many connections'),
    OperationalError('1205: Lock wait timeout exceeded; try restarting transaction'),
    OperationalError('1213: Deadlock found when trying to get lock; try restarting transaction'),
    OperationalError('2006: MySQL server has gone away'),
    OperationalError('2013: Lost connection to MySQL server during query'),
    OperationalError('other type of deadlock detected'),
}

NON_RETRYABLE_ERRORS = {
    OperationalError('-1 other error'),
    RuntimeError('1040: Too many connections'),
    Exception('completely random exception')
}


def test_retry_fail():
    max_tries = 2
    for future_error in RETRYABLE_ERRORS:

        with patch('django_db_retry.on_back_off', wraps=on_back_off) as mock_back_off, \
             patch('django_db_retry.on_give_up', wraps=on_give_up) as mock_give_up, \
             patch('django_db_retry.random_jitter', return_value=0):
            my_query_retry = QueryRetry(max_tries=max_tries)

            @my_query_retry
            def raising_func():
                # imagine that database doesn't go up and always raises an exception
                raise future_error

            with pytest.raises(OperationalError) as exc:
                raising_func()

            assert exc.value is future_error
            assert mock_back_off.call_count == max_tries - 1
            assert mock_give_up.call_count == 1


def test_retry_succeed():

    for future_error in RETRYABLE_ERRORS:

        will_raise = True

        @with_query_retry
        def conditional_raising_func():
            nonlocal will_raise
            if will_raise:
                will_raise = False
                raise future_error

            return True

        result = conditional_raising_func()
        assert result is True


def test_retry_doesnt_work_with_non_eligible_error():
    for non_retryable_error in NON_RETRYABLE_ERRORS:
        with patch('django_db_retry.on_back_off', wraps=on_back_off) as mock_back_off, \
             patch('django_db_retry.on_give_up', wraps=on_give_up) as mock_give_up, \
             patch('django_db_retry.random_jitter', return_value=0):

            @with_query_retry
            def raising_func():
                raise non_retryable_error

            with pytest.raises(non_retryable_error.__class__) as exc:
                raising_func()

            assert exc.value is non_retryable_error
            assert mock_back_off.call_count == 0
            assert mock_give_up.call_count == 0