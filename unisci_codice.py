# dump_rapido.py - versione minimalista e aggressiva
import os
from datetime import datetime

output_file = f"all_code.txt" #_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"

with open(output_file, "w", encoding="utf-8") as out:
    out.write(f"=== DUMP PROGETTO ===\n")
    out.write(f"Generato: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    out.write(f"Cartella: {os.getcwd()}\n\n")

    for root, dirs, files in os.walk("."):
        # salta cartelle fastidiose
        if '__pycache__' in root or '.git' in root or 'venv' in root:
            continue
            
        for file in files:
            if file.endswith(('.py', '.yaml', '.yml', '.txt', '.md', '.json')):
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, ".")
                
                out.write(f"\n{'='*70}\n")
                out.write(f"FILE: {rel_path}\n")
                out.write(f"{'='*70}\n\n")
                
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    out.write(content + "\n\n")
                except Exception as e:
                    out.write(f"ERRORE lettura: {e}\n\n")

    out.write("\n=== FINE ===\n")

print(f"Creato: {output_file}")
print(f"Dimensione: {os.path.getsize(output_file) / 1024:.1f} KB")