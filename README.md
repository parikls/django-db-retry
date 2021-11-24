# django-db-retry

## Motivation

Should be used to deal with network errors and deadlocks during execution of queries.
Usually when you develop a project locally with a single user - everything works perfectly. 
But when it comes to the real world - any application can (and definitely will) face network issues. 
Another one case - deadlocks, which I personally see too often in across different projects. The 
only possible solution here to avoid the data-loss is to do a query retry.
This package is using the `backoff` library under the hood 

## Usage

[!] Now this works **ONLY WITH MYSQL**. If someone requires postgres support - please create an issue

Right now there are two possible usages:

- To monkey-patch django methods globally
- Use a decorator

## Monkey-patching:

[!] IMPORTANT: global patching won't handle retries for atomic transactions. `with_query_retry` should be used

... somewhere on the top level of your project ...
```python

from django_db_retry import patch as install_db_retries
install_db_retries()
```

## Decorator usage

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