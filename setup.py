from setuptools import setup, find_packages

setup(
    name="ghanageo",
    version="1.0.0",
    description="Comprehensive geographic data for Ghana",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'ghanageo': ['data/*.db'],
    },
    install_requires=[],
    extras_require={
        'api': ['fastapi', 'uvicorn'],
    },
    entry_points={
        "console_scripts": [
            "ghanageo-api=ghanageo.client:serve_api",
        ],
    },
    python_requires=">=3.7",
)
