from setuptools import setup, find_packages

setup(
    name="moroccan-legal-rag",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # "sentence-transformers>=2.2.0",
        "psycopg2-binary>=2.9.0",
        "numpy>=1.24.0",
        "requests>=2.28.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "tui": ["textual>=8.0.0"],
    },
)
