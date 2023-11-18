# to install vmon as Python package
from setuptools import find_packages, setup

setup(
    name='vmon',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'anyio',
        'flask[async]',
        'Flask-WTF',
        'Flask-SQLAlchemy',
        'flask-admin',
        'gunicorn',
        'httpcore',
        'httpx',
        'psycopg2',
        'psycopg2-binary',
        'redis',
        'rq',

    ],
)