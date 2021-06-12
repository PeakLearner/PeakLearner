from setuptools import setup

# List of dependencies installed via `pip install -e .`
# by virtue of the Setuptools `install_requires` value below.
requires = [
    'pyramid',
    'pyramid_jinja2',
    'pyramid_google_login',
    'pyramid_openapi3',
    'uwsgi',
]

# List of dependencies installed via `pip install -e ".[dev]"`
# by virtue of the Setuptools `extras_require` value in the Python
# dictionary below.
dev_requires = [
    'pytest',
    'pytest_cov',
    'webtest',
    'selenium',
]

setup(
    name='PeakLearner',
    version='2.0.0',
    install_requires=requires,
    extras_require={
        'dev': dev_requires,
    },
    entry_points={
        'paste.app_factory': [
            'main = PeakLearner:main'
        ],
    },
)