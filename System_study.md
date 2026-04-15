# System Study — Pemrosesan IR2 oleh Python untuk Per-File LLM Generation

## Tujuan

Dokumen ini menganalisis bagaimana Python memproses `ir2_structure.json` sehingga setiap pemanggilan LLM menghasilkan **tepat satu file source code**. Ini adalah studi desain untuk pipeline Step 3 (IR2 → generated files).

---

## 1. Gambaran Besar Pipeline

```
ir2.json (data aktual)
     │
     ▼
[Python: decompose()]
     │  — baca sharedContext + participants
     │  — buat flat list "GenerationTask"
     ▼
[List[GenerationTask]]
     │
     ▼  ← loop satu per satu
[Python: build_prompt(task)]
     │  — pilih system prompt per file_type
     │  — inject hanya context yang dibutuhkan task ini
     ▼
[Prompt String]
     │
     ▼
[LLM API Call]
     │
     ▼
[Raw LLM Response]
     │
     ▼
[Python: extract_code(response)]
     │  — strip markdown fences & prose
     │  — validasi baris pertama = import
     ▼
[File Content String]
     │
     ▼
[Python: write_file(task.path, content)]
     │
     ▼
[File tersimpan di output_dir/]
```

---

## 2. Struktur Data: GenerationTask

Python tidak langsung memproses `ir2_structure.json` mentah. Langkah pertama adalah mem-flatten IR2 menjadi list `GenerationTask` — satu entri per file yang akan digenerate.

### Definisi GenerationTask

```python
@dataclass
class GenerationTask:
    path: str           # path file output, e.g. "src/App.tsx"
    file_type: str      # "app_root" | "global_state" | "login_page" |
                        # "layout" | "protected_route" | "ui_kit" | "dynamic_page"
    context: dict       # minimal IR2 data yang dibutuhkan file ini
    order: int          # urutan generate (lihat seksi 3)
```

### Fungsi decompose()

```python
def decompose(ir2: dict) -> list[GenerationTask]:
    tasks = []
    shared = ir2["sharedContext"]
    order = 0

    # -- Core files (urutan tetap) --
    core_map = {
        "src/shared/state/globalState.ts":      "global_state",
        "src/shared/components/ProtectedRoute.tsx": "protected_route",
        "src/shared/components/Layout.tsx":     "layout",
        "src/shared/components/UI.tsx":         "ui_kit",
        "src/shared/pages/LoginPage.tsx":       "login_page",
        "src/App.tsx":                          "app_root",
    }
    for path, file_type in core_map.items():
        tasks.append(GenerationTask(
            path=path,
            file_type=file_type,
            context=build_core_context(file_type, ir2),
            order=order
        ))
        order += 1

    # -- Dynamic pages (satu per task per participant) --
    for participant in ir2["participants"]:
        for task_def in participant["tasks"]:
            tasks.append(GenerationTask(
                path=f"src/modules/{participant['name']}/pages/{task_def['component']}.tsx",
                file_type="dynamic_page",
                context=build_page_context(task_def, participant, shared),
                order=order
            ))
            order += 1

    return tasks
```

**Hasil dari Self-service-restaurant** (22 file):
```
order  0  →  src/shared/state/globalState.ts        [global_state]
order  1  →  src/shared/components/ProtectedRoute.tsx [protected_route]
order  2  →  src/shared/components/Layout.tsx        [layout]
order  3  →  src/shared/components/UI.tsx            [ui_kit]
order  4  →  src/shared/pages/LoginPage.tsx          [login_page]
order  5  →  src/App.tsx                             [app_root]
order  6  →  src/modules/GuestFoodConsumption/pages/EnterrestaurantPage.tsx  [dynamic_page]
order  7  →  src/modules/GuestFoodConsumption/pages/ChoosedishPage.tsx       [dynamic_page]
...
order 21  →  src/modules/ChefMealPreparation/pages/InformemployeePage.tsx    [dynamic_page]
```

---

## 3. Urutan Generate dan Alasan

Urutan **bukan** alfabetis — melainkan berdasarkan dependency:

```
globalState.ts        ← diimpor oleh SEMUA file lain → harus pertama
ProtectedRoute.tsx    ← diimpor oleh App.tsx
Layout.tsx            ← diimpor oleh App.tsx
UI.tsx                ← diimpor oleh dynamic pages
LoginPage.tsx         ← diimpor oleh App.tsx
App.tsx               ← membutuhkan semua di atas
dynamic_pages         ← independen satu sama lain, bisa di-generate paralel
```

Dengan urutan ini, jika LLM melihat contoh file di few-shot prompt, konvensi sudah terbentuk sejak awal dan file-file berikutnya mengikutinya.

---

## 4. Context Injection: Minimal Per File Type

Kunci efisiensi: setiap GenerationTask hanya menyertakan **subset IR2 yang relevan**, bukan seluruh IR2. Ini mengurangi ukuran prompt dan mencegah model terdistraksi.

### Fungsi build_core_context()

```python
def build_core_context(file_type: str, ir2: dict) -> dict:
    shared = ir2["sharedContext"]

    if file_type == "global_state":
        return {
            "roles": shared["roles"],
            "stateSchema": shared["stateSchema"],
        }

    if file_type == "login_page":
        return {
            "roles": shared["roles"],
            "defaultRoutesPerRole": shared["defaultRoutesPerRole"],
        }

    if file_type == "layout":
        return {
            "roles": shared["roles"],
            "allRoutes": shared["allRoutes"],
        }

    if file_type == "protected_route":
        return {
            "defaultRoutesPerRole": shared["defaultRoutesPerRole"],
        }

    if file_type == "app_root":
        return {
            "allRoutes": shared["allRoutes"],
            "defaultRoutesPerRole": shared["defaultRoutesPerRole"],
        }

    if file_type == "ui_kit":
        return {}  # tidak butuh IR2 — komponen statis

    return {}
```

### Fungsi build_page_context()

```python
def build_page_context(task_def: dict, participant: dict, shared: dict) -> dict:
    return {
        "moduleName": participant["name"],
        "role": participant["role"],
        "task": task_def,               # taskId, name, route, pageType,
                                        # description, stateReads, stateWrites,
                                        # waitCondition, autoWriteOnMount,
                                        # nextRoute, ui
        "stateSchema": shared["stateSchema"],  # untuk type-checking di dalam page
    }
```

---

## 5. Konstruksi Prompt

Setiap LLM call menggunakan **dua message**: system prompt (statis per file_type) + user message (dinamis berisi context JSON).

### System Prompt Template per file_type

```python
SYSTEM_PROMPTS = {

    "global_state": """
You are generating src/shared/state/globalState.ts for a React + Zustand app.
Rules:
- Export: type Role, const useGlobalState
- Auth state stored in sessionStorage (isAuthenticated, user object, login(), logout())
- ProcessState stored in localStorage, cross-tab sync via window.dispatchEvent(StorageEvent)
- ProcessState fields come from input stateSchema — use them as optional fields in the type
- updateProcessState(updates: Partial<ProcessState>) merges and writes to localStorage
- resetProcess() clears localStorage and resets processState to {}
OUTPUT CONTRACT: raw TypeScript only, no markdown fences, first line must be an import.
""",

    "login_page": """
You are generating src/shared/pages/LoginPage.tsx.
Rules:
- Render a role selector (dropdown or button group) using input roles[].display as label
- Name text input field
- On submit: call login(name, selectedRole) then navigate to defaultRoutesPerRole[selectedRole]
- Import useGlobalState from ../state/globalState
OUTPUT CONTRACT: raw TypeScript only, no markdown fences, first line must be an import.
""",

    "layout": """
You are generating src/shared/components/Layout.tsx.
Rules:
- Use <Outlet /> from react-router-dom for child routes
- Sidebar or top navbar with navigation links
- Filter allRoutes by user.role to show only relevant links
- Logout button: calls logout() then navigate('/login')
- Reset button: calls resetProcess()
OUTPUT CONTRACT: raw TypeScript only, no markdown fences, first line must be an import.
""",

    "protected_route": """
You are generating src/shared/components/ProtectedRoute.tsx.
Rules:
- If not isAuthenticated: redirect to /login
- If authenticated but wrong role: redirect to defaultRoutesPerRole[user.role]
- Props: allowedRoles: string[], children: ReactNode
OUTPUT CONTRACT: raw TypeScript only, no markdown fences, first line must be an import.
""",

    "ui_kit": """
You are generating src/shared/components/UI.tsx — reusable atomic components.
Components to generate:
- Card: props { title: string, children: ReactNode } — white card with shadow
- Button: props { onClick?, type?, disabled?, fullWidth?, className?, children } — blue primary button
- Input: props { label, value, onChange, placeholder? } — labeled text input
OUTPUT CONTRACT: raw TypeScript only, no markdown fences, first line must be an import.
""",

    "app_root": """
You are generating src/App.tsx — the React Router root.
Rules:
- BrowserRouter > Routes
- Route path="/login" → LoginPage (no protection)
- All other routes wrapped in <Layout /> then <ProtectedRoute allowedRoles={[...]} />
- Use allRoutes[] to register every route and its allowedRoles
- Default route "/" → <Navigate to="/login" />
OUTPUT CONTRACT: raw TypeScript only, no markdown fences, first line must be an import.
""",

    "dynamic_page": """
You are generating a single BPMN task page component for a React app.
Stack: React 18, TypeScript, Tailwind CSS, React Router v6, Zustand.
State access: import { useGlobalState } from '../../../shared/state/globalState'
UI components: import { Card, Button, Input } from '../../../shared/components/UI'
Export the component as a named export: export const {ComponentName} = () => { ... }

pageType logic:
- write-navigate: button click → updateProcessState(stateWrites) → navigate(nextRoute)
- wait-then-write: polling processState[waitCondition.field]; show waiting UI if falsy, activate button if truthy; on click → updateProcessState(stateWrites) → navigate(nextRoute)
- form-write-navigate: <form> with inputs pre-filled from stateReads; on submit → updateProcessState(stateWrites) → navigate(nextRoute)
- read-display-navigate: read stateReads for display; NO updateProcessState; button → navigate(nextRoute)
- auto-write-on-mount: useEffect on mount → updateProcessState({autoWriteOnMount.field: value}); then behave as wait-then-write

OUTPUT CONTRACT: raw TypeScript only, no markdown fences, first line must be an import.
""",
}
```

### User Message Builder

```python
def build_user_message(task: GenerationTask) -> str:
    return f"""Generate the file: {task.path}

Context (IR2 excerpt):
{json.dumps(task.context, indent=2)}

Generate the complete file content now."""
```

---

## 6. Loop Generate Utama

```python
def generate_all(ir2: dict, output_dir: str, llm_client):
    tasks = decompose(ir2)
    results = {}

    for task in tasks:
        print(f"[{task.order+1}/{len(tasks)}] Generating {task.path} ...")

        system_prompt = SYSTEM_PROMPTS[task.file_type]
        user_message  = build_user_message(task)

        raw_response = llm_client.chat(
            system=system_prompt,
            user=user_message,
        )

        code = extract_code(raw_response)

        if not validate(code, task):
            # retry sekali dengan error feedback
            raw_response = llm_client.chat(
                system=system_prompt,
                user=build_retry_message(user_message, code, task),
            )
            code = extract_code(raw_response)

        write_file(output_dir, task.path, code)
        results[task.path] = "ok"

    return results
```

---

## 7. Ekstraksi & Validasi Output

LLM sering menambahkan prose atau markdown fences meskipun sudah dilarang di output contract. Fungsi `extract_code()` membersihkannya:

```python
def extract_code(raw: str) -> str:
    # Strip markdown fences
    raw = re.sub(r'^```[a-z]*\n', '', raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r'\n```$', '', raw.strip())

    # Strip baris prose sebelum import pertama
    lines = raw.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('export '):
            return '\n'.join(lines[i:])

    return raw
```

### Fungsi validate()

```python
def validate(code: str, task: GenerationTask) -> bool:
    # Baris pertama harus import atau export
    first_line = code.strip().split('\n')[0]
    if not (first_line.startswith('import') or first_line.startswith('export')):
        return False

    # dynamic_page harus meng-export nama component yang benar
    if task.file_type == "dynamic_page":
        component = task.context["task"]["component"]
        if f"export const {component}" not in code and f"export default function {component}" not in code:
            return False

    # global_state harus export useGlobalState
    if task.file_type == "global_state":
        if "export const useGlobalState" not in code:
            return False

    return True
```

---

## 8. Retry dengan Error Feedback

Jika `validate()` gagal, Python membangun pesan retry yang spesifik:

```python
def build_retry_message(original_user_msg: str, bad_code: str, task: GenerationTask) -> str:
    issues = []
    first_line = bad_code.strip().split('\n')[0]
    if not first_line.startswith('import'):
        issues.append(f"- First line is not an import statement: '{first_line}'")
    if task.file_type == "dynamic_page":
        component = task.context["task"]["component"]
        if f"export const {component}" not in bad_code:
            issues.append(f"- Missing named export: 'export const {component}'")
    if task.file_type == "global_state":
        if "export const useGlobalState" not in bad_code:
            issues.append("- Missing: 'export const useGlobalState'")

    return f"""Previous attempt had the following issues:
{chr(10).join(issues)}

Fix these issues only and regenerate the complete file.

{original_user_msg}"""
```

---

## 9. Ringkasan: Berapa LLM Call per Proyek?

Untuk Self-service-restaurant (3 participant, 17 task total):

| Kelompok | Jumlah File | LLM Calls |
|---|---|---|
| Core files | 6 | 6 |
| Dynamic pages — Guest (7 task) | 7 | 7 |
| Dynamic pages — Employee (8 task) | 8 | 8 |
| Dynamic pages — Chef (3 task) | 3 | 3 |
| **Total minimum** | **24** | **24** |
| + retry (estimasi 10% fail) | ~2-3 | ~2-3 |
| **Total realistis** | — | **~26** |

Setiap call menghasilkan tepat **satu file** — tidak ada batching, tidak ada array output.

---

## 10. Poin Kritis Desain

| Keputusan | Alasan |
|---|---|
| Satu call = satu file | Model 7b tidak reliabel menghasilkan 20+ file dalam satu call; konteks terlalu besar |
| Context injection minimal | Hindari `instruction dilution` — model 7b mengabaikan instruksi yang terkubur di prompt panjang |
| Urutan fixed (shared → App → modules) | `globalState.ts` mengatur konvensi import; semua file berikutnya mengikutinya via few-shot consistency |
| Validasi sebelum write | Mencegah file korup tersimpan ke disk; retry dengan feedback lebih efektif dari retry blind |
| System prompt terpisah per file_type | Setiap file type butuh instruksi berbeda; satu system prompt umum terlalu ambigu untuk model 7b |
