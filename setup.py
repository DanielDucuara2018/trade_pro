from setuptools import find_packages, setup

VERSION = "0.1"

INSTALL_REQUIRES = [
    "aio-pika==9.1.2",
    "apischema==0.18.0",
    "asyncio==3.4.3",
    "fastapi[all]==0.92.0",
    "matplotlib==3.7.1",
    "numpy==1.24.2",
    "orjson==3.9.1",
    "psycopg2==2.9.1",
    "python-binance==1.0.16",
    "python-telegram-bot==20.0a2",
    "PyYAML==6.0",
    "SQLAlchemy==1.4.37",
    "TA-Lib==0.4.26",
]

setup(
    name="trade-pro",
    version=VERSION,
    python_requires=">=3.9.0",
    packages=find_packages(exclude=["tests"]),
    author="Daniel Ducuara",
    author_email="daniel14015@gmail.com",
    description="Launch trading proccesses",
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "cli = trade_pro.main:console",
            "trade-pro = trade_pro.main:main",
            "telegram = trade_pro.telegram.runner:run",
            "strategy = trade_pro.strategy.runner:strategy",
            "back-testing = trade_pro.strategy.runner:back_testing",
        ]
    },
    install_requires=INSTALL_REQUIRES,
    extras_require={
        "dev": [
            "alembic==1.9.4",
            "bandit==1.7.0",
            "mypy==0.931",
            "pre-commit==3.1.0",
            "pylint==2.7.0",
            "black==22.10.0",
            "isort==5.10.1",
            "beautysh==6.2.1",
            "autoflake==1.7.7",
        ],
        "test": [
            "pytest==6.2.4",
            "pytest-mock==3.6.1",
            "pytest-cov==2.12.1",
            "pytest-asyncio==0.15.1",
        ],
    },
)
