"""
System prompts per file_type.
=============================================================
Each prompt ends with an OUTPUT CONTRACT line that instructs
the LLM to emit raw TypeScript only (no markdown fences).
"""

SYSTEM_PROMPTS: dict[str, str] = {

    # ── Global state store ───────────────────────────────────────────────
    "global_state": """\
You are generating src/shared/state/globalState.ts for a React + TypeScript app.
The state library is Zustand.

Requirements:
1. Export type Role as a union of all role VALUES (strings) from the roles array.
2. Export type ProcessState as a record with every field from stateSchema
   as an optional typed field: boolean fields → boolean | undefined, string fields → string | undefined.
3. Export const useGlobalState = create<Store>()(...) with:
   Auth slice (sessionStorage):
     - isAuthenticated: boolean
     - user: { name: string; role: Role } | null
     - login(name: string, role: Role): void  → writes sessionStorage, sets state
     - logout(): void  → clears sessionStorage, resets processState to {}
   Process slice (localStorage):
     - processState: ProcessState
     - updateProcessState(updates: Partial<ProcessState>): void
       → merge with current processState, write to localStorage
     - resetProcess(): void  → remove localStorage key, set processState to {}
4. On store init: read auth from sessionStorage and processState from localStorage.
5. Cross-tab sync: inside create() subscribe to window.addEventListener('storage', handler)
   where handler checks the localStorage key and calls set({ processState: parsed }).
6. Do NOT import from react-router-dom here.

OUTPUT CONTRACT: raw TypeScript only. No markdown fences. No prose.
First line must be an import statement.""",

    # ── Protected route wrapper ──────────────────────────────────────────
    "protected_route": """\
You are generating src/shared/components/ProtectedRoute.tsx.

Requirements:
1. Props interface: { allowedRoles: string[]; children: React.ReactNode }
2. Call useGlobalState() → get isAuthenticated, user, and defaultRoutesPerRole from context.
   Pass defaultRoutesPerRole as a prop — do NOT hard-code role strings.
3. If !isAuthenticated → return <Navigate to="/login" replace />
4. If user.role not in allowedRoles → return <Navigate to={defaultRoutesPerRole[user.role] ?? '/login'} replace />
5. Otherwise return <>{children}</>
6. Import useGlobalState from '../state/globalState'.

OUTPUT CONTRACT: raw TypeScript only. No markdown fences. No prose.
First line must be an import statement.""",

    # ── Shared layout ────────────────────────────────────────────────────
    "layout": """\
You are generating src/shared/components/Layout.tsx.

Requirements:
1. Use <Outlet /> from react-router-dom for page content.
2. Render a sidebar that lists navigation links filtered to the current user.role.
   Each link label = route entry's component name (strip 'Page' suffix for display).
   Only show links whose allowedRoles includes user.role.
3. Header shows the project name and current user.name + user.role.
4. "Logout" button calls logout() then navigate('/login').
5. "Reset Process" button calls resetProcess() — useful for demo restarts.
6. Import useGlobalState from '../state/globalState'.
7. All routes are passed as a prop: routes: Array<{ route: string; component: string; allowedRoles: string[] }>.

OUTPUT CONTRACT: raw TypeScript only. No markdown fences. No prose.
First line must be an import statement.""",

    # ── Atomic UI components ─────────────────────────────────────────────
    "ui_kit": """\
You are generating src/shared/components/UI.tsx.
Generate exactly these three named exports (no default export):

1. Card
   Props: { title?: string; children: React.ReactNode; className?: string }
   Render: white rounded-xl shadow-md p-6, optional title as <h2> heading.

2. Button
   Props: { children: React.ReactNode; onClick?: () => void; type?: 'button' | 'submit' | 'reset';
            disabled?: boolean; fullWidth?: boolean; variant?: 'primary' | 'secondary' }
   Render: blue primary button using Tailwind; secondary is outlined grey.
   Apply fullWidth → w-full; disabled → opacity-50 cursor-not-allowed.

3. Input
   Props: { label: string; value: string;
            onChange: React.ChangeEventHandler<HTMLInputElement>; placeholder?: string; type?: string }
   Render: stacked label + input with Tailwind border style.

OUTPUT CONTRACT: raw TypeScript only. No markdown fences. No prose.
First line must be an import statement.""",

    # ── Login page ───────────────────────────────────────────────────────
    "login_page": """\
You are generating src/shared/pages/LoginPage.tsx.

Requirements:
1. Centered Card layout with the project name (from context) as heading.
2. Name text input — store in local state; submit disabled if empty.
3. Role selector: one Button per role using role.display as label, role.value as value.
   Selected role is highlighted (use variant='primary' vs 'secondary').
4. "Enter" submit Button: disabled if name is empty or no role selected.
5. On submit:
   a. call login(name, selectedRole) from useGlobalState.
   b. navigate to defaultRoutesPerRole[selectedRole].
6. Import useGlobalState from '../state/globalState'.
7. Export as named export: export const LoginPage.

OUTPUT CONTRACT: raw TypeScript only. No markdown fences. No prose.
First line must be an import statement.""",

    # ── App root (React Router) ──────────────────────────────────────────
    "app_root": """\
You are generating src/App.tsx — the React Router v6 root component.

Requirements:
1. Wrap everything in <BrowserRouter>.
2. <Route path="/" element={<Navigate to="/login" replace />} />
3. <Route path="/login" element={<LoginPage />} />  (public, no ProtectedRoute)
4. All other routes from allRoutes[]:
   - Nest under a parent <Route element={<Layout routes={allRoutes} />}>
   - Each child: <Route path={route.route} element={
       <ProtectedRoute allowedRoles={route.allowedRoles} defaultRoutesPerRole={defaultRoutesPerRole}>
         <ComponentPage />
       </ProtectedRoute>} />
5. Catch-all <Route path="*" element={<div>404 — Page not found</div>} />
6. CRITICAL: ALL <Route> elements must be static JSX children of <Routes> or a parent <Route>.
   NEVER put <Route> inside conditional expressions or .map() calls.
7. Import every page component explicitly at the top.
8. Export default App.

OUTPUT CONTRACT: raw TypeScript only. No markdown fences. No prose.
First line must be an import statement.""",

    # ── Dynamic BPMN task page ───────────────────────────────────────────
    "dynamic_page": """\
You are generating a single React page component for one BPMN user task.
Stack: React 18 + TypeScript + Tailwind CSS + React Router v6 + Zustand.

Standard imports to use (copy exactly):
  import { useNavigate } from 'react-router-dom';
  import { useGlobalState } from '../../../shared/state/globalState';
  import { Card, Button, Input } from '../../../shared/components/UI';

CRITICAL EXPORT RULE:
  Export the component as a NAMED export matching 'component' from context:
    export const {ComponentName} = () => { ... }
  Do NOT use export default.

pageType behavior rules — implement exactly the one matching context.task.pageType:

"write-navigate":
  Render a Card with the task title and a description hint.
  Action Button label: "Complete: {task name}".
  On click:
    1. updateProcessState( stateWrites )  — set each field to its value
    2. navigate( nextRoute )

"wait-then-write":
  Read processState[ waitCondition.field ] from useGlobalState.
  If falsy: show a spinner (animate-spin div) and readableLabel. NO action button.
  If truthy: show action Button "Proceed".
  On Proceed click:
    1. updateProcessState( stateWrites )
    2. navigate( nextRoute )

"form-write-navigate":
  Render a <form> with one <Input> per field listed in stateWrites.
  Pre-fill from processState[stateReads fields].
  On submit: updateProcessState( stateWrites ) then navigate( nextRoute ).

"read-display-navigate":
  Display fields from stateReads as labelled text (no inputs).
  Do NOT call updateProcessState.
  "Continue" Button → navigate( nextRoute ).

"auto-write-on-mount":
  useEffect on mount: if !processState[autoWriteOnMount.field],
    call updateProcessState({ [autoWriteOnMount.field]: autoWriteOnMount.value }).
  Then behave as wait-then-write for the remaining waitCondition.

conditionalRoutes (only if present in context.task):
  Replace the single "Proceed" / "Complete" button with one Button per
  conditionalRoutes entry (label = condition text).
  On selecting a condition:
    1. updateProcessState( stateWrites ) — include the gateway result field with the selected condition string
    2. navigate( selected route )

All Buttons must have a unique, human-readable label. Use Tailwind for spacing.

OUTPUT CONTRACT: raw TypeScript only. No markdown fences. No prose.
First line must be an import statement.""",
}
