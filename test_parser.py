"""Quick test of the updated BPMN parser on all 3 sources."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "code", "study_case_carwash"))
from bpmn_ir1 import parse_bpmn

def test_file(label, path):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    with open(path, encoding="utf-8") as f:
        ir1 = parse_bpmn(f.read())

    print(f"Participants : {[p['name'] for p in ir1['participants']]}")
    print(f"Lanes        : {[(l['name'], len(l['flowNodeRefs'])) for l in ir1['lanes']]}")
    print(f"Tasks ({len(ir1['tasks'])})")
    for t in ir1["tasks"][:5]:
        print(f"  - {t['name'][:40]:40s}  lane={t.get('laneName','?')}")
    print(f"Gateways ({len(ir1['gateways'])})")
    for g in ir1["gateways"]:
        print(f"  - {g['name'][:35]:35s}  type={g['gatewayType']:20s}  dir={g['gatewayDirection']}  lane={g.get('laneName','?')}")
    print(f"Events ({len(ir1['events'])})")
    for e in ir1["events"]:
        print(f"  - {e['name'][:35]:35s}  type={e['eventType']:20s}  def={e.get('eventDefinitionType','?')}")
    print(f"SeqFlows     : {len(ir1['sequenceFlows'])}")
    print(f"MsgFlows     : {len(ir1['messageFlows'])}")
    print(f"node_to_lane : {len(ir1.get('node_to_lane',{}))}")
    return ir1

BASE = os.path.dirname(__file__)

# 1) ProcessMind - Car-Wash (no lanes, simple)
test_file("Car-Wash (ProcessMind)", os.path.join(BASE, "dataset/BPMN_ProcessMind/Car-Wash.bpmn"))

# 2) ITS - User Management (Bizagi, bare namespace, lanes)
test_file("ITS - User Management", os.path.join(BASE, "dataset/BPMN_ITS/1.Employee cooperative (main).User management/Diagram 2.bpmn"))

# 3) Camunda - Dispatch-of-goods (lanes, inclusive + parallel gateways)
test_file("Dispatch-of-goods (Camunda)", os.path.join(BASE, "dataset/BPMN_Camunda/Dispatch-of-goods.bpmn"))

# 4) Camunda - recourse (eventBasedGateway, timer/message events)
test_file("Recourse (Camunda)", os.path.join(BASE, "dataset/BPMN_Camunda/recourse.bpmn"))

# 5) ProcessMind - Pizza-Store (full: eventBased + parallel + timer + terminate + lanes)
test_file("Pizza-Store (ProcessMind)", os.path.join(BASE, "dataset/BPMN_ProcessMind/Pizza-Store.bpmn"))

# 6) Camunda - self-service-restaurant
test_file("Self-Service-Restaurant (Camunda)", os.path.join(BASE, "dataset/BPMN_Camunda/self-service-restaurant.bpmn"))

print("\n\nAll tests completed!")
