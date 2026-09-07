from setuptools import setup, find_packages

setup(
    name="saeka",
    version="1.7.0",
    description="Saeka GCP Cloud Run Deployer",
    author="Saeka Tojirp",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "saeka=saeka.deploy:main",
        ],
    },
)
