"""
Car-Wash Study Case Pipeline — Entry Point
==========================================
Orchestrates: BPMN → IR1 → IR2 → LLM → React source files

Usage examples:
  python main.py                        Full pipeline (generate app)
  python main.py --dry-run              Build prompts, skip LLM calls
  python main.py --save-ir              Also write ir1_carwash.json + ir2_carwash.json
  python main.py --step ir1             Parse BPMN → IR1 only, then stop
  python main.py --step ir2             Parse BPMN → IR1 → IR2, then stop
  python main.py --ir2 ir2_carwash.json Skip steps 1-2, use existing IR2
  python main.py --output ./out --model qwen2.5-coder:7b
"""

import argparse
import json
import os
import sys

# Ensure this directory is on the path so sibling modules import correctly
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from bpmn_ir1 import parse_bpmn
from ir1_ir2  import transform_ir1_to_ir2
from generator import generate_all

# ── Default paths ─────────────────────────────────────────────────────────────
_REPO = os.path.abspath(os.path.join(_HERE, '..', '..'))

DEFAULT_BPMN   = os.path.join(_REPO, 'dataset', 'BPMN_ProcessMind', 'Car-Wash.bpmn')
DEFAULT_OUTPUT = os.path.join(_REPO, 'generated_app', 'CarWashApp')
DEFAULT_MODEL  = 'qwen2.5-coder:7b'
DEFAULT_OLLAMA = 'http://localhost:11434'


# ── Step 1: BPMN → IR1 ───────────────────────────────────────────────────────

def step_parse(bpmn_path: str) -> dict:
    print(f"\n[Step 1] Parsing BPMN  →  IR1")
    print(f"  file : {bpmn_path}")

    with open(bpmn_path, 'r', encoding='utf-8') as fh:
        xml = fh.read()

    ir1 = parse_bpmn(xml)

    print(f"  participants  : {[p['name'] for p in ir1['participants']]}")
    print(f"  tasks         : {len(ir1['tasks'])}")
    print(f"  gateways      : {len(ir1['gateways'])}")
    print(f"  sequenceFlows : {len(ir1['sequenceFlows'])}")
    print(f"  messageFlows  : {len(ir1['messageFlows'])}")
    print(f"  stateSchema   : {list(ir1['stateSchema'].keys())}")
    return ir1


def save_ir1(ir1: dict, out_dir: str):
    path = os.path.join(out_dir, 'ir1_carwash.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(ir1, fh, indent=2)
    print(f"  IR1 saved → {path}")


# ── Step 2: IR1 → IR2 ────────────────────────────────────────────────────────

def step_transform(ir1: dict) -> dict:
    print(f"\n[Step 2] Transforming IR1  →  IR2")

    ir2 = transform_ir1_to_ir2(ir1, project_name='CarWashApp')

    print(f"  project    : {ir2['project']}")
    print(f"  roles      : {[r['display'] for r in ir2['sharedContext']['roles']]}")
    print(f"  routes     : {len(ir2['sharedContext']['allRoutes'])}")
    print(f"  stateSchema: {list(ir2['sharedContext']['stateSchema'].keys())}")

    for p in ir2['participants']:
        task_names = [t['component'] for t in p['tasks']]
        types      = [t['pageType']  for t in p['tasks']]
        print(f"\n  Participant: {p['name']}  (defaultRoute={p['defaultRoute']})")
        for tname, ttype in zip(task_names, types):
            print(f"    • {tname}  [{ttype}]")

    return ir2


def save_ir2(ir2: dict, out_dir: str):
    path = os.path.join(out_dir, 'ir2_carwash.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(ir2, fh, indent=2)
    print(f"\n  IR2 saved → {path}")


# ── Step 3: IR2 → Files ───────────────────────────────────────────────────────

def step_generate(ir2: dict, output_dir: str, model: str, base_url: str, dry_run: bool):
    print(f"\n[Step 3] Generating React source files")
    os.makedirs(output_dir, exist_ok=True)

    results = generate_all(
        ir2        = ir2,
        output_dir = output_dir,
        model      = model,
        base_url   = base_url,
        dry_run    = dry_run,
    )

    failed = [p for p, s in results.items() if s == 'failed']
    if failed:
        print("Files that failed validation (saved with warning header):")
        for f in failed:
            print(f"  {f}")

    if not dry_run:
        print(f"\nGenerated app location: {output_dir}")
        print("Next step: scaffold a Vite React-TS project there and merge the src/ files.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Car-Wash BPMN → IR1 → IR2 → React (Ollama pipeline)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--bpmn', metavar='FILE', default=DEFAULT_BPMN,
        help=f'Path to BPMN file (default: dataset/BPMN_ProcessMind/Car-Wash.bpmn)',
    )
    parser.add_argument(
        '--ir2', metavar='FILE',
        help='Skip Steps 1-2 and load IR2 from this JSON file',
    )
    parser.add_argument(
        '--output', metavar='DIR', default=DEFAULT_OUTPUT,
        help=f'Output directory for generated app (default: generated_app/CarWashApp)',
    )
    parser.add_argument(
        '--model', metavar='NAME', default=DEFAULT_MODEL,
        help=f'Ollama model name (default: {DEFAULT_MODEL})',
    )
    parser.add_argument(
        '--ollama', metavar='URL', default=DEFAULT_OLLAMA,
        help=f'Ollama base URL (default: {DEFAULT_OLLAMA})',
    )
    parser.add_argument(
        '--step', choices=['ir1', 'ir2', 'generate', 'all'], default='all',
        help='Stop after this step (default: all)',
    )
    parser.add_argument(
        '--save-ir', action='store_true',
        help='Write ir1_carwash.json and ir2_carwash.json alongside this script',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Build prompts but skip LLM calls (for inspection / CI)',
    )
    args = parser.parse_args()

    print("=" * 64)
    print(" Car-Wash BPMN → React Pipeline (Study Case)")
    print("=" * 64)

    # ── Load or build IR2 ──────────────────────────────────────────────────
    if args.ir2:
        print(f"\n[Skip Steps 1-2] Loading IR2 from: {args.ir2}")
        with open(args.ir2, 'r', encoding='utf-8') as fh:
            ir2 = json.load(fh)
    else:
        ir1 = step_parse(args.bpmn)
        if args.save_ir:
            save_ir1(ir1, _HERE)
        if args.step == 'ir1':
            print("\nDone (step=ir1).")
            return

        ir2 = step_transform(ir1)
        if args.save_ir:
            save_ir2(ir2, _HERE)
        if args.step == 'ir2':
            print("\nDone (step=ir2).")
            return

    # ── Generate ───────────────────────────────────────────────────────────
    step_generate(ir2, args.output, args.model, args.ollama, args.dry_run)


if __name__ == '__main__':
    main()
