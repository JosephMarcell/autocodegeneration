"""
BPMN XML → IR1 Parser
=====================
Parses a BPMN collaboration XML into a structured IR1 dict containing:
  - participants (pools)
  - tasks, gateways, events
  - sequenceFlows, messageFlows
  - stateSchema (auto-derived from task + gateway names)
"""

import xml.etree.ElementTree as ET
import re

# ── Namespace ────────────────────────────────────────────────────────────────
# Works for both bpmn: and bpmn2: prefixes since we match by URI
NS = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
NS_DI = '{http://www.omg.org/spec/BPMN/20100524/DI}'
NS_DC = '{http://www.omg.org/spec/DD/20100524/DC}'

TASK_TYPES = [
    'userTask', 'serviceTask', 'task', 'sendTask',
    'receiveTask', 'manualTask', 'businessRuleTask', 'scriptTask',
]
GW_TYPES = [
    'exclusiveGateway', 'parallelGateway', 'inclusiveGateway',
    'complexGateway', 'eventBasedGateway',
]
EVENT_TYPES = [
    'startEvent', 'endEvent', 'intermediateCatchEvent',
    'intermediateThrowEvent', 'boundaryEvent',
]
EVENT_DEF_TYPES = [
    'messageEventDefinition', 'timerEventDefinition',
    'conditionalEventDefinition', 'terminateEventDefinition',
    'signalEventDefinition', 'errorEventDefinition',
    'escalationEventDefinition', 'compensateEventDefinition',
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _find_direct(parent, tag):
    """Find direct-child elements by BPMN tag name."""
    result = parent.findall(f'bpmn:{tag}', NS)
    if not result:
        # Fallback: bare tag (for files without namespace declaration)
        result = parent.findall(tag)
    return result


def _clean_state_key(raw: str) -> str:
    """Convert raw task/gateway name to a snake_case state key fragment."""
    cleaned = re.sub(r'\s+', ' ', raw.strip())
    key = re.sub(r'[^a-zA-Z0-9]', '_', cleaned).lower().strip('_')
    return re.sub(r'_+', '_', key)


# ── Main parser ───────────────────────────────────────────────────────────────

def parse_bpmn(xml_string: str) -> dict:
    """
    Parse BPMN XML string into IR1.

    Returns a dict with keys:
      project_name, participants, proc_to_participant,
      tasks, gateways, events, sequenceFlows, messageFlows, stateSchema
    """
    root = ET.fromstring(xml_string)

    ir1 = {
        "project_name": "",
        "participants": [],           # [{id, name, processRef}]
        "proc_to_participant": {},    # processId → participantName
        "lanes": [],                  # [{id, name, processId, flowNodeRefs}]
        "node_to_lane": {},           # nodeId → laneName
        "tasks": [],
        "gateways": [],
        "events": [],
        "sequenceFlows": [],
        "messageFlows": [],
        "stateSchema": {},
    }

    # ── 1. Collaboration & Participants ──────────────────────────────────────
    collab = root.find('.//bpmn:collaboration', NS)
    if collab is None:
        collab = root.find('.//collaboration')

    if collab is not None:
        ir1["project_name"] = collab.get('name', '')
        for p in _find_direct(collab, 'participant'):
            part = {
                "id":         p.get('id', ''),
                "name":       p.get('name', '').strip(),
                "processRef": p.get('processRef', ''),
            }
            ir1["participants"].append(part)
            if part["processRef"]:
                ir1["proc_to_participant"][part["processRef"]] = part["name"]

    # ── 2. Processes ─────────────────────────────────────────────────────────
    processes = root.findall('.//bpmn:process', NS)
    if not processes:
        processes = root.findall('.//process')
    if not processes:
        return ir1

    if not ir1["project_name"]:
        ir1["project_name"] = processes[0].get('name', 'App')

    for proc in processes:
        proc_id          = proc.get('id', '')
        participant_name = ir1["proc_to_participant"].get(proc_id, proc.get('name', ''))

        # Lanes (Priority 1 Patch)
        for lane_set in _find_direct(proc, 'laneSet'):
            for lane in _find_direct(lane_set, 'lane'):
                lane_name = lane.get('name', '').strip()
                refs = [ref.text.strip() for ref in _find_direct(lane, 'flowNodeRef') if ref.text]
                ir1["lanes"].append({
                    "id":           lane.get('id', ''),
                    "name":         lane_name,
                    "processId":    proc_id,
                    "flowNodeRefs": refs,
                })
                for node_id in refs:
                    ir1["node_to_lane"][node_id] = lane_name

        # Fallback: if no participant, use lane as participantName
        if not ir1["participants"] and ir1["lanes"]:
            for lane in ir1["lanes"]:
                ir1["proc_to_participant"][lane["processId"]] = lane["name"]

        # Tasks
        for ttype in TASK_TYPES:
            for elem in _find_direct(proc, ttype):
                eid = elem.get('id', '')
                ir1["tasks"].append({
                    "id":              eid,
                    "name":            elem.get('name', '').strip(),
                    "type":            ttype,
                    "participantName": participant_name,
                    "laneName":        ir1["node_to_lane"].get(eid, ''),
                    "processId":       proc_id,
                    "asyncFlag":       ttype in ('serviceTask', 'sendTask', 'receiveTask'),
                    "incoming":  [i.text.strip() for i in _find_direct(elem, 'incoming')  if i.text],
                    "outgoing":  [o.text.strip() for o in _find_direct(elem, 'outgoing')  if o.text],
                })

        # Events (Priority 2 Patch: event subtype extraction)
        for etype in EVENT_TYPES:
            for elem in _find_direct(proc, etype):
                eid = elem.get('id', '')
                # Detect event definition sub-type (multiple possible)
                evt_def_types = []
                for edt in EVENT_DEF_TYPES:
                    if _find_direct(elem, edt):
                        evt_def_types.append(edt)
                ir1["events"].append({
                    "id":                  eid,
                    "name":                elem.get('name', '').strip(),
                    "eventType":           etype,
                    "eventDefinitionType": evt_def_types if evt_def_types else '',
                    "participantName":     participant_name,
                    "laneName":            ir1["node_to_lane"].get(eid, ''),
                    "processId":           proc_id,
                    "incoming":  [i.text.strip() for i in _find_direct(elem, 'incoming')  if i.text],
                    "outgoing":  [o.text.strip() for o in _find_direct(elem, 'outgoing')  if o.text],
                })

        # Gateways — infer direction when attribute is absent
        for gtype in GW_TYPES:
            for elem in _find_direct(proc, gtype):
                eid      = elem.get('id', '')
                incoming = [i.text.strip() for i in _find_direct(elem, 'incoming') if i.text]
                outgoing = [o.text.strip() for o in _find_direct(elem, 'outgoing') if o.text]
                direction = elem.get('gatewayDirection', '')
                if not direction:
                    # eventBasedGateway is always diverging by BPMN spec
                    if gtype == 'eventBasedGateway':
                        direction = 'Diverging'
                    elif len(outgoing) > len(incoming):
                        direction = 'Diverging'
                    elif len(incoming) > len(outgoing):
                        direction = 'Converging'
                ir1["gateways"].append({
                    "id":               eid,
                    "name":             elem.get('name', '').strip(),
                    "gatewayType":      gtype.replace('Gateway', ''),
                    "gatewayDirection": direction,
                    "participantName":  participant_name,
                    "laneName":         ir1["node_to_lane"].get(eid, ''),
                    "processId":        proc_id,
                    "incoming":         incoming,
                    "outgoing":         outgoing,
                })

        # Sequence flows
        for flow in _find_direct(proc, 'sequenceFlow'):
            cond = re.sub(r'\s+', ' ', flow.get('name', '').strip())
            ir1["sequenceFlows"].append({
                "id":        flow.get('id', ''),
                "source":    flow.get('sourceRef', ''),
                "target":    flow.get('targetRef', ''),
                "condition": cond,
                "processId": proc_id,
            })

    # ── 2b. Geometric lane inference (Bizagi fallback) ────────────────────────
    # If lanes exist but no flowNodeRefs were found, infer from BPMNShape bounds
    if ir1["lanes"] and not ir1["node_to_lane"]:
        lane_ids = {l["id"] for l in ir1["lanes"]}
        lane_bounds = {}   # laneId -> (x, y, w, h)
        node_bounds = {}   # nodeId -> (cx, cy)  center point
        all_node_ids = (
            {t["id"] for t in ir1["tasks"]} |
            {e["id"] for e in ir1["events"]} |
            {g["id"] for g in ir1["gateways"]}
        )
        for shape in root.iter(f"{NS_DI}BPMNShape"):
            ref = shape.get("bpmnElement", "")
            bounds = shape.find(f"{NS_DC}Bounds")
            if bounds is None:
                continue
            x = float(bounds.get("x", 0))
            y = float(bounds.get("y", 0))
            w = float(bounds.get("width", 0))
            h = float(bounds.get("height", 0))
            if ref in lane_ids:
                lane_bounds[ref] = (x, y, w, h)
            elif ref in all_node_ids:
                node_bounds[ref] = (x + w / 2, y + h / 2)
        # Match each node center to a containing lane
        for nid, (cx, cy) in node_bounds.items():
            for lane_rec in ir1["lanes"]:
                lid = lane_rec["id"]
                if lid not in lane_bounds:
                    continue
                lx, ly, lw, lh = lane_bounds[lid]
                if lx <= cx <= lx + lw and ly <= cy <= ly + lh:
                    ir1["node_to_lane"][nid] = lane_rec["name"]
                    lane_rec["flowNodeRefs"].append(nid)
                    break
        # Back-fill laneName on already-collected elements
        for collection in (ir1["tasks"], ir1["events"], ir1["gateways"]):
            for item in collection:
                if not item["laneName"]:
                    item["laneName"] = ir1["node_to_lane"].get(item["id"], "")

    # ── 3. Message flows ─────────────────────────────────────────────────────
    if collab is not None:
        for mf in _find_direct(collab, 'messageFlow'):
            ir1["messageFlows"].append({
                "id":        mf.get('id', ''),
                "sourceRef": mf.get('sourceRef', ''),
                "targetRef": mf.get('targetRef', ''),
                "name":      mf.get('name', ''),
            })

    # ── 4. Auto-derive stateSchema ───────────────────────────────────────────
    # Boolean _completed flag for every task
    for task in ir1["tasks"]:
        k = _clean_state_key(task["name"])
        if k:
            ir1["stateSchema"][f"{k}_completed"] = False

    # String _result field for every diverging gateway
    for gw in ir1["gateways"]:
        if gw["gatewayDirection"] == "Diverging" and gw["name"]:
            k = _clean_state_key(gw["name"])
            if k:
                ir1["stateSchema"][f"{k}_result"] = ""

    return ir1
