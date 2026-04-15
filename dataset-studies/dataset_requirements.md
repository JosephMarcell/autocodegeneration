# Dataset untuk Spesialisasi LLM: React Code Generation dari IR2

**Konteks:** Pipeline ini menggunakan LLM lokal (default: `qwen2.5-coder:7b` via Ollama) dengan prompt engineering murni. Agar LLM menghasilkan kode React yang lebih akurat dan konsisten, dibutuhkan **fine-tuning dataset** berbentuk pasangan `(input: system+user prompt) → (output: file TypeScript yang benar)`.

---

## Motivasi: Bug pada Output LLM Saat Ini

Tanpa fine-tuning, ada pola kegagalan berulang yang terlihat di `generated_app/CarWashApp/`:

### Bug 1 — `ChoosesWashPage.tsx`: `conditionalRoutes` diabaikan

**Yang seharusnya:** Dua button terpisah — "ECO" navigate ke `/customer/pay-8`, "Polish Plus" navigate ke `/customer/pays-15`.

**Yang dihasilkan LLM:**
```tsx
// Hanya satu button — navigate ke nextRoute saja, conditionalRoutes diabaikan
const handleComplete = () => {
  updateProcessState({ which_wash_program_result: "selected condition label" });
  navigate("/customer/pays-15");  // hard-coded, tidak conditional
};
```

### Bug 2 — `DrivesAwayPage.tsx`: akses field yang tidak ada di runtime state

**Yang dihasilkan LLM:**
```tsx
<p>{processState.waitCondition.readableLabel}</p>
// SALAH: waitCondition bukan field di Zustand store
// readableLabel hanya ada di IR2, bukan di runtime state
```

**Yang benar:**
```tsx
<p>Waiting for car wash to finish...</p>  // string literal dari context.task.waitCondition.readableLabel
```

### Bug 3 — `App.tsx`: `<Route>` dibuat dengan `.map()` meskipun dilarang eksplisit di OUTPUT CONTRACT

---

Bug-bug ini terjadi karena model tidak pernah melihat contoh **yang benar** untuk pola spesifik pipeline ini. Fine-tuning dengan dataset yang tepat akan menghilangkan pola kegagalan ini.

---

## 1. Format Dataset

Format **JSONL** (satu record per baris), kompatibel dengan Unsloth/LoRA, QLoRA, dan Ollama fine-tuning:

```jsonl
{"messages": [
  {"role": "system",    "content": "<system_prompt untuk file_type ini>"},
  {"role": "user",      "content": "<build_user_message() output untuk task ini>"},
  {"role": "assistant", "content": "<file TypeScript yang benar dan valid>"}
]}
```

Format ini kompatibel dengan:
- **Ollama** fine-tuning (Modelfile + dataset)
- **Unsloth / LoRA** fine-tuning untuk model seperti Qwen2.5-Coder, DeepSeek-Coder
- **OpenAI fine-tuning API** (untuk perbandingan)

---

## 2. Cakupan yang Dibutuhkan

Dataset harus merepresentasikan **semua kombinasi** dari dua dimensi utama:

### Dimensi A: `file_type` (7 tipe)

| `file_type` | Min. contoh | Catatan |
|---|---|---|
| `global_state` | 10 | Variasi: jumlah role berbeda, stateSchema besar/kecil |
| `protected_route` | 5 | Relatif statis — sedikit variasi struktural |
| `layout` | 10 | Variasi jumlah route, jumlah role |
| `ui_kit` | 5 | Hampir tidak berubah — perlu agar LLM tidak "kreatif" |
| `login_page` | 10 | Variasi: 2 role, 3 role, 4+ role |
| `app_root` | 15 | Variasi jumlah route, nama komponen — bug prone |
| `dynamic_page` | **150+** | ← paling kritis, lihat Dimensi B |

### Dimensi B: `pageType` untuk `dynamic_page` (5 pola + kombinasi)

| `pageType` | Min. contoh | Status |
|---|---|---|
| `write-navigate` | 30 | Pola paling sederhana |
| `write-navigate` + `conditionalRoutes` | 30 | **Bug prone** — Bug 1 di atas |
| `wait-then-write` | 30 | **Bug prone** — Bug 2 di atas |
| `wait-then-write` + `conditionalRoutes` | 20 | Kombinasi paling kompleks |
| `form-write-navigate` | 20 | Form dengan multiple Input fields |
| `read-display-navigate` | 15 | Read-only display page |
| `auto-write-on-mount` | 10 | useEffect + wait pattern |

**Total `dynamic_page`: ~155 contoh**

> Rasio lebih banyak pada pola yang bug-prone karena LLM membutuhkan lebih banyak contoh
> untuk menginternalisasi pola yang tidak umum di training data publiknya.

---

## 3. Sumber Data yang Sudah Tersedia di Workspace

Dataset tidak harus dibuat dari nol. Ada sumber primer yang sudah tersedia:

### 3.1 BPMN_ITS — 67 Proses BPMN

`dataset/BPMN_ITS/` berisi 67 file BPMN dari sistem koperasi karyawan:

```
1.  User management
2.  Add new member
3.  Make a cash transaction
4.  Display member list
5.  Change work unit
6.  Make a report of the mandatory savings bill
7.  Make a report on validation of mandatory savings
8.  Make a report on mandatory savings account book
9.  Displays the history of moving work units
10. Login
11–67. (kasus tambahan)
```

Setiap BPMN dapat diparsing menjadi IR1 → IR2, dan setiap task dalam IR2 menjadi satu training sample untuk `dynamic_page`. Dari 67 proses dengan rata-rata 5 task per proses, ini menghasilkan **~335 contoh `dynamic_page`** potensial.

### 3.2 BPMN_ProcessMind — 4 Proses

`dataset/BPMN_ProcessMind/` berisi:
- `Car-Wash.bpmn` — sudah dianalisis, 11 task
- `Pizza-Store.bpmn`
- `Recruitment-and-Selection.bpmn`
- `Smart-Parking.bpmn`

### 3.3 BPMN_Camunda — 4 Proses

`dataset/BPMN_Camunda/` berisi proses standar bisnis yang lebih kompleks (Dispatch of Goods, Recourse, dll.).

### Total Potensi Training Samples

| Sumber | Proses | Est. tasks | Est. samples |
|---|---|---|---|
| BPMN_ITS | 67 | ~400 | ~400 `dynamic_page` + ~67 `app_root` |
| BPMN_ProcessMind | 4 | ~40 | ~40 `dynamic_page` + 4 set core files |
| BPMN_Camunda | 4 | ~30 | ~30 `dynamic_page` + 4 set core files |
| **Total** | **75** | **~470** | **~550 samples** |

Dengan 75 BPMN yang sudah ada, target **500 samples berkualitas tinggi** untuk LoRA fine-tuning sangat realistis.

---

## 4. Cara Menghasilkan Dataset (Pipeline Otomatis)

Dataset dapat di-generate dengan memperluas pipeline yang sudah ada:

```
dataset/BPMN_*/**.bpmn
        │
        ▼ parse_bpmn() → IR1
        ▼ transform_ir1_to_ir2() → IR2
        ▼ decompose(IR2) → [GenerationTask × N]
        │
        ▼ untuk setiap task:
           input  = build_user_message(task)               ← sudah ada di generator.py
           output = generate_reference_code(task)          ← PERLU DIBUAT
        │
        ▼ validate(code, task) == True
        ▼ simpan sebagai JSONL record
```

### Strategi untuk Ground Truth Output

| Strategi | Kecepatan | Kualitas | Biaya |
|---|---|---|---|
| **A. Human-in-the-loop** | Lambat | Tertinggi | Nol (waktu reviewer) |
| **B. GPT-4o / Claude sebagai oracle** | Cepat | Tinggi | Biaya API |
| **C. Template-based code generator** | Sangat cepat | Rendah | Nol |

**Rekomendasi:** Strategi B untuk bulk generation (>80% samples), Strategi A untuk pola yang sering
gagal (`conditionalRoutes`, `wait-then-write`).

---

## 5. Anatomi Satu Training Sample

### 5.1 Record lengkap untuk `DrivesAwayPage.tsx` (perbaikan Bug 2)

```jsonl
{
  "messages": [
    {
      "role": "system",
      "content": "You are generating a single React page component for one BPMN user task.\nStack: React 18 + TypeScript + Tailwind CSS + React Router v6 + Zustand.\n...\npageType: wait-then-write\n  Read processState[ waitCondition.field ] from useGlobalState.\n  If falsy: show spinner and readableLabel STRING LITERAL from context — NOT from processState.\n  If truthy: show action Button.\n  On click: updateProcessState(stateWrites) then navigate(nextRoute).\n\nOUTPUT CONTRACT: raw TypeScript only. No markdown fences."
    },
    {
      "role": "user",
      "content": "Generate the file: src/modules/Customer/pages/DrivesAwayPage.tsx\n\nContext (IR2 excerpt):\n{\n  \"task\": {\n    \"component\": \"DrivesAwayPage\",\n    \"pageType\": \"wait-then-write\",\n    \"stateWrites\": [{\"field\": \"drives_away_completed\", \"value\": true}],\n    \"waitCondition\": {\"field\": \"dry_completed\", \"readableLabel\": \"Waiting for car wash to finish...\"},\n    \"nextRoute\": \"/customer/complete\",\n    \"ui\": {\"title\": \"Waiting for Car Wash\"}\n  }\n}"
    },
    {
      "role": "assistant",
      "content": "import { useNavigate } from 'react-router-dom';\nimport { useGlobalState } from '../../../shared/state/globalState';\nimport { Card, Button } from '../../../shared/components/UI';\n\nexport const DrivesAwayPage = () => {\n  const navigate = useNavigate();\n  const { processState, updateProcessState } = useGlobalState();\n\n  if (!processState.dry_completed) {\n    return (\n      <Card title=\"Waiting for Car Wash\">\n        <div className=\"flex flex-col items-center gap-4 py-8\">\n          <div className=\"animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600\" />\n          <p className=\"text-gray-600\">Waiting for car wash to finish...</p>\n        </div>\n      </Card>\n    );\n  }\n\n  const handleProceed = () => {\n    updateProcessState({ drives_away_completed: true });\n    navigate('/customer/complete');\n  };\n\n  return (\n    <Card title=\"Waiting for Car Wash\">\n      <Button onClick={handleProceed} fullWidth>Drive Away</Button>\n    </Card>\n  );\n};"
    }
  ]
}
```

**Hal kritis yang harus benar di bagian `assistant`:**
- `"Waiting for car wash to finish..."` adalah **string literal** dari `context.task.waitCondition.readableLabel` — bukan `processState.waitCondition.readableLabel`
- `updateProcessState` didapat dari destructuring `useGlobalState()`, bukan import terpisah
- Spinner menggunakan Tailwind murni, bukan teks `"Loading..."`

---

### 5.2 Record untuk `ChoosesWashPage.tsx` (perbaikan Bug 1)

Output yang **benar** untuk `conditionalRoutes`:

```tsx
import { useNavigate } from 'react-router-dom';
import { useGlobalState } from '../../../shared/state/globalState';
import { Card, Button } from '../../../shared/components/UI';

export const ChoosesWashPage = () => {
  const navigate = useNavigate();
  const { updateProcessState } = useGlobalState();

  const handleSelect = (condition: string, route: string) => {
    updateProcessState({
      chooses_wash_completed: true,
      which_wash_program_result: condition,
    });
    navigate(route);
  };

  return (
    <Card title="Choose Wash Program">
      <p className="text-gray-600 mb-6">Radio/card selector with 2 options</p>
      <div className="flex flex-col gap-3">
        <Button onClick={() => handleSelect('ECO', '/customer/pay-8')} fullWidth>
          ECO
        </Button>
        <Button
          onClick={() => handleSelect('Polish Plus', '/customer/pays-15')}
          variant="secondary"
          fullWidth
        >
          Polish Plus
        </Button>
      </div>
    </Card>
  );
};
```

**Hal kritis:** Setiap entry di `conditionalRoutes` → satu `<Button>` tersendiri, bukan satu button dengan hard-coded `nextRoute`.

---

## 6. Checkpoint Kualitas per Sample

Setiap sample harus lulus semua kriteria berikut sebelum disimpan ke dataset:

| Kriteria | Cara Validasi |
|---|---|
| Baris pertama adalah `import` statement | `validate()` di `generator.py` |
| Named export `export const {ComponentName}` ada | `validate()` |
| Tidak ada markdown fences (` ``` `) | `validate()` |
| File dapat di-parse sebagai TypeScript valid | `tsc --noEmit` atau `ts-morph` |
| Semua field dari `stateWrites` digunakan di `updateProcessState()` | Regex check |
| `waitCondition.field` digunakan sebagai kondisi `if` | Regex check untuk `wait-then-write` |
| Semua `conditionalRoutes` diimplementasi sebagai button terpisah | AST / regex check |
| Import path `'../../../shared/...'` benar | String match |
| Tidak ada `export default` | String check |
| `readableLabel` muncul sebagai string literal, bukan `processState.*` | Regex check |

---

## 7. Ukuran Dataset yang Disarankan

| Tujuan | Jumlah samples | Keterangan |
|---|---|---|
| **LoRA fine-tuning** (QLoRA, Unsloth) model 7B | 500–1000 | Efisien, realistis dengan dataset yang ada |
| **Full fine-tuning** model kecil (≤3B) | 2000–5000 | Perlu lebih banyak sumber BPMN |
| **Few-shot injection** langsung di prompt | 5–10 per `file_type` | Tanpa fine-tuning, efek segera tapi terbatas |

---

## 8. Struktur Folder Dataset yang Disarankan

```
dataset/
├── BPMN_Camunda/          ← sumber BPMN (sudah ada)
├── BPMN_ITS/              ← sumber BPMN (sudah ada)
├── BPMN_ProcessMind/      ← sumber BPMN (sudah ada)
└── finetune/              ← BARU
    ├── raw/               ← output mentah dari oracle LLM (perlu review)
    │   ├── global_state/
    │   ├── dynamic_page/
    │   │   ├── write_navigate/
    │   │   ├── wait_then_write/
    │   │   ├── conditional_routes/
    │   │   ├── form_write_navigate/
    │   │   └── read_display_navigate/
    │   └── app_root/
    ├── reviewed/          ← sudah diverifikasi manusia
    ├── train.jsonl        ← 80% untuk training
    ├── val.jsonl          ← 10% untuk validasi
    └── test.jsonl         ← 10% untuk evaluasi final
```

---

## 9. Ringkasan

| Pertanyaan | Jawaban |
|---|---|
| Format dataset? | JSONL instruction-following (system + user + assistant) |
| Berapa samples minimal? | ~500 (LoRA), ~2000 (full fine-tune) |
| Tipe file yang paling butuh contoh? | `dynamic_page` dengan `conditionalRoutes` dan `wait-then-write` |
| Sumber data sudah ada? | Ya — 75 BPMN di `dataset/` → ~550 samples potensial |
| Cara generate ground truth? | GPT-4o/Claude sebagai oracle + human review untuk kasus edge |
| Tools yang dibutuhkan? | Script Python: BPMN → IR2 → JSONL (extend `generator.py`) |
| Efek yang diharapkan? | LLM tidak lagi: mengabaikan `conditionalRoutes`, mengakses `processState.waitCondition`, membuat `<Route>` dengan `.map()` |
