
import os
import sys
import json
import importlib.util

# Dynamically import parse_bpmn
bpmn_ir1_path = os.path.join('code', 'study_case_carwash', 'bpmn_ir1.py')
spec_bpmn = importlib.util.spec_from_file_location('bpmn_ir1', bpmn_ir1_path)
bpmn_ir1 = importlib.util.module_from_spec(spec_bpmn)
spec_bpmn.loader.exec_module(bpmn_ir1)
parse_bpmn = bpmn_ir1.parse_bpmn

# Dynamically import transform_ir1_to_ir2
ir1_ir2_path = os.path.join('code', 'study_case_carwash', 'ir1_ir2.py')
spec_ir2 = importlib.util.spec_from_file_location('ir1_ir2', ir1_ir2_path)
ir1_ir2 = importlib.util.module_from_spec(spec_ir2)
spec_ir2.loader.exec_module(ir1_ir2)
transform_ir1_to_ir2 = ir1_ir2.transform_ir1_to_ir2

# Directory containing all ITS BPMN files
BPMN_DIR = 'dataset/BPMN_ITS'
# Output directory for IR1/IR2 files
OUTPUT_DIR = 'dataset-finetune'

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Walk through all subfolders and find .bpmn files
bpmn_files = []
for root, dirs, files in os.walk(BPMN_DIR):
    for file in files:
        if file.endswith('.bpmn'):
            bpmn_files.append(os.path.join(root, file))

print(f"Found {len(bpmn_files)} BPMN files.")

for bpmn_path in bpmn_files:
    with open(bpmn_path, 'r', encoding='utf-8') as f:
        xml = f.read()
    ir1 = parse_bpmn(xml)
    ir2 = transform_ir1_to_ir2(ir1)
    # Use a unique prefix for each file based on folder and file name
    rel_path = os.path.relpath(bpmn_path, BPMN_DIR)
    prefix = rel_path.replace(os.sep, '__').replace('.bpmn', '')
    ir1_path = os.path.join(OUTPUT_DIR, f'{prefix}_ir1.json')
    ir2_path = os.path.join(OUTPUT_DIR, f'{prefix}_ir2.json')
    with open(ir1_path, 'w', encoding='utf-8') as f:
        json.dump(ir1, f, indent=2)
    with open(ir2_path, 'w', encoding='utf-8') as f:
        json.dump(ir2, f, indent=2)
    print(f"Processed: {bpmn_path} → {ir1_path}, {ir2_path}")
