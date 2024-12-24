from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from apps.quality_analyzer import quality_analyzer
from apps.utils.legacy_converter.legacy_converter import convert_legacy_to_unicode

app = FastAPI()

# Define the Pydantic model for the input format
class InputRequest(BaseModel):
    input_text: str

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
        # Use the quality_analyzer function to process the input text
        outputText, result = quality_analyzer(request.input_text, request.encoding)
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
        # Use the quality_analyzer function to process the input text
        outputText, result = convert_legacy_to_unicode(request.input_text, request.encoding)
        return {"output": outputText, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")
