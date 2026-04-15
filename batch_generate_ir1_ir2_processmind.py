import os
import json
import importlib.util

# Dynamic import for parser and transformer
bpmn_ir1_path = os.path.join('code', 'study_case_carwash', 'bpmn_ir1.py')
spec_bpmn = importlib.util.spec_from_file_location('bpmn_ir1', bpmn_ir1_path)
bpmn_ir1 = importlib.util.module_from_spec(spec_bpmn)
spec_bpmn.loader.exec_module(bpmn_ir1)
parse_bpmn = bpmn_ir1.parse_bpmn

ir1_ir2_path = os.path.join('code', 'study_case_carwash', 'ir1_ir2.py')
spec_ir2 = importlib.util.spec_from_file_location('ir1_ir2', ir1_ir2_path)
ir1_ir2 = importlib.util.module_from_spec(spec_ir2)
spec_ir2.loader.exec_module(ir1_ir2)
transform_ir1_to_ir2 = ir1_ir2.transform_ir1_to_ir2

BPMN_DIR = 'dataset/BPMN_ProcessMind'
OUTPUT_DIR = 'dataset-finetune/dataset_ProcessMind'
os.makedirs(OUTPUT_DIR, exist_ok=True)

bpmn_files = [f for f in os.listdir(BPMN_DIR) if f.endswith('.bpmn')]

for bpmn_file in bpmn_files:
    bpmn_path = os.path.join(BPMN_DIR, bpmn_file)
    with open(bpmn_path, 'r', encoding='utf-8') as f:
        xml = f.read()
    ir1 = parse_bpmn(xml)
    ir2 = transform_ir1_to_ir2(ir1)
    prefix = bpmn_file.replace('.bpmn', '')
    ir1_path = os.path.join(OUTPUT_DIR, f'{prefix}_ir1.json')
    ir2_path = os.path.join(OUTPUT_DIR, f'{prefix}_ir2.json')
    with open(ir1_path, 'w', encoding='utf-8') as f:
        json.dump(ir1, f, indent=2)
    with open(ir2_path, 'w', encoding='utf-8') as f:
        json.dump(ir2, f, indent=2)
    print(f"Processed: {bpmn_file} → {ir1_path}, {ir2_path}")
