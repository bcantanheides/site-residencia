#!/usr/bin/env python3
"""
Parse ENADE/ENARE exam PDFs (extracted with pdftotext -raw) into structured JSON.
Each exam year produces a separate array of questions.
"""

import re
import json


def clean_text(text):
    """Clean up common PDF extraction artifacts."""
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
    return text


def find_first_question_line(lines):
    """Find where actual questions start (skip instruction pages)."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in ('1', '01'):
            # Check if next lines look like a question
            ahead = ' '.join(l.strip() for l in lines[i+1:i+5] if l.strip())
            if len(ahead) > 20 and not 'Lembre-se' in ahead and not 'fiscal' in ahead:
                return i
    return 0


def find_exam_end(lines):
    """Find where the first exam type ends (skip duplicate Tipo 02, etc)."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Detect start of second exam type
        if i > 100 and ('T2095022N' in stripped or 'T2046009N' in stripped or
                        re.match(r'^T\d{7}N$', stripped)):
            return i
        # Or if we see "PROVA" + "02" pattern
        if i > 100 and stripped == '02' and i > 0:
            prev = lines[i-1].strip() if i > 0 else ''
            if 'Lembre-se' in prev or 'PROVA' in prev:
                return i - 5  # back up a few lines
    return len(lines)


def parse_enade_raw(filepath, year, max_questions=None):
    """Parse an ENADE exam raw text file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
    
    # Determine expected question count
    if max_questions is None:
        # Count unique question numbers
        nums = set()
        for line in all_lines:
            stripped = line.strip()
            if re.match(r'^\d{1,3}$', stripped):
                n = int(stripped)
                if 1 <= n <= 100:
                    nums.add(n)
        max_questions = max(nums) if nums else 60
    
    # Trim to first exam copy only
    end_line = find_exam_end(all_lines)
    lines = all_lines[:end_line]
    
    # Find question starts: a standalone number between 1 and max_questions
    question_positions = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r'^\d{1,3}$', stripped):
            num = int(stripped)
            if 1 <= num <= max_questions:
                # Verify it's actually a question number, not page number or other
                # Check that there's substantive text nearby (within 5 lines)
                ahead = ' '.join(l.strip() for l in lines[i+1:i+6] if l.strip())
                # Skip if it's part of header/footer
                if ('Página' in ahead or 'Lembre-se' in ahead or 
                    'MEDICINA VETERINÁRIA' == ahead.strip() or
                    'INSCRIÇÃO' in ahead):
                    continue
                # Skip instruction page numbers
                if i < find_first_question_line(lines) - 5:
                    continue
                question_positions.append((i, num))
    
    # Remove duplicates - keep only first occurrence of each number
    seen = set()
    unique_positions = []
    for pos, num in question_positions:
        if num not in seen:
            seen.add(num)
            unique_positions.append((pos, num))
    question_positions = unique_positions
    
    # Sort by position
    question_positions.sort(key=lambda x: x[0])
    
    questions = []
    
    for idx, (line_idx, q_num) in enumerate(question_positions):
        # Find end of this question
        if idx + 1 < len(question_positions):
            end_idx = question_positions[idx + 1][0]
        else:
            end_idx = len(lines)
        
        # Collect question text
        q_lines = []
        for j in range(line_idx + 1, end_idx):
            stripped = lines[j].strip()
            # Skip noise lines
            if not stripped:
                continue
            if stripped.startswith('\x0c'):
                stripped = stripped.lstrip('\x0c').strip()
                if not stripped:
                    continue
            if 'Exame Nacional de Residência' in stripped:
                continue
            if 'EXAME NACIONAL DE RESIDÊNCIA' in stripped:
                continue
            if 'INSTITUTO AOCP' in stripped:
                continue
            if 'FGV CONHECIMENTO' in stripped:
                continue
            if re.match(r'^MEDICINA VETERINÁRIA.*Tipo', stripped):
                continue
            if re.match(r'^MEDICINA VETERINÁRIA.*Página', stripped):
                continue
            if stripped.startswith('Tipo 0') or stripped.startswith('TIPO 1'):
                continue
            if re.match(r'^Competências?\s*\(', stripped, re.IGNORECASE):
                continue
            if stripped in ('habilidades, atitudes) Comuns', 
                           'Habilidades, Atitudes) Comuns',
                           'Habilidades e Atitudes) Comuns',
                           'Habilidades, Atitudes) Específicas',
                           'Habilidades e Atitudes) Específicas'):
                continue
            if stripped.startswith('Competências (Conhecimentos'):
                continue
            if stripped == 'Conhecimentos Gerais':
                continue
            if stripped.startswith('Conhecimentos Específicos'):
                continue
            q_lines.append(stripped)
        
        if not q_lines:
            continue
        
        # Join text
        text_joined = ' '.join(q_lines)
        
        # Find options
        first_option = re.search(r'\(A\)\s', text_joined)
        
        opts = {}
        question_text = text_joined
        
        if first_option:
            question_text = text_joined[:first_option.start()].strip()
            options_text = text_joined[first_option.start():]
            
            opt_matches = list(re.finditer(r'\(([A-E])\)\s*(.*?)(?=\([A-E]\)\s|$)', options_text))
            for om in opt_matches:
                letter = om.group(1)
                opt_text = clean_text(om.group(2))
                opts[letter] = opt_text
        
        question_text = clean_text(question_text)
        
        if len(question_text) < 10:
            continue
        
        # Determine subcategory based on typical exam structure
        # First ~10-20 questions are usually "Conhecimentos Comuns/Gerais"
        if q_num <= 20:
            cat = "Conhecimentos Gerais"
        else:
            cat = "Conhecimentos Específicos (Veterinária)"
        
        questions.append({
            "id": q_num,
            "source": f"ENARE {year}",
            "question": question_text,
            "options": opts,
            "category": cat,
            "year": year
        })
    
    return questions


def main():
    files = {
        '2021-2022': '/home/ubuntu/Downloads/site-residencia/enade_2021-2022_raw2.txt',
        '2022-2023': '/home/ubuntu/Downloads/site-residencia/enade_2022-2023_raw2.txt',
        '2023-2024': '/home/ubuntu/Downloads/site-residencia/enade_2023-2024_raw2.txt',
        '2024-2025': '/home/ubuntu/Downloads/site-residencia/enade_2024-2025_raw2.txt',
        '2025-2026': '/home/ubuntu/Downloads/site-residencia/enade_2025-2026_raw2.txt',
    }
    
    all_data = {}
    total = 0
    
    for year, filepath in sorted(files.items()):
        print(f"\n=== Parsing ENARE {year} ===")
        questions = parse_enade_raw(filepath, year)
        
        with_opts = sum(1 for q in questions if len(q['options']) >= 2)
        print(f"  Total questions: {len(questions)}")
        print(f"  With 2+ options: {with_opts}")
        
        if questions:
            print(f"  Range: Q{questions[0]['id']} - Q{questions[-1]['id']}")
            # Show a few samples
            for q in questions[:2]:
                print(f"    Q{q['id']}: {q['question'][:80]}...")
                print(f"      Options: {list(q['options'].keys())}")
            
            few_opts = [q for q in questions if len(q['options']) < 2]
            if few_opts:
                print(f"  Questions with <2 options: {[q['id'] for q in few_opts]}")
        
        all_data[year] = questions
        total += len(questions)
    
    # Save JSON
    with open('/home/ubuntu/Downloads/site-residencia/enade_questoes.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n\nTotal ENARE questions: {total}")
    print("Saved to enade_questoes.json")
    
    # Also generate JS file
    compact = json.dumps(all_data, ensure_ascii=False, separators=(',', ':'))
    with open('/home/ubuntu/Downloads/site-residencia/enade_questoes.js', 'w', encoding='utf-8') as f:
        f.write(f'var ENADE_DATA = {compact};')
    print(f"Saved enade_questoes.js ({len(compact)} bytes)")


if __name__ == '__main__':
    main()
