import os
import torch
from transformers import BertForSequenceClassification, AutoTokenizer

label_mapping = {0: "Legacy Font Encoding", 1: "Romanized Text Encoding"}


def get_absolute_path(relative_path):
    return os.path.abspath(relative_path)


model_path = "inference_base\\models\\bert-base-uncased\\"
model = BertForSequenceClassification.from_pretrained(get_absolute_path(model_path))
tokenizer = AutoTokenizer.from_pretrained(get_absolute_path(model_path))
model.eval()


def inference(word):
    inputs = tokenizer(
        word, return_tensors="pt", truncation=True, padding=True, max_length=180
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    inputs = {key: val.to(device) for key, val in inputs.items()}
    with torch.no_grad():
        logits = model(**inputs)[0]
        predictions = torch.argmax(logits, dim=1).cpu().numpy()
    predicted_label = label_mapping[predictions[0]]
    return predicted_label
