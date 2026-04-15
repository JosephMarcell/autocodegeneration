"""
Generator: IR2 → List[GenerationTask] → LLM calls → React source files
=======================================================================
Implements the three-stage inner loop from System_study.md:
  1. decompose(ir2)      → ordered list of GenerationTask
  2. build_user_message  → per-task prompt (system + user)
  3. generate_all loop   → LLM call → extract_code → validate → retry → write
"""

from __future__ import annotations
import dataclasses
import json
import os
import re
import sys

import requests

# Allow running this file directly (e.g. python generator.py)
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from prompts import SYSTEM_PROMPTS


# ── Data model ────────────────────────────────────────────────────────────────

@dataclasses.dataclass
class GenerationTask:
    path:      str   # relative output path, e.g. 'src/shared/state/globalState.ts'
    file_type: str   # key into SYSTEM_PROMPTS
    context:   dict  # IR2 slice passed as user-message JSON
    order:     int   # generation sequence index (0-based)


# ── Context builders ──────────────────────────────────────────────────────────

def build_core_context(file_type: str, ir2: dict) -> dict:
    """Return the minimal IR2 slice that a core-file prompt needs."""
    shared = ir2['sharedContext']
    match file_type:
        case 'global_state':
            return {'roles': shared['roles'], 'stateSchema': shared['stateSchema']}
        case 'protected_route':
            return {'defaultRoutesPerRole': shared['defaultRoutesPerRole']}
        case 'layout':
            return {
                'roles':    shared['roles'],
                'allRoutes': shared['allRoutes'],
            }
        case 'ui_kit':
            return {}
        case 'login_page':
            return {
                'project': ir2['project'],
                'roles':   shared['roles'],
                'defaultRoutesPerRole': shared['defaultRoutesPerRole'],
            }
        case 'app_root':
            return {
                'project':              ir2['project'],
                'allRoutes':            shared['allRoutes'],
                'defaultRoutesPerRole': shared['defaultRoutesPerRole'],
            }
    return {}


def build_page_context(task_def: dict, participant: dict, shared: dict) -> dict:
    """Return the IR2 slice for a dynamic BPMN-task page."""
    return {
        'moduleName':  participant['name'],
        'role':        participant['role'],
        'task':        task_def,
        'stateSchema': shared['stateSchema'],
    }


# ── Decompose ─────────────────────────────────────────────────────────────────

# Fixed order for the 6 core infrastructure files
_CORE_FILES: list[tuple[str, str]] = [
    ('src/shared/state/globalState.ts',          'global_state'),
    ('src/shared/components/ProtectedRoute.tsx',  'protected_route'),
    ('src/shared/components/Layout.tsx',          'layout'),
    ('src/shared/components/UI.tsx',              'ui_kit'),
    ('src/shared/pages/LoginPage.tsx',            'login_page'),
    ('src/App.tsx',                               'app_root'),
]


def decompose(ir2: dict) -> list[GenerationTask]:
    """
    Build the ordered GenerationTask list from an IR2 dict.
    Order: core infra files first, then dynamic pages per participant/task.
    """
    tasks:   list[GenerationTask] = []
    shared = ir2['sharedContext']

    # ── Core shared files ─────────────────────────────────────────────────
    for idx, (path, ftype) in enumerate(_CORE_FILES):
        tasks.append(GenerationTask(
            path      = path,
            file_type = ftype,
            context   = build_core_context(ftype, ir2),
            order     = idx,
        ))

    # ── Dynamic pages ─────────────────────────────────────────────────────
    order = len(_CORE_FILES)
    for participant in ir2['participants']:
        for task_def in participant['tasks']:
            path = (
                f"src/modules/{participant['name']}"
                f"/pages/{task_def['component']}.tsx"
            )
            tasks.append(GenerationTask(
                path      = path,
                file_type = 'dynamic_page',
                context   = build_page_context(task_def, participant, shared),
                order     = order,
            ))
            order += 1

    return tasks


# ── Prompt building ───────────────────────────────────────────────────────────

def build_user_message(task: GenerationTask) -> str:
    ctx_json = json.dumps(task.context, indent=2)
    return (
        f"Generate the file: {task.path}\n\n"
        f"Context (IR2 excerpt):\n{ctx_json}\n\n"
        "Generate the complete file content now. Follow all OUTPUT CONTRACT rules."
    )


def build_retry_message(original_msg: str, bad_code: str, task: GenerationTask) -> str:
    """Return a user message that describes validation failures for a retry."""
    issues: list[str] = []
    lines  = bad_code.strip().split('\n')
    first  = lines[0].strip() if lines else ''

    if not (first.startswith('import') or first.startswith('export') or first.startswith('//')):
        issues.append(f"• First line must be an import/export statement. Got: '{first[:80]}'")

    if task.file_type == 'dynamic_page':
        comp = task.context['task']['component']
        if f'export const {comp}' not in bad_code:
            issues.append(f"• Missing named export: 'export const {comp}'")

    if task.file_type == 'global_state' and 'export const useGlobalState' not in bad_code:
        issues.append("• Missing: 'export const useGlobalState'")

    if '```' in bad_code:
        issues.append("• Contains markdown code fences (```). Output raw TypeScript only.")

    if not issues:
        issues.append("• Output does not satisfy the OUTPUT CONTRACT. Review all rules.")

    issues_str = '\n'.join(issues)
    return (
        f"The previous attempt had these issues:\n{issues_str}\n\n"
        f"Fix ONLY these issues and regenerate the COMPLETE file.\n\n"
        f"{original_msg}"
    )


# ── Code extraction & validation ──────────────────────────────────────────────

def extract_code(raw: str) -> str:
    """Strip markdown fences and leading prose from LLM output."""
    raw = raw.strip()
    # Remove fenced code blocks (```typescript ... ``` or ``` ... ```)
    raw = re.sub(r'^```[a-zA-Z]*\s*\n?', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\n?```\s*$',           '', raw, flags=re.MULTILINE)
    raw = raw.strip()
    # Skip any leading prose until first code line
    lines = raw.split('\n')
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('import ') or s.startswith('export ') or s.startswith('//'):
            return '\n'.join(lines[i:]).strip()
    return raw


def validate(code: str, task: GenerationTask) -> bool:
    """Light structural validation; does NOT exec the code."""
    if not code.strip():
        return False
    first = code.strip().split('\n')[0].strip()
    if not (first.startswith('import') or first.startswith('export') or first.startswith('//')):
        return False
    if task.file_type == 'dynamic_page':
        comp = task.context['task']['component']
        if f'export const {comp}' not in code:
            return False
    if task.file_type == 'global_state':
        if 'export const useGlobalState' not in code:
            return False
    if '```' in code:
        return False
    return True


# ── Ollama LLM client ─────────────────────────────────────────────────────────

def call_llm(
    system_prompt: str,
    user_message:  str,
    model:         str,
    base_url:      str,
    timeout:       int = 180,
) -> str:
    """
    POST to Ollama /api/chat and return the assistant message content.
    Raises requests.HTTPError on non-2xx; requests.ConnectionError if Ollama is down.
    """
    url     = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_message},
        ],
        "stream": False,
        "options": {
            "temperature":  0.2,    # deterministic for code generation
            "num_predict":  2048,   # max tokens per response
        },
    }
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()['message']['content']


# ── File writer ───────────────────────────────────────────────────────────────

def write_file(output_dir: str, rel_path: str, content: str) -> str:
    """Write content to output_dir/rel_path, creating directories as needed."""
    full = os.path.join(output_dir, rel_path.replace('/', os.sep))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as fh:
        fh.write(content)
    return full


# ── Main generation loop ──────────────────────────────────────────────────────

_STATUS = {
    'ok':               '✓ ok',
    'retry_ok':         '✓ ok (retry)',
    'failed':           '✗ FAILED',
    'dry_run':          '— dry run',
    'connection_error': '✗ connection error',
}


def generate_all(
    ir2:        dict,
    output_dir: str,
    model:      str  = 'qwen2.5-coder:7b',
    base_url:   str  = 'http://localhost:11434',
    dry_run:    bool = False,
) -> dict[str, str]:
    """
    Full pipeline: decompose IR2 → build prompts → call LLM → validate → write files.

    Returns a dict mapping relative file path → status string.
    """
    gen_tasks: list[GenerationTask] = decompose(ir2)
    results:   dict[str, str]       = {}
    total = len(gen_tasks)

    print(f"\n{'=' * 64}")
    print(f"  Pipeline: {total} files  |  model: {model}")
    print(f"  Output  : {output_dir}")
    if dry_run:
        print("  Mode    : DRY RUN (no LLM calls)")
    print(f"{'=' * 64}\n")

    for task in gen_tasks:
        prefix        = f"[{task.order + 1:02d}/{total}]"
        system_prompt = SYSTEM_PROMPTS[task.file_type]
        user_message  = build_user_message(task)

        print(f"{prefix} {task.path}")
        print(f"         type={task.file_type}  sys={len(system_prompt)}c  usr={len(user_message)}c")

        if dry_run:
            results[task.path] = 'dry_run'
            print(f"         {_STATUS['dry_run']}\n")
            continue

        try:
            # ── Attempt 1 ──────────────────────────────────────────────
            raw   = call_llm(system_prompt, user_message, model, base_url)
            code  = extract_code(raw)

            if validate(code, task):
                write_file(output_dir, task.path, code)
                results[task.path] = 'ok'
                print(f"         {_STATUS['ok']}  ({len(code)} chars)\n")
                continue

            # ── Attempt 2 (retry with issue description) ───────────────
            print(f"         [warn] validation failed — retrying...")
            retry_msg = build_retry_message(user_message, code, task)
            raw2      = call_llm(system_prompt, retry_msg, model, base_url)
            code2     = extract_code(raw2)

            if validate(code2, task):
                write_file(output_dir, task.path, code2)
                results[task.path] = 'retry_ok'
                print(f"         {_STATUS['retry_ok']}  ({len(code2)} chars)\n")
            else:
                # Save with a warning header so the developer can inspect
                warned = f"// AUTO-GENERATED — VALIDATION FAILED — REVIEW NEEDED\n{code2}"
                write_file(output_dir, task.path, warned)
                results[task.path] = 'failed'
                print(f"         {_STATUS['failed']}  (saved with warning header)\n")

        except requests.exceptions.ConnectionError:
            results[task.path] = 'connection_error'
            print(f"         {_STATUS['connection_error']}")
            print("         Cannot reach Ollama. Ensure `ollama serve` is running.\n")
            break   # no point continuing

        except requests.exceptions.HTTPError as exc:
            results[task.path] = f'http_error: {exc.response.status_code}'
            print(f"         [error] HTTP {exc.response.status_code}: {exc}\n")

        except Exception as exc:
            results[task.path] = f'error: {exc}'
            print(f"         [error] {exc}\n")

    # ── Summary ───────────────────────────────────────────────────────────
    ok    = sum(1 for v in results.values() if v in ('ok', 'retry_ok'))
    fail  = sum(1 for v in results.values() if v == 'failed')
    skip  = sum(1 for v in results.values() if v == 'dry_run')
    print(f"{'=' * 64}")
    print(f"  done: {ok} ok  |  {fail} failed  |  {skip} dry-run  |  {total} total")
    print(f"{'=' * 64}\n")

    return results
