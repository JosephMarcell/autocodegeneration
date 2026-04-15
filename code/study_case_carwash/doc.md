# Study Case — Car-Wash Pipeline Documentation

Pipeline otomatis dari file BPMN Car-Wash menjadi source code aplikasi React TypeScript yang siap dikembangkan. Dokumen ini menjelaskan arsitektur, alur kerja, setiap modul, dan cara menjalankan pipeline.

---

## Daftar Isi

1. [Gambaran Umum](#1-gambaran-umum)
2. [Struktur Folder](#2-struktur-folder)
3. [Alur Pipeline](#3-alur-pipeline)
4. [Modul-modul](#4-modul-modul)
   - [bpmn_ir1.py — Parser BPMN → IR1](#41-bpmn_ir1py--parser-bpmn--ir1)
   - [ir1_ir2.py — Transformer IR1 → IR2](#42-ir1_ir2py--transformer-ir1--ir2)
   - [prompts.py — System Prompts LLM](#43-promptspy--system-prompts-llm)
   - [generator.py — Generator File React](#44-generatorpy--generator-file-react)
   - [main.py — Entry Point CLI](#45-mainpy--entry-point-cli)
5. [Format IR1](#5-format-ir1)
6. [Format IR2](#6-format-ir2)
7. [pageType dan Perilaku Halaman](#7-pagetype-dan-perilaku-halaman)
8. [Output yang Dihasilkan](#8-output-yang-dihasilkan)
9. [Cara Menjalankan](#9-cara-menjalankan)
10. [Contoh Nyata: Car-Wash](#10-contoh-nyata-car-wash)

---

## 1. Gambaran Umum

Pipeline ini mengimplementasikan studi kasus dari `Study_Case_Carwash.md`. Tujuannya adalah mengotomatisasi pembuatan aplikasi web React dari sebuah file BPMN Collaboration, tanpa menulis kode secara manual.

```
Car-Wash.bpmn
    │
    ▼ [Step 1: bpmn_ir1.py]
  IR1 (dict Python)
    │
    ▼ [Step 2: ir1_ir2.py]
  IR2 (dict Python / JSON)
    │
    ▼ [Step 3: generator.py + prompts.py]
  LLM (Ollama qwen2.5-coder:7b)
    │
    ▼
  React TypeScript source files
  (Zustand + React Router v6 + Tailwind CSS)
```

**Stack yang dihasilkan:**
- React 18 + TypeScript
- React Router v6
- Zustand (global state)
- Tailwind CSS

**Model LLM:** `qwen2.5-coder:7b` via Ollama (`http://localhost:11434`)

---

## 2. Struktur Folder

```
code/study_case_carwash/
├── bpmn_ir1.py          # Step 1: parse BPMN XML → IR1
├── ir1_ir2.py           # Step 2: transform IR1 → IR2
├── prompts.py           # System prompts LLM per file_type
├── generator.py         # Step 3: decompose IR2 → LLM → tulis file
├── main.py              # Entry point CLI
├── requirements.txt     # Dependensi Python (requests)
├── doc.md               # Dokumen ini
│
├── ir1_carwash.json     # (opsional, dibuat bila --save-ir)
└── ir2_carwash.json     # (opsional, dibuat bila --save-ir)
```

Output dihasilkan ke:
```
generated_app/CarWashApp/
└── src/
    ├── App.tsx
    ├── shared/
    │   ├── state/
    │   │   └── globalState.ts
    │   ├── components/
    │   │   ├── Layout.tsx
    │   │   ├── ProtectedRoute.tsx
    │   │   └── UI.tsx
    │   └── pages/
    │       └── LoginPage.tsx
    └── modules/
        ├── Customer/
        │   └── pages/
        │       ├── PullsCarUpToCarWashPage.tsx
        │       ├── ChoosesWashPage.tsx
        │       ├── Pays15Page.tsx
        │       ├── Pay8Page.tsx
        │       └── DrivesAwayPage.tsx
        └── CarWashMachine/
            └── pages/
                ├── SoftClothWashPage.tsx
                ├── DoublePolishPage.tsx
                ├── WheelCleanPage.tsx
                ├── ClearCoatProtectionPage.tsx
                ├── WheelLusterWheelCleanPage.tsx
                └── DryPage.tsx
```

---

## 3. Alur Pipeline

### Step 1 — BPMN → IR1 (`bpmn_ir1.py`)

Membaca XML BPMN dan mengekstrak semua elemen struktural ke dalam IR1 (Intermediate Representation level 1). IR1 bersifat structural — hanya memindahkan data dari XML ke Python dict tanpa logika aplikasi.

### Step 2 — IR1 → IR2 (`ir1_ir2.py`)

Menambahkan semantik aplikasi ke IR1. Setiap task diberi:
- `pageType` — jenis perilaku halaman React
- `waitCondition` — field state yang ditunggu (jika task menerima messageFlow)
- `conditionalRoutes` — pilihan navigasi (jika task menuju gateway divergen)
- `stateWrites` — field state yang ditulis saat task selesai
- `nextRoute` — route tujuan setelah task selesai

### Step 3 — IR2 → Files (`generator.py` + `prompts.py`)

IR2 di-decompose menjadi daftar `GenerationTask`. Setiap task menghasilkan satu file React. Untuk setiap file, sistem membangun pasangan prompt (system + user) lalu memanggil LLM. Hasil divalidasi; jika gagal, dilakukan satu kali retry dengan deskripsi masalah.

---

## 4. Modul-modul

### 4.1 `bpmn_ir1.py` — Parser BPMN → IR1

**Fungsi utama:** `parse_bpmn(xml_string: str) -> dict`

**Yang diparse:**
| Elemen BPMN | Hasil di IR1 |
|---|---|
| `<participant>` | `ir1['participants']` |
| `<process>` | dipetakan ke participant via `proc_to_participant` |
| `<userTask>`, `<task>`, dst. | `ir1['tasks']` |
| `<exclusiveGateway>`, dst. | `ir1['gateways']` (dengan `gatewayDirection` auto-inferred) |
| `<startEvent>`, `<endEvent>`, dst. | `ir1['events']` |
| `<sequenceFlow>` | `ir1['sequenceFlows']` |
| `<messageFlow>` | `ir1['messageFlows']` |

**Auto-derivasi `stateSchema`:**
- Setiap task menghasilkan field boolean: `{task_name_snake}_completed`
- Setiap gateway divergen menghasilkan field string: `{gateway_name_snake}_result`

**Catatan namespace:** Parser mendukung prefix `bpmn:` dan `bpmn2:` secara otomatis karena matching dilakukan by URI (`http://www.omg.org/spec/BPMN/20100524/MODEL`).

---

### 4.2 `ir1_ir2.py` — Transformer IR1 → IR2

**Fungsi utama:** `transform_ir1_to_ir2(ir1: dict, project_name: str) -> dict`

#### Urutan Task (`task_order`)

Proses dengan `startEvent` (misal: Customer):
1. Task-task yang dapat dicapai via sequenceFlow dari startEvent — diurutkan secara topologis
2. Message-triggered tasks (task yang menerima messageFlow) — ditambahkan di akhir

Proses tanpa `startEvent` (misal: Car Wash Machine):
1. Message-triggered tasks sebagai entry point — ditaruh di awal
2. Successor tasks via sequenceFlow — diurutkan secara topologis

#### Penentuan `pageType`

| Kondisi | pageType |
|---|---|
| Task menerima messageFlow | `wait-then-write` |
| Task biasa (tidak menerima messageFlow) | `write-navigate` |

#### Penentuan `waitCondition`

Jika satu task menerima messageFlow dari **satu sumber**:
```json
{ "field": "dry_completed", "readableLabel": "Waiting for dry..." }
```

Jika satu task menerima messageFlow dari **beberapa sumber** (multi-source):
- Dibuat synthetic state field: `{task_name_snake}_triggered`
- Field ini ditambahkan ke `stateSchema` dengan nilai awal `false`
- Setiap task sumber mendapatkan extra `stateWrite` untuk field ini

Contoh: `SoftClothWash` menerima messageFlow dari `Pay8` dan `Pays15`:
```json
"waitCondition": { "field": "soft_cloth_wash_triggered", "readableLabel": "Waiting for customer payment..." }
```
Dan `Pay8` serta `Pays15` keduanya mendapat tambahan `stateWrite`:
```json
{ "field": "soft_cloth_wash_triggered", "value": true }
```

#### Penentuan `nextRoute`

| Kondisi | nextRoute |
|---|---|
| Outgoing → task biasa | route task tersebut |
| Outgoing → diverging gateway | default route dari cabang pertama + `conditionalRoutes` |
| Outgoing → converging gateway | route task setelah gateway |
| Outgoing → endEvent | `/role/complete` |
| Tidak ada outgoing (terminal) | route message-triggered task pertama di participant yang sama, atau `/role/complete` |

#### Helper Functions

| Fungsi | Transformasi |
|---|---|
| `pascal(s)` | `'car wash machine'` → `'CarWashMachine'` |
| `kebab(s)` | `'Car Wash Machine'` → `'car-wash-machine'` |
| `state_key_of(name)` | `'Dry'` → `'dry_completed'` |
| `role_internal(name)` | `'Car Wash Machine'` → `'carwashmachine'` |

---

### 4.3 `prompts.py` — System Prompts LLM

**Ekspor:** `SYSTEM_PROMPTS: dict[str, str]`

Berisi 7 system prompt, masing-masing untuk satu `file_type`:

| Key | File yang Dihasilkan |
|---|---|
| `global_state` | `src/shared/state/globalState.ts` |
| `protected_route` | `src/shared/components/ProtectedRoute.tsx` |
| `layout` | `src/shared/components/Layout.tsx` |
| `ui_kit` | `src/shared/components/UI.tsx` |
| `login_page` | `src/shared/pages/LoginPage.tsx` |
| `app_root` | `src/App.tsx` |
| `dynamic_page` | Setiap halaman task BPMN |

Setiap prompt diakhiri dengan **OUTPUT CONTRACT**:
```
OUTPUT CONTRACT: raw TypeScript only. No markdown fences. No prose.
First line must be an import statement.
```

Prompt `dynamic_page` menjelaskan semua 5 perilaku `pageType` dan cara menangani `conditionalRoutes`.

---

### 4.4 `generator.py` — Generator File React

#### `GenerationTask` (dataclass)

```python
@dataclass
class GenerationTask:
    path:      str   # path relatif output, mis. 'src/shared/state/globalState.ts'
    file_type: str   # kunci ke SYSTEM_PROMPTS
    context:   dict  # irisan IR2 yang relevan
    order:     int   # urutan generasi (0-based)
```

#### `decompose(ir2) -> list[GenerationTask]`

Menghasilkan daftar task terurut:
1. 6 core infrastructure files (urutan tetap)
2. Dynamic pages per participant, per task (urutan dari IR2)

Total untuk Car-Wash: **17 file** (6 core + 5 Customer pages + 6 Machine pages)

#### Alur Generasi Per File

```
build_user_message(task)
        │
        ▼
call_llm(system_prompt, user_message)
        │
        ▼
extract_code(raw)         ← strip markdown fences, skip prose
        │
        ▼
validate(code, task)
        │
   ┌────┴────┐
  ok        fail
   │          │
write_file  build_retry_message  →  call_llm (attempt 2)
                                         │
                                    validate again
                                    ┌────┴────┐
                                   ok        fail
                                    │          │
                                write_file  write_file
                                           + warning header
```

#### `validate(code, task)`

Pengecekan ringan (tidak mengeksekusi kode):
- Baris pertama harus `import` / `export` / `//`
- `dynamic_page`: harus ada `export const {ComponentName}`
- `global_state`: harus ada `export const useGlobalState`
- Tidak boleh ada backtick ` ``` `

#### `call_llm(system, user, model, base_url)`

- Endpoint: `POST {base_url}/api/chat`
- Parameter: `temperature=0.2`, `num_predict=2048`, `stream=false`
- Timeout: 180 detik

---

### 4.5 `main.py` — Entry Point CLI

**Fungsi:** Orkestrasi ketiga step pipeline via argumen CLI.

```
python main.py [OPSI]
```

| Argumen | Default | Keterangan |
|---|---|---|
| `--bpmn FILE` | `dataset/BPMN_ProcessMind/Car-Wash.bpmn` | Path file BPMN |
| `--ir2 FILE` | — | Muat IR2 dari JSON (skip Step 1 & 2) |
| `--output DIR` | `generated_app/CarWashApp` | Folder output |
| `--model NAME` | `qwen2.5-coder:7b` | Nama model Ollama |
| `--ollama URL` | `http://localhost:11434` | URL base Ollama |
| `--step {ir1,ir2,generate,all}` | `all` | Berhenti setelah step tertentu |
| `--save-ir` | false | Simpan `ir1_carwash.json` dan `ir2_carwash.json` |
| `--dry-run` | false | Build prompt saja, tidak panggil LLM |

---

## 5. Format IR1

```json
{
  "project_name": "Car-Wash",
  "participants": [
    { "id": "...", "name": "Customer", "processRef": "Process_1" }
  ],
  "proc_to_participant": { "Process_1": "Customer" },
  "tasks": [
    {
      "id": "task_1", "name": "Chooses Wash",
      "processId": "Process_1", "participantName": "Customer",
      "incoming": ["sf_1"], "outgoing": ["sf_2"]
    }
  ],
  "gateways": [
    {
      "id": "gw_1", "name": "Which wash program?",
      "type": "exclusiveGateway", "gatewayDirection": "Diverging",
      "processId": "Process_1",
      "incoming": ["sf_2"], "outgoing": ["sf_3", "sf_4"]
    }
  ],
  "events": [
    {
      "id": "ev_1", "eventType": "startEvent",
      "processId": "Process_1",
      "incoming": [], "outgoing": ["sf_0"]
    }
  ],
  "sequenceFlows": [
    { "id": "sf_2", "source": "task_1", "target": "gw_1", "condition": null }
  ],
  "messageFlows": [
    { "id": "mf_1", "sourceRef": "task_dry", "targetRef": "task_drives_away" }
  ],
  "stateSchema": {
    "chooses_wash_completed": false,
    "which_wash_program_result": ""
  }
}
```

---

## 6. Format IR2

```json
{
  "project": "CarWashApp",
  "stack": {
    "framework": "React 18", "language": "TypeScript",
    "router": "React Router v6", "styling": "Tailwind CSS",
    "stateLib": "Zustand", "stateImport": "src/shared/state/globalState.ts"
  },
  "sharedContext": {
    "roles": [
      { "display": "Customer", "value": "customer", "internal": "customer" }
    ],
    "defaultRoutesPerRole": {
      "customer": "/customer/pulls-car-up-to-car-wash"
    },
    "stateSchema": {
      "chooses_wash_completed": false,
      "soft_cloth_wash_triggered": false
    },
    "allRoutes": [
      {
        "route": "/customer/chooses-wash",
        "role": "customer",
        "component": "ChoosesWashPage",
        "allowedRoles": ["customer"]
      }
    ]
  },
  "participants": [
    {
      "name": "Customer", "role": "customer",
      "defaultRoute": "/customer/pulls-car-up-to-car-wash",
      "tasks": [
        {
          "taskId": "customer-chooses-wash",
          "name": "ChoosesWash",
          "route": "/customer/chooses-wash",
          "component": "ChoosesWashPage",
          "pageType": "write-navigate",
          "description": "Customer: Chooses Wash.",
          "stateReads": [],
          "stateWrites": [
            { "field": "chooses_wash_completed", "value": true }
          ],
          "waitCondition": null,
          "autoWriteOnMount": null,
          "nextRoute": "/customer/pays-15",
          "conditionalRoutes": [
            { "route": "/customer/pays-15", "condition": "Pays15" },
            { "route": "/customer/pay-8",   "condition": "Pay8" }
          ],
          "ui": {
            "title": "Chooses Wash",
            "hint": "Page for BPMN task 'Chooses Wash' (write-navigate)."
          }
        }
      ]
    }
  ]
}
```

---

## 7. `pageType` dan Perilaku Halaman

### `write-navigate`
Halaman aksi sederhana. Satu tombol "Complete: {nama task}". Saat diklik: tulis `stateWrites` ke global state, lalu navigasi ke `nextRoute`.

### `wait-then-write`
Halaman menunggu. Baca `processState[waitCondition.field]`:
- **false / undefined** → tampilkan spinner + `waitCondition.readableLabel`. Tombol tidak ada.
- **true** → tampilkan tombol "Proceed". Saat diklik: tulis `stateWrites`, navigasi ke `nextRoute`.

### `form-write-navigate`
Halaman dengan form input. Render `<Input>` per field di `stateWrites`. Saat submit: tulis semua field ke state, navigasi ke `nextRoute`.

### `read-display-navigate`
Halaman tampilan data. Tampilkan field dari `stateReads` sebagai teks. Tidak memanggil `updateProcessState`. Tombol "Continue" → navigasi ke `nextRoute`.

### `auto-write-on-mount`
`useEffect` saat mount: jika `processState[autoWriteOnMount.field]` belum diset, tulis nilainya. Kemudian berlaku seperti `wait-then-write`.

### `conditionalRoutes`
Jika task memiliki field `conditionalRoutes`, ganti tombol tunggal dengan satu tombol per kondisi. Setiap tombol menuliskan `stateWrites` (termasuk gateway result) dan navigasi ke route yang sesuai.

---

## 8. Output yang Dihasilkan

### Core Infrastructure (6 file)

| # | File | Isi |
|---|---|---|
| 1 | `src/shared/state/globalState.ts` | Zustand store: auth (sessionStorage) + processState (localStorage) + cross-tab sync |
| 2 | `src/shared/components/ProtectedRoute.tsx` | Guard route berdasarkan `allowedRoles` |
| 3 | `src/shared/components/Layout.tsx` | Sidebar + header + Outlet, sidebar filter per role |
| 4 | `src/shared/components/UI.tsx` | Komponen atomik: `Card`, `Button`, `Input` |
| 5 | `src/shared/pages/LoginPage.tsx` | Form login dengan pilih nama dan role |
| 6 | `src/App.tsx` | React Router v6 root dengan semua route statik |

### Dynamic Pages (per task BPMN)

Setiap halaman di-generate oleh prompt `dynamic_page` dengan konteks task spesifik dari IR2. Named export wajib sesuai `component` field dari IR2.

---

## 9. Cara Menjalankan

### Prasyarat

```powershell
# Install dependensi Python
pip install -r requirements.txt

# Pastikan Ollama berjalan dengan model yang benar
ollama serve
ollama pull qwen2.5-coder:7b
```

### Perintah Umum

```powershell
# Jalankan pipeline penuh
python main.py

# Dry-run (cek prompt tanpa panggil LLM)
python main.py --dry-run

# Simpan IR1 dan IR2 sebagai file JSON untuk inspeksi
python main.py --step ir2 --save-ir

# Hanya parse BPMN ke IR1
python main.py --step ir1 --save-ir

# Gunakan IR2 yang sudah ada (skip Step 1 & 2)
python main.py --ir2 ir2_carwash.json

# Output ke folder kustom
python main.py --output ../../generated_app/MyCarWash
```

### Setelah Generate

Output di `generated_app/CarWashApp/src/` adalah file-file TypeScript yang perlu digabungkan ke project Vite:

```powershell
# Di folder generated_app/CarWashApp (atau buat baru):
npm create vite@latest . -- --template react-ts
npm install react-router-dom zustand
npm install -D tailwindcss @tailwindcss/vite
# Salin/timpa folder src/ dengan hasil generate
npm run dev
```

---

## 10. Contoh Nyata: Car-Wash

### Diagram Proses

```
Customer:
  PullsCarUpToCarWash → ChoosesWash →[gateway]→ Pays15 ──┐
                                              → Pay8   ──┤
                                                          │ (messageFlow)
  DrivesAway ←──────────────────────────────────────────(wait)

Car Wash Machine:
  SoftClothWash ←─────── (messageFlow dari Pays15 + Pay8, multi-source)
  SoftClothWash →[gateway]→ DoublePolish → ClearCoatProtection → Dry → (end)
                          → WheelClean  → WheelLusterWheelClean → Dry → (end)
  Dry ──────────────────────────────────────────────────────→ (messageFlow ke DrivesAway)
```

### Hasil IR2 — Poin Penting

**`SoftClothWash`** (multi-source messageFlow):
```json
{
  "pageType": "wait-then-write",
  "waitCondition": {
    "field": "soft_cloth_wash_triggered",
    "readableLabel": "Waiting for customer payment..."
  }
}
```
Field `soft_cloth_wash_triggered` ditambahkan ke `stateSchema` secara otomatis.

**`Pays15` dan `Pay8`** (terminal, tidak ada outgoing sequenceFlow):
```json
{
  "stateWrites": [
    { "field": "pays_15_completed", "value": true },
    { "field": "soft_cloth_wash_triggered", "value": true }
  ],
  "nextRoute": "/customer/drives-away"
}
```

**`ChoosesWash`** (menuju gateway divergen):
```json
{
  "nextRoute": "/customer/pays-15",
  "conditionalRoutes": [
    { "route": "/customer/pays-15", "condition": "Pays15" },
    { "route": "/customer/pay-8",   "condition": "Pay8" }
  ]
}
```

**`DrivesAway`** (menunggu `Dry`):
```json
{
  "pageType": "wait-then-write",
  "waitCondition": {
    "field": "dry_completed",
    "readableLabel": "Waiting for car wash to finish..."
  }
}
```

### Ringkasan 17 File yang Dihasilkan

| # | File | pageType / type |
|---|---|---|
| 1 | `src/shared/state/globalState.ts` | `global_state` |
| 2 | `src/shared/components/ProtectedRoute.tsx` | `protected_route` |
| 3 | `src/shared/components/Layout.tsx` | `layout` |
| 4 | `src/shared/components/UI.tsx` | `ui_kit` |
| 5 | `src/shared/pages/LoginPage.tsx` | `login_page` |
| 6 | `src/App.tsx` | `app_root` |
| 7 | `src/modules/Customer/pages/PullsCarUpToCarWashPage.tsx` | `write-navigate` |
| 8 | `src/modules/Customer/pages/ChoosesWashPage.tsx` | `write-navigate` + `conditionalRoutes` |
| 9 | `src/modules/Customer/pages/Pays15Page.tsx` | `write-navigate` |
| 10 | `src/modules/Customer/pages/Pay8Page.tsx` | `write-navigate` |
| 11 | `src/modules/Customer/pages/DrivesAwayPage.tsx` | `wait-then-write` |
| 12 | `src/modules/CarWashMachine/pages/SoftClothWashPage.tsx` | `wait-then-write` + `conditionalRoutes` |
| 13 | `src/modules/CarWashMachine/pages/DoublePolishPage.tsx` | `write-navigate` |
| 14 | `src/modules/CarWashMachine/pages/WheelCleanPage.tsx` | `write-navigate` |
| 15 | `src/modules/CarWashMachine/pages/ClearCoatProtectionPage.tsx` | `write-navigate` |
| 16 | `src/modules/CarWashMachine/pages/WheelLusterWheelCleanPage.tsx` | `write-navigate` |
| 17 | `src/modules/CarWashMachine/pages/DryPage.tsx` | `write-navigate` |
