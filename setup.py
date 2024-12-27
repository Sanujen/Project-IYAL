from setuptools import setup, find_packages

setup(
    name="iyal_quality_analyzer",
    version="0.1",
    description="A library for transforming Tamil text to a normalized unicode form.",
    author="Sanujen Premkumar, Sathveegan Yogendrarajah, Nisanthan Sivarasa",
    author_email="sanuprem6@gmail.com, sathvee2000@gmail.com, nisanthan.20@cse.mrt.ac.lk",
    packages=find_packages(include=["iyal_quality_analyzer", "iyal_quality_analyzer.*"]),
    install_requires=[
        "fastapi==0.115.6",
        "pydantic==2.10.4",
        "requests==2.32.3",
        "streamlit==1.41.1",
        "python-dotenv==1.0.1",
        "googletrans==3.1.0a0",
        "google-transliteration-api==1.0.3",
        "transformers==4.47.1",
        "torch==2.5.1",
        "nltk==3.9.1",
    ],
)