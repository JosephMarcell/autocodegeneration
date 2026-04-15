import sys, os
sys.path.insert(0, "code/study_case_carwash")
from bpmn_ir1 import parse_bpmn

with open("dataset/BPMN_ProcessMind/Pizza-Store.bpmn", encoding="utf-8") as f:
    ir1 = parse_bpmn(f.read())

for gw in ir1["gateways"]:
    if gw["gatewayType"] == "eventBased":
        print("eventBasedGateway:", gw["id"], repr(gw["name"]))
        print("  incoming:", gw["incoming"])
        print("  outgoing:", gw["outgoing"])
        # What flows INTO the gateway
        for sf in ir1["sequenceFlows"]:
            if sf["target"] == gw["id"]:
                src_id = sf["source"]
                src_name = "?"
                for t in ir1["tasks"]:
                    if t["id"] == src_id:
                        src_name = f"task:{t['name']}"
                for e in ir1["events"]:
                    if e["id"] == src_id:
                        src_name = f"event:{e['name']}({e['eventType']})"
                print(f"  <- {src_name} (id={src_id})")
        # Where outgoing flows go
        for sf in ir1["sequenceFlows"]:
            if sf["source"] == gw["id"]:
                tgt_id = sf["target"]
                for e in ir1["events"]:
                    if e["id"] == tgt_id:
                        print(f"  -> event:{e['name']}({e['eventType']})")
                        for sf2 in ir1["sequenceFlows"]:
                            if sf2["source"] == e["id"]:
                                for t in ir1["tasks"]:
                                    if t["id"] == sf2["target"]:
                                        print(f"     -> task:{t['name']}")

# Also check OrderAPizza outgoing
print("\n--- OrderAPizza flow ---")
for t in ir1["tasks"]:
    if t["name"] == "Order a pizza":
        print(f"task id={t['id']}  outgoing={t['outgoing']}")
        for out_id in t["outgoing"]:
            for sf in ir1["sequenceFlows"]:
                if sf["id"] == out_id:
                    print(f"  sf -> target={sf['target']}")
                    for gw in ir1["gateways"]:
                        if gw["id"] == sf["target"]:
                            print(f"  -> gateway: {gw['gatewayType']} {gw['gatewayDirection']}")
                    for e in ir1["events"]:
                        if e["id"] == sf["target"]:
                            print(f"  -> event: {e['name']}({e['eventType']})")
