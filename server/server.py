from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from apps.quality_analyzer import quality_analyzer

app = FastAPI()

# Define the Pydantic model for the input format
class InputRequest(BaseModel):
    input_word: str

    model_config = ConfigDict(extra='allow')

@app.post("/analyze/")
async def analyze_input(request: InputRequest):
    """
    Endpoint to analyze mixed Tamil and English input.

    Args:
        request (InputRequest): Request body containing the input_word.

    Returns:
        str: The normalized Tamil Unicode output.
    """
    try:
        # Use the quality_analyzer function to process the input word
        result = quality_analyzer(request.input_word)
        return {"normalized_input": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")
