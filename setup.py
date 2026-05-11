from setuptools import setup, find_packages

setup(
    name="epc_modules",
    version="1.0.0",
    description="Comprehensive EPC Module for ERPNext",
    author="EPC Development Team",
    author_email="dev@organization.com",
    packages=find_packages(exclude=["epc_modules.tests.*"]),
    python_requires=">=3.10",
)