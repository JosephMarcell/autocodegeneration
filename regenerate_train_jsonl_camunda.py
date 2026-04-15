import os
import json
import sys

# Add code/study_case_carwash to sys.path for direct import
sys.path.insert(0, os.path.abspath('code/study_case_carwash'))
import generator

dir_ir2 = 'dataset-finetune/dataset_Camunda'
output_jsonl = 'dataset-finetune/dataset_Camunda/train.jsonl'

# Template generator for assistant content

def template_code(task):
    if task.file_type == 'global_state':
        return "import create from 'zustand';\n\nexport const useGlobalState = create(() => ({}));"
    if task.file_type == 'protected_route':
        return "import { useGlobalState } from '../state/globalState';\nexport const ProtectedRoute = () => null;"
    if task.file_type == 'layout':
        return "import { Outlet } from 'react-router-dom';\nimport { useGlobalState } from '../state/globalState';\nexport const Layout = () => <Outlet />;"
    if task.file_type == 'ui_kit':
        return "import React from 'react';\nexport const Card = ({ children }) => <div>{children}</div>;\nexport const Button = ({ children }) => <button>{children}</button>;\nexport const Input = (props) => <input {...props} />;"
    if task.file_type == 'login_page':
        return "import { useGlobalState } from '../state/globalState';\nexport const LoginPage = () => null;"
    if task.file_type == 'app_root':
        return "import { BrowserRouter, Routes, Route } from 'react-router-dom';\nexport const App = () => <BrowserRouter><Routes></Routes></BrowserRouter>;"
    if task.file_type == 'dynamic_page':
        comp = task.context['task']['component']
        page_type = task.context['task'].get('pageType', '')
        imports = "import { useNavigate } from 'react-router-dom';\nimport { useGlobalState } from '../../../shared/state/globalState';\nimport { Card, Button } from '../../../shared/components/UI';"
        if page_type == 'write-navigate':
            return f"{imports}\n\nexport const {comp} = () => {{\n  const navigate = useNavigate();\n  const {{ updateProcessState }} = useGlobalState();\n  return (\n    <Card title=\"Task\">\n      <Button onClick={{() => {{ updateProcessState({{}}); navigate('/'); }} }} fullWidth>Complete</Button>\n    </Card>\n  );\n}};"
        if page_type == 'wait-then-write':
            wait_field = task.context['task'].get('waitCondition', {}).get('field', 'wait_field')
            readable = task.context['task'].get('waitCondition', {}).get('readableLabel', 'Waiting...')
            return f"{imports}\n\nexport const {comp} = () => {{\n  const navigate = useNavigate();\n  const {{ processState, updateProcessState }} = useGlobalState();\n  if (!processState.{wait_field}) {{\n    return (<Card title=\"Wait\"><div>{readable}</div></Card>);\n  }}\n  return (<Card title=\"Wait\"><Button onClick={{() => {{ updateProcessState({{}}); navigate('/'); }} }} fullWidth>Proceed</Button></Card>);\n}};"
        # fallback
        return f"{imports}\n\nexport const {comp} = () => null;"
    return '// Not implemented'

ir2_files = [f for f in os.listdir(dir_ir2) if f.endswith('_ir2.json')]

with open(output_jsonl, 'w', encoding='utf-8') as out_f:
    for fname in ir2_files:
        with open(os.path.join(dir_ir2, fname), 'r', encoding='utf-8') as f:
            ir2 = json.load(f)
        tasks = generator.decompose(ir2)
        for task in tasks:
            system_prompt = generator.SYSTEM_PROMPTS[task.file_type]
            user_message = generator.build_user_message(task)
            assistant = template_code(task)
            record = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant}
                ]
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + '\n')
print(f"Done. Output: {output_jsonl}")
