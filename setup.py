from setuptools import setup, find_packages

setup(
    name="crypto_analyzer",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'PyQt6',
        'plotly',
        'pandas',
        'numpy',
        'psycopg2-binary',
        'python-dotenv',
        'kucoin-python',
        'setuptools',
        'PyQtWebEngine'
    ]
) 