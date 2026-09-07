from setuptools import setup, find_packages

setup(
    name="saeka",
    version="1.5.0",  # Bump version for the new release
    description="Saeka GCP Cloud Run Deployer",
    author="Saeka Tojirp",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "pip s=saeka.deploy:main",
        ],
    },
)
