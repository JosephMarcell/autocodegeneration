import xml.etree.ElementTree as ET

tree = ET.parse("dataset/BPMN_ITS/1.Employee cooperative (main).User management/Diagram 2.bpmn")
root = tree.getroot()

# Collect all namespace URIs used
ns_model = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
ns_di = "{http://www.omg.org/spec/BPMN/20100524/DI}"
ns_dc = "{http://www.omg.org/spec/DD/20100524/DC}"

# Get lane IDs and names
lanes = {}
for elem in root.iter():
    tag = elem.tag.replace(ns_model, "")
    if tag == "lane":
        lid = elem.get("id", "")
        lname = elem.get("name", "")
        lanes[lid] = lname
        print(f"LANE: id={lid}  name={lname}")

print()

# Get BPMNShape bounds for lanes and tasks
shapes = {}
for shape in root.iter(f"{ns_di}BPMNShape"):
    ref = shape.get("bpmnElement", "")
    bounds = shape.find(f"{ns_dc}Bounds")
    if bounds is not None:
        x = float(bounds.get("x", 0))
        y = float(bounds.get("y", 0))
        w = float(bounds.get("width", 0))
        h = float(bounds.get("height", 0))
        is_lane = ref in lanes
        label = f"LANE:{lanes[ref]}" if is_lane else ref[:40]
        shapes[ref] = {"x": x, "y": y, "w": w, "h": h, "is_lane": is_lane}
        if is_lane:
            print(f"LANE SHAPE: {label:30s}  x={x:7.1f} y={y:7.1f} w={w:7.1f} h={h:7.1f}")

print()

# Get task/gateway/event IDs and names
nodes = {}
for elem in root.iter():
    tag = elem.tag.replace(ns_model, "")
    if tag in ("task", "userTask", "serviceTask", "sendTask", "receiveTask", "manualTask",
               "businessRuleTask", "scriptTask", "exclusiveGateway", "parallelGateway",
               "inclusiveGateway", "eventBasedGateway", "startEvent", "endEvent",
               "intermediateCatchEvent", "intermediateThrowEvent"):
        nid = elem.get("id", "")
        nname = elem.get("name", "")
        nodes[nid] = {"name": nname, "type": tag}

# Match nodes to lanes via bounding box containment
for nid, ninfo in nodes.items():
    if nid in shapes:
        ns = shapes[nid]
        nx, ny = ns["x"] + ns["w"]/2, ns["y"] + ns["h"]/2  # center point
        matched_lane = None
        for lid, lname in lanes.items():
            if lid in shapes:
                ls = shapes[lid]
                if (ls["x"] <= nx <= ls["x"] + ls["w"] and
                    ls["y"] <= ny <= ls["y"] + ls["h"]):
                    matched_lane = lname
                    break
        print(f"NODE: {ninfo['name'][:35]:35s} ({ninfo['type']:20s})  ->  lane={matched_lane}")
    else:
        print(f"NODE: {ninfo['name'][:35]:35s} ({ninfo['type']:20s})  ->  NO SHAPE")
