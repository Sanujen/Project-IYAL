import os
import torch
from transformers import pipeline


import os
import torch
from transformers import pipeline


class Inference:
    """
    A class used to perform inference using a pre-trained mBART model for colloquial to standard Tamil translation.

    Attributes
    ----------
    cache_dir : str
        Directory to cache the model. Default to absolute path of this file directory + models + {model_version}
    model_name : str
        Name of the pre-trained model on huggingface.co. Default to "sanujen/mBART_Tamil_Colloquial_to_Standard".
    model_version : str
        Version of the model. Default to "version_1".

    pipe : transformers.pipelines.Pipeline
        Pipeline for text translation.
    device : torch.device
        Device to run the model on (CPU or GPU).

    Methods
    -------
    inference(sentence)
        Performs inference on the given sentence and returns the translated sentence.

    """

    def __init__(
        self,
        cache_dir=None,
        model_name="sanujen/mBART_Tamil_Colloquial_to_Standard",
        model_version="version_1",
    ):
        self.model_version = model_version
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(__file__),
            "models/colloquial_to_standard",
            self.model_version,
        )
        self.model_name = model_name

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.pipe = pipeline(
            "text2text-generation",
            model=self.model_name,
            device=0 if torch.cuda.is_available() else -1,
        )

    def inference(self, sentence):
        return self.pipe(sentence)[0]["generated_text"]
