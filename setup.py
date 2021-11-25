import pathlib

from setuptools import setup

here = pathlib.Path(__file__).parent
readme_path = here / "README.md"
requirements_path = here / "requirements.txt"


with readme_path.open() as f:
    README = f.read()

with requirements_path.open() as f:
    requirements = [line for line in f.readlines()]


setup(
    name='django-db-retry',
    version='0.1.2',
    description='Adds support for database query retries',
    long_description=README,
    long_description_content_type='text/markdown',
    author='Dmytro Smyk',
    author_email='porovozls@gmail.com',
    url='https://github.com/parikls/django-db-retry',
    packages=["django_db_retry"],
    classifiers=[
        "Operating System :: OS Independent",
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    install_requires=requirements,
    python_requires='>=3.5.3'
)