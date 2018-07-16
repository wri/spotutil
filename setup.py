import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gfw-create-spot-worker",
    version="0.0.1",
    author="Charlie Hofmann",
    author_email="chofmann@wri.org",
    description="Create an AWS Spot request. View active Spot instances",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wri/gfw-create-spot-worker",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)