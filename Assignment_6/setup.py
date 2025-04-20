from setuptools import setup, find_packages

setup(
    name="mcp_agent",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "google-generativeai==0.3.2",
        "pydantic==2.5.2",
        "python-dotenv==1.0.0",
        "requests==2.31.0"
    ]
) 