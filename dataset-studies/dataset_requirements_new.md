# Dataset Requirements untuk Fine-tuning Qwen2.5-Coder:7B

## Tujuan

Dataset ini digunakan untuk fine-tuning LLM lokal (`qwen2.5-coder:7b` via Ollama) agar mampu men-generate file-file React TypeScript dari IR2 (Intermediate Representation 2) secara akurat dan konsisten.

IR2 adalah representasi terstruktur dari BPMN diagram yang berisi semua informasi yang dibutuhkan LLM untuk menghasilkan satu aplikasi React lengkap.

---

## 1. File Apa Saja yang Harus Di-generate? (App Structure)

Berdasarkan `App_structure.md`, setiap aplikasi terdiri dari **6 core files** dan **N dynamic files**:

### Core Files (6 file, sama untuk semua app)

| # | File | file_type | Deskripsi |
|---|------|-----------|-----------|
| 1 | `src/shared/state/globalState.ts` | `global_state` | Zustand store: auth (sessionStorage) + processState (localStorage + cross-tab sync) |
| 2 | `src/shared/components/ProtectedRoute.tsx` | `protected_route` | Route guard: redirect jika belum login atau role tidak sesuai |
| 3 | `src/shared/components/Layout.tsx` | `layout` | Sidebar + header + Outlet. Navigasi per role, logout, reset process |
| 4 | `src/shared/components/UI.tsx` | `ui_kit` | Komponen atomik: Card, Button, Input |
| 5 | `src/shared/pages/LoginPage.tsx` | `login_page` | Form login: name input + role selector + redirect ke defaultRoute |
| 6 | `src/App.tsx` | `app_root` | BrowserRouter + semua Route statis + ProtectedRoute wrapper |

### Dynamic Files (1 per task BPMN)

| File Pattern | file_type | Deskripsi |
|-------------|-----------|-----------|
| `src/modules/{ModuleName}/pages/{PageName}.tsx` | `dynamic_page` | Satu halaman per BPMN user task, perilaku ditentukan oleh `pageType` |

> Contoh: Self-service-restaurant memiliki 3 participant × rata-rata 6 task = **18 dynamic pages** + 6 core files = **24 file total**.

---

## 2. Analisis Benchmark: Self-service-restaurant

Benchmark app di `generated_app/Self-service-restaurant/` adalah contoh output **yang benar** dan menjadi acuan kualitas dataset.

### 2.1 Arsitektur

```
src/
├── App.tsx                                    ← app_root
├── shared/
│   ├── state/globalState.ts                   ← global_state
│   ├── components/
│   │   ├── Layout.tsx                         ← layout
│   │   ├── ProtectedRoute.tsx                 ← protected_route
│   │   └── UI.tsx                             ← ui_kit
│   └── pages/LoginPage.tsx                    ← login_page
└── modules/
    ├── GuestFoodConsumption/pages/            ← 7 dynamic pages
    ├── EmployeeOrderProcessing/pages/         ← 8 dynamic pages
    └── ChefMealPreparation/pages/             ← 3 dynamic pages
```

### 2.2 Analisis globalState.ts

```typescript
export type Role = 'guest' | 'employee' | 'chef';

type ProcessState = {
    dish?: { name: string; price: number; description: string };
    pendingOrder?: { dishName: string; price: number; instructions: string; tableNumber?: string };
    paymentRequested?: boolean;   // Employee → Guest (cross-role sync)
    paymentReceived?: boolean;    // Guest → Employee
    buzzerSetup?: boolean;
    buzzerOffered?: boolean;      // Employee → Guest
    buzzerTaken?: boolean;        // Guest → Employee
    chefOrder?: { dishName: string; notes: string };  // Employee → Chef
    mealInHatch?: boolean;        // Chef → Employee
    chefInformedEmployee?: boolean; // Chef → Employee
    buzzerRinging?: boolean;      // Employee → Guest
    mealAvailableForGuest?: boolean;
};
```

**Pola penting:**
- Auth menggunakan sessionStorage (per-tab), processState menggunakan localStorage (shared cross-tab)
- Cross-tab sync via `window.dispatchEvent(StorageEvent)` dan `window.addEventListener('storage')`
- Semua field ProcessState bersifat optional (`?`)

### 2.3 Analisis App.tsx

```typescript
// Import statis — SEMUA page di-import eksplisit
import { EnterrestaurantPage } from './modules/GuestFoodConsumption/pages/EnterrestaurantPage';
// ... (28 import total)

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<Layout />}>
          {/* Setiap route ditulis statis sebagai JSX */}
          <Route path="/guest" element={
            <ProtectedRoute allowedRoles={['guest']}>
              <EnterrestaurantPage />
            </ProtectedRoute>
          } />
          {/* ... semua route lainnya ... */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

**Aturan kritis:** Route HARUS statis JSX. DILARANG menggunakan `.map()` atau conditional expression di dalam `<Routes>`.

### 2.4 Analisis LoginPage.tsx

- Form dengan name input + role selector (button per role)
- Menggunakan `lucide-react` icons per role
- `login(name, selectedRole)` lalu `navigate()` berdasarkan role
- Switch-case untuk redirect per role

### 2.5 Analisis Layout.tsx

- Sidebar collapsible dengan navigasi per role
- Theme berbeda per role (warna sidebar, accent)
- Menu items di-filter berdasarkan `user.role`
- Tombol logout + reset simulation
- Header dengan role badge
- `<Outlet />` untuk konten halaman

### 2.6 Analisis ProtectedRoute.tsx

- Cek `isAuthenticated` → redirect ke `/login`
- Cek `allowedRoles.includes(user.role)` → redirect ke home role
- Minimal, ~20 baris

### 2.7 Analisis UI.tsx

- 3 komponen: Card, Button, Input
- Named exports (bukan default)
- Tailwind CSS murni, tidak ada dependency eksternal
- Button memiliki variant (primary/secondary/danger) dan fullWidth prop

### 2.8 Analisis Dynamic Pages — Pola per pageType

Berdasarkan analisis 18 dynamic pages di Self-service-restaurant:

#### pageType: `write-navigate` (6 halaman)

| Halaman | stateWrites | nextRoute |
|---------|------------|-----------|
| EnterrestaurantPage | *(none)* | /guest/choose-dish |
| HandoverbuzzerPage | buzzerOffered: true | /employee/inform-chef |
| HandovermealPage | mealAvailableForGuest: true | /employee/call-guest |
| PlacemealinhatchPage | mealInHatch: true | /chef/inform-employee |
| InformemployeePage | chefInformedEmployee: true | /chef |
| GetmealPage | *(none)* | /guest/eat-meal |

**Pola kode:**
```typescript
export const HandoverbuzzerPage = () => {
  const navigate = useNavigate();
  const { updateProcessState } = useGlobalState();
  const handleClick = () => {
    updateProcessState({ buzzerOffered: true });  // stateWrites
    navigate('/employee/inform-chef');              // nextRoute
  };
  return (
    <Card title="Hand Over Buzzer">
      <p>...</p>
      <Button onClick={handleClick} fullWidth>Confirm Handover</Button>
    </Card>
  );
};
```

#### pageType: `wait-then-write` (3 halaman)

| Halaman | waitCondition | stateWrites | nextRoute |
|---------|--------------|------------|-----------|
| PaymoneyPage | paymentRequested | paymentReceived: true | /guest/take-buzzer |
| TakebuzzerPage | buzzerOffered → buzzerRinging | buzzerTaken: true | /guest/get-meal |
| SetoffbuzzerPage | chefInformedEmployee | buzzerRinging: true | /employee/hand-over-meal |

**Pola kode:**
```typescript
export const PaymoneyPage = () => {
  const { processState, updateProcessState } = useGlobalState();
  const canPay = processState.paymentRequested;  // waitCondition.field

  if (!canPay) {
    return (
      <Card title="...">
        <div className="animate-spin ..."/>         {/* spinner */}
        <p>Waiting for cashier to request payment...</p>  {/* readableLabel sebagai STRING LITERAL */}
      </Card>
    );
  }
  // ... form/button untuk melanjutkan
  const handlePay = () => {
    updateProcessState({ paymentReceived: true });  // stateWrites
    navigate('/guest/take-buzzer');                   // nextRoute
  };
};
```

**KRITIS:** `readableLabel` harus menjadi string literal di JSX, BUKAN `processState.waitCondition.readableLabel` (field itu tidak ada di runtime).

#### pageType: `form-write-navigate` (4 halaman)

| Halaman | stateReads | stateWrites | nextRoute |
|---------|-----------|------------|-----------|
| PlaceorderPage | dish | pendingOrder | /guest/pay-money |
| EnterorderPage | pendingOrder | pendingOrder (+tableNumber) | /employee/collect-money |
| SetupbuzzerPage | *(none)* | buzzerSetup: true | /employee/hand-over-buzzer |
| InformchefPage | pendingOrder | chefOrder | /employee/set-off-buzzer |

**Pola kode:**
```typescript
export const InformchefPage = () => {
  const { processState, updateProcessState } = useGlobalState();
  const [notes, setNotes] = useState(processState.pendingOrder?.instructions || '');
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateProcessState({
      chefOrder: { dishName: processState.pendingOrder?.dishName || '', notes }
    });
    navigate('/employee/set-off-buzzer');
  };
  return (
    <Card title="Inform Chef">
      <form onSubmit={handleSubmit}>
        <Input label="Kitchen Notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <Button type="submit" fullWidth>Send Order to Kitchen</Button>
      </form>
    </Card>
  );
};
```

#### pageType: `read-display-navigate` (1 halaman)

| Halaman | stateReads | nextRoute |
|---------|-----------|-----------|
| PreparemealPage | chefOrder | /chef/place-meal-in-hatch |

**Pola kode:** Membaca state untuk display, tidak memanggil `updateProcessState`. Button navigate saja.

#### pageType: `auto-write-on-mount` (1 halaman)

| Halaman | autoWriteOnMount | waitCondition | nextRoute |
|---------|-----------------|--------------|-----------|
| CollectmoneyPage | paymentRequested: true | paymentReceived | /employee/set-up-buzzer |

**Pola kode:**
```typescript
export const CollectmoneyPage = () => {
  const { processState, updateProcessState } = useGlobalState();
  useEffect(() => {
    if (!processState.paymentRequested) {
      updateProcessState({ paymentRequested: true });  // autoWriteOnMount
    }
  }, []);
  const isPaid = processState.paymentReceived;  // waitCondition
  // ... render waiting/action UI berdasarkan isPaid
};
```

### 2.9 Distribusi pageType di Self-service-restaurant

| pageType | Jumlah | Persentase |
|----------|--------|-----------|
| write-navigate | 6 | 33% |
| wait-then-write | 3 | 17% |
| form-write-navigate | 4 | 22% |
| read-display-navigate | 1 | 6% |
| auto-write-on-mount | 1 | 6% |
| navigate-only (end/start) | 3 | 17% |

---

## 3. Skema IR2 untuk Dataset

Setiap sample di dataset menggunakan context dari IR2. Berikut skema IR2 lengkap:

### 3.1 Top-Level Structure

```json
{
  "project": "SelfServiceRestaurant",
  "stack": {
    "framework": "React 18",
    "language": "TypeScript",
    "router": "React Router v6",
    "styling": "Tailwind CSS",
    "stateLib": "Zustand",
    "stateImport": "src/shared/state/globalState.ts"
  },
  "sharedContext": { ... },
  "participants": [ ... ]
}
```

### 3.2 sharedContext

```json
"sharedContext": {
  "roles": [
    { "display": "Guest", "value": "guest", "internal": "guest" }
  ],
  "defaultRoutesPerRole": {
    "guest": "/guest/enter-restaurant"
  },
  "stateSchema": {
    "paymentRequested": false,
    "paymentReceived": false,
    "dish": null,
    "pendingOrder": null
  },
  "allRoutes": [
    {
      "route": "/guest/pay-money",
      "role": "guest",
      "component": "PaymoneyPage",
      "allowedRoles": ["guest"]
    }
  ]
}
```

### 3.3 participants[] dan tasks[]

```json
{
  "name": "GuestFoodConsumption",
  "role": "guest",
  "defaultRoute": "/guest/enter-restaurant",
  "tasks": [
    {
      "taskId": "guest-pay-money",
      "name": "PayMoney",
      "route": "/guest/pay-money",
      "component": "PaymoneyPage",
      "pageType": "wait-then-write",
      "description": "Guest pays via card. Locked until employee initiates.",
      "stateReads": [
        { "field": "pendingOrder", "use": "display total amount" }
      ],
      "stateWrites": [
        { "field": "paymentReceived", "value": true }
      ],
      "waitCondition": {
        "field": "paymentRequested",
        "readableLabel": "Waiting for cashier to request payment..."
      },
      "autoWriteOnMount": null,
      "nextRoute": "/guest/take-buzzer",
      "conditionalRoutes": null,
      "ui": {
        "title": "Secure Payment",
        "hint": "Card number, expiry, CVC inputs. Disabled until waitCondition true."
      }
    }
  ]
}
```

### 3.4 Field Kritis per tasks[]

| Field | Tipe | Untuk file_type | Fungsi |
|-------|------|----------------|--------|
| `taskId` | string | dynamic_page | ID unik `{role}-{task-name}` |
| `pageType` | enum | dynamic_page | Menentukan pola kode: write-navigate / wait-then-write / form-write-navigate / read-display-navigate / auto-write-on-mount |
| `stateReads[]` | array | dynamic_page | Field processState yang dibaca untuk display |
| `stateWrites[]` | array | dynamic_page | Field processState yang ditulis saat aksi |
| `waitCondition` | object\|null | dynamic_page | Field yang harus truthy sebelum tombol aktif |
| `autoWriteOnMount` | object\|null | dynamic_page | Field yang ditulis otomatis di useEffect on mount |
| `nextRoute` | string | dynamic_page | Target navigate() setelah aksi utama |
| `conditionalRoutes[]` | array\|null | dynamic_page | Gateway: satu Button per entry, bukan satu button dengan hard-coded route |
| `ui.title` | string | dynamic_page | Heading halaman |
| `ui.hint` | string | dynamic_page | Petunjuk layout/interaksi untuk LLM |

### 3.5 Bagian IR2 yang Dipakai per file_type

| file_type | Data IR2 yang dibutuhkan |
|-----------|------------------------|
| `global_state` | `sharedContext.roles`, `sharedContext.stateSchema` |
| `protected_route` | `sharedContext.defaultRoutesPerRole` |
| `layout` | `sharedContext.allRoutes`, `sharedContext.roles`, project name |
| `ui_kit` | *(tidak bergantung IR2 — hampir identik antar app)* |
| `login_page` | `sharedContext.roles`, `sharedContext.defaultRoutesPerRole`, project name |
| `app_root` | `sharedContext.allRoutes`, `sharedContext.defaultRoutesPerRole`, semua import paths |
| `dynamic_page` | `participants[].tasks[]` (satu task = satu sample), `sharedContext.stateSchema` |

---

## 4. Format Dataset

Format **JSONL** (satu record per baris), kompatibel dengan Unsloth/LoRA dan Ollama fine-tuning:

```jsonl
{"messages": [
  {"role": "system",    "content": "<system_prompt sesuai file_type>"},
  {"role": "user",      "content": "<instruksi + IR2 context JSON>"},
  {"role": "assistant", "content": "<kode TypeScript yang benar dan valid>"}
]}
```

### 4.1 System Prompt

Setiap file_type memiliki system prompt tersendiri (didefinisikan di `prompts.py`). System prompt berisi:
- Stack yang digunakan
- Standard imports yang wajib di-copy
- Export rules (named export, bukan default)
- Behavior rules per pageType (untuk dynamic_page)
- OUTPUT CONTRACT: raw TypeScript only, no markdown fences, first line = import

### 4.2 User Message

Berisi instruksi generate + IR2 context JSON yang relevan:

```
Generate the file: src/modules/GuestFoodConsumption/pages/PaymoneyPage.tsx

Context (IR2 excerpt):
{
  "moduleName": "GuestFoodConsumption",
  "role": "guest",
  "task": { ... },
  "stateSchema": { ... }
}
```

### 4.3 Assistant Content (Ground Truth)

Kode TypeScript mentah yang valid dan benar. Harus memenuhi:
- Baris pertama = import statement
- Named export matching component name
- Tidak ada markdown fence
- Dapat di-parse sebagai TypeScript
- Mengikuti pageType behavior rules secara tepat

---

## 5. Kebutuhan Jumlah Sample per file_type

### 5.1 Core Files

| file_type | Min. sample | Variasi yang dibutuhkan |
|-----------|------------|------------------------|
| `global_state` | 10 | Variasi jumlah role (2-4), ukuran stateSchema (5-20 field), tipe field (boolean/string/object) |
| `protected_route` | 5 | Relatif statis, sedikit variasi |
| `layout` | 10 | Variasi jumlah route (5-20), jumlah role (2-4) |
| `ui_kit` | 5 | Hampir identik — agar LLM tidak "berkreasi" |
| `login_page` | 10 | Variasi 2/3/4+ role, nama project berbeda |
| `app_root` | 15 | **Bug-prone** — variasi jumlah route, nama komponen. Harus statis JSX! |

### 5.2 Dynamic Pages

| pageType | Min. sample | Catatan |
|----------|------------|---------|
| `write-navigate` | 30 | Pola paling sederhana |
| `write-navigate` + `conditionalRoutes` | 30 | **Bug-prone** — LLM sering mengabaikan conditionalRoutes |
| `wait-then-write` | 30 | **Bug-prone** — LLM sering mengakses `processState.waitCondition.readableLabel` |
| `wait-then-write` + `conditionalRoutes` | 20 | Kombinasi paling kompleks |
| `form-write-navigate` | 20 | Form dengan input fields |
| `read-display-navigate` | 15 | Read-only display |
| `auto-write-on-mount` | 10 | useEffect + wait pattern |

**Total dynamic_page: ~155 sample**

### 5.3 Total Target

| Kategori | Jumlah |
|----------|--------|
| Core files (6 tipe × rata-rata 9) | ~55 |
| Dynamic pages (7 pola) | ~155 |
| **Total** | **~210 minimum** |
| **Target optimal (LoRA)** | **500–1000** |

---

## 6. Bug yang Harus Dihilangkan oleh Fine-tuning

Tanpa fine-tuning, Qwen2.5-Coder:7B menghasilkan bug berulang berikut (terlihat di `generated_app/CarWashApp/`):

### Bug 1 — conditionalRoutes diabaikan

**Salah:**
```tsx
const handleComplete = () => {
  updateProcessState({ which_wash_program_result: "selected condition label" });
  navigate("/customer/pays-15");  // hard-coded satu route
};
```

**Benar (dari benchmark):**
```tsx
const handleSelect = (condition: string, route: string) => {
  updateProcessState({
    chooses_wash_completed: true,
    which_wash_program_result: condition,  // kondisi yang dipilih
  });
  navigate(route);  // route sesuai condition
};
// Satu Button PER conditionalRoutes entry
<Button onClick={() => handleSelect('ECO', '/customer/pay-8')}>ECO</Button>
<Button onClick={() => handleSelect('Polish Plus', '/customer/pays-15')}>Polish Plus</Button>
```

### Bug 2 — readableLabel diakses dari processState

**Salah:**
```tsx
<p>{processState.waitCondition.readableLabel}</p>
// waitCondition TIDAK ADA di runtime processState
```

**Benar (dari benchmark):**
```tsx
<p>Waiting for cashier to request payment...</p>
// String literal dari IR2 context, bukan akses runtime state
```

### Bug 3 — Route di-generate dengan .map()

**Salah:**
```tsx
{allRoutes.map(route => <Route path={route.route} element={...} />)}
```

**Benar (dari benchmark):**
```tsx
<Route path="/guest" element={<ProtectedRoute allowedRoles={['guest']}><EnterrestaurantPage /></ProtectedRoute>} />
<Route path="/guest/choose-dish" element={...} />
// Setiap route ditulis sebagai JSX statis
```

### Bug 4 — Output minimal tanpa implementasi

**Salah:**
```tsx
export const LoginPage = () => null;
```

---

## 7. Sumber Data yang Tersedia

| Sumber | Jumlah BPMN | Est. tasks | Est. dynamic_page samples |
|--------|-------------|-----------|--------------------------|
| BPMN_ITS | 67 | ~335 | ~335 |
| BPMN_ProcessMind | 4 | ~40 | ~40 |
| BPMN_Camunda | 4 | ~30 | ~30 |
| **Total** | **75** | **~405** | **~405 dynamic_page** |

Ditambah core files (75 BPMN × 6 core file_type = ~450 core samples potensial), total potensi mencapai **~855 samples**. Lebih dari cukup untuk LoRA fine-tuning.

---

## 8. Checkpoint Kualitas per Sample

Setiap sample HARUS lulus semua validasi:

| # | Kriteria | Cara Cek |
|---|---------|----------|
| 1 | Baris pertama = `import` statement | Regex |
| 2 | Named export `export const {ComponentName}` | Regex |
| 3 | Tidak ada markdown fence (` ``` `) | String check |
| 4 | File valid TypeScript | `tsc --noEmit` atau `ts-morph` |
| 5 | Semua `stateWrites` field ada di `updateProcessState()` | Regex |
| 6 | `waitCondition.field` digunakan sebagai kondisi `if` | Regex (untuk wait-then-write) |
| 7 | Semua `conditionalRoutes` → button terpisah | AST/regex check |
| 8 | Import path `'../../../shared/...'` benar | String match |
| 9 | Tidak ada `export default` | String check |
| 10 | `readableLabel` = string literal, bukan `processState.*` | Regex |

---

## 9. Strategi Ground Truth

| Strategi | Kecepatan | Kualitas | Biaya |
|----------|-----------|---------|-------|
| **A. Human-in-the-loop** | Lambat | Tertinggi | Nol (waktu reviewer) |
| **B. GPT-4o / Claude sebagai oracle** | Cepat | Tinggi | Biaya API |
| **C. Template-based code generator** | Sangat cepat | Medium | Nol |

**Rekomendasi:** Strategi C untuk bulk generation pola sederhana (write-navigate, read-display-navigate), Strategi B untuk pola kompleks (conditionalRoutes, wait-then-write), Strategi A untuk review final.

---

## 10. Struktur Folder Dataset

```
dataset-finetune/
├── dataset_Camunda/
│   ├── *_ir1.json, *_ir2.json
│   ├── train.jsonl
│   └── doc.md
├── dataset_ITS/
│   ├── *_ir1.json, *_ir2.json
│   ├── train.jsonl          ← BELUM ADA
│   └── doc.md
├── dataset_ProcessMind/
│   ├── *_ir1.json, *_ir2.json
│   ├── train.jsonl          ← BELUM ADA
│   └── doc.md
└── final/                   ← BELUM ADA
    ├── train.jsonl           ← 80% gabungan semua sumber
    ├── val.jsonl             ← 10%
    └── test.jsonl            ← 10%
```

---

## 11. Ringkasan

| Pertanyaan | Jawaban |
|------------|---------|
| Model target? | Qwen2.5-Coder:7B via Ollama |
| Format dataset? | JSONL instruction-following (system + user + assistant) |
| Berapa file_type? | 7 (global_state, protected_route, layout, ui_kit, login_page, app_root, dynamic_page) |
| Berapa pageType untuk dynamic_page? | 5 (write-navigate, wait-then-write, form-write-navigate, read-display-navigate, auto-write-on-mount) + variant conditionalRoutes |
| Benchmark acuan? | `generated_app/Self-service-restaurant/` (18 pages, 3 roles) |
| Skema IR yang dipakai? | IR2 — berisi project, stack, sharedContext (roles, stateSchema, allRoutes), participants[].tasks[] |
| Minimum samples? | ~210 (core + dynamic), target optimal 500–1000 untuk LoRA |
| Sumber BPMN? | 75 file (ITS 67, ProcessMind 4, Camunda 4) → ~855 samples potensial |
| Bug utama yang diatasi? | conditionalRoutes diabaikan, readableLabel diakses dari processState, .map() route, output minimal |
