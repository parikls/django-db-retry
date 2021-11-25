[![PyPI version](https://badge.fury.io/py/django-db-retry.svg)](https://badge.fury.io/py/django-db-retry) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-db-retry.svg)
![GitHub stars](https://img.shields.io/github/stars/parikls/django-db-retry.svg) ![PyPI - Downloads](https://img.shields.io/pypi/dm/django-db-retry.svg) ![GitHub issues](https://img.shields.io/github/issues/parikls/django-db-retry.svg)

## Description

Django database retries. Main motivation for using this - to deal with network/db issues to avoid data-loss.

Usually when you develop a project locally with a single user - everything works perfectly. Local networks are super-stable, and simultaneous users don't bother you.
When it comes to the real world - your application can (and definitely will) face network issues.
Second case - deadlocks, which I personally see too often across different projects.
And the only possible solution here to avoid the data-loss - to do a query retry.

**IMPORTANT:** Right now this works **ONLY WITH MYSQL**. If someone requires postgres/other dbs support - please create an issue

## Usage

Install: `pip install django-db-retry`

Choose your flow (or use both):

- Monkey-patch django internal methods (**IMPORTANT:** global patching won't handle retries for atomic transactions. `with_query_retry` decorator should be used instead)
- Use explicit decorator

## Monkey-patch:


Add next code somewhere on the top level of your project
```python

from django_db_retry import install as install_db_retries
install_db_retries()
```

That's it =)
All the needed underlying django methods will be wrapped with the retry decorator and 
will do execution retry if your app will face a network issue or deadlock 

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
 
Configuring own value of retries 
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
- Add possibility to install the package using django `INSTALLED_APPS` settings