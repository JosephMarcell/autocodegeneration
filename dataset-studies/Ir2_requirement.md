# IR2 Requirement untuk Self-Service Restaurant

Dokumen ini mendefinisikan field-field apa saja yang dibutuhkan dalam IR2 agar LLM dapat men-generate web seperti `Self-service-restaurant` secara akurat dan konsisten.

---

## 1. Plan Analisis: Apa yang Harus Dipetakan dari Source Code ke IR2

Sebelum membuat IR2, lakukan analisis pada web hasil generate dengan urutan berikut:

### Step 1 — Identifikasi Participant & Role
Dari `globalState.ts`, ekstrak type `Role`:
- Setiap nilai adalah **role** (internal string untuk auth dan routing)
- Setiap role → satu **participant** → satu **module folder** (`src/modules/{ModuleName}/`)

Contoh dari Self-service-restaurant:
```
Role: 'guest' | 'employee' | 'chef'
→ Modules: GuestFoodConsumption / EmployeeOrderProcessing / ChefMealPreparation
```

### Step 2 — Identifikasi State Schema (ProcessState)
Dari `globalState.ts`, ekstrak semua field di `ProcessState`:
- Tiap field adalah **shared state** yang ditulis oleh satu role dan dibaca oleh role lain
- Catat **type** (boolean, string, object) dan **default value** (undefined / false / "")
- Tandai **siapa yang menulis** (writer) dan **siapa yang membaca** sebagai kondisi (reader/waiter)

Contoh dari Self-service-restaurant:
```
paymentRequested: boolean   → ditulis Employee (CollectMoney), dibaca Guest (PayMoney) sebagai waitCondition
paymentReceived: boolean    → ditulis Guest (PayMoney), dibaca Employee (CollectMoney) sebagai waitCondition
chefOrder: object           → ditulis Employee (InformChef), dibaca Chef (PrepareMeal) untuk display
chefInformedEmployee: bool  → ditulis Chef (InformEmployee), dibaca Employee (SetoffBuzzer) sebagai waitCondition
```

### Step 3 — Identifikasi Pola Page (pageType)
Dari setiap file `{PageName}Page.tsx`, identifikasi pola dominan:

| pageType | Pola Kode | Contoh File |
|---|---|---|
| `write-navigate` | Klik tombol → `updateProcessState({...})` → `navigate(nextRoute)` | ChoosedishPage, PlaceorderPage |
| `wait-then-write` | Render terbagi: jika kondisi belum terpenuhi → tampil "waiting"; jika terpenuhi → aktifkan tombol → tulis state | PaymoneyPage, CollectmoneyPage, SetoffbuzzerPage |
| `form-write-navigate` | Ada `<form>` → input dikumpulkan → submit → `updateProcessState` → `navigate` | InformchefPage, EnterorderPage |
| `read-display-navigate` | Hanya membaca `processState` untuk tampilan, tidak ada interaksi menulis | PreparemealPage (progress bar), GetmealPage |
| `auto-write-on-mount` | `useEffect` langsung menulis state saat halaman dibuka, tidak perlu interaksi user | CollectmoneyPage (mengatur `paymentRequested: true` saat mount) |

### Step 4 — Identifikasi Cross-Role Dependencies
Setiap `waitCondition` mencerminkan **dependency antar participant**. Peta dependency yang harus ada di IR2:

| Page yang Menunggu | State yang Ditunggu | Ditulis Oleh |
|---|---|---|
| `PaymoneyPage` (Guest) | `paymentRequested` | Employee (CollectmoneyPage, via mount) |
| `CollectmoneyPage` (Employee) | `paymentReceived` | Guest (PaymoneyPage) |
| `TakebuzzerPage` (Guest) | `buzzerOffered` | Employee (HandoverbuzzerPage) |
| `SetoffbuzzerPage` (Employee) | `chefInformedEmployee` | Chef (InformemployeePage) |

### Step 5 — Identifikasi Routing
Dari `App.tsx`, ekstrak semua route:
- Path URL → component → role yang diizinkan
- Default route per role (redirect setelah login)

---

## 2. Struktur IR2 yang Dibutuhkan

### Top-Level Fields

```json
{
  "project": "<NamaApp>",
  "stack": { ... },
  "sharedContext": { ... },
  "participants": [ ... ]
}
```

---

### `stack` — Tidak berubah antar proyek

```json
"stack": {
  "framework": "React 18",
  "language": "TypeScript",
  "router": "React Router v6",
  "styling": "Tailwind CSS",
  "stateLib": "Zustand",
  "stateImport": "src/shared/state/globalState.ts"
}
```

---

### `sharedContext` — Konteks bersama lintas participant

```json
"sharedContext": {
  "roles": [
    { "display": "Guest", "value": "guest", "internal": "guest" }
  ],
  "defaultRoutesPerRole": {
    "guest": "/guest/enter-restaurant"
  },
  "stateSchema": {
    "<fieldName>": "<defaultValue>"
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

**Field `stateSchema`** adalah peta lengkap seluruh field `ProcessState`:
- Key = nama field
- Value = default value (`false`, `""`, `null`, atau contoh shape object jika tipenya object)

---

### `participants[]` — Satu entri per role/participant

```json
{
  "name": "GuestFoodConsumption",
  "role": "guest",
  "defaultRoute": "/guest/enter-restaurant",
  "tasks": [ ... ]
}
```

---

### `tasks[]` — Satu entri per halaman (paling kritis)

Ini adalah field **paling kritis** karena menentukan isi setiap page component.

```json
{
  "taskId": "guest-choose-dish",
  "name": "ChooseDish",
  "route": "/guest/choose-dish",
  "component": "ChoosedishPage",
  "pageType": "write-navigate",
  "description": "Display a menu grid. User selects a dish.",
  "stateReads": [],
  "stateWrites": [
    {
      "field": "dish",
      "value": "{ name, price, description } from selected menu item"
    }
  ],
  "waitCondition": null,
  "autoWriteOnMount": null,
  "nextRoute": "/guest/place-order",
  "ui": {
    "title": "Menu Catalog",
    "hint": "Grid of selectable dishes with name, price, and icon"
  }
}
```

#### Penjelasan setiap field `tasks[]`:

| Field | Tipe | Wajib | Keterangan |
|---|---|---|---|
| `taskId` | string | Ya | ID unik, format: `{role}-{task-name}` |
| `name` | string | Ya | Nama task dalam PascalCase (dipakai untuk component name + halaman) |
| `route` | string | Ya | URL path React Router |
| `component` | string | Ya | Nama component yang akan digenerate (`{name}Page`) |
| `pageType` | enum | Ya | Salah satu dari: `write-navigate`, `wait-then-write`, `form-write-navigate`, `read-display-navigate`, `auto-write-on-mount` |
| `description` | string | Ya | Deskripsi tujuan halaman untuk LLM |
| `stateReads` | array | Ya | Field `processState` yang dibaca untuk display (bukan wait) |
| `stateWrites` | array | Ya | Field `processState` yang ditulis beserta value-nya |
| `waitCondition` | object\|null | Ya | Kondisi yang harus `true` sebelum tombol aktif: `{ field, readableLabel }` |
| `autoWriteOnMount` | object\|null | Ya | State yang langsung ditulis saat halaman dibuka (tanpa interaksi user) |
| `nextRoute` | string | Ya | Route tujuan setelah aksi utama |
| `ui.title` | string | Opsional | Judul halaman |
| `ui.hint` | string | Opsional | Petunjuk UI khusus untuk LLM |

---

## 3. Contoh Lengkap: Mapping Source Code → IR2

### Contoh 1: `PaymoneyPage` (pageType: `wait-then-write`)

**Source code logic:**
```tsx
const canPay = processState.paymentRequested;       // waitCondition
updateProcessState({ paymentReceived: true });       // stateWrites
navigate('/guest/take-buzzer');                      // nextRoute
```

**IR2 yang dibutuhkan:**
```json
{
  "taskId": "guest-pay-money",
  "name": "PayMoney",
  "route": "/guest/pay-money",
  "component": "PaymoneyPage",
  "pageType": "wait-then-write",
  "description": "Guest pays for their order via card. Payment form is locked until employee initiates it.",
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
  "ui": {
    "title": "Secure Payment",
    "hint": "Show card number, expiry, CVC inputs. Disable all until waitCondition is true."
  }
}
```

---

### Contoh 2: `CollectmoneyPage` (pageType: `auto-write-on-mount` + `wait-then-write`)

**Source code logic:**
```tsx
useEffect(() => {
  if (!processState.paymentRequested) {
    updateProcessState({ paymentRequested: true });   // autoWriteOnMount
  }
}, []);
const isPaid = processState.paymentReceived;          // waitCondition
navigate('/employee/set-up-buzzer');                  // nextRoute
```

**IR2 yang dibutuhkan:**
```json
{
  "taskId": "employee-collect-money",
  "name": "CollectMoney",
  "route": "/employee/collect-money",
  "component": "CollectmoneyPage",
  "pageType": "wait-then-write",
  "description": "Employee initiates payment request on mount, then waits for guest to pay.",
  "stateReads": [
    { "field": "pendingOrder", "use": "display amount due" }
  ],
  "stateWrites": [],
  "waitCondition": {
    "field": "paymentReceived",
    "readableLabel": "Waiting for guest to complete payment..."
  },
  "autoWriteOnMount": {
    "field": "paymentRequested",
    "value": true
  },
  "nextRoute": "/employee/set-up-buzzer",
  "ui": {
    "title": "Collect Payment",
    "hint": "Show loading spinner while waiting, green checkmark when paid."
  }
}
```

---

### Contoh 3: `InformchefPage` (pageType: `form-write-navigate`)

**IR2 yang dibutuhkan:**
```json
{
  "taskId": "employee-inform-chef",
  "name": "InformChef",
  "route": "/employee/inform-chef",
  "component": "InformchefPage",
  "pageType": "form-write-navigate",
  "description": "Employee reviews the order and adds kitchen notes before sending to chef.",
  "stateReads": [
    { "field": "pendingOrder", "use": "pre-fill form with dish name and instructions" }
  ],
  "stateWrites": [
    {
      "field": "chefOrder",
      "value": "{ dishName: pendingOrder.dishName, notes: form input }"
    }
  ],
  "waitCondition": null,
  "autoWriteOnMount": null,
  "nextRoute": "/employee/set-off-buzzer",
  "ui": {
    "title": "Inform Chef",
    "hint": "Show order ticket summary + textarea for kitchen notes."
  }
}
```

---

## 4. Ringkasan: Field Minimum yang Harus Ada di IR2

### Untuk `globalState.ts`:
- `sharedContext.roles[]` → `Role` type + login form options
- `sharedContext.stateSchema` → semua field `ProcessState` + default value + type hint

### Untuk `App.tsx`:
- `sharedContext.allRoutes[]` → semua route + component + allowedRoles
- `sharedContext.defaultRoutesPerRole` → redirect setelah login per role

### Untuk setiap page component:
- `pageType` → menentukan template logika yang dipakai
- `stateReads[]` → menentukan apa yang ditampilkan dan dari mana
- `stateWrites[]` → menentukan apa yang ditulis saat aksi user
- `waitCondition` → menentukan kapan tombol/form aktif (cross-role sync)
- `autoWriteOnMount` → menentukan state yang langsung ditulis saat halaman dibuka
- `nextRoute` → menentukan navigasi setelah aksi
- `description` + `ui.hint` → panduan konten UI untuk LLM

