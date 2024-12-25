import os
import torch
from transformers import pipeline, AutoTokenizer, BertForSequenceClassification

cache_dir = "inference_base\\models\\version_0"
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

label_mapping = {0: "Legacy Font Encoding", 1: "Romanized Text Encoding"}

pipe = pipeline(
    "text-classification", model="sanujen/fyp_0", device=0, cache_dir=cache_dir
)

tokenizer = AutoTokenizer.from_pretrained("sanujen/fyp_0", cache_dir=cache_dir)
model = BertForSequenceClassification.from_pretrained(
    "sanujen/fyp_0", cache_dir=cache_dir
)
model.eval()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)


def inference(word):
    inputs = tokenizer(
        word, return_tensors="pt", truncation=True, padding=True, max_length=180
    )
    inputs = {key: val.to(device) for key, val in inputs.items()}
    with torch.no_grad():
        logits = model(**inputs)[0]
        predictions = torch.argmax(logits, dim=1).cpu().numpy()
    predicted_label = label_mapping[predictions[0]]
    return predicted_label
