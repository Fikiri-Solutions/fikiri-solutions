"""
Fikiri Replit Integration Package
Setup script for pip installation
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fikiri-replit",
    version="1.0.0",
    author="Fikiri Solutions",
    author_email="support@fikirisolutions.com",
    description="Fikiri integration package for Replit projects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fikirisolutions/fikiri-replit",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "flask": ["flask>=2.0.0"],
        "fastapi": ["fastapi>=0.68.0", "uvicorn>=0.15.0", "email-validator>=2.0.0"],
    },
)
