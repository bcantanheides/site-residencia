import re
import json

def parse_gabarito(filepath, title_marker):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the section for the specified title
    start_idx = content.find(title_marker)
    if start_idx == -1:
        print(f"Marker '{title_marker}' not found in {filepath}")
        return {}
        
    section = content[start_idx:start_idx+3000] # assume it fits in 3000 chars
    
    # We are looking for lines with numbers and lines with letters.
    lines = section.split('\n')
    answers = {}
    
    nums = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if line contains question numbers (e.g., 1 2 3 4 5)
        # Using a simple heuristic: if it has many numbers separated by spaces
        tokens = line.split()
        if len(tokens) >= 5 and all(t.isdigit() for t in tokens):
            nums = tokens
        elif nums and len(tokens) == len(nums) and all(t in 'ABCDE*X' for t in tokens):
            # This is the answer line
            for i, num in enumerate(nums):
                answers[num] = tokens[i]
            nums = [] # reset
            
    return answers

files = [
    ('2021-2022', '/home/ubuntu/Downloads/site-residencia/gabarito_2021-2022.txt', 'MEDICINA VETERINÁRIA - PROVA 1'),
    ('2022-2023', '/home/ubuntu/Downloads/site-residencia/gabarito_2022-2023.txt', 'MEDICINA VETERINÁRIA - PROVA 1'),
    ('2023-2024', '/home/ubuntu/Downloads/site-residencia/gabarito_2023-2024.txt', 'MEDICINA VETERINÁRIA - PROVA 1'),
    ('2024-2025', '/home/ubuntu/Downloads/site-residencia/gabarito_2024-2025.txt', 'MEDICINA VETERINÁRIA (MEDVETT01) - PROVA TIPO 1'),
    ('2025-2026', '/home/ubuntu/Downloads/site-residencia/gabarito_2025-2026.txt', 'Medicina veterinária - 1'),
]

all_gabaritos = {}
for year, path, marker in files:
    ans = parse_gabarito(path, marker)
    print(f"{year}: extracted {len(ans)} answers")
    all_gabaritos[year] = ans

with open('/home/ubuntu/Downloads/site-residencia/enade_questoes.json', 'r', encoding='utf-8') as f:
    enade = json.load(f)

for year, questions in enade.items():
    if year in all_gabaritos:
        ans_dict = all_gabaritos[year]
        for q in questions:
            qid = str(q['id'])
            if qid in ans_dict:
                val = ans_dict[qid]
                # * or X means annulled, we can set it to None or leave it out, but user wants answers to check
                q['correct_answer'] = val
            else:
                print(f"Missing answer for {year} Q{qid}")

with open('/home/ubuntu/Downloads/site-residencia/enade_questoes.json', 'w', encoding='utf-8') as f:
    json.dump(enade, f, ensure_ascii=False, indent=2)

compact = json.dumps(enade, ensure_ascii=False, separators=(',', ':'))
with open('/home/ubuntu/Downloads/site-residencia/enade_questoes.js', 'w', encoding='utf-8') as f:
    f.write(f'var ENADE_DATA = {compact};')

print("Updated enade_questoes.json and .js")
