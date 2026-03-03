"""Setup script for Chat P1.

Note: This project uses Poetry for dependency management.
This setup.py is provided for compatibility with tools that require it.

For development, use Poetry:
    poetry install
    poetry run pytest
"""

from setuptools import find_packages, setup

setup(
    name="chatp1",
    version="0.1.0",
    author="Prateek Mulye",
    description="AI-powered Formula 1 expert chatbot",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    # Dependencies are managed by Poetry - see pyproject.toml
    install_requires=[],
)
