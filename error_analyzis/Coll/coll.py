import pandas as pd
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F
from tqdm import tqdm

# Load IndicBERT with slow tokenizer to avoid conversion issues
model_name = "ai4bharat/indic-bert"
try:
    # Try with fast tokenizer first
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
except Exception as e:
    print(f"Fast tokenizer failed, trying slow tokenizer: {e}")
    # Fallback to slow tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)

model = AutoModel.from_pretrained(model_name)
model.eval()

# Function to get CLS embedding
def get_embedding(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
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
        # Add default values for failed rows
        similarities.append(0.0)
        similarities2.append(0.0)

# create a new df with the similarities
df_similarities = pd.DataFrame({
    'similarity_gpt_actual': similarities,
    'similarity_system_actual': similarities2
})
# Save with individual scores
df_similarities.to_csv("tamil_sentence_similarity_and_actual_standardized.csv", index=False)

# Compute average similarity
if similarities:
    average_similarity = sum(similarities) / len(similarities)
    print(f"\n✅ Overall Average Similarity Score: {average_similarity:.4f}")
else:
    print("\n❌ No similarities computed successfully")
