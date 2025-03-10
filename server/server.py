import json
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel, ConfigDict
from iyal_quality_analyzer.quality_analyzer import (
    multi_sentence_quality_analyzer,
    get_encoding_fun,
)
from iyal_quality_analyzer.utils.legacy_converter.legacy_converter import (
    convert_legacy_to_unicode,
)
from iyal_quality_analyzer.inference_base.inference import Inference
from iyal_quality_analyzer.inference_base.inference_coll_to_stand import (
    Inference as CollToStandInference,
)


classifier = None
coll_to_stand = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global classifier
    global coll_to_stand
    print("Loading Classifier model...")
    classifier = Inference()
    print("Loading Colloquial to Standard model...")
    coll_to_stand = CollToStandInference()
    print("Models loaded")
    yield
    print("Shutting down...")


def enforce_dict(req, custom_type):
    """
    Enforces the request to be a dictionary.

    Args:
        req (Union[dict, str, custom_type]): The request to enforce as a dictionary.
        custom_type (type): The custom type to enforce.

    Returns:
        dict: The request as a dictionary.

    raises:
        TypeError: If the request type is not supported.

    """
    print("Request enforced as dictionary")
    if isinstance(req, dict):
        print("Request is already a dictionary: %s" % req)
        return req
    elif isinstance(req, str):
        print("Request is a string")
        req = json.loads(req)
    elif isinstance(req, custom_type):
        print("Request is a custom type")
        req = req.model_dump()
    else:
        raise TypeError(
            f"Support not added for enforcing type to be a dictionary: {type(req)}"
        )
    print("Request: %s" % req)
    return req


app = FastAPI(lifespan=lifespan)


# Define the Pydantic model for the input format
class InputRequest(BaseModel):
    input_text: str

    model_config = ConfigDict(extra="allow")


# Define the Pydantic model for the input format
class InputRequest(BaseModel):
    input_text: str
    encoding: str = None

    model_config = ConfigDict(extra="allow")


@app.post("/analyze/")
def analyze_input(request: InputRequest):
    """
    Analyzes the input text and returns tuple containing the normalized Tamil Unicode text and an array of dictionaries containing the classification results.

    Args:
        request (InputRequest): The input request containing the text to analyze.

    Returns:
        dict: A dictionary containing the normalized Tamil Unicode text and the classification results.

    """
    try:
        print("Request: %s" % request)
        request_dict = enforce_dict(request, InputRequest)
        # Use the quality_analyzer function to process the input text
        encoding = request_dict.get("encoding", None)
        need_translation = request_dict.get("need_translation", False)
        colloquial_to_standard = request_dict.get(
            "colloquial_to_standard", False)

        outputText, result = multi_sentence_quality_analyzer(
            classifier,
            coll_to_stand,
            request_dict["input_text"],
            encoding,
            need_translation,
            colloquial_to_standard,
        )
        print("outputText: ", outputText)
        print("result: ", result)
        return {"output": outputText, "result": result}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing input: {str(e)}")


# api for legacy to unicode
@app.post("/legacy2unicode/")
def legacy2unicode(request: InputRequest):
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
        encoding = request_dict.get("encoding", None)
        outputText = convert_legacy_to_unicode(
            request_dict["input_text"], encoding)
        print("outputText: ", outputText)
        return {"output": outputText}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing input: {str(e)}")


@app.post("/get_encoding/")
def get_encoding(request: InputRequest):
    """
    Gets the encoding of the input text.

    Args:
        request (InputRequest): The input request containing the text to analyze.

    Returns:
        dict: A dictionary containing the encoding of the input text.

    """
    try:
        print("request: ", request)
        request_dict = enforce_dict(request, InputRequest)

        input_text = request_dict["input_text"]

        inference_model = Inference()
        encoding = get_encoding_fun(inference_model, input_text)
        print("encoding: ", encoding)
        return {"encoding": encoding}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing input: {str(e)}")


# POST request to colloquial to standard translation inference
@app.post("/colloquial_to_standard/")
def colloquial_to_standard(request: InputRequest):
    """
    Translates colloquial Tamil text to standard Tamil.

    Args:
        request (InputRequest): The input request containing the colloquial Tamil text to translate.

    Returns:
        dict: A dictionary containing the translated standard Tamil text.

    """
    try:
        print("request: ", request)
        request_dict = enforce_dict(request, InputRequest)
        outputText = coll_to_stand.inference(request_dict["input_text"])
        print("outputText: ", outputText)
        return {"standard_tamil": outputText}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing input: {str(e)}")
