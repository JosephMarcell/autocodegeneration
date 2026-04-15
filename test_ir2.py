"""Test IR1 -> IR2 transformation on files with advanced gateways."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "code", "study_case_carwash"))
from bpmn_ir1 import parse_bpmn
from ir1_ir2 import transform_ir1_to_ir2

BASE = os.path.dirname(__file__)

def test_ir2(label, bpmn_path):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    with open(bpmn_path, encoding="utf-8") as f:
        ir1 = parse_bpmn(f.read())

    try:
        ir2 = transform_ir1_to_ir2(ir1)
    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback
        traceback.print_exc()
        return None

    print(f"project       : {ir2.get('project')}")
    schema = ir2.get('sharedContext', {}).get('stateSchema', {})
    print(f"stateSchema   : {len(schema)} keys")
    for part in ir2.get("participants", []):
        print(f"\n  Participant: {part['name']} (role={part['role']})")
        print(f"  defaultRoute: {part.get('defaultRoute')}")
        for t in part.get("tasks", []):
            ptype = t.get("pageType", "?")
            conds = t.get("conditionalRoutes", [])
            wc = t.get("waitCondition")
            nxt = t.get("nextRoute", "?")
            cond_str = ""
            if conds:
                cond_str = f"  COND={[c.get('condition','') + '->' + c.get('targetRoute','') for c in conds]}"
            wc_str = f"  WAIT={wc['field']}" if wc else ""
            print(f"    - {t['name'][:30]:30s}  type={ptype:20s}  next={nxt}{wc_str}{cond_str}")
    return ir2


# 1) Car-Wash - baseline regression test
test_ir2("Car-Wash (ProcessMind)", os.path.join(BASE, "dataset/BPMN_ProcessMind/Car-Wash.bpmn"))

# 2) Dispatch-of-goods - parallel + inclusive gateways
test_ir2("Dispatch-of-goods (Camunda)", os.path.join(BASE, "dataset/BPMN_Camunda/Dispatch-of-goods.bpmn"))

# 3) Recourse - eventBasedGateway
test_ir2("Recourse (Camunda)", os.path.join(BASE, "dataset/BPMN_Camunda/recourse.bpmn"))

# 4) Pizza-Store - parallel + eventBased + multi-participant
test_ir2("Pizza-Store (ProcessMind)", os.path.join(BASE, "dataset/BPMN_ProcessMind/Pizza-Store.bpmn"))

print("\n\nAll IR2 tests completed!")
