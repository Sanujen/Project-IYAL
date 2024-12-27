import os
import torch
from transformers import pipeline, AutoTokenizer, BertForSequenceClassification

class Inference:
    """
    A class used to perform inference using a pre-trained BERT model for sequence classification.

    Attributes
    ----------
    cache_dir : str
        Directory to cache the model. Default to absolute path of this file directory + models + {model_version}
    model_name : str
        Name of the pre-trained model on huggingface.co. Default to "sanujen/fyp_0".
    model_version : str
        Version of the model. Default to "version_0".
    label_mapping : dict
        Mapping of label indices to label names.
    pipe : transformers.pipelines.Pipeline
        Pipeline for text classification.
    tokenizer : transformers.AutoTokenizer
        Tokenizer for the pre-trained model.
    model : transformers.BertForSequenceClassification
        Pre-trained BERT model for sequence classification.
    device : torch.device
        Device to run the model on (CPU or GPU).

    Methods
    -------
    inference(word)
        Performs inference on the given word and returns the predicted label.
        
    """
    def __init__(self, cache_dir = None, model_name = "sanujen/fyp_0", model_version = "version_0"):
        #"iyal_quality_analyzer\\inference_base\\models\\version_0"
        # absolute path of this file directory + models + {model_version}
        self.model_version = model_version
        self.cache_dir = cache_dir if cache_dir else os.path.join(os.path.dirname(__file__), "models", self.model_version)
        self.model_name = model_name if model_name else "sanujen/fyp_0"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.label_mapping = {0: "Legacy Font Encoding", 1: "Romanized Text Encoding"}

        self.pipe = pipeline(
            "text-classification", model=self.model_name, device=0, cache_dir=self.cache_dir
        )

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, cache_dir=self.cache_dir)
        self.model = BertForSequenceClassification.from_pretrained(
            self.model_name, cache_dir=self.cache_dir
        )
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)

    def inference(self, word):
        """
        Performs inference on the given word and returns the predicted label.

        Args:
            word (str): The input word to classify.

        Returns:
            str: The predicted label for the input word.

        """
        inputs = self.tokenizer(
            word, return_tensors="pt", truncation=True, padding=True, max_length=180
        )
        inputs = {key: val.to(self.device) for key, val in inputs.items()}
        with torch.no_grad():
            logits = self.model(**inputs)[0]
            predictions = torch.argmax(logits, dim=1).cpu().numpy()
        predicted_label = self.label_mapping[predictions[0]]
        return predicted_label
    
