# pylint:disable=line-too-long

import setuptools

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

with open("LICENSE", encoding="utf-8") as f:
    license = f.read()  # pylint:disable=redefined-builtin


setuptools.setup(
    name="django_logical_replication",
    version="2.0.2",
    author="Christopher Huber",
    author_email="security@selfdecode.com",
    description="A Django package to sync tables across environments using PostgreSQL logical replication",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/selfdecode/django-logical-replication",
    packages=setuptools.find_packages(exclude=["sample_project"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Django",
        "Framework :: Django :: 5.2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
    ],
    python_requires=">=3.12",
    install_requires=[
        "Django>=5.2",
        "psycopg[binary]>=3.0",
    ],
)
