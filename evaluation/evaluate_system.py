import pandas as pd
import requests
from pathlib import Path

# === Configuration ===
INPUT_FILE = "Questions_eval.xlsx"
OUTPUT_FILE = "Evaluation.xlsx"
API_URL = "http://localhost:8000/api/generate_response"  # 
NUM_RUNS = 2  # 

# === Load input file ===
input_path = Path(INPUT_FILE)
if not input_path.exists():
    raise FileNotFoundError(f"Input file '{INPUT_FILE}' not found.")

df_input = pd.read_excel(input_path)

# === Prepare output DataFrame ===
df = df_input.copy()

# === Perform multiple runs ===
for run_index in range(1, NUM_RUNS + 1):
    col_name = f"System_Response_{run_index}"
    df[col_name] = ""

    print(f"\n🚀 Starting Run {run_index}/{NUM_RUNS}...")
    for i, row in df.iterrows():
        question = str(row["Question"])
        try:
            res = res = requests.post(API_URL, data={"question": question})
            res.raise_for_status()
            data = res.json()
            answer = data.get("answer", "No answer returned")
        except Exception as e:
            answer = f"Error: {str(e)}"
        df.at[i, col_name] = answer
        print(f"✅ Q{i+1}: {question[:50]}... → Response length: {len(answer)}")

# === Save result ===
df.to_excel(OUTPUT_FILE, index=False)
print(f"\n📁 All {NUM_RUNS} runs completed. Results saved to '{OUTPUT_FILE}'")
