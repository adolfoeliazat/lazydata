import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="lazydata",
    version="1.0.1",
    author="Robert Stojnic",
    author_email="robert.stojnic@gmail.com",
    description="Scalable data dependencies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rstojnic/lazydata",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    scripts=['lazydata/bin/lazydata']
)