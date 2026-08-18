import re
import json

def extract_fgv_gabarito():
    with open('/home/ubuntu/Downloads/site-residencia/questoes_comentadas_raw.txt', 'r', encoding='utf-8') as f:
        text = f.read()

    # The format is typically: 
    # 1. (FGV...
    # ...
    # ✅✅Gabarito: Letra E
    
    # We can use a regex to find all gabaritos.
    # However, to map them reliably to question numbers, we should try to extract blocks or just rely on the order?
    # No, it's better to find question numbers and their corresponding gabaritos.
    
    # Let's split by question numbers: "1. (FGV", "2. (FGV", etc.
    # A more robust regex for question start: r'\n\s*(\d+)\.\s*\('
    
    parts = re.split(r'\n\s*(\d+)\.\s*\(', text)
    # parts[0] is preamble.
    # parts[1] is '1', parts[2] is text for q1, parts[3] is '2', etc.
    
    answers = {}
    
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            q_num = int(parts[i])
            q_text = parts[i+1]
            
            # Find gabarito in q_text
            match = re.search(r'Gabarito:\s*Letra\s*([A-E])', q_text, re.IGNORECASE)
            if match:
                answers[str(q_num)] = match.group(1).upper()
            else:
                print(f"Warning: Gabarito not found for question {q_num}")
    
    print(f"Extracted {len(answers)} gabaritos out of {len(parts)//2} questions.")
    
    # Now let's update questoes.json
    with open('/home/ubuntu/Downloads/site-residencia/questoes.json', 'r', encoding='utf-8') as f:
        questoes = json.load(f)
        
    updated = 0
    for q in questoes:
        q_id = str(q['id'])
        if q_id in answers:
            q['correct_answer'] = answers[q_id]
            updated += 1
            
    print(f"Updated {updated} questions with correct answers.")
    
    with open('/home/ubuntu/Downloads/site-residencia/questoes.json', 'w', encoding='utf-8') as f:
        json.dump(questoes, f, ensure_ascii=False, indent=2)
        
    # Also write to questoes.js
    compact = json.dumps(questoes, ensure_ascii=False, separators=(',', ':'))
    with open('/home/ubuntu/Downloads/site-residencia/questoes.js', 'w', encoding='utf-8') as f:
        f.write(f'var QUESTIONS = {compact};')

extract_fgv_gabarito()
