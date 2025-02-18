# Project-IYAL

CSE Final Year Research and Development Project

## Table of Contents

[Steps to start the development](#steps-to-start-the-development)  
[.env file](#env-file)
[FastAPI](#fastapi)
[Streamlit](#streamlit)
[Usage for each functions](#usage-for-function)
[Notes on Translation and Transliteration](#notes-on-translation-and-transliteration)

## Steps to start the development

1. Clone the repository
2. Create and activate a virtual environment

```bash
python3 -m venv .venv
# or
python -m venv .venv

.venv\Scripts\activate
```

3. Install the requirements

```bash
pip install -r requirements.txt
```

4. Create a branch from development branch

```bash
git checkout development
git pull origin development
git checkout -b <name of the dev>/dev/<feature>
```

## .env file

1. Create a `.env` file in the root directory
2. Add the following environment variables

```env
BASE_API_URL="http://127.0.0.1:8000"
```

## FastAPI

1. Run the FastAPI server

```bash
# you may need to,
pip install "fastapi[standard]"

fastapi dev .\server\server.py

# The default port is 8000
# if you want to specify the port
fastapi dev .\server\server.py --port 8000
```

## Streamlit

1. Run the Streamlit server

```bash
streamlit run .\ui\main.py

# The default port is 8501
# if you want to specify the port
streamlit run .\ui\main.py --server.port 8989
```

## installation

```bash
# install the package
pip install https://github.com/Sanujen/Project-IYAL/releases/download/v1.0.0-alpha/iyal_quality_analyzer-1.0-py3-none-any.whl

# Refer the usage for each functions to use the package in your code base.
```

## Usage for each functions

1. Import the required function

```python
from iyal_quality_analyzer import convert_legacy_to_unicode
from iyal_quality_analyzer import classify_unicode
from iyal_quality_analyzer import transliterate
from iyal_quality_analyzer import translate_english_to_tamil
from iyal_quality_analyzer import is_english_word
from iyal_quality_analyzer import Inference
from iyal_quality_analyzer import quality_analyzer
from iyal_quality_analyzer import single_word_quality_analyzer
from iyal_quality_analyzer import multi_sentence_quality_analyzer
from iyal_quality_analyzer import get_encoding_fun
```

2. Usage

```python
# convert_legacy_to_unicode
convert_legacy_to_unicode("mfuk;", "bamini2utf2") # returns "அகரம்"
classify_unicode("mfuk;") # returns "Legacy Font Encoding"
transliterate("akaram") # returns "அகரம்"
translate_english_to_tamil("Hello") # returns "வணக்கம்"
is_english_word("Hello") # returns True

# Inference
inference = Inference()

# quality_analyzer
quality_analyzer(Inference, "Kaalai வணkkam உலகம் cyfk;", "bamini2utf2") # returns "காலை வணக்கம் உலகம் உலகம்"  AND also it will return an array of objects
single_word_quality_analyzer(Inference, "வணkkam", "bamini2utf2") # returns "வணக்கம்" AND also it will return an object
multi_sentence_quality_analyzer(Inference, "Kaalai வணkkam உலகம் cyfk;. இரவு வணkkam உலகம் cyfk;", "bamini2utf2") # returns "காலை வணக்கம் உலகம் உலகம். இரவு வணக்கம் உலகம் உலகம்" AND also it will return an array of  sentence objects
get_encoding_fun("Kaalai வணkkam உலகம் cyfk;.") # Automatically detects the encoding and returns it.
```

##### Notes on Inference

1. The Inference class is used to load the model
2. Make sure you have internet connection before using the Inference class
3. The model can be created with a custom path specified for storing the model. If a custom path is not provided, the model will be saved in the default directory, which is the absolute path of the directory where the `Inference` class is located, appended with /models/{model_version}.

```python
inference = Inference(cache_dir="path/to/model_dir")
```

4. Also you can give custom model name and model version

```python
inference = Inference(model_name="model_name", model_version="model_version")
```

5. The `Inference` class initializes by checking the cache directory for the model. If the model is not found in the cache, it automatically downloads the model from the server.

## Notes on Translation and Transliteration

1. We have use google APIs for translation and transliteration.
2. Transliteration: https://github.com/narVidhai/Google-Transliterate-API/blob/master/Languages.md
   - This is not Google’s official library since Google has deprecated Input Tools API.
3. Translation: https://github.com/ssut/py-googletrans
   - This is an unofficial library using the web API of translate.google.com and also is not associated with Google.
