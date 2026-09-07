from setuptools import setup, find_packages

setup(
    name="saeka",
    version="1.8.1",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "saeka": ["setup.sh"],
    },
    entry_points={
        "console_scripts": [
            "saeka=saeka.deploy:main",
        ],
    },
)
