# Alur Pengerjaan — AutoCodeGeneration

## Rencana

1. Formulasi algoritma python utk parser ( BPMN -> IR1 -> IR2)
2. Pengerjaan dataset ( ambil dataset BPMN -> IR1 -> IR2)
    - Struktur App 
    J:\react PRA TA\AutoCodeGeneration\struktur-app
    - study case ( ambil sample BPMN -> IR1 -> IR2 -> App )
    CONTOH -> J:\react PRA TA\AutoCodeGeneration\generated_app\Self-service-restaurant 
    - pembuatan dataset (semua BPMN -> IR1 -> IR2 -> JSONL)
    - Validasi dataset
3. Finetuning
4. Evaluasi 
5. Buat sistem keseluruhan ( upload BPMN -> Proses -> App )

---

## Evaluasi Progress (per 15 April 2026)

### 1. Formulasi Algoritma Parser (BPMN → IR1 → IR2) — ✅ SELESAI

| Komponen | File | Status |
|----------|------|--------|
| BPMN → IR1 | `code/study_case_carwash/bpmn_ir1.py` | ✅ Selesai |
| IR1 → IR2 | `code/study_case_carwash/ir1_ir2.py` | ✅ Selesai |
| Orchestrator | `code/study_case_carwash/main.py` | ✅ Selesai |
| Prompt builder | `code/study_case_carwash/prompts.py` (7 file_type) | ✅ Selesai |
| Decomposer + Generator | `code/study_case_carwash/generator.py` | ✅ Selesai |
| Notebook demo | `code/generate_per_file.ipynb` (21 cell) | ✅ Struktur ada, belum dieksekusi |

**Catatan:** Parser mendukung namespace BPMN, semua tipe element (participant, task, gateway, message flow), dan derivasi otomatis pageType, routing, stateWrites, waitCondition, conditionalRoutes.

---

### 2. Pengerjaan Dataset — ⚠️ SEBAGIAN SELESAI

#### 2a. Struktur App — ✅ Selesai
- Definisi di `struktur-app/App_structure.md`
- 7 file_type: global_state, protected_route, layout, ui_kit, login_page, app_root, dynamic_page

#### 2b. Study Case — ✅ Selesai
- Self-service-restaurant: `generated_app/Self-service-restaurant/` (full React app)
- CarWashApp: `generated_app/CarWashApp/` (full React app)
- Dokumentasi: `Study_Case_Carwash.md`, `Ir2_requirement.md`

⚠️ **Masalah pada generated app:**
- `CarWashApp/globalState.ts` ditandai "VALIDATION FAILED"
- `App.tsx` menggunakan `.map()` untuk route (melanggar OUTPUT CONTRACT)
- Beberapa page menghasilkan kode minimal (misal `export const LoginPage = () => null;`)
- Kualitas output LLM belum memadai tanpa fine-tuning

#### 2c. Pembuatan Dataset (BPMN → IR1 → IR2 → JSONL) — ⚠️ Sebagian

**Sumber BPMN (75 file total):**

| Sumber | Jumlah BPMN | IR1 | IR2 | train.jsonl |
|--------|-------------|-----|-----|-------------|
| Camunda | 4 | ✅ 4 | ✅ 4 | ✅ Ada (placeholder assistant) |
| ITS | 67 | ✅ 67 | ✅ 67 | ❌ Belum dibuat |
| ProcessMind | 4 | ✅ 4 | ✅ 4 | ❌ Belum dibuat |
| **Total** | **75** | **75** | **75** | **1 dari 3 sumber** |

**Script batch yang sudah ada:**
- `batch_generate_ir1_ir2_camunda.py` — batch Camunda
- `batch_generate_ir1_ir2.py` / `batch_generate_ir1_ir2_processmind.py` — batch ProcessMind
- `generate_jsonl_from_ir2_camunda.py` — IR2 → JSONL (Camunda)
- `regenerate_train_jsonl_camunda.py` — regenerasi dataset Camunda

**Yang belum:**
- train.jsonl untuk ITS dan ProcessMind belum digenerate
- Assistant content masih placeholder/dummy (bukan ground truth)
- Belum ada script JSONL untuk ITS dan ProcessMind

#### 2d. Validasi Dataset — ⚠️ Parsial
- Validasi format sudah ada di `doc.md` (Camunda): cek markdown fence, import statement, named export, TypeScript parseable
- Belum ada skrip validasi otomatis menyeluruh
- Belum ada validasi semantik (apakah kode sesuai pageType behavior)

---

### 3. Finetuning — ❌ BELUM DIMULAI

- Belum ada skrip finetuning di workspace
- Infrastruktur target: Ollama + Unsloth + Qwen2.5-Coder-7B (dari doc.md)
- **Blocker:** dataset train.jsonl belum lengkap & assistant content masih placeholder

---

### 4. Evaluasi — ❌ BELUM DIMULAI

- Belum ada skrip evaluasi atau test framework
- Unit test yang ada (`test_parser.py`, `test_ir2.py`, `test_pizza_flow.py`) hanya untuk parser, bukan untuk hasil fine-tuning
- Belum ada metrik evaluasi (code validity, behavioral correctness, dsb)

---

### 5. Sistem Keseluruhan (Upload BPMN → Proses → App) — ❌ BELUM DIMULAI

- Belum ada web UI atau API endpoint
- Belum ada integrasi end-to-end (upload → parse → generate → deploy)

---

## Ringkasan Status Keseluruhan

| Fase | Progress | Estimasi |
|------|----------|----------|
| 1. Parser BPMN → IR1 → IR2 | ✅ 100% | Selesai |
| 2a. Struktur App | ✅ 100% | Selesai |
| 2b. Study Case | ✅ 100% | Selesai (dengan catatan kualitas) |
| 2c. Pembuatan Dataset JSONL | ⚠️ ~40% | IR1/IR2 semua selesai, JSONL baru Camunda |
| 2d. Validasi Dataset | ⚠️ ~20% | Hanya validasi format manual |
| 3. Finetuning | ❌ 0% | Belum dimulai |
| 4. Evaluasi | ❌ 0% | Belum dimulai |
| 5. Sistem Keseluruhan | ❌ 0% | Belum dimulai |

## Bottleneck & Langkah Selanjutnya

1. **Prioritas tinggi:** Generate train.jsonl untuk ITS (67 file) dan ProcessMind (4 file)
2. **Prioritas tinggi:** Ganti placeholder assistant content dengan ground truth code yang valid
3. **Prioritas sedang:** Buat skrip validasi otomatis (TypeScript parse check, pageType behavior check)
4. **Setelah dataset siap:** Mulai finetuning (LoRA pada Qwen2.5-Coder-7B)
5. **Setelah finetuning:** Evaluasi kualitas output vs baseline
6. **Terakhir:** Bangun sistem end-to-end
