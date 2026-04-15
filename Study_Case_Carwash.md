# Study Case: Implementasi Pipeline pada Car-Wash.bpmn

**Objektif:** Menelusuri bagaimana pipeline `System_study.md` memproses BPMN Car-Wash dari awal (BPMN XML) hingga akhir (per-file LLM generation).

**Source:** `dataset/BPMN_ProcessMind/Car-Wash.bpmn`

---

## 1. Analisis BPMN Car-Wash

### 1.1 Participant & Process

| Participant | Process ID | Role (internal) |
|---|---|---|
| Customer | Process_id-54d8a5a1 | `customer` |
| Car Wash Machine | Process_id-ba446fe3 | `carwashmachine` |

### 1.2 Peta Task per Participant

**Customer (5 task):**
```
StartEvent → Pulls car up to car wash → Chooses wash → [Gateway: Which wash program?]
                                                          ├── "ECO"         → Pay 8
                                                          └── "Polish Plus" → Pays 15
                                                       Drives away → EndEvent
```

**Car Wash Machine (6 task):**
```
Soft Cloth Wash → [Gateway: Which wash program?]
                     ├── "ECO"         → Wheel Clean ──────────────────────→ Dry
                     └── "Polish Plus" → Double Polish → Clear Coat Protection → Wheel Luster Wheel Clean → Dry
```

### 1.3 Message Flows (Cross-Participant Communication)

| # | Source (sender) | Target (receiver) | Arti |
|---|---|---|---|
| 1 | Customer: **Pay 8** | Machine: **Soft Cloth Wash** | Pembayaran ECO memicu proses cuci |
| 2 | Customer: **Pays 15** | Machine: **Soft Cloth Wash** | Pembayaran Polish Plus memicu proses cuci |
| 3 | Machine: **Dry** | Customer: **Drives away** | Selesai cuci memicu customer pergi |

### 1.4 Gateway

| Gateway | Tipe | Arah | Kondisi |
|---|---|---|---|
| Which wash program? (Customer) | Exclusive | Diverging | `ECO` → Pay 8, `Polish Plus` → Pays 15 |
| Which wash program? (Machine) | Exclusive | Diverging | `ECO` → Wheel Clean, `Polish Plus` → Double Polish |

---

## 2. Step 1 → IR1: Apa yang Dihasilkan Parser

`main.py: parse_bpmn_to_json()` mengekstrak struktur berikut dari Car-Wash.bpmn:

```
IR1.roles         = [Customer, Car Wash Machine]
IR1.tasks         = 11 task (5 Customer + 6 Machine)
IR1.events        = [1 startEvent, 1 endEvent]
IR1.gateways      = [2 exclusiveGateway — masing-masing participant]
IR1.sequenceFlows = 13 flow (7 Customer + 6 Machine)
IR1.messageFlows  = 3 flow (cross-participant)
IR1.stateSchema   = auto-generated dari nama task + gateway:
```

**stateSchema yang dihasilkan otomatis:**
```json
{
  "drives_away_completed": false,
  "pulls_car_up_to_car_wash_completed": false,
  "chooses_wash_completed": false,
  "pay_8_completed": false,
  "pays_15_completed": false,
  "double_polish_completed": false,
  "dry_completed": false,
  "wheel_luster_wheel_clean_completed": false,
  "soft_cloth_wash_completed": false,
  "wheel_clean_completed": false,
  "clear_coat_protection_completed": false,
  "which_wash_program_result": ""
}
```

**Catatan kritis:** State schema hanya berisi boolean `_completed` per task dan `_result` per gateway. Ini cukup untuk BPMN sederhana tanpa data passing antar-participant.

---

## 3. Step 2 → IR2: Apa yang Dihasilkan Transformer

IR2 untuk Car-Wash mengikuti `ir2_structure.json`. Berikut trace dari IR1 ke IR2:

### 3.1 sharedContext

```
IR1.roles → IR2.sharedContext.roles:
  [{ display: "Customer", value: "customer" },
   { display: "Car Wash Machine", value: "carwashmachine" }]

IR1.stateSchema → IR2.sharedContext.stateSchema (copy langsung)

IR1.tasks + sequenceFlows → IR2.sharedContext.allRoutes (11 route)
IR1.startEvent per process → IR2.sharedContext.defaultRoutesPerRole:
  { customer: "/customer/pulls-car-up-to-car-wash",
    carwashmachine: "/carwashmachine/soft-cloth-wash" }
```

### 3.2 participants[]

```
IR1.roles[0] "Customer" → IR2.participants[0]:
  name: "Customer"
  role: "customer"
  tasks: [5 task entries]

IR1.roles[1] "Car Wash Machine" → IR2.participants[1]:
  name: "CarWashMachine"
  role: "carwashmachine"
  tasks: [6 task entries]
```

### 3.3 Mapping Task → pageType

Berdasarkan IR1 task properties dan flow analysis:

| Task | pageType | Alasan |
|---|---|---|
| Pulls car up to car wash | `write-navigate` | Langsung complete → navigate |
| Chooses wash | `write-navigate` + `conditionalRoutes` | Gateway split setelah task → 2 opsi |
| Pay 8 | `write-navigate` | Action → complete → messageFlow ke Machine |
| Pays 15 | `write-navigate` | Action → complete → messageFlow ke Machine |
| Drives away | `wait-then-write` | **Menunggu** messageFlow dari Dry → baru aktif |
| Soft Cloth Wash | `wait-then-write` + `conditionalRoutes` | **Menunggu** messageFlow dari Pay 8/Pays 15, lalu gateway split |
| Wheel Clean | `write-navigate` | Langsung complete → navigate ke Dry |
| Double Polish | `write-navigate` | Langsung complete → navigate |
| Clear Coat Protection | `write-navigate` | Langsung complete → navigate |
| Wheel Luster Wheel Clean | `write-navigate` | Langsung complete → navigate ke Dry |
| Dry | `write-navigate` | Complete → trigger messageFlow ke Customer |

### 3.4 Cross-Role Dependencies dari Message Flows

| waitCondition.field | Ditulis Oleh | Dibaca Oleh |
|---|---|---|
| `pay_8_completed` \|\| `pays_15_completed` | Customer (Pay 8 / Pays 15) | Machine (Soft Cloth Wash) |
| `dry_completed` | Machine (Dry) | Customer (Drives away) |

### 3.5 Contoh Task Entry Lengkap

**ChoosesWashPage — write-navigate dengan conditionalRoutes:**
```json
{
  "taskId": "customer-chooses-wash",
  "name": "ChoosesWash",
  "route": "/customer/chooses-wash",
  "component": "ChoosesWashPage",
  "pageType": "write-navigate",
  "description": "Customer selects wash program: ECO ($8) or Polish Plus ($15).",
  "stateReads": [],
  "stateWrites": [
    { "field": "chooses_wash_completed", "value": true },
    { "field": "which_wash_program_result", "value": "selected option string" }
  ],
  "waitCondition": null,
  "autoWriteOnMount": null,
  "conditionalRoutes": [
    { "route": "/customer/pay-8", "condition": "ECO" },
    { "route": "/customer/pays-15", "condition": "Polish Plus" }
  ],
  "nextRoute": "/customer/pays-15",
  "ui": {
    "title": "Choose Wash Program",
    "hint": "Radio buttons or card selector with 2 options: ECO and Polish Plus."
  }
}
```

**DrivesAwayPage — wait-then-write (menunggu message flow):**
```json
{
  "taskId": "customer-drives-away",
  "name": "DrivesAway",
  "route": "/customer/drives-away",
  "component": "DrivesAwayPage",
  "pageType": "wait-then-write",
  "description": "Customer waits for car wash to complete (Dry), then drives away.",
  "stateReads": [],
  "stateWrites": [
    { "field": "drives_away_completed", "value": true }
  ],
  "waitCondition": {
    "field": "dry_completed",
    "readableLabel": "Waiting for car wash to finish..."
  },
  "autoWriteOnMount": null,
  "nextRoute": "/customer/complete",
  "ui": {
    "title": "Waiting for Car Wash",
    "hint": "Show waiting spinner until dry_completed is true. Then show 'Drive Away' button."
  }
}
```

---

## 4. Step 3 → decompose(): Daftar GenerationTask

Setelah IR2 terbentuk, `decompose()` menghasilkan flat list berikut:

```
order   path                                                         file_type
─────   ──────────────────────────────────────────────────────────   ─────────────
  0     src/shared/state/globalState.ts                              global_state
  1     src/shared/components/ProtectedRoute.tsx                     protected_route
  2     src/shared/components/Layout.tsx                             layout
  3     src/shared/components/UI.tsx                                 ui_kit
  4     src/shared/pages/LoginPage.tsx                               login_page
  5     src/App.tsx                                                  app_root
  6     src/modules/Customer/pages/PullsCarUpToCarWashPage.tsx       dynamic_page
  7     src/modules/Customer/pages/ChoosesWashPage.tsx               dynamic_page
  8     src/modules/Customer/pages/Pay8Page.tsx                      dynamic_page
  9     src/modules/Customer/pages/Pays15Page.tsx                    dynamic_page
 10     src/modules/Customer/pages/DrivesAwayPage.tsx                dynamic_page
 11     src/modules/CarWashMachine/pages/SoftClothWashPage.tsx       dynamic_page
 12     src/modules/CarWashMachine/pages/DoublePolishPage.tsx        dynamic_page
 13     src/modules/CarWashMachine/pages/ClearCoatProtectionPage.tsx dynamic_page
 14     src/modules/CarWashMachine/pages/WheelLusterWheelCleanPage.tsx dynamic_page
 15     src/modules/CarWashMachine/pages/WheelCleanPage.tsx          dynamic_page
 16     src/modules/CarWashMachine/pages/DryPage.tsx                 dynamic_page
```

**Total: 17 file → 17 LLM calls minimum**

---

## 5. Step 3 → Contoh Prompt yang Dibangun

### 5.1 globalState.ts (order 0)

**System prompt:** `SYSTEM_PROMPTS["global_state"]`

**User message (context yang di-inject):**
```json
{
  "roles": [
    { "display": "Customer", "value": "customer" },
    { "display": "Car Wash Machine", "value": "carwashmachine" }
  ],
  "stateSchema": {
    "drives_away_completed": false,
    "pulls_car_up_to_car_wash_completed": false,
    "chooses_wash_completed": false,
    "pay_8_completed": false,
    "pays_15_completed": false,
    "double_polish_completed": false,
    "dry_completed": false,
    "wheel_luster_wheel_clean_completed": false,
    "soft_cloth_wash_completed": false,
    "wheel_clean_completed": false,
    "clear_coat_protection_completed": false,
    "which_wash_program_result": ""
  }
}
```

### 5.2 ChoosesWashPage.tsx (order 7) — dynamic_page dengan conditional routes

**System prompt:** `SYSTEM_PROMPTS["dynamic_page"]` (dengan `{ComponentName}` = `ChoosesWashPage`)

**User message (context yang di-inject):**
```json
{
  "moduleName": "Customer",
  "role": "customer",
  "task": {
    "taskId": "customer-chooses-wash",
    "name": "ChoosesWash",
    "component": "ChoosesWashPage",
    "pageType": "write-navigate",
    "description": "Customer selects wash program: ECO ($8) or Polish Plus ($15).",
    "stateWrites": [
      { "field": "chooses_wash_completed", "value": true },
      { "field": "which_wash_program_result", "value": "selected option" }
    ],
    "conditionalRoutes": [
      { "route": "/customer/pay-8", "condition": "ECO" },
      { "route": "/customer/pays-15", "condition": "Polish Plus" }
    ],
    "nextRoute": "/customer/pays-15",
    "ui": { "title": "Choose Wash Program", "hint": "Radio/card selector with 2 options" }
  },
  "stateSchema": { "...12 fields..." }
}
```

### 5.3 DrivesAwayPage.tsx (order 10) — dynamic_page dengan waitCondition

**User message (context yang di-inject):**
```json
{
  "moduleName": "Customer",
  "role": "customer",
  "task": {
    "taskId": "customer-drives-away",
    "component": "DrivesAwayPage",
    "pageType": "wait-then-write",
    "stateWrites": [{ "field": "drives_away_completed", "value": true }],
    "waitCondition": {
      "field": "dry_completed",
      "readableLabel": "Waiting for car wash to finish..."
    },
    "nextRoute": "/customer/complete",
    "ui": { "title": "Waiting for Car Wash", "hint": "Spinner until dry_completed, then Drive Away button" }
  }
}
```

---

## 6. Estimasi LLM Calls

| Kelompok | File | Calls |
|---|---|---|
| Core files | 6 | 6 |
| Customer pages | 5 | 5 |
| CarWashMachine pages | 6 | 6 |
| **Total minimum** | **17** | **17** |
| + retry (~10%) | | ~2 |
| **Total realistis** | | **~19** |

---

## 7. Temuan & Masalah pada IR2 Existing (`Car-Wash_IR/ir2.json`)

Saat membandingkan IR2 yang sudah ada dengan struktur `ir2_structure.json`, ditemukan beberapa **gap**:

### 7.1 Masalah: Tidak Ada `participants[]` Array

IR2 existing menggunakan `tasks[]` flat (bukan nested di `participants[].tasks[]`). Setiap task entry berisi metadata lengkap per-file (path, group, schema, constraints).

**Dampak:** `decompose()` di System_study tidak bisa langsung memproses IR2 existing — perlu adaptor.

**Solusi:** Migrasi IR2 ke format `ir2_structure.json` yang sudah didefinisikan, atau tulis adaptor yang mem-parse `tasks[].group` untuk mengelompokkan ke participants.

### 7.2 Masalah: Tidak Ada `pageType` / `waitCondition` / `stateWrites`

IR2 existing menggunakan `input.uiType: "action"` untuk semua task — **tidak membedakan** antara `write-navigate` dan `wait-then-write`. Semua page diperlakukan identik.

**Dampak:** LLM tidak tahu bahwa `DrivesAwayPage` harus menunggu `dry_completed` sebelum tombol aktif. Semua page akan sama — klik tombol → navigate.

**Solusi:** Tambahkan field `pageType`, `waitCondition`, `stateReads`, `stateWrites` dari analysis message flows + gateway conditions.

### 7.3 Masalah: Message Flow Tidak Terpetakan ke waitCondition

3 message flow di BPMN tidak memiliki representasi di IR2 existing. Hanya ada `conditionalRoutes` untuk gateway, tapi tidak ada mekanisme **cross-participant waiting**.

**Solusi:** Untuk setiap message flow, generate:
- `waitCondition` di task target (receiver)
- `stateWrites` yang sesuai di task source (sender)

### 7.4 Masalah: `defaultRoutesPerRole.carwashmachine` Salah

IR2 existing: `"/carwashmachine/double-polish"` — ini bukan task pertama Machine.

Task pertama Machine adalah `Soft Cloth Wash` (menerima message flow dari Customer). Default route seharusnya: `"/carwashmachine/soft-cloth-wash"`.

---

## 8. Ringkasan

### Pipeline berjalan untuk Car-Wash.bpmn?

**Secara struktural: Ya** — BPMN → IR1 → IR2 → decompose → 17 GenerationTask → 17 LLM calls.

### Gap utama yang perlu ditutup:

| # | Gap | Prioritas |
|---|---|---|
| 1 | IR2 format lama (`tasks[]` flat) vs format baru (`participants[].tasks[]`) | Tinggi |
| 2 | Tidak ada `pageType` / `waitCondition` di IR2 existing | Tinggi |
| 3 | Message flows tidak dipetakan ke cross-role state dependencies | Tinggi |
| 4 | Default route carwashmachine salah | Sedang |
| 5 | `conditionalRoutes` belum ada di `ir2_structure.json` — perlu ditambahkan | Sedang |

### Fitur baru yang dibutuhkan di `ir2_structure.json`:

`conditionalRoutes` — field opsional di `tasks[]` untuk gateway-driven routing:
```json
"conditionalRoutes": [
  { "route": "/customer/pay-8", "condition": "ECO" },
  { "route": "/customer/pays-15", "condition": "Polish Plus" }
]
```

Ini dipetakan ke UI **selector** (radio buttons / dropdown) di halaman, dan LLM harus menggunakan `which_wash_program_result` state untuk menyimpan pilihan.
