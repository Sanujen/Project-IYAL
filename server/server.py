"""
TODO:
    1. API for find encoding automatically by given text. should return the font style. This function should be available in quality_analyzer.py

"""

import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from iyal_quality_analyzer.quality_analyzer import quality_analyzer
from iyal_quality_analyzer.utils.legacy_converter.legacy_converter import convert_legacy_to_unicode
from iyal_quality_analyzer.inference_base.inference import Inference

def enforce_dict(req, custom_type):
    print("Request enforced as dictionary")
    if isinstance(req, dict):
        print("Request is already a dictionary: %s"%req)
        return req
    elif isinstance(req, str):
        print("Request is a string")
        req = json.loads(req)
    elif isinstance(req, custom_type):
        print("Request is a custom type")
        req = req.model_dump()
    else:
        raise TypeError(f"Support not added for enforcing type to be a dictionary: {type(req)}")
    print("Request: %s"%req)
    return req

app = FastAPI()

# Define the Pydantic model for the input format
class InputRequest(BaseModel):
    input_text: str

    model_config = ConfigDict(extra='allow')

# Define the Pydantic model for the input format
class InputRequest(BaseModel):
    input_text: str
    encoding: str = None

    model_config = ConfigDict(extra='allow')

@app.post("/analyze/")
async def analyze_input(request: InputRequest):
    """
    Analyzes the input text and returns tuple containing the normalized Tamil Unicode text and an array of dictionaries containing the classification results.
    
    Args:
        request (InputRequest): The input request containing the text to analyze.

    Returns:
        dict: A dictionary containing the normalized Tamil Unicode text and the classification results.

    """
    try:
        print("Request: %s"%request)
        request_dict = enforce_dict(request, InputRequest)
        # Use the quality_analyzer function to process the input text
        encoding = request_dict.get('encoding', None)
        inference_model = Inference()
        outputText, result = quality_analyzer(inference_model, request_dict['input_text'], encoding)
        print("outputText: ", outputText)
        print("result: ", result)
        return {"output": outputText, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")

# api for legacy to unicode
@app.post("/legacy2unicode/")
async def legacy2unicode(request: InputRequest):
    """
    Converts legacy Tamil text to Unicode.

    Args:
        request (InputRequest): The input request containing the legacy Tamil text to convert.

    Returns:
        dict: A dictionary containing the converted Unicode text.

    """
    try:
        print("request: ", request)
        request_dict = enforce_dict(request, InputRequest)
        # Use the convert_legacy_to_unicode function to process the input text
        encoding = request_dict.get('encoding', None)
        outputText = convert_legacy_to_unicode(request_dict['input_text'], encoding)
        print("outputText: ", outputText)
        return {"output": outputText}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")
