"""
IR1 → IR2 Transformer (new format per ir2_structure.json)
==========================================================
Converts the structural IR1 into an IR2 that includes:
  - participants[] with tasks[]
  - pageType per task (write-navigate / wait-then-write / ...)
  - waitCondition derived from incoming messageFlows
  - conditionalRoutes derived from exclusive gateway successors
  - stateWrites derived from task completion + messageFlow triggers
  - nextRoute derived by traversing sequenceFlows

Key rules from Study_Case_Carwash.md:
  • tasks that RECEIVE a messageFlow → pageType = wait-then-write
  • tasks that lead INTO a diverging gateway → conditionalRoutes added
  • tasks with no outgoing sequenceFlow (terminal) → navigate to
    the first message-triggered task in the same participant, or /role/complete
  • multiple messageFlows to one task → create a combined trigger state field
"""

from __future__ import annotations
import re


# ── Name helpers ──────────────────────────────────────────────────────────────

def pascal(s: str) -> str:
    """'pulls car up to car wash' → 'PullsCarUpToCarWash'"""
    parts = re.split(r'[\s_\-]+', s.strip())
    return ''.join(p.capitalize() for p in parts if p)


def kebab(s: str) -> str:
    """'Pulls car up to car wash' → 'pulls-car-up-to-car-wash'"""
    s = re.sub(r'[^a-zA-Z0-9\s]', '', s)
    return re.sub(r'[\s_]+', '-', s.strip()).lower()


def state_key_of(task_name: str) -> str:
    """'Pulls car up to car wash' → 'pulls_car_up_to_car_wash_completed'"""
    k = re.sub(r'[^a-zA-Z0-9\s]', '', task_name)
    k = re.sub(r'\s+', '_', k.strip()).lower()
    return f"{k}_completed"


def role_internal(name: str) -> str:
    """'Car Wash Machine' → 'carwashmachine'"""
    return re.sub(r'\s+', '', name.lower())


# ── IR1 lookup helpers ────────────────────────────────────────────────────────

def _task_by_id(tid: str, ir1: dict):
    return next((t for t in ir1['tasks'] if t['id'] == tid), None)


def _event_by_id(eid: str, ir1: dict):
    return next((e for e in ir1['events'] if e['id'] == eid), None)


def _gw_by_id(gid: str, ir1: dict):
    return next((g for g in ir1['gateways'] if g['id'] == gid), None)


def _sf_by_id(fid: str, ir1: dict):
    return next((f for f in ir1['sequenceFlows'] if f['id'] == fid), None)


# ── Route helpers ─────────────────────────────────────────────────────────────

def task_route(task: dict) -> str:
    return f"/{kebab(task['participantName'])}/{kebab(task['name'])}"


def complete_route(participant_name: str) -> str:
    return f"/{kebab(participant_name)}/complete"


# ── Reachability & ordering ───────────────────────────────────────────────────

def reachable_from_start(proc_id: str, ir1: dict) -> set:
    """Return set of task IDs reachable via sequenceFlows from startEvent."""
    start_events = [
        e for e in ir1['events']
        if e['processId'] == proc_id and e['eventType'] == 'startEvent'
    ]
    visited_flows: set = set()
    reachable: set = set()
    queue = [flow_id for se in start_events for flow_id in se['outgoing']]

    while queue:
        fid = queue.pop(0)
        if fid in visited_flows:
            continue
        visited_flows.add(fid)
        sf = _sf_by_id(fid, ir1)
        if not sf:
            continue
        tgt = sf['target']
        task = _task_by_id(tgt, ir1)
        if task:
            reachable.add(task['id'])
            queue.extend(task['outgoing'])
        gw = _gw_by_id(tgt, ir1)
        if gw:
            queue.extend(gw['outgoing'])
        evt = _event_by_id(tgt, ir1)
        if evt:
            queue.extend(evt.get('outgoing', []))

    return reachable


def msg_triggered_tasks(proc_id: str, ir1: dict) -> list:
    """Return tasks in process that are targeted by a messageFlow."""
    msg_targets = {mf['targetRef'] for mf in ir1['messageFlows']}
    return [t for t in ir1['tasks'] if t['processId'] == proc_id and t['id'] in msg_targets]


def _reachable_from_flow_ids(flow_ids: list, ir1: dict) -> set:
    """BFS from a list of sequenceFlow IDs; return the set of reachable task IDs."""
    visited: set = set()
    reachable: set = set()
    queue = list(flow_ids)
    while queue:
        fid = queue.pop(0)
        if fid in visited:
            continue
        visited.add(fid)
        sf = _sf_by_id(fid, ir1)
        if not sf:
            continue
        tgt = sf['target']
        task = _task_by_id(tgt, ir1)
        if task:
            reachable.add(task['id'])
            queue.extend(task['outgoing'])
        gw = _gw_by_id(tgt, ir1)
        if gw:
            queue.extend(gw['outgoing'])
        evt = _event_by_id(tgt, ir1)
        if evt:
            queue.extend(evt.get('outgoing', []))
    return reachable


def task_order(proc_id: str, ir1: dict) -> list:
    """
    Return tasks in execution order:
      • If process has a startEvent:
          1. Sequence-flow-reachable tasks (topologically sorted)
          2. Message-triggered tasks appended at the end (e.g. DrivesAway)
      • If process has NO startEvent (e.g. Car Wash Machine):
          Message-triggered tasks come first, then their successors via sequenceFlows.
    """
    all_tasks = [t for t in ir1['tasks'] if t['processId'] == proc_id]
    reach     = reachable_from_start(proc_id, ir1)
    mt        = msg_triggered_tasks(proc_id, ir1)
    mt_ids    = {t['id'] for t in mt}

    has_start = bool(reach)

    if not has_start:
        # No startEvent (e.g. Car Wash Machine) — treat message-triggered tasks as entry points
        # and traverse their outgoing flows to discover the rest.
        mt_flow_ids = [fid for t in mt for fid in t['outgoing']]
        reach       = _reachable_from_flow_ids(mt_flow_ids, ir1)

    seq_tasks  = [t for t in all_tasks if t['id'] in reach  and t['id'] not in mt_ids]
    wait_tasks = [t for t in all_tasks if t['id'] in mt_ids]

    if has_start:
        # Normal process: seq-flow tasks first, message-triggered wait tasks at end
        return _topo_sort(seq_tasks, ir1) + wait_tasks
    else:
        # No startEvent: message-triggered tasks (entry) first, then their successors
        return wait_tasks + _topo_sort(seq_tasks, ir1)


def _topo_sort(tasks: list, ir1: dict) -> list:
    """Topological sort; treats gateway hops as direct task→task edges."""
    if not tasks:
        return []
    task_ids = {t['id'] for t in tasks}
    gw_ids   = {g['id'] for g in ir1['gateways']}
    in_deg   = {t['id']: 0 for t in tasks}
    adj      = {t['id']: [] for t in tasks}

    def _add_edge(src, tgt):
        if src in task_ids and tgt in task_ids and tgt not in adj[src]:
            adj[src].append(tgt)
            in_deg[tgt] += 1

    def _resolve_gw_targets(gw_id, visited=None):
        """Recursively resolve gateway targets to task IDs, handling gateway chains."""
        if visited is None:
            visited = set()
        if gw_id in visited:
            return []
        visited.add(gw_id)
        gw = _gw_by_id(gw_id, ir1)
        if not gw:
            return []
        targets = []
        for out_id in gw['outgoing']:
            sf2 = _sf_by_id(out_id, ir1)
            if sf2:
                if sf2['target'] in task_ids:
                    targets.append(sf2['target'])
                elif sf2['target'] in gw_ids:
                    targets.extend(_resolve_gw_targets(sf2['target'], visited))
        return targets

    for sf in ir1['sequenceFlows']:
        # Direct task → task
        if sf['source'] in task_ids and sf['target'] in task_ids:
            _add_edge(sf['source'], sf['target'])
        # task → gateway → ... → task  (multi-hop through gateway chains)
        elif sf['source'] in task_ids and sf['target'] in gw_ids:
            for resolved_tid in _resolve_gw_targets(sf['target']):
                _add_edge(sf['source'], resolved_tid)

    queue  = [tid for tid in task_ids if in_deg[tid] == 0]
    result = []
    task_map = {t['id']: t for t in tasks}
    while queue:
        tid = queue.pop(0)
        result.append(task_map[tid])
        for nxt in adj[tid]:
            in_deg[nxt] -= 1
            if in_deg[nxt] == 0:
                queue.append(nxt)
    # Append any remaining (cycle fallback)
    result += [t for t in tasks if t not in result]
    return result


# ── Routing analysis ──────────────────────────────────────────────────────────

def gateway_branch_targets(gw: dict, ir1: dict) -> list:
    """Return list of (sequenceFlow, task) reachable from a diverging gateway's outgoing flows.

    Resolves intermediate nodes:
      - gateway → task  (direct)
      - gateway → event → task  (eventBased gateway pattern)
      - gateway → gateway → task (gateway chain)
    """
    targets = []
    for out_id in gw['outgoing']:
        sf = _sf_by_id(out_id, ir1)
        if not sf:
            continue
        tgt_task = _task_by_id(sf['target'], ir1)
        if tgt_task:
            targets.append((sf, tgt_task))
            continue
        # gateway → event → task  (eventBased gateway pattern)
        evt = _event_by_id(sf['target'], ir1)
        if evt:
            for evt_out_id in evt.get('outgoing', []):
                sf2 = _sf_by_id(evt_out_id, ir1)
                if sf2:
                    nxt = _task_by_id(sf2['target'], ir1)
                    if nxt:
                        # Use originating sf for condition but record the event name
                        label = sf['condition'] or evt.get('name', '') or pascal(nxt['name'])
                        label = re.sub(r'\s+', ' ', label).strip()  # normalize whitespace
                        # Create a synthetic sf-like dict with the resolved label
                        targets.append(({**sf, 'condition': label}, nxt))
                        break
            continue
        # gateway → gateway chain: follow through converging gateway
        inner_gw = _gw_by_id(sf['target'], ir1)
        if inner_gw:
            for inner_out_id in inner_gw['outgoing']:
                sf2 = _sf_by_id(inner_out_id, ir1)
                if sf2:
                    nxt = _task_by_id(sf2['target'], ir1)
                    if nxt:
                        targets.append((sf2, nxt))
    return targets


def gateway_conditional_routes(gw: dict, ir1: dict) -> list:
    """Return [{route, condition}] for each branch of a diverging gateway."""
    routes = []
    for sf, tgt_task in gateway_branch_targets(gw, ir1):
        routes.append({
            "route":     task_route(tgt_task),
            "condition": sf['condition'] or pascal(tgt_task['name']),
        })
    return routes


def gateway_parallel_routes(gw: dict, ir1: dict) -> list:
    """Return list of route strings for all branches of a parallel diverging gateway."""
    routes = []
    for _sf, tgt_task in gateway_branch_targets(gw, ir1):
        routes.append(task_route(tgt_task))
    return routes


def find_next_route(task: dict, ir1: dict) -> tuple:
    """
    Returns (nextRoute: str, conditionalRoutes: list | None).

    Logic:
      - outgoing → task → that task's route
      - outgoing → diverging gateway → conditionalRoutes from gateway branches
      - outgoing → converging gateway → follow through to next task
      - outgoing → endEvent → /role/complete
      - no outgoing (terminal) → first msg-triggered task in same process, or /role/complete
    """
    outgoing_flows = [sf for sf in ir1['sequenceFlows'] if sf['source'] == task['id']]

    # ── Terminal task (no outgoing sequence flow) ─────────────────────────
    if not outgoing_flows:
        waited = msg_triggered_tasks(task['processId'], ir1)
        already = reachable_from_start(task['processId'], ir1)
        waiting_only = [t for t in waited if t['id'] not in already]
        if waiting_only:
            return task_route(waiting_only[0]), None
        return complete_route(task['participantName']), None

    # ── Single outgoing flow ───────────────────────────────────────────────
    if len(outgoing_flows) == 1:
        sf  = outgoing_flows[0]
        tgt = sf['target']

        # → diverging gateway
        gw = _gw_by_id(tgt, ir1)
        if gw and gw['gatewayDirection'] == 'Diverging':
            gw_type = gw.get('gatewayType', 'exclusive')

            # Parallel gateway: all branches execute; first branch as nextRoute,
            # expose parallelRoutes so generator can emit concurrent navigation
            if gw_type == 'parallel':
                p_routes = gateway_parallel_routes(gw, ir1)
                first = p_routes[0] if p_routes else complete_route(task['participantName'])
                # Wait for all branches to complete before continuing
                return first, [{"route": r, "condition": "__parallel__"} for r in p_routes]

            # EventBased gateway: wait for first event; expose as conditional
            # with special __eventBased__ marker so generator knows semantics
            if gw_type == 'eventBased':
                cond = gateway_conditional_routes(gw, ir1)
                default = cond[0]['route'] if cond else complete_route(task['participantName'])
                for c in cond:
                    c['condition'] = f"__eventBased__{c['condition']}"
                return default, (cond if cond else None)

            # Exclusive / inclusive gateway: conditional routes (default)
            cond = gateway_conditional_routes(gw, ir1)
            default = cond[0]['route'] if cond else complete_route(task['participantName'])
            return default, (cond if cond else None)

        # → converging gateway (pass-through)
        if gw and gw['gatewayDirection'] == 'Converging':
            for gw_out_id in gw['outgoing']:
                sf2 = _sf_by_id(gw_out_id, ir1)
                if sf2:
                    nxt = _task_by_id(sf2['target'], ir1)
                    if nxt:
                        return task_route(nxt), None
            return complete_route(task['participantName']), None

        # → task
        nxt = _task_by_id(tgt, ir1)
        if nxt:
            return task_route(nxt), None

        # → endEvent
        evt = _event_by_id(tgt, ir1)
        if evt and evt['eventType'] == 'endEvent':
            return complete_route(task['participantName']), None

    return complete_route(task['participantName']), None


# ── Wait-condition analysis ───────────────────────────────────────────────────

def build_wait_info(task: dict, ir1: dict) -> tuple:
    """
    Returns (waitCondition: dict | None, extra_writes: list[{task_id, field}]).

    If a task receives messageFlows:
      - single source  → waitCondition.field = state_key_of(source_task)
      - multiple sources → create a combined trigger field
        e.g. soft_cloth_wash_triggered (added to stateSchema by the caller)
    """
    incoming_msgs = [mf for mf in ir1['messageFlows'] if mf['targetRef'] == task['id']]
    if not incoming_msgs:
        return None, []

    source_tasks = [_task_by_id(mf['sourceRef'], ir1) for mf in incoming_msgs]
    source_tasks = [t for t in source_tasks if t]

    if not source_tasks:
        return None, []

    if len(source_tasks) == 1:
        field = state_key_of(source_tasks[0]['name'])
        wc    = {"field": field, "readableLabel": f"Waiting for {source_tasks[0]['name'].lower()}..."}
        return wc, [{"task_id": source_tasks[0]['id'], "field": field}]

    # Multiple sources → combined trigger field
    raw = re.sub(r'[^a-z0-9_]', '_', task['name'].lower().strip())
    combined = re.sub(r'_+', '_', raw).strip('_') + '_triggered'
    wc = {"field": combined, "readableLabel": f"Waiting for {task['name'].lower()} trigger..."}
    return wc, [{"task_id": st['id'], "field": combined} for st in source_tasks]


# ── Main transformer ──────────────────────────────────────────────────────────

def transform_ir1_to_ir2(ir1: dict, project_name: str = None) -> dict:
    """
    Transform IR1 → new-format IR2 (per ir2_structure.json).

    Implements the mapping described in Study_Case_Carwash.md sections 3.2–3.5.
    """
    proj = project_name or pascal(ir1.get('project_name', 'App'))

    # ── Pre-pass: collect all wait-condition relationships ────────────────
    wait_conditions: dict = {}    # task_id → waitCondition dict
    extra_writes:    dict = {}    # source task_id → [extra_field, ...]
    extra_schema:    dict = {}    # new stateSchema fields

    for task in ir1['tasks']:
        wc, writes = build_wait_info(task, ir1)
        if wc:
            wait_conditions[task['id']] = wc
            if len(writes) > 1:
                extra_schema[wc['field']] = False   # combined trigger field
            for w in writes:
                extra_writes.setdefault(w['task_id'], []).append(w['field'])

    # ── State schema ──────────────────────────────────────────────────────
    state_schema = {**ir1['stateSchema'], **extra_schema}

    # ── Roles ─────────────────────────────────────────────────────────────
    roles = [
        {"display": p['name'], "value": role_internal(p['name']), "internal": role_internal(p['name'])}
        for p in ir1['participants']
    ]

    # ── allRoutes ─────────────────────────────────────────────────────────
    all_routes = [
        {
            "route":        task_route(t),
            "role":         role_internal(t['participantName']),
            "component":    pascal(t['name']) + 'Page',
            "allowedRoles": [role_internal(t['participantName'])],
        }
        for t in ir1['tasks']
    ]

    # ── defaultRoutesPerRole ──────────────────────────────────────────────
    default_routes: dict = {}
    for p in ir1['participants']:
        role_val = role_internal(p['name'])
        # Try startEvent successor first
        start_evts = [e for e in ir1['events']
                      if e['processId'] == p['processRef'] and e['eventType'] == 'startEvent']
        first = None
        for se in start_evts:
            for fid in se['outgoing']:
                sf = _sf_by_id(fid, ir1)
                if sf:
                    t = _task_by_id(sf['target'], ir1)
                    if t:
                        first = t
                        break
        # Fallback: first message-triggered task
        if not first:
            mt = msg_triggered_tasks(p['processRef'], ir1)
            first = mt[0] if mt else None
        if first:
            default_routes[role_val] = task_route(first)

    # ── participants[] ────────────────────────────────────────────────────
    participants = []
    for p in ir1['participants']:
        role_val    = role_internal(p['name'])
        module_name = pascal(p['name'])
        ordered     = task_order(p['processRef'], ir1)

        task_entries = []
        for task in ordered:
            tid        = task['id']
            comp_name  = pascal(task['name']) + 'Page'
            route_path = task_route(task)
            wc         = wait_conditions.get(tid)

            next_route, cond_routes = find_next_route(task, ir1)

            page_type = 'wait-then-write' if wc else 'write-navigate'

            # stateWrites: always write the task's _completed flag
            state_writes = [{"field": state_key_of(task['name']), "value": True}]

            # Extra writes for combined-trigger scenario (e.g. Pay8 → soft_cloth_wash_triggered)
            for extra_field in extra_writes.get(tid, []):
                state_writes.append({"field": extra_field, "value": True})

            # Write gateway result if task leads into a gateway
            if cond_routes:
                for sf in ir1['sequenceFlows']:
                    if sf['source'] == tid:
                        gw = _gw_by_id(sf['target'], ir1)
                        if gw and gw['name']:
                            k = re.sub(r'[^a-zA-Z0-9]', '_', gw['name']).lower().strip('_')
                            k = re.sub(r'_+', '_', k)
                            gw_result_key = f"{k}_result"
                            if gw_result_key in state_schema:
                                state_writes.append({
                                    "field": gw_result_key,
                                    "value": "selected condition label",
                                })
                        break

            entry = {
                "taskId":          f"{role_val}-{kebab(task['name'])}",
                "name":            pascal(task['name']),
                "route":           route_path,
                "component":       comp_name,
                "pageType":        page_type,
                "description":     f"{task['participantName']}: {task['name']}.",
                "stateReads":      [],
                "stateWrites":     state_writes,
                "waitCondition":   wc,
                "autoWriteOnMount": None,
                "nextRoute":       next_route,
                "ui": {
                    "title": task['name'],
                    "hint":  f"Page for BPMN task '{task['name']}' ({page_type}).",
                },
            }
            if cond_routes:
                entry["conditionalRoutes"] = cond_routes

            task_entries.append(entry)

        participants.append({
            "name":         module_name,
            "role":         role_val,
            "defaultRoute": default_routes.get(role_val, complete_route(p['name'])),
            "tasks":        task_entries,
        })

    return {
        "project": proj,
        "stack": {
            "framework":   "React 18",
            "language":    "TypeScript",
            "router":      "React Router v6",
            "styling":     "Tailwind CSS",
            "stateLib":    "Zustand",
            "stateImport": "src/shared/state/globalState.ts",
        },
        "sharedContext": {
            "roles":               roles,
            "defaultRoutesPerRole": default_routes,
            "stateSchema":         state_schema,
            "allRoutes":           all_routes,
        },
        "participants": participants,
    }
