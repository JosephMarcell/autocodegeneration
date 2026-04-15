
import os
import json
import sys

# Add code/study_case_carwash to sys.path for direct import
sys.path.insert(0, os.path.abspath('code/study_case_carwash'))
import generator

dir_ir2 = 'dataset-finetune/dataset_Camunda'
output_jsonl = 'dataset-finetune/dataset_Camunda/train.jsonl'

ir2_files = [f for f in os.listdir(dir_ir2) if f.endswith('_ir2.json')]

with open(output_jsonl, 'w', encoding='utf-8') as out_f:
    for fname in ir2_files:
        with open(os.path.join(dir_ir2, fname), 'r', encoding='utf-8') as f:
            ir2 = json.load(f)
        tasks = generator.decompose(ir2)
        for task in tasks:
            system_prompt = generator.SYSTEM_PROMPTS[task.file_type]
            user_message = generator.build_user_message(task)
            # Dummy ground truth: placeholder TypeScript (replace with real codegen/LLM call)
            assistant = f"// TODO: generate code for {task.path}\nexport const Dummy = () => null;"
            record = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant}
                ]
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + '\n')
print(f"Done. Output: {output_jsonl}")
