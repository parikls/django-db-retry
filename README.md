# django-db-retry

## Motivation

Main motivation - to avoid data loss.

Usually when you develop a project locally with a single user - everything works perfectly. Local 
network is super-stable, and simultaneous users doesn't bother you.
When it comes to the real world - your application can (and definitely will) face network issues. 
Second case - deadlocks, which I personally see too often across different projects. 
And the only possible solution here to avoid the data-loss - to do a query retry.

**IMPORTANT:** Now this works **ONLY WITH MYSQL**. If someone requires postgres/other dbs support - please create an issue

## Usage

Install: `pip install django-db-retry`

Choose your flow (or use both):

- Monkey-patch django methods globally
- Use a decorator

## Monkey-patch:

**IMPORTANT:** global patching won't handle retries for atomic transactions. `with_query_retry` should be used

Add next code somewhere on the top level of your project
```python

from django_db_retry import install as install_db_retries
install_db_retries()
```

## Decorator

Can be used on top of any function/view and will do a retry if deadlock/network error will happen.
Default number of retries is 5. This value can be configured by using the `QueryRetry` class (see example 2):

```python
from django_db_retry import with_query_retry
from django.db.transaction import atomic

@with_query_retry
def some_view():
    query_0, query_1 = ...
    with atomic():
        query_0()
        query_1()
    return ...
```

Default number of retries is 5. 
It can be configured by creating your own retry decorator, e.g.
```python
from django_db_retry import QueryRetry
from django.db.transaction import atomic

my_retry_decorator = QueryRetry(max_tries=100)

@my_retry_decorator
def some_view():
    query_0, query_1 = ...
    with atomic():
        query_0()
        query_1()
    return ...
```
# Todo

- Deal with atomic transactions during global patching