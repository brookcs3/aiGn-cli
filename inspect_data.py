import pandas as pd

try:
    # Load dataset
    df = pd.read_json("hf://datasets/Anis1123/quip-dataset/with-annotation.json")
    print("Dataset Columns:", df.columns)
    print("\nFirst 5 rows:")
    print(df.head(5))
    
    # Check for text column
    if 'text' in df.columns:
        print("\nSanple texts:")
        for t in df['text'].head(3):
            print(f"- {t}")
except Exception as e:
    print(f"Error viewing dataset: {e}")
