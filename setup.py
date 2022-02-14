from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="spotutil",
    version="0.1.0",
    author="Charlie Hofmann, Thomas Maschler, David Gibbs",
    author_email="david.gibbs@wri.org",
    description="Create an AWS ec2 spot request. View active spot instances. Delete active spot instances",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wri/spotutil",
    packages=find_packages(),
    install_requires=[
        "click",
        "botocore",
        "boto3",
        "prettytable",
        "urllib3<1.27,>=1.25.5",
        "pytz",
        "retrying",
        "requests",
        "future",
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
