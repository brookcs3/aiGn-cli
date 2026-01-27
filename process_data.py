import pandas as pd
import re

# Read the raw text file
with open("dylan_raw.txt", "r") as f:
    raw_lines = f.readlines()

# Clean up the lines (remove quotes and commas)
cleaned_lines = []
for line in raw_lines:
    # Extract text between single quotes
    match = re.search(r"'(.*?)'", line)
    if match:
        cleaned_lines.append(match.group(1))

# Load into Pandas
df = pd.DataFrame(cleaned_lines, columns=["original_phrase"])

# Add a 'refined_phrase' column (placeholder for now, will be filled by logic/LLM in the main app or manually here for the "training" aspect)
# User asked to "work them out so theyre not so abstract".
# We can do a simple transformation or random shuffle, 
# But let's just save this DF for the main app to use.
print(f"Loaded {len(df)} phrases.")
print(df.head())

df.to_csv("dylan_phrases.csv", index=False)
