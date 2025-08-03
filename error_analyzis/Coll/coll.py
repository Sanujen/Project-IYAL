import pandas as pd
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F
from tqdm import tqdm

# Load IndicBERT
model_name = "ai4bharat/indic-bert"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)
model.eval()

# Function to get CLS embedding
def get_embedding(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state[:, 0, :]

# Load your CSV
df = pd.read_csv("unified_tamil_data.csv")

similarities = []
similarities2 = []
for idx, row in tqdm(df.iterrows(), total=len(df)):
    s1 = str(row['gpt_generated'])
    s2 = str(row['system_generated'])
    s3 = str(row['actual_standardized'])

    try:
        emb1 = get_embedding(s1)
        emb2 = get_embedding(s2)
        emb3 = get_embedding(s3)
        cosine_sim = F.cosine_similarity(emb1, emb3).item()
        cosine_sim2 = F.cosine_similarity(emb2, emb3).item()
        similarities.append(cosine_sim)
        similarities2.append(cosine_sim2)
    except Exception as e:
        print(f"Skipping row {idx} due to error: {e}")

# Add to DataFrame
df['similarity_gpt_actual'] = similarities
df['similarity_system_actual'] = similarities2
# Save with individual scores
df.to_csv("tamil_sentence_similarity_and_actual_standardized.csv", index=False)

# Compute average similarity
average_similarity = sum(similarities) / len(similarities)
print(f"\n✅ Overall Average Similarity Score: {average_similarity:.4f}")
