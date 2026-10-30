from setuptools import setup, find_packages

setup(
    name="iyal_text_normalizer",
    version="2.0.0",
    description="A library and monolithic web service for transforming Tamil, Tanglish, and Legacy Font text into normalized Standard Tamil Unicode.",
    author="Sanujen Premkumar, Sathveegan Yogendrarajah, Nisanthan Sivarasa",
    author_email="sanuprem6@gmail.com, sathvee2000@gmail.com, nisanthan.20@cse.mrt.ac.lk",
    packages=find_packages(include=["iyal_quality_analyzer", "iyal_quality_analyzer.*"]),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.32.0",
        "transformers>=4.47.0",
        "torch>=2.5.0",
        "sentencepiece>=0.2.0",
        "nltk>=3.9.1",
    ],
)
