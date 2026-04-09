"""
BPMN to React.js Transformation Engine  (v4)
=============================================
Step 1: BPMN XML  →  IR1  (Intermediate Representation — parsed workflow graph)
Step 2: IR1       →  IR2  (Structured per-task prompt manifest for LLM)
Step 3: IR2       →  output.json  (LLM-generated React/TypeScript files)

Usage:
    # Full pipeline (requires ANTHROPIC_API_KEY env var)
    python bpmn_to_react2.py <bpmn_file> [output_dir]

    # Steps 1+2 only (no API call)
    python bpmn_to_react2.py <bpmn_file> [output_dir] --no-llm

    # Fine-tuning pair export
    python bpmn_to_react2.py <bpmn_file> [output_dir] --export-ft

Changelog v4:
  - IR1: infer gatewayDirection from in/out degree when attribute absent
  - IR1: populate controlHint (split/join) from inferred direction
  - IR2: fix follow() — traverse intermediateCatchEvent / intermediateThrowEvent
  - IR2: add allowedRoles back to page descriptors
  - IR2: add waitingFor hint when page leads through intermediate event
  - Step 3: LLM generation via Anthropic API with strict validation
  - Step 3: auto-fix common LLM errors (path mismatch, missing files)
  - Output: to_finetune_pair() for JSONL dataset export
  - Prompt: build_llm_prompt() rewritten with structured IR2 format —
      5-category file_types taxonomy, explicit forbidden list,
      output_example block, and slim user_message for u22646K token budget
      (optimised for Qwen2.5-Coder-7B-Instruct local inference)
"""

import xml.etree.ElementTree as ET
import json
import os
import sys
import re
import urllib.request
import urllib.error


# ============================================================================
# STEP 1: BPMN XML → IR1
# ============================================================================

def parse_bpmn_to_json(bpmn_xml_string: str) -> dict:
    """
    Parse BPMN XML into IR1.

    v3 fixes:
    - Infer gatewayDirection (Diverging/Converging) from flow degree
      when the attribute is missing or empty in the XML.
    - Populate controlHint accordingly.
    """

    ns = {
        'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
        'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
        'dc':    'http://www.omg.org/spec/DD/20100524/DC',
        'di':    'http://www.omg.org/spec/DD/20100524/DI',
    }
    for prefix, uri in ns.items():
        ET.register_namespace(prefix, uri)

    root = ET.fromstring(bpmn_xml_string)

    # Detect default namespace
    default_ns = ''
    if root.tag.startswith('{'):
        default_ns = root.tag.split('}')[0] + '}'

    def find_all(parent, tag):
        r = parent.findall(f'.//bpmn:{tag}', ns)
        if not r and default_ns:
            r = parent.findall(f'.//{default_ns}{tag}')
        if not r:
            r = parent.findall(f'.//{tag}')
        return r

    def find_one(parent, tag):
        r = find_all(parent, tag)
        return r[0] if r else None

    def find_direct(parent, tag):
        r = parent.findall(f'bpmn:{tag}', ns)
        if not r and default_ns:
            r = parent.findall(f'{default_ns}{tag}')
        if not r:
            r = parent.findall(tag)
        return r

    result = {
        "process":       {"id": "", "name": "", "type": "", "participants": []},
        "roles":         [],
        "tasks":         [],
        "events":        [],
        "gateways":      [],
        "sequenceFlows": [],
        "messageFlows":  [],
        "stateSchema":   {},
    }

    # ── 1. Collaboration / participants ───────────────────────────────────────
    collaboration = find_one(root, 'collaboration')
    proc_to_participant: dict = {}

    if collaboration is not None:
        collab_name = collaboration.get('name', '')
        for participant in find_direct(collaboration, 'participant'):
            part = {
                "id":         participant.get('id', ''),
                "name":       participant.get('name', ''),
                "processRef": participant.get('processRef', ''),
            }
            result['process']['participants'].append(part)
            if part['processRef']:
                proc_to_participant[part['processRef']] = {
                    "id":   part['id'],
                    "name": part['name'],
                }
        if collab_name:
            result['process']['name'] = collab_name

    # ── 2. All processes ──────────────────────────────────────────────────────
    all_processes = find_all(root, 'process')
    if not all_processes:
        print("[WARN] No processes found in BPMN")
        return result

    primary = all_processes[0]
    result['process']['id']   = primary.get('id', '')
    result['process']['name'] = result['process']['name'] or primary.get('name', '')
    result['process']['type'] = 'collaboration' if collaboration is not None else 'process'

    TASK_INTERACTION_HINTS = {
        'userTask':         'form',
        'serviceTask':      'api-call',
        'sendTask':         'send',
        'receiveTask':      'receive',
        'manualTask':       'manual',
        'businessRuleTask': 'decision',
        'scriptTask':       'script',
        'task':             'action',
    }
    EVENT_TRIGGER_MAP = {
        'messageEventDefinition':    'message',
        'timerEventDefinition':      'timer',
        'signalEventDefinition':     'signal',
        'errorEventDefinition':      'error',
        'escalationEventDefinition': 'escalation',
        'compensateEventDefinition': 'compensation',
        'conditionalEventDefinition':'conditional',
        'linkEventDefinition':       'link',
        'terminateEventDefinition':  'terminate',
        'cancelEventDefinition':     'cancel',
    }

    lane_member_to_role: dict = {}

    for proc in all_processes:
        proc_id          = proc.get('id', '')
        participant_info = proc_to_participant.get(proc_id, {"id": "", "name": ""})
        participant_name = participant_info.get("name", "")
        participant_id   = participant_info.get("id",   "")

        # Lane assignments (fine-grained role)
        for lane_set in find_direct(proc, 'laneSet'):
            for lane in find_direct(lane_set, 'lane'):
                lane_name = lane.get('name', '')
                if lane_name:
                    for ref in find_direct(lane, 'flowNodeRef'):
                        if ref.text:
                            lane_member_to_role[ref.text.strip()] = lane_name

        # Tasks
        task_types = ['userTask', 'serviceTask', 'task', 'sendTask',
                      'receiveTask', 'manualTask', 'businessRuleTask', 'scriptTask']
        for ttype in task_types:
            for elem in find_direct(proc, ttype):
                eid  = elem.get('id', '')
                role = lane_member_to_role.get(eid, participant_name)
                result['tasks'].append({
                    "id":              eid,
                    "name":            elem.get('name', ''),
                    "type":            ttype,
                    "role":            role,
                    "participantId":   participant_id,
                    "processId":       proc_id,
                    "interactionHint": TASK_INTERACTION_HINTS.get(ttype, ''),
                    "stateModel":      [],
                    "asyncFlag":       ttype in ('serviceTask', 'sendTask', 'receiveTask'),
                    "incoming": [i.text.strip() for i in find_direct(elem, 'incoming') if i.text],
                    "outgoing": [o.text.strip() for o in find_direct(elem, 'outgoing') if o.text],
                })

        # Events
        event_types = ['startEvent', 'endEvent', 'intermediateCatchEvent',
                       'intermediateThrowEvent', 'boundaryEvent']
        for etype in event_types:
            for elem in find_direct(proc, etype):
                eid     = elem.get('id', '')
                trigger = ''
                for child in elem:
                    local = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if local in EVENT_TRIGGER_MAP:
                        trigger = EVENT_TRIGGER_MAP[local]
                        break
                role = lane_member_to_role.get(eid, participant_name)
                result['events'].append({
                    "id":            eid,
                    "name":          elem.get('name', ''),
                    "eventType":     etype,
                    "trigger":       trigger,
                    "role":          role,
                    "participantId": participant_id,
                    "processId":     proc_id,
                    "incoming": [i.text.strip() for i in find_direct(elem, 'incoming') if i.text],
                    "outgoing": [o.text.strip() for o in find_direct(elem, 'outgoing') if o.text],
                })

        # Gateways — NOTE: gatewayDirection is often absent; we'll infer it below
        gw_types = ['exclusiveGateway', 'parallelGateway', 'inclusiveGateway',
                    'complexGateway', 'eventBasedGateway']
        for gtype in gw_types:
            for elem in find_direct(proc, gtype):
                eid  = elem.get('id', '')
                role = lane_member_to_role.get(eid, participant_name)
                incoming = [i.text.strip() for i in find_direct(elem, 'incoming') if i.text]
                outgoing = [o.text.strip() for o in find_direct(elem, 'outgoing') if o.text]
                direction    = elem.get('gatewayDirection', '')
                control_hint = ''
                if direction == 'Diverging':
                    control_hint = 'split'
                elif direction == 'Converging':
                    control_hint = 'join'
                result['gateways'].append({
                    "id":               eid,
                    "name":             elem.get('name', ''),
                    "gatewayType":      gtype.replace('Gateway', ''),
                    "gatewayDirection": direction,
                    "controlHint":      control_hint,
                    "role":             role,
                    "participantId":    participant_id,
                    "processId":        proc_id,
                    "incoming":         incoming,
                    "outgoing":         outgoing,
                })

        # Sequence flows — normalize newlines in condition labels
        for flow in find_direct(proc, 'sequenceFlow'):
            raw_cond = flow.get('name', '')
            clean_cond = re.sub(r'\s+', ' ', raw_cond.strip())
            result['sequenceFlows'].append({
                "id":        flow.get('id', ''),
                "source":    flow.get('sourceRef', ''),
                "target":    flow.get('targetRef', ''),
                "condition": clean_cond,
                "processId": proc_id,
            })

    # Message flows
    if collaboration is not None:
        for msg in find_direct(collaboration, 'messageFlow'):
            result['messageFlows'].append({
                "id":          msg.get('id', ''),
                "sourceRef":   msg.get('sourceRef', ''),
                "targetRef":   msg.get('targetRef', ''),
                "messageType": msg.get('name', ''),
            })

    # Roles from participants
    for part in result['process']['participants']:
        result['roles'].append({
            "id":          part['id'],
            "name":        part['name'],
            "participant": part['id'],
            "processRef":  part['processRef'],
        })

    # ── 3. Infer gatewayDirection where absent ────────────────────────────────
    # Rule: more outgoing than incoming → Diverging (split)
    #       more incoming than outgoing → Converging (join)
    for gw in result['gateways']:
        if not gw['gatewayDirection']:
            n_in  = len(gw['incoming'])
            n_out = len(gw['outgoing'])
            if n_out > n_in:
                gw['gatewayDirection'] = 'Diverging'
                gw['controlHint']      = 'split'
            elif n_in > n_out:
                gw['gatewayDirection'] = 'Converging'
                gw['controlHint']      = 'join'
            # n_in == n_out == 1: ambiguous; leave empty

    # ── 4. stateSchema from task names + gateway names ────────────────────────
    def _clean_state_key(raw: str) -> str:
        """Collapse whitespace/newlines then convert non-alnum to underscore."""
        cleaned = re.sub(r'\s+', ' ', raw.strip())
        key = re.sub(r'[^a-zA-Z0-9]', '_', cleaned).lower().strip('_')
        return re.sub(r'_+', '_', key)

    state_fields: dict = {}
    for task in result['tasks']:
        if task['name']:
            state_fields[f"{_clean_state_key(task['name'])}_completed"] = False
    for gw in result['gateways']:
        if gw['name']:
            state_fields[f"{_clean_state_key(gw['name'])}_result"] = ""
    result['stateSchema'] = state_fields

    return result


# ============================================================================
# STEP 2: IR1 → IR2
# ============================================================================

def create_react_prompt_json(ir1_data: dict, bpmn_file_path: str = None) -> dict:
    """
    Transform IR1 into IR2: structured per-task prompt manifest.

    v3 fixes:
    - follow() now traverses intermediateCatchEvent / intermediateThrowEvent
    - follow() skips Converging gateways to avoid duplicate exits
    - allowedRoles re-added to page descriptors
    - waitingFor field added when task passes through intermediate event
    - Stricter constraints for App.tsx and ProtectedRoute
    """

    # ── helpers ───────────────────────────────────────────────────────────────

    def sanitize(name: str) -> str:
        """Replace newlines/tabs with space and collapse whitespace. Used on all BPMN names."""
        return re.sub(r'\s+', ' ', name.replace('\n', ' ').replace('\t', ' ')).strip()

    def slugify(name: str) -> str:
        s = sanitize(name).lower()
        s = re.sub(r'[^a-z0-9\s-]', '', s)
        s = re.sub(r'[\s_]+', '-', s)
        return re.sub(r'-+', '-', s).strip('-')

    def pascal(name: str) -> str:
        return ''.join(w.capitalize()
                       for w in re.sub(r'[^a-zA-Z0-9\s]', '', sanitize(name)).split())

    def role_key(name: str) -> str:
        return re.sub(r'[^a-z0-9]', '', sanitize(name).lower())

    # ── project name ──────────────────────────────────────────────────────────

    if bpmn_file_path:
        base         = os.path.splitext(os.path.basename(bpmn_file_path))[0]
        project_name = ''.join(w.capitalize()
                                for w in re.split(r'[^a-zA-Z0-9]+', base) if w) + "App"
    else:
        raw          = ir1_data['process'].get('name') or ir1_data['process'].get('id') or "Workflow"
        project_name = re.sub(r'[^a-zA-Z0-9]', '', raw) + "App"

    # ── element lookup ────────────────────────────────────────────────────────

    all_elements: dict = {}
    for t in ir1_data.get('tasks',    []): all_elements[t['id']] = {**t, '_kind': 'task'}
    for e in ir1_data.get('events',   []): all_elements[e['id']] = {**e, '_kind': 'event'}
    for g in ir1_data.get('gateways', []): all_elements[g['id']] = {**g, '_kind': 'gateway'}

    flow_by_id: dict = {f['id']: f for f in ir1_data.get('sequenceFlows', [])}

    # ── process → participant map ─────────────────────────────────────────────

    proc_to_part: dict = {
        p['processRef']: p
        for p in ir1_data['process'].get('participants', [])
    }

    # ── group tasks by processId ──────────────────────────────────────────────

    tasks_by_proc: dict = {}
    for t in ir1_data.get('tasks', []):
        tasks_by_proc.setdefault(t.get('processId', ''), []).append(t)

    # ── BFS task ordering (following sequence flows from start event) ─────────

    def ordered_tasks_for(proc_id: str, tasks: list) -> list:
        proc_els = {eid: el for eid, el in all_elements.items()
                    if el.get('processId') == proc_id}
        adj: dict = {}
        for sf in ir1_data.get('sequenceFlows', []):
            if sf.get('processId') == proc_id:
                adj.setdefault(sf['source'], []).append(sf['target'])

        starts = [e['id'] for e in ir1_data.get('events', [])
                  if e.get('processId') == proc_id and e['eventType'] == 'startEvent']

        ordered, visited, queue = [], set(), list(starts)
        while queue:
            cur = queue.pop(0)
            if cur in visited:
                continue
            visited.add(cur)
            el = proc_els.get(cur)
            if el and el['_kind'] == 'task':
                ordered.append(cur)
            queue.extend(nxt for nxt in adj.get(cur, []) if nxt not in visited)

        task_map    = {t['id']: t for t in tasks}
        result      = [task_map[tid] for tid in ordered if tid in task_map]
        result     += [t for t in tasks if t['id'] not in {x['id'] for x in result}]
        return result

    # ── resolve next routes (gateway + intermediate event aware) ─────────────

    INTERMEDIATE_TYPES = {'intermediateCatchEvent', 'intermediateThrowEvent'}

    def resolve_next_routes(task: dict, role: str) -> tuple:
        """
        Returns (next_route: str, conditional_routes: list, parallel_triggers: list,
                 waiting_for: str|None).

        v3-fix:
        - Conditions are now chained across nested gateways: "no > If insurance necessary"
        - Each exit carries splitType: 'exclusive' | 'inclusive' | 'parallel'
        - Inclusive/parallel diverging branches are separated into parallel_triggers
          when they target a different lane (cross-lane concurrent execution).
        - default_route prefers same-lane unconditional branch, then 'always', then same-lane.
        """
        exits:       list = []
        waiting_for: str  = None
        visited_gw:  set  = set()

        def follow(element_id: str, condition: str = '',
                   depth: int = 0, split_type: str = 'exclusive'):
            nonlocal waiting_for
            if depth > 20:
                return
            el = all_elements.get(element_id)
            if not el:
                return

            kind = el['_kind']

            if kind == 'task':
                target_role = task_id_to_role.get(el['id'], role)
                exits.append({
                    'route':     f"/{target_role}/{slugify(sanitize(el.get('name', el['id'])))}",
                    'condition': condition,
                    'splitType': split_type,
                    'targetRole': target_role,
                })

            elif kind == 'event':
                etype = el.get('eventType', '')
                if etype == 'endEvent':
                    exits.append({
                        'route':     f"/{role}/complete",
                        'condition': condition,
                        'splitType': split_type,
                        'targetRole': role,
                    })
                elif etype in INTERMEDIATE_TYPES:
                    if not waiting_for and el.get('name'):
                        waiting_for = sanitize(el['name'])
                    for fid in el.get('outgoing', []):
                        fl = flow_by_id.get(fid)
                        if fl:
                            follow(fl['target'], condition, depth + 1, split_type)

            elif kind == 'gateway':
                gw_id = el['id']
                if gw_id in visited_gw:
                    return
                visited_gw.add(gw_id)
                ctrl      = el.get('controlHint', '')
                direction = el.get('gatewayDirection', '')
                gw_type   = el.get('gatewayType', 'exclusive')  # inclusive, parallel, exclusive…

                if ctrl == 'join' or direction == 'Converging':
                    # Pass-through converging gateway — follow its single outgoing
                    for fid in el.get('outgoing', []):
                        fl = flow_by_id.get(fid)
                        if fl:
                            follow(fl['target'], condition, depth + 1, split_type)
                else:
                    # Diverging gateway — determine the split type for child branches
                    if gw_type == 'parallel':
                        child_split = 'parallel'
                    elif gw_type == 'inclusive':
                        child_split = 'inclusive'
                    else:
                        child_split = 'exclusive'

                    for fid in el.get('outgoing', []):
                        fl = flow_by_id.get(fid)
                        if fl:
                            edge_cond = sanitize(fl.get('condition', ''))
                            # FIX: chain parent condition with edge condition
                            if edge_cond and condition:
                                combined = f"{condition} > {edge_cond}"
                            else:
                                combined = edge_cond or condition
                            follow(fl['target'], combined, depth + 1, child_split)

        for fid in task.get('outgoing', []):
            fl = flow_by_id.get(fid)
            if fl:
                raw_cond = sanitize(fl.get('condition', ''))
                follow(fl['target'], raw_cond)

        if not exits:
            return f"/{role}/complete", [], [], waiting_for

        # Deduplicate by route
        seen_routes:  set  = set()
        unique_exits: list = []
        for ex in exits:
            if ex['route'] not in seen_routes:
                seen_routes.add(ex['route'])
                unique_exits.append(ex)

        # Separate parallel/inclusive cross-lane exits as "parallel_triggers"
        # These fire concurrently and target a DIFFERENT role — they are coordination hints,
        # not primary navigation routes for the current role's UI.
        parallel_triggers: list = []
        primary_exits:     list = []
        for ex in unique_exits:
            is_concurrent = ex['splitType'] in ('parallel', 'inclusive')
            is_cross_lane = ex['targetRole'] != role
            if is_concurrent and is_cross_lane:
                parallel_triggers.append(ex)
            else:
                primary_exits.append(ex)

        # If all exits are cross-lane (e.g. Logistics' Insure parcel going to Warehouse),
        # treat them as primary exits instead so the task still has a nextRoute.
        if not primary_exits:
            primary_exits = unique_exits
            parallel_triggers = []

        # Smart default_route selection:
        # 1. Unconditional same-lane route
        # 2. 'always' condition (inclusive gateway always-branch)
        # 3. First same-lane route
        # 4. First route overall
        def _rank_default(ex: dict) -> int:
            same = ex['targetRole'] == role
            cond = ex.get('condition', '')
            if same and not cond:             return 0  # unconditional same-lane — best
            if not cond:                      return 1  # unconditional any-lane
            if same and cond.endswith('always'): return 2  # inclusive 'always' same-lane
            if cond.endswith('always'):        return 3  # inclusive 'always' cross-lane
            if same:                          return 4  # conditional same-lane
            return 5

        primary_exits.sort(key=_rank_default)
        default_route = primary_exits[0]['route']
        cond_routes   = [x for x in primary_exits if x['condition']]

        # Strip internal fields from output dicts
        def _clean(ex: dict) -> dict:
            return {'route': ex['route'], 'condition': ex['condition']}

        return (default_route,
                [_clean(x) for x in cond_routes],
                [_clean(x) for x in parallel_triggers],
                waiting_for)

    # ── task → lane_role lookup (for cross-lane routing) ─────────────────────
    # Maps task_id → role_key of its lane (or pool-level role if no lanes).
    # Built BEFORE module descriptors so resolve_next_routes can use it.
    task_id_to_role: dict = {
        t['id']: role_key(t['role']) if t.get('role') else ''
        for t in ir1_data.get('tasks', [])
    }

    # ── build module descriptors ──────────────────────────────────────────────

    modules:        list = []
    role_options:   list = []
    default_routes: dict = {}
    seen_roles:     set  = set()   # deduplicate role_options

    for proc_id, proc_tasks in tasks_by_proc.items():
        part = proc_to_part.get(proc_id)
        if not part:
            continue  # black-box pool — skip

        pool_raw_name  = sanitize(part.get('name', proc_id))
        pool_module    = pascal(pool_raw_name)

        # ── Lane detection ──────────────────────────────────────────────────
        # A process is "lane-based" when its tasks carry distinct role values
        # that differ from the pool name itself (i.e. assigned via laneSet).
        lane_names_ordered: list = list(dict.fromkeys(
            sanitize(t['role']) for t in proc_tasks
            if t.get('role') and sanitize(t['role']) != pool_raw_name
        ))
        is_lane_based = len(lane_names_ordered) > 1

        if is_lane_based:
            # ── Lane-based: one sub-module per lane ─────────────────────────
            # File path : src/modules/{PoolModule}/lanes/{LaneName}/pages/{PageName}.tsx
            # Route     : /{lane_role}/{slug}
            # role_option: one entry per lane (Secretary, Logistics, Warehouse …)
            for lane_name in lane_names_ordered:
                lane_tasks = [t for t in proc_tasks
                              if sanitize(t.get('role', '')) == lane_name]
                if not lane_tasks:
                    continue

                lane_role = role_key(lane_name)
                lane_mod  = pascal(lane_name)

                if lane_role not in seen_roles:
                    seen_roles.add(lane_role)
                    role_options.append({
                        "display":  lane_name,
                        "value":    lane_role,
                        "internal": lane_role,
                        "pool":     pool_raw_name,  # extra context for Login page
                    })

                ordered = ordered_tasks_for(proc_id, lane_tasks)
                pages:  list = []

                for task in ordered:
                    task_name = sanitize(task.get('name') or task.get('id'))
                    slug      = slugify(task_name)
                    page_name = pascal(task_name) + "Page"
                    route     = f"/{lane_role}/{slug}"

                    next_r, cond_r, par_r, waiting_for = resolve_next_routes(task, lane_role)
                    ui_type = "form" if task.get('interactionHint') == 'form' else "action"

                    pages.append({
                        "name":              page_name,
                        # Sub-folder per lane inside the pool module
                        "filePath":          (f"src/modules/{pool_module}/"
                                              f"lanes/{lane_mod}/pages/{page_name}.tsx"),
                        "route":             route,
                        "uiType":            ui_type,
                        "taskName":          task_name,
                        "taskType":          task['type'],
                        "asyncFlag":         task.get('asyncFlag', False),
                        "role":              lane_role,
                        "allowedRoles":      [lane_role],
                        "lane":              lane_name,
                        "poolModule":        pool_module,
                        "waitingFor":        waiting_for,
                        "nextRoute":         next_r,
                        "conditionalRoutes": cond_r or None,
                        "parallelTriggers":  par_r or None,
                    })

                if pages:
                    default_routes[lane_role] = pages[0]['route']
                    modules.append({
                        "name":            pool_module,
                        "laneName":        lane_name,
                        "laneModuleName":  lane_mod,
                        "isLaneBased":     True,
                        "participantId":   part.get('id', ''),
                        "participantName": pool_raw_name,
                        "role":            lane_role,
                        "defaultRoute":    pages[0]['route'],
                        "pages":           pages,
                    })

        else:
            # ── Standard: one module per pool/process ───────────────────────
            pool_role = role_key(pool_raw_name)

            if pool_role not in seen_roles:
                seen_roles.add(pool_role)
                role_options.append({
                    "display":  pool_raw_name,
                    "value":    pool_role,
                    "internal": pool_role,
                })

            ordered = ordered_tasks_for(proc_id, proc_tasks)
            pages:  list = []

            for task in ordered:
                task_name = sanitize(task.get('name') or task.get('id'))
                slug      = slugify(task_name)
                page_name = pascal(task_name) + "Page"
                route     = f"/{pool_role}/{slug}"

                next_r, cond_r, par_r, waiting_for = resolve_next_routes(task, pool_role)
                ui_type = "form" if task.get('interactionHint') == 'form' else "action"

                pages.append({
                    "name":              page_name,
                    "filePath":          f"src/modules/{pool_module}/pages/{page_name}.tsx",
                    "route":             route,
                    "uiType":            ui_type,
                    "taskName":          task_name,
                    "taskType":          task['type'],
                    "asyncFlag":         task.get('asyncFlag', False),
                    "role":              pool_role,
                    "allowedRoles":      [pool_role],
                    "waitingFor":        waiting_for,
                    "nextRoute":         next_r,
                    "conditionalRoutes": cond_r or None,
                    "parallelTriggers":  par_r or None,
                })

            if pages:
                default_routes[pool_role] = pages[0]['route']
                modules.append({
                    "name":            pool_module,
                    "isLaneBased":     False,
                    "participantId":   part.get('id', ''),
                    "participantName": pool_raw_name,
                    "role":            pool_role,
                    "defaultRoute":    pages[0]['route'],
                    "pages":           pages,
                })

    # ── shared context ────────────────────────────────────────────────────────

    state_schema: dict = ir1_data.get('stateSchema', {})

    shared_context = {
        "roles":                role_options,
        "defaultRoutesPerRole": default_routes,
        "stateSchema":          state_schema,
        "allRoutes": [
            {"route": p["route"], "role": p["role"],
             "component": p["name"], "allowedRoles": p["allowedRoles"]}
            for mod in modules for p in mod["pages"]
        ],
    }

    stack = {
        "framework":   "React 18",
        "language":    "TypeScript",
        "router":      "React Router v6",
        "styling":     "Tailwind CSS",
        "stateLib":    "Zustand",
        "stateImport": "src/shared/state/globalState.ts",
    }

    # ── task builders ─────────────────────────────────────────────────────────

    BASE_IMPORTS = [
        "react",
        "react-router-dom",
        "zustand",
        "src/shared/state/globalState.ts  (useGlobalState — MUST NOT regenerate this file)",
    ]

    def task_global_state() -> dict:
        return {
            "task":        "generate",
            "description": (
                "Zustand store: auth session + per-task workflow state. "
                "MUST export useGlobalState() hook and GlobalState interface."
            ),
            "path":  "src/shared/state/globalState.ts",
            "group": "shared",
            "input": {
                "roles":       role_options,
                "stateSchema": state_schema,
            },
            "schema": {
                "exports": [
                    "export interface GlobalState",
                    "export const useGlobalState: () => GlobalState & GlobalActions",
                ],
                "fields": {
                    "isAuthenticated": "boolean",
                    "role":            "string | null",
                    "userName":        "string",
                    "token":           "string | null",
                    "workflowState":   (
                        f"Initialized with all keys from stateSchema: "
                        f"{json.dumps(state_schema)}"
                    ),
                },
                "actions": {
                    "login":          "(userName: string, role: string, token?: string) => void",
                    "logout":         "() => void",
                    "updateWorkflow": "(key: string, value: boolean | string) => void",
                },
            },
            "constraints": {
                "output_format":   "ts",
                "imports":         ["zustand", "zustand/middleware"],
                "persist_session": True,
                "max_lines":       120,
            },
        }

    def task_protected_route() -> dict:
        return {
            "task":        "generate",
            "description": (
                "ProtectedRoute component: "
                "(1) if not isAuthenticated → <Navigate to='/login' />. "
                "(2) if allowedRoles provided and role NOT in allowedRoles → <Navigate to='/login' />. "
                "(3) else render <Outlet />."
            ),
            "path":  "src/shared/components/ProtectedRoute.tsx",
            "group": "shared",
            "input": {"roles": role_options},
            "schema": {
                "exports": ["export default function ProtectedRoute(props: ProtectedRouteProps)"],
                "props": {
                    "allowedRoles": "string[]  // optional — if absent, any authenticated role passes",
                },
            },
            "constraints": {
                "output_format": "tsx",
                "imports":       BASE_IMPORTS,
                "max_lines":     50,
            },
        }

    def task_layout() -> dict:
        return {
            "task":        "generate",
            "description": (
                f"Layout shell for {project_name}: "
                "sticky top navbar with project title, role badge (useGlobalState().role), "
                "and a Logout button calling logout(). Body: <main><Outlet /></main>."
            ),
            "path":  "src/shared/components/Layout.tsx",
            "group": "shared",
            "input": {"projectName": project_name, "roles": role_options},
            "schema": {"exports": ["export default function Layout()"]},
            "constraints": {
                "output_format":     "tsx",
                "imports":           BASE_IMPORTS,
                "no_external_ui_lib": True,
                "max_lines":         70,
            },
        }

    def task_login_page() -> dict:
        return {
            "task":        "generate",
            "description": (
                "Login page: centered card with 'userName' text input "
                "and a 'role' <select> populated from roles list. "
                "On submit: call useGlobalState().login(userName, role), "
                "then navigate to defaultRoutesPerRole[role]. "
                "Disable submit if userName is empty or role not selected."
            ),
            "path":  "src/shared/pages/LoginPage.tsx",
            "group": "shared",
            "input": {
                "roles":                role_options,
                "defaultRoutesPerRole": default_routes,
            },
            "schema": {"exports": ["export default function LoginPage()"]},
            "constraints": {
                "output_format":     "tsx",
                "imports":           BASE_IMPORTS,
                "no_external_ui_lib": True,
                "max_lines":         80,
            },
        }

    def task_app_tsx() -> dict:
        all_routes = shared_context["allRoutes"]
        # Build the exact Route list as a string hint for the LLM
        route_hint = []
        for r in all_routes:
            ar = r.get('allowedRoles', [])
            route_hint.append({
                "path":         r["route"],
                "component":    r["component"],
                "allowedRoles": ar,
            })
        return {
            "task":        "generate",
            "description": (
                "Root App.tsx using BrowserRouter. "
                "Register ALL routes flat inside <Routes> — NEVER use conditional JSX around <Route>. "
                "Wrap all protected routes with <ProtectedRoute allowedRoles={[...]}> via Route element prop. "
                "Route '/' redirects to defaultRoute for current role (or /login). "
                "Route '/login' renders <LoginPage /> (public). "
                "Add /:role/complete routes with a plain 'Process Completed' message. "
                "Add catch-all '*' with a 404 message."
            ),
            "path":  "src/App.tsx",
            "group": "shared",
            "input": {
                "roles":                role_options,
                "defaultRoutesPerRole": default_routes,
                "routes":               route_hint,
            },
            "schema": {
                "exports": ["export default function App()"],
                "CRITICAL": (
                    "NEVER put <Route> inside {condition && ...}. "
                    "ALL <Route> elements must be direct children of <Routes>. "
                    "Use allowedRoles prop on <ProtectedRoute> wrapping the route element."
                ),
            },
            "constraints": {
                "output_format": "tsx",
                "imports":       BASE_IMPORTS + [
                    "src/shared/pages/LoginPage",
                    "src/shared/components/ProtectedRoute",
                    "src/shared/components/Layout",
                    # Use actual filePath (correct for both lane and pool pages)
                    *[p['filePath'].replace('.tsx', '')
                      for mod in modules for p in mod['pages']],
                ],
                "max_lines": 130,
            },
        }

    def task_module_page(mod: dict, page: dict) -> dict:
        cond     = page.get('conditionalRoutes')
        par      = page.get('parallelTriggers')   # cross-lane concurrent triggers
        waiting  = page.get('waitingFor')
        is_lane  = mod.get('isLaneBased', False)
        lane_name = page.get('lane', '')

        # Group key: include lane name when lane-based for clearer LLM context
        group_key = (f"module:{mod['name']}/lane:{mod.get('laneModuleName', '')}"
                     if is_lane else f"module:{mod['name']}")

        # Import depth: lane pages are 5 levels deep → ../../../../../
        import_depth = "../../../../../" if is_lane else "../../../../"
        shared_state_import = f"{import_depth}shared/state/globalState"

        # Build routing description
        if cond:
            routing_desc = (
                "Show a choice selector: "
                + ", ".join(f"'{c['condition']}' → navigate('{c['route']}')" for c in cond)
                + f". Default: navigate('{page['nextRoute']}')."
            )
        else:
            routing_desc = f"On action complete: navigate('{page['nextRoute']}')."

        # Parallel triggers: cross-lane branches (inclusive/parallel gateways)
        # These fire concurrently from the BPMN but in a single-role React app they
        # are coordination hints only — the current role navigates on its own primary route.
        if par:
            par_desc = (
                " PARALLEL BPMN BRANCHES (inclusive/parallel gateway — these run "
                "concurrently in the process but are handled by other roles): "
                + "; ".join(f"'{p['condition']}' triggers role at '{p['route']}'" for p in par)
                + ". NOTE: this page should navigate its own primaryRoute only; "
                "the parallel branch is initiated independently by the target role's login."
            )
            routing_desc += par_desc

        if waiting:
            routing_desc += (
                f" NOTE: task waits for '{waiting}' event — "
                "show 'Waiting...' state and a 'Continue' button to simulate event."
            )

        if page['uiType'] == 'form':
            ui_fields = [
                f"Labelled text inputs for '{page['taskName']}' data fields",
                "Submit: validate → updateWorkflow(key, true) → routing action",
            ]
        else:
            ui_fields = [
                f"Status card: '{page['taskName']}' in progress",
                f"Action button: {'async call (loading/error state) → ' if page['asyncFlag'] else ''}"
                f"updateWorkflow(key, true) → routing action",
            ]

        desc_prefix = (f"[{mod['name']} / lane:{lane_name} / role:{page['role']}]"
                       if is_lane else f"[{mod['name']} / role:{page['role']}]")

        return {
            "task":        "generate",
            "description": (
                f"{desc_prefix} Page for BPMN task '{page['taskName']}' ({page['taskType']}). "
                f"UI: {page['uiType']}. {routing_desc}"
            ),
            "path":  page['filePath'],
            "group": group_key,
            "input": {
                "taskName":          page['taskName'],
                "taskType":          page['taskType'],
                "role":              page['role'],
                "allowedRoles":      page['allowedRoles'],
                "lane":              lane_name if is_lane else None,
                "poolModule":        mod['name'] if is_lane else None,
                "uiType":            page['uiType'],
                "asyncFlag":         page['asyncFlag'],
                "waitingFor":        waiting,
                "nextRoute":         page['nextRoute'],
                "conditionalRoutes": cond,
                "parallelTriggers":  par,   # coordination hint for the LLM
            },
            "schema": {
                "exports": [f"export default function {page['name']}()"],
                "ui": {
                    "fields":  ui_fields,
                    "routing": routing_desc,
                    "layout":  "white card, page heading, Tailwind",
                },
            },
            "constraints": {
                "output_format":  "tsx",
                "imports":        BASE_IMPORTS + [
                    f"{shared_state_import}  (useGlobalState)",
                    "DO NOT wrap in Layout — it is already in the router",
                ],
                "role_guard":     f"if (role !== '{page['role']}') navigate('/login')",
                "state_key":      f"updateWorkflow key: '{_state_key(page['taskName'])}_completed'",
                "async_pattern":  "async/await with isLoading + error useState" if page['asyncFlag'] else None,
                "max_lines":      110,
            },
        }

    # ── assemble IR2 ──────────────────────────────────────────────────────────

    ir2_tasks: list = []
    ir2_tasks.append(task_global_state())
    ir2_tasks.append(task_layout())
    ir2_tasks.append(task_protected_route())
    ir2_tasks.append(task_login_page())
    ir2_tasks.append(task_app_tsx())
    for mod in modules:
        for page in mod['pages']:
            ir2_tasks.append(task_module_page(mod, page))

    return {
        "project":       project_name,
        "stack":         stack,
        "sharedContext": shared_context,
        "tasks":         ir2_tasks,
    }


def _state_key(task_name: str) -> str:
    """Convert task name to stateSchema key prefix.
    Must produce the same output as IR1's _clean_state_key().
    """
    cleaned = re.sub(r'\s+', ' ', task_name.strip())   # collapse whitespace/newlines
    key = re.sub(r'[^a-zA-Z0-9]', '_', cleaned).lower().strip('_')
    return re.sub(r'_+', '_', key)


# ============================================================================
# STEP 3: IR2 → output.json  (LLM generation + validation + auto-fix)
# ============================================================================

def build_llm_prompt(ir2_data: dict) -> tuple:
    """
    Build (system_prompt, user_message) from IR2.

    v4 — structured IR2 prompt format:
    - system_prompt now carries explicit file_types taxonomy (5 categories),
      forbidden list, stack contract, and a minimal output_example.
    - user_message is slimmed to per-task specs only (saves tokens for 7B models).
    - Designed for Qwen2.5-Coder-7B-Instruct; total prompt target ≤ 6 000 tokens.
    """
    project  = ir2_data.get("project", "App")
    stack    = ir2_data.get("stack", {})
    ctx      = ir2_data.get("sharedContext", {})
    roles    = ctx.get("roles", [])
    routes   = ctx.get("defaultRoutesPerRole", {})
    schema   = ctx.get("stateSchema", {})
    tasks    = ir2_data.get("tasks", [])

    exact_paths = [t["path"] for t in tasks]

    # ── 1. File-type taxonomy (5 categories) ─────────────────────────────────
    # Build the dynamic_page entry from actual page tasks so the LLM gets
    # concrete import-depth and routing rules without repeating them per file.
    module_page_tasks = [t for t in tasks if t.get("group", "").startswith("module:")]
    lane_page_tasks   = [t for t in module_page_tasks
                         if "lane:" in t.get("group", "")]
    pool_page_tasks   = [t for t in module_page_tasks
                         if "lane:" not in t.get("group", "")]

    import_depth_rules = (
        "src/modules/X/pages/Y.tsx            → import from '../../../../shared/state/globalState'\n"
        "src/modules/X/lanes/L/pages/Y.tsx    → import from '../../../../../shared/state/globalState'"
    )

    file_types_block = f"""FILE_TYPES — understand each category before writing code:

1. app_root  [src/App.tsx]
   Role   : BrowserRouter root. Register ALL {len(exact_paths)} paths as flat <Route> children.
            Wrap protected routes with <ProtectedRoute allowedRoles={{[...]}}>.
            '/' → Navigate to defaultRoute for current role or '/login'.
            '/login' → <LoginPage /> (public). Add /:role/complete + catch-all '*'.
   CRITICAL: NEVER put <Route> inside conditional JSX {{condition && <Route .../>}}.

2. login_page  [src/shared/pages/LoginPage.tsx]
   Role   : Centered card. 'userName' text input + 'role' <select> from roles list.
            On submit: useGlobalState().login(userName, role) → navigate(defaultRoutesPerRole[role]).
            Disable submit when userName empty or role unselected.

3. layout  [src/shared/components/Layout.tsx]
   Role   : Sticky navbar showing role badge + Logout button (calls logout() → '/login').
            <main><Outlet /></main> body. No sidebar needed.

4. protected_route  [src/shared/components/ProtectedRoute.tsx]
   Role   : Props: {{ allowedRoles?: string[] }}.
            !isAuthenticated → <Navigate to='/login' />.
            role not in allowedRoles → <Navigate to='/login' />.
            else → <Outlet />.

5. dynamic_page  [src/modules/*/pages/*.tsx  or  src/modules/*/lanes/*/pages/*.tsx]
   Role   : One file per BPMN task. Heading = taskName.
            uiType='form'   → labeled inputs inferred from taskName + Submit button.
            uiType='action' → status card + Proceed/Complete button.
            asyncFlag=true  → show isLoading + error useState.
            conditionalRoutes != null → render radio/select for branch before navigating.
            waitingFor != null → show 'Waiting for <event>...' state + Continue button.
            On completion: updateWorkflow('<stateKey>_completed', true) → navigate(nextRoute).
   Import depth:
{import_depth_rules}"""

    # ── 2. Forbidden list ─────────────────────────────────────────────────────
    forbidden_block = """FORBIDDEN — violations break the build or the contract:
- Do NOT generate src/shared/state/globalState.ts (it already exists; do not recreate it)
- Do NOT add files not listed in the exact path manifest below
- Do NOT use <form> HTML elements — use <div> with onClick handlers
- Do NOT hardcode role strings — derive from roles list in input
- Do NOT drop _workflow_meta / IR2 metadata into output objects
- Do NOT import lucide-react, @heroicons, or any icon library
- Do NOT put <Route> inside conditional JSX"""

    # ── 3. Output contract ────────────────────────────────────────────────────
    output_contract = f"""OUTPUT CONTRACT:
task         : fill_react_file_content
output_format: JSON array — no markdown fences, no prose, no trailing commas
array_length : exactly {len(exact_paths)} objects
object_shape : {{"path": "<exact path>", "content": "<TypeScript source>"}}

PATH RULES:
- Copy paths EXACTLY — PascalCase filenames must be preserved.  NEVER lowercase them.
- NEVER add parentheses () or brackets [] to any folder/file name segment.

Exact paths to generate ({len(exact_paths)} total):
{chr(10).join(f'  {i+1:2d}. {p}' for i, p in enumerate(exact_paths))}"""

    # ── 4. Routing + state contract ───────────────────────────────────────────
    routing_block = "ROUTING CONTRACT:\n"
    for r in roles:
        dflt = routes.get(r["internal"], "?")
        routing_block += f"  role '{r['internal']}' → prefix '/{r['internal']}/'  default: {dflt}\n"

    state_block = (
        f"STATE CONTRACT (globalState.ts — DO NOT regenerate):\n"
        f"  useGlobalState() returns: {{ isAuthenticated, role, userName, token,\n"
        f"    workflowState, login(userName,role,token?), logout(), updateWorkflow(key,value) }}\n"
        f"  workflowState keys: {json.dumps(list(schema.keys()), ensure_ascii=False)}"
    )

    # ── 5. Minimal output_example ─────────────────────────────────────────────
    first_dynamic = next((t for t in tasks if t.get("group", "").startswith("module:")), None)
    example_path  = first_dynamic["path"] if first_dynamic else "src/modules/Example/pages/ExamplePage.tsx"
    output_example_block = (
        f'OUTPUT EXAMPLE (shape only — fill all {len(exact_paths)} entries):\n'
        f'[\n'
        f'  {{"path": "src/App.tsx", "content": "import React from \'react\'; ..."}},\n'
        f'  {{"path": "src/shared/pages/LoginPage.tsx", "content": "import React ..."}},\n'
        f'  {{"path": "{example_path}", "content": "import React ..."}}\n'
        f']'
    )

    # ── Assemble system_prompt ────────────────────────────────────────────────
    stack_line = (
        f"Stack: {stack.get('framework','React 18')} + {stack.get('language','TypeScript')} + "
        f"{stack.get('router','React Router v6')} + {stack.get('styling','Tailwind CSS')} + "
        f"{stack.get('stateLib','Zustand')}. Tailwind CSS only — no inline style objects."
    )

    system_prompt = "\n\n".join([
        f'You are a React 18 + TypeScript code generator for the "{project}" project.',
        stack_line,
        file_types_block,
        forbidden_block,
        output_contract,
        routing_block.rstrip(),
        state_block,
        output_example_block,
    ])

    # ── user_message: slim per-task specs ────────────────────────────────────
    user_lines = [
        f"Generate all {len(tasks)} files for {project}.",
        "",
        "=== FILE SPECIFICATIONS ===",
    ]

    for i, t in enumerate(tasks, 1):
        user_lines += [
            "",
            f"--- [{i}/{len(tasks)}] {t['path']} ---",
            f"Goal: {t['description']}",
        ]
        inp = t.get("input")
        if inp:
            # Emit only non-empty fields to save tokens
            slim = {k: v for k, v in inp.items()
                    if v is not None and v != [] and v != {}}
            user_lines.append(f"Input: {json.dumps(slim, ensure_ascii=False)}")

        sch = t.get("schema", {})
        exports = sch.get("exports", [])
        if exports:
            user_lines.append(f"Must export: {exports}")
        if sch.get("CRITICAL"):
            user_lines.append(f"CRITICAL: {sch['CRITICAL']}")

        cst = t.get("constraints", {})
        for field in ("role_guard", "state_key", "async_pattern"):
            val = cst.get(field)
            if val:
                user_lines.append(f"{field}: {val}")

    user_lines += ["", "Return the JSON array now. No preamble."]
    user_message = "\n".join(user_lines)

    return system_prompt, user_message


def call_llm_generate(ir2_data: dict,
                      api_key: str = None,
                      model: str = "claude-sonnet-4-20250514") -> list:
    """
    Call Anthropic /v1/messages and return list of {path, content} dicts.
    Raises on HTTP errors.
    """
    system_prompt, user_message = build_llm_prompt(ir2_data)

    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError(
            "ANTHROPIC_API_KEY not set. "
            "Export it: export ANTHROPIC_API_KEY=sk-ant-..."
        )

    headers = {
        "Content-Type":      "application/json",
        "anthropic-version": "2023-06-01",
        "x-api-key":         key,
    }
    payload = {
        "model":      model,
        "max_tokens": 16000,
        "system":     system_prompt,
        "messages":   [{"role": "user", "content": user_message}],
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data    = json.dumps(payload).encode(),
        headers = headers,
        method  = "POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            response = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"API HTTP {e.code}: {body}") from e

    raw = response["content"][0]["text"].strip()

    # Strip accidental markdown fences
    raw = re.sub(r'^```(?:json)?\s*\n?', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\n?```\s*$',          '', raw, flags=re.MULTILINE)

    try:
        output = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned non-JSON response: {e}\n\nRaw:\n{raw[:500]}") from e

    if not isinstance(output, list):
        raise ValueError(f"LLM returned {type(output).__name__}, expected list")

    return output


def validate_and_fix_output(output: list, ir2_data: dict) -> tuple:
    """
    Validate LLM output against IR2 path manifest.
    Auto-fix case mismatches and return (fixed_output, issues_list).
    """
    expected_paths = [t["path"] for t in ir2_data.get("tasks", [])]
    expected_set   = set(expected_paths)
    issues: list   = []

    # Build case-insensitive lookup for auto-fix
    lower_to_expected = {p.lower(): p for p in expected_paths}

    fixed_output: list = []
    seen_paths:   set  = set()

    for item in output:
        if not isinstance(item, dict):
            issues.append(f"SKIP non-dict item: {type(item)}")
            continue

        path    = item.get("path", "")
        content = item.get("content", "")

        # Auto-fix 1: lowercase → correct case
        if path not in expected_set:
            correct = lower_to_expected.get(path.lower())
            if correct:
                issues.append(f"AUTO-FIX path case: '{path}' → '{correct}'")
                path = correct
            else:
                issues.append(f"HALLUCINATED file (removed): '{path}'")
                continue

        # Deduplicate
        if path in seen_paths:
            issues.append(f"DUPLICATE (removed): '{path}'")
            continue

        seen_paths.add(path)
        fixed_output.append({"path": path, "content": content})

    # Check for missing files
    for ep in expected_paths:
        if ep not in seen_paths:
            issues.append(f"MISSING file (empty stub added): '{ep}'")
            fixed_output.append({"path": ep, "content": ""})

    # Re-sort to match expected order
    path_order = {p: i for i, p in enumerate(expected_paths)}
    fixed_output.sort(key=lambda x: path_order.get(x["path"], 999))

    # Content quality checks (warn only)
    for item in fixed_output:
        c = item["content"]
        p = item["path"]
        if not c:
            issues.append(f"WARN empty content: '{p}'")
            continue
        # Check for correct route prefix
        ctx   = ir2_data.get("sharedContext", {})
        for role_opt in ctx.get("roles", []):
            rk = role_opt["internal"]
            if f"modules/{pascal_from_role(ir2_data, rk)}/" in p:
                if f"/{rk}/" not in c and f"'{rk}'" not in c:
                    issues.append(f"WARN possible wrong route prefix in '{p.split('/')[-1]}'")
        # Check globalState.ts exports
        if "globalState.ts" in p:
            for required in ["useGlobalState", "login", "logout", "updateWorkflow", "workflowState"]:
                if required not in c:
                    issues.append(f"WARN globalState.ts missing symbol: '{required}'")
        # Check ProtectedRoute accepts allowedRoles
        if "ProtectedRoute" in p and "allowedRoles" not in c:
            issues.append("WARN ProtectedRoute does not accept allowedRoles prop")

    return fixed_output, issues


def pascal_from_role(ir2_data: dict, role: str) -> str:
    """Find PascalCase module name for a given role key."""
    for mod in ir2_data.get("sharedContext", {}).get("allRoutes", []):
        if mod["role"] == role:
            # Extract module name from path like src/modules/ModuleName/...
            m = re.search(r'src/modules/([^/]+)/', mod.get("route", ""))
            if m:
                return m.group(1)
    # Fallback
    ctx   = ir2_data.get("sharedContext", {})
    roles = {r["internal"]: r["display"] for r in ctx.get("roles", [])}
    display = roles.get(role, role)
    return re.sub(r'[^a-zA-Z0-9]', '', display.title())


def generate_output(ir2_data: dict,
                    api_key: str   = None,
                    model: str     = "claude-sonnet-4-20250514") -> tuple:
    """
    Full Step 3: call LLM → validate → fix → return (output, issues).
    """
    print("  Calling LLM API...", flush=True)
    raw_output = call_llm_generate(ir2_data, api_key, model)
    print(f"  LLM returned {len(raw_output)} files.", flush=True)

    fixed, issues = validate_and_fix_output(raw_output, ir2_data)

    if issues:
        print(f"  Validation issues ({len(issues)}):")
        for iss in issues:
            prefix = "[AUTO-FIX]" if iss.startswith("AUTO-FIX") else \
                     "[ERROR]"    if iss.startswith("MISSING") or iss.startswith("HALLUCI") else \
                     "[WARN]"
            print(f"    {prefix} {iss}")
    else:
        print("  All files valid.")

    return fixed, issues


# ============================================================================
# DATASET UTILITIES
# ============================================================================

def to_finetune_pair(ir2_data: dict, output: list) -> dict:
    """
    Convert (IR2, output) into a fine-tuning (input_prompt, expected_output) pair.

    The 'input_prompt' is the LLM user message (from build_llm_prompt).
    The 'expected_output' is the validated output JSON string.

    Format is compatible with Anthropic fine-tuning JSONL:
    {
        "messages": [
            {"role": "system",    "content": <system_prompt>},
            {"role": "user",      "content": <user_message>},
            {"role": "assistant", "content": <json_output>},
        ]
    }
    """
    system_prompt, user_message = build_llm_prompt(ir2_data)
    assistant_content = json.dumps(output, ensure_ascii=False)
    return {
        "messages": [
            {"role": "system",    "content": system_prompt},
            {"role": "user",      "content": user_message},
            {"role": "assistant", "content": assistant_content},
        ]
    }


# ============================================================================
# PIPELINE RUNNER
# ============================================================================

def run_pipeline(bpmn_file_path: str,
                 output_dir:     str  = None,
                 run_llm:        bool = True,
                 export_ft:      bool = False,
                 api_key:        str  = None,
                 model:          str  = "claude-sonnet-4-20250514") -> tuple:
    """
    Run the full 3-step pipeline (or just Steps 1+2 if run_llm=False).
    Returns (ir1, ir2, output, issues).
    """
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(bpmn_file_path))
    os.makedirs(output_dir, exist_ok=True)

    # ── Step 1 ────────────────────────────────────────────────────────────────
    sep = "=" * 60
    print(sep)
    print("STEP 1: BPMN XML → IR1")
    print(sep)

    with open(bpmn_file_path, 'r', encoding='utf-8') as f:
        bpmn_xml = f.read()
    print(f"  Input : {bpmn_file_path}  ({len(bpmn_xml):,} chars)")

    ir1 = parse_bpmn_to_json(bpmn_xml)

    ir1_path = os.path.join(output_dir, 'ir1.json')
    with open(ir1_path, 'w', encoding='utf-8') as f:
        json.dump(ir1, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] IR1 — {len(ir1['process']['participants'])} participants, "
          f"{len(ir1['tasks'])} tasks, {len(ir1['gateways'])} gateways, "
          f"{len(ir1['sequenceFlows'])} flows")
    for t in ir1['tasks']:
        print(f"     [task] {t['name']:40s} role={t['role']}")
    for g in ir1['gateways']:
        print(f"     [gw]   {g['name']:40s} direction={g['gatewayDirection']}  "
              f"hint={g['controlHint']}")
    print(f"  Saved → {ir1_path}")

    # ── Step 2 ────────────────────────────────────────────────────────────────
    print(f"\n{sep}")
    print("STEP 2: IR1 → IR2")
    print(sep)

    ir2 = create_react_prompt_json(ir1, bpmn_file_path=bpmn_file_path)

    ir2_path = os.path.join(output_dir, 'ir2.json')
    with open(ir2_path, 'w', encoding='utf-8') as f:
        json.dump(ir2, f, indent=2, ensure_ascii=False)

    tasks_list    = ir2.get("tasks", [])
    shared_tasks  = [t for t in tasks_list if t.get("group") == "shared"]
    module_tasks  = [t for t in tasks_list if t.get("group", "").startswith("module:")]

    print(f"\n[OK] IR2 — {len(tasks_list)} tasks  "
          f"(shared: {len(shared_tasks)}, module pages: {len(module_tasks)})")
    ctx = ir2.get("sharedContext", {})
    for r in ctx.get("roles", []):
        dflt = ctx.get("defaultRoutesPerRole", {}).get(r["internal"], "?")
        print(f"     role '{r['internal']}' → default: {dflt}")
    for t in module_tasks:
        inp   = t['input']
        cond  = inp.get('conditionalRoutes')
        wait  = inp.get('waitingFor')
        hints = []
        if cond:  hints.append(f"cond:{[c['condition'] for c in cond]}")
        if wait:  hints.append(f"wait:'{wait}'")
        print(f"     [{t['group']:20s}] {t['path'].split('/')[-1]:45s} "
              f"next={inp['nextRoute'].split('/')[-1]:25s} {' '.join(hints)}")
    print(f"  Saved → {ir2_path}")

    # ── Step 3 ────────────────────────────────────────────────────────────────
    output: list = []
    issues: list = []

    if run_llm:
        print(f"\n{sep}")
        print("STEP 3: IR2 → output.json  (LLM)")
        print(sep)
        try:
            output, issues = generate_output(ir2, api_key=api_key, model=model)
            out_path = os.path.join(output_dir, 'output.json')
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            print(f"\n[OK] output.json — {len(output)} files, "
                  f"{sum(len(x['content']) for x in output):,} chars total")
            print(f"  Saved → {out_path}")
        except Exception as e:
            print(f"\n[ERROR] Step 3 failed: {e}")
            issues.append(str(e))
    else:
        print("\n[SKIP] Step 3 (--no-llm flag set)")

    # ── Fine-tuning export ────────────────────────────────────────────────────
    if export_ft and output:
        ft_path = os.path.join(output_dir, 'ft_pair.jsonl')
        pair    = to_finetune_pair(ir2, output)
        with open(ft_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')
        print(f"\n[OK] Fine-tuning pair saved → {ft_path}")

    print(f"\n{sep}")
    print("[OK] Pipeline complete!")
    print(sep)
    return ir1, ir2, output, issues


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="BPMN → IR1 → IR2 → output.json pipeline (v3)"
    )
    parser.add_argument("bpmn_file",  help="Path to .bpmn file")
    parser.add_argument("output_dir", nargs="?", default=None,
                        help="Output directory (default: same as bpmn_file)")
    parser.add_argument("--no-llm",   action="store_true",
                        help="Skip Step 3 (no API call)")
    parser.add_argument("--export-ft", action="store_true",
                        help="Export fine-tuning JSONL pair")
    parser.add_argument("--api-key",  default=None,
                        help="Anthropic API key (overrides ANTHROPIC_API_KEY env var)")
    parser.add_argument("--model",    default="claude-sonnet-4-20250514",
                        help="Model to use for Step 3")

    args = parser.parse_args()

    if not os.path.exists(args.bpmn_file):
        print(f"[ERROR] File not found: {args.bpmn_file}")
        sys.exit(1)

    run_pipeline(
        bpmn_file_path = args.bpmn_file,
        output_dir     = args.output_dir,
        run_llm        = not args.no_llm,
        export_ft      = args.export_ft,
        api_key        = args.api_key,
        model          = args.model,
    )