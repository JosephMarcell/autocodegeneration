import xml.etree.ElementTree as ET
tree = ET.parse("dataset/BPMN_ITS/1.Employee cooperative (main).User management/Diagram 2.bpmn")
root = tree.getroot()
ns = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"

for elem in root.iter():
    tag = elem.tag.replace(ns, "")
    if "lane" in tag.lower() or "flowNodeRef" in tag:
        name = elem.get("name", "")
        eid = elem.get("id", "")
        print(f"TAG: {tag}  name={name}  id={eid}")
        for child in elem:
            ctag = child.tag.replace(ns, "")
            print(f"  CHILD: {ctag}  text={child.text}  id={child.get('id','')}")
            for gc in child:
                gctag = gc.tag.replace(ns, "")
                print(f"    GC: {gctag}  text={gc.text}  id={gc.get('id','')}")
                for ggc in gc:
                    ggctag = ggc.tag.replace(ns, "")
                    print(f"      GGC: {ggctag}  text={ggc.text}  id={ggc.get('id','')}")
