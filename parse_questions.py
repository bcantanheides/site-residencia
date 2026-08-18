#!/usr/bin/env python3
"""
Parse the raw text extracted from FOCO NO ENARE 1000 QUESTÕES PDF
and generate a structured JSON file for the study site.
"""

import re
import json

def parse_questions(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = f.read()
    
    # Remove license lines, page numbers, @preparatorioenarevet, and form feeds
    lines = raw.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('Licensed to'):
            continue
        if stripped == '@preparatorioenarevet':
            continue
        if stripped == '\x0c' or stripped == '':
            continue
        # Skip standalone page numbers
        if re.match(r'^\d+$', stripped):
            continue
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Find all question starts: "NUMBER. (SOURCE) question text..."
    # We capture the full source including nested parens
    question_pattern = re.compile(
        r'(?:^|\n)\s*(\d+)\.\s*\((.+?)\)\s*(.*?)(?=\n\s*\d+\.\s*\(|\Z)',
        re.DOTALL
    )
    
    questions = []
    
    for match in question_pattern.finditer(text):
        num = int(match.group(1))
        source_raw = match.group(2).strip()
        body_raw = match.group(3).strip()
        
        # The source may include the year after a dash, like "FGV - Analista (MPE SP) - 2023"
        # But our regex split at first ), so we might have "FGV - Analista (MPE SP"
        # and then "- 2023) question text" in body_raw
        # Let's fix: check if body starts with something like "- 2023)" or "- 2024)"
        year_prefix = re.match(r'^-\s*(\d{4})\)\s*', body_raw)
        if year_prefix:
            source_raw = source_raw + ' - ' + year_prefix.group(1)
            body_raw = body_raw[year_prefix.end():].strip()
        elif body_raw.startswith(')'):
            # closing paren from nested source
            body_raw = body_raw[1:].strip()
        
        # Clean up the body text - normalize whitespace within lines
        body_lines = body_raw.split('\n')
        body_cleaned = []
        for bl in body_lines:
            bl = bl.strip()
            if bl:
                body_cleaned.append(bl)
        body_text = ' '.join(body_cleaned)
        
        # Find the first option to split question text from options
        first_option = re.search(r'\(A\)\s', body_text)
        
        opts = {}
        if first_option:
            question_text = body_text[:first_option.start()].strip()
            options_text = body_text[first_option.start():]
            
            # Parse individual options
            opt_matches = list(re.finditer(r'\(([A-E])\)\s*(.*?)(?=\([A-E]\)\s|$)', options_text))
            for om in opt_matches:
                letter = om.group(1)
                opt_text = om.group(2).strip()
                opt_text = re.sub(r'\s+', ' ', opt_text).strip()
                # Remove trailing period if duplicated
                opts[letter] = opt_text
        else:
            question_text = body_text
        
        # Clean question text
        question_text = re.sub(r'\s+', ' ', question_text).strip()
        
        # Fix common PDF artifacts: "so-\nbre" -> "sobre", "muni-\ncípios" -> "municípios"  
        question_text = re.sub(r'(\w)-\s+(\w)', r'\1\2', question_text)
        for letter in opts:
            opts[letter] = re.sub(r'(\w)-\s+(\w)', r'\1\2', opts[letter])
        
        # Determine category
        if num <= 200:
            category = "Conhecimentos Comuns/SUS"
        else:
            category = "Conhecimentos Específicos (Veterinária)"
        
        questions.append({
            "id": num,
            "source": source_raw,
            "question": question_text,
            "options": opts,
            "category": category
        })
    
    return questions

def main():
    questions = parse_questions('/home/ubuntu/Downloads/site-residencia/questoes_raw.txt')
    
    # Sort by ID
    questions.sort(key=lambda q: q['id'])
    
    # Remove duplicates
    seen = set()
    unique_questions = []
    for q in questions:
        if q['id'] not in seen:
            seen.add(q['id'])
            unique_questions.append(q)
    
    print(f"Total questions parsed: {len(unique_questions)}")
    
    # Print first few for verification
    for q in unique_questions[:3]:
        print(f"\n--- Question {q['id']} ---")
        print(f"Source: {q['source']}")
        print(f"Category: {q['category']}")
        print(f"Question: {q['question'][:150]}...")
        for letter, text in q['options'].items():
            print(f"  ({letter}) {text[:100]}")
    
    # Print some from the middle
    print("\n\n--- Middle questions ---")
    for q in unique_questions[199:202]:
        print(f"\n--- Question {q['id']} ---")
        print(f"Source: {q['source']}")
        print(f"Category: {q['category']}")
        print(f"Question: {q['question'][:150]}...")
    
    # Check how many have options
    with_options = sum(1 for q in unique_questions if len(q['options']) >= 2)
    print(f"\nQuestions with 2+ options: {with_options}")
    without_options = [q['id'] for q in unique_questions if len(q['options']) < 2]
    if without_options:
        print(f"Questions without enough options: {without_options[:20]}")
    
    # Save to JSON
    with open('/home/ubuntu/Downloads/site-residencia/questoes.json', 'w', encoding='utf-8') as f:
        json.dump(unique_questions, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved {len(unique_questions)} questions to questoes.json")

if __name__ == '__main__':
    main()
