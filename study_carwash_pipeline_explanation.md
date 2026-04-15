# Penjelasan Pipeline: Apakah LLM Dipanggil Berkali-Kali?

**Jawaban singkat: Ya.** LLM dipanggil **satu kali per file** yang dihasilkan, dengan prompt yang **berbeda-beda** untuk setiap file. Pada kasus Car-Wash, itu berarti **minimal 17 kali pemanggilan LLM**.

---

## 1. Gambaran Besar Pipeline

```
Car-Wash.bpmn
    │
    ▼ Step 1: parse_bpmn()
   IR1 (JSON)
    │
    ▼ Step 2: transform_ir1_to_ir2()
   IR2 (JSON)
    │
    ▼ Step 3: generate_all()
         │
         ▼ decompose(ir2)
        [GenerationTask × 17]
         │
         ▼ loop (satu per task)
        build_user_message(task)  ← prompt berbeda tiap iterasi
         │
         ▼
        call_llm(system_prompt, user_message)  ← LLM dipanggil
         │
         ▼ extract_code() → validate()
         │   gagal?
         ▼
        call_llm(system_prompt, retry_msg)     ← retry jika perlu
         │
         ▼
        write_file()  → .tsx / .ts
```

---

## 2. Mengapa Harus Berkali-Kali?

Setiap file React yang dihasilkan memiliki **tujuan, logika, dan konteks yang berbeda**. Tidak mungkin meminta LLM menghasilkan 17 file sekaligus dalam satu prompt karena:

1. **Token limit** — satu response LLM tidak cukup untuk 17 file lengkap.
2. **Konteks berbeda** — `globalState.ts` butuh `stateSchema`, sedangkan `DrivesAwayPage.tsx` butuh `waitCondition` dan `nextRoute`.
3. **Fokus lebih baik** — LLM menghasilkan kode yang lebih akurat saat diberi satu tugas spesifik per call.

---

## 3. Apa yang Berbeda di Setiap Prompt?

Setiap pemanggilan LLM terdiri dari dua bagian:

### 3.1 System Prompt — berubah per `file_type`

| `file_type` | Digunakan untuk |
|---|---|
| `global_state` | `src/shared/state/globalState.ts` |
| `protected_route` | `src/shared/components/ProtectedRoute.tsx` |
| `layout` | `src/shared/components/Layout.tsx` |
| `ui_kit` | `src/shared/components/UI.tsx` |
| `login_page` | `src/shared/pages/LoginPage.tsx` |
| `app_root` | `src/App.tsx` |
| `dynamic_page` | Semua 11 halaman BPMN task (berubah via `{ComponentName}`) |

System prompt untuk `dynamic_page` di-template dengan nama komponen spesifik, misalnya `ChoosesWashPage` vs `DrivesAwayPage`.

### 3.2 User Message — **selalu berbeda**, berisi potongan IR2

Dibangun oleh fungsi `build_user_message()` di `generator.py`:

```python
def build_user_message(task: GenerationTask) -> str:
    ctx_json = json.dumps(task.context, indent=2)
    return (
        f"Generate the file: {task.path}\n\n"
        f"Context (IR2 excerpt):\n{ctx_json}\n\n"
        "Generate the complete file content now. Follow all OUTPUT CONTRACT rules."
    )
```

Setiap task memiliki `task.context` yang berbeda — hanya potongan IR2 yang **relevan** untuk file tersebut saja yang di-inject.

---

## 4. Contoh Perbandingan Prompt Antar File

### Prompt untuk `globalState.ts` (order 0)

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

→ LLM diminta menghasilkan **Zustand/Context store** dengan semua field state.

---

### Prompt untuk `ChoosesWashPage.tsx` (order 7)

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

→ LLM diminta menghasilkan **halaman dengan radio button** + conditional navigation berdasarkan pilihan user.

---

### Prompt untuk `DrivesAwayPage.tsx` (order 10)

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
    "ui": {
      "title": "Waiting for Car Wash",
      "hint": "Spinner until dry_completed is true. Then show Drive Away button."
    }
  }
}
```

→ LLM diminta menghasilkan **halaman polling/spinner** yang menunggu `dry_completed` berubah menjadi `true` sebelum tombol aktif.

---

## 5. Setiap LLM Call Berdiri Sendiri (Stateless)

**Penting:** LLM **tidak memiliki memori** antar-call. Setiap request adalah HTTP POST baru ke Ollama:

```
File 01: POST /api/chat  { messages: [system_global_state, user_context_1] }
File 02: POST /api/chat  { messages: [system_protected_route, user_context_2] }
...
File 17: POST /api/chat  { messages: [system_dynamic_page, user_context_17] }
```

LLM tidak "tahu" bahwa file ke-7 dan file ke-10 adalah bagian dari aplikasi yang sama, kecuali informasi itu di-inject secara eksplisit lewat `user_message`. Konsistensi antar-file dijamin oleh **IR2** — bukan oleh konteks conversation LLM.

---

## 6. Mekanisme Retry

Jika validasi kode gagal, ada **retry otomatis** dengan prompt tambahan yang mendeskripsikan masalahnya:

```python
def build_retry_message(original_msg, bad_code, task):
    issues = []
    if not (first.startswith('import') or first.startswith('export')):
        issues.append("• First line must be an import/export statement.")
    if task.file_type == 'dynamic_page':
        if f'export const {comp}' not in bad_code:
            issues.append(f"• Missing named export: 'export const {comp}'")
    if '```' in bad_code:
        issues.append("• Contains markdown code fences. Output raw TypeScript only.")
    ...
```

Retry prompt = deskripsi masalah + **user message asli diulang** → LLM diminta memperbaiki.

---

## 7. Daftar 17 LLM Calls untuk Car-Wash

| # | File | `file_type` | Konteks Kunci |
|---|---|---|---|
| 01 | `src/shared/state/globalState.ts` | `global_state` | `roles`, `stateSchema` |
| 02 | `src/shared/components/ProtectedRoute.tsx` | `protected_route` | `defaultRoutesPerRole` |
| 03 | `src/shared/components/Layout.tsx` | `layout` | `roles`, `allRoutes` |
| 04 | `src/shared/components/UI.tsx` | `ui_kit` | *(kosong)* |
| 05 | `src/shared/pages/LoginPage.tsx` | `login_page` | `project`, `roles`, `defaultRoutesPerRole` |
| 06 | `src/App.tsx` | `app_root` | `project`, `allRoutes`, `defaultRoutesPerRole` |
| 07 | `.../PullsCarUpToCarWashPage.tsx` | `dynamic_page` | `pageType: write-navigate` |
| 08 | `.../ChoosesWashPage.tsx` | `dynamic_page` | `pageType: write-navigate` + `conditionalRoutes` |
| 09 | `.../Pay8Page.tsx` | `dynamic_page` | `pageType: write-navigate` |
| 10 | `.../Pays15Page.tsx` | `dynamic_page` | `pageType: write-navigate` |
| 11 | `.../DrivesAwayPage.tsx` | `dynamic_page` | `pageType: wait-then-write` + `waitCondition: dry_completed` |
| 12 | `.../SoftClothWashPage.tsx` | `dynamic_page` | `pageType: wait-then-write` + `waitCondition: pay_8 \|\| pays_15` + `conditionalRoutes` |
| 13 | `.../DoublePolishPage.tsx` | `dynamic_page` | `pageType: write-navigate` |
| 14 | `.../ClearCoatProtectionPage.tsx` | `dynamic_page` | `pageType: write-navigate` |
| 15 | `.../WheelLusterWheelCleanPage.tsx` | `dynamic_page` | `pageType: write-navigate` |
| 16 | `.../WheelCleanPage.tsx` | `dynamic_page` | `pageType: write-navigate` |
| 17 | `.../DryPage.tsx` | `dynamic_page` | `pageType: write-navigate` (trigger `dry_completed`) |

**+retry ≈ 2 calls tambahan → total realistis: ~19 LLM calls.**

---

## 8. Kesimpulan

| Pertanyaan | Jawaban |
|---|---|
| Apakah LLM dipanggil berkali-kali? | **Ya**, satu call per file |
| Apakah promptnya berbeda-beda? | **Ya**, system prompt + user message unik per file |
| Apakah LLM ingat response sebelumnya? | **Tidak**, setiap call berdiri sendiri (stateless) |
| Apa yang menjaga konsistensi antar-file? | **IR2** — sumber kebenaran tunggal yang di-inject ke setiap prompt |
| Berapa total call untuk Car-Wash? | **17 minimum, ~19 realistis** |
