from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="spotutil",
    version="0.0.2",
    author="Charlie Hofmann, Thomas Maschler",
    author_email="thomas.maschler@wri.org",
    description="Create an AWS Spot request. View active Spot instances",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wri/spotutil",
    packages=["spotutil"],
    install_requires=[
        "click",
        "botocore",
        "boto3",
        "prettytable",
        "urllib3==1.23",
        "pytz",
        "retrying",
        "requests",
    ],
    classifiers=(
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    entry_points="""
        [console_scripts]
        spotutil=spotutil.spotutil:spotutil
        """,
)
