import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set style for academic paper
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 10

# Load the data
df = pd.read_csv("tamil_sentence_similarity_and_actual_standardized.csv")

# Prepare data for box plot
data_for_plot = []
labels = []

# Add GPT similarity scores
data_for_plot.append(df['similarity_gpt_actual'].values)
labels.append('GPT-Generated')

# Add System similarity scores  
data_for_plot.append(df['similarity_system_actual'].values)
labels.append('System-Generated')

# Create the box plot
fig, ax = plt.subplots(figsize=(8, 6))

# Create box plot
bp = ax.boxplot(data_for_plot, labels=labels, patch_artist=True, 
                boxprops=dict(facecolor='lightblue', alpha=0.7),
                medianprops=dict(color='red', linewidth=2),
                flierprops=dict(marker='o', markerfacecolor='red', markersize=4))

# Customize the plot
ax.set_title('Similarity Score Distribution: GPT vs System-Generated Tamil Translations', 
             fontweight='bold', pad=20)
ax.set_ylabel('Cosine Similarity Score', fontweight='bold')
ax.set_ylim(0.99, 1.001)  # Focus on the high similarity range
ax.grid(True, alpha=0.3)

# Add statistics text
gpt_mean = df['similarity_gpt_actual'].mean()
system_mean = df['similarity_system_actual'].mean()
gpt_std = df['similarity_gpt_actual'].std()
system_std = df['similarity_system_actual'].std()

stats_text = f'GPT Mean: {gpt_mean:.4f} (±{gpt_std:.4f})\nSystem Mean: {system_mean:.4f} (±{system_std:.4f})'
ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

# Add sample size
ax.text(0.02, 0.02, f'n = {len(df)} samples', transform=ax.transAxes,
        verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

plt.tight_layout()
plt.savefig('tamil_similarity_analysis.png', dpi=300, bbox_inches='tight')
plt.show()

# Print summary statistics
print("=== SIMILARITY ANALYSIS SUMMARY ===")
print(f"Sample size: {len(df)}")
print(f"\nGPT-Generated vs Actual:")
print(f"  Mean: {gpt_mean:.4f}")
print(f"  Std:  {gpt_std:.4f}")
print(f"  Min:  {df['similarity_gpt_actual'].min():.4f}")
print(f"  Max:  {df['similarity_gpt_actual'].max():.4f}")

print(f"\nSystem-Generated vs Actual:")
print(f"  Mean: {system_mean:.4f}")
print(f"  Std:  {system_std:.4f}")
print(f"  Min:  {df['similarity_system_actual'].min():.4f}")
print(f"  Max:  {df['similarity_system_actual'].max():.4f}")

# Calculate improvement
improvement = gpt_mean - system_mean
print(f"\nGPT improvement over System: {improvement:.4f} ({improvement*100:.2f}%)") 