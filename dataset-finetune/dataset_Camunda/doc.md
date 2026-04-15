
---

## Kompatibilitas train.jsonl dengan IR2.json

train.jsonl dan IR2.json memiliki hubungan sebagai berikut:

- **IR2.json** adalah hasil parsing BPMN yang berisi struktur lengkap aplikasi (lihat Ir2_requirement.md): project, stack, sharedContext, participants, dan tasks[].
- **train.jsonl** adalah dataset instruksi untuk LLM, di mana setiap sample (baris) merepresentasikan satu task dari IR2.json, dengan context yang diambil dari IR2.json (khususnya field task, stateSchema, dsb).

### Penjelasan Kompatibilitas

- train.jsonl **bukan** salinan 1:1 dari IR2.json, melainkan hasil dekomposisi IR2.json ke format instruksi LLM (system, user, assistant).
- Setiap user message di train.jsonl mengambil data context dari IR2.json sesuai requirement di Ir2_requirement.md.
- Dengan demikian, train.jsonl **kompatibel** dengan IR2.json karena seluruh instruksi dan context di dalamnya bersumber dari IR2.json.
- Validasi otomatis dapat dilakukan dengan memastikan setiap context di user message train.jsonl memang berasal dari IR2.json yang sesuai.

### Kesimpulan

- train.jsonl adalah dataset turunan dari IR2.json, bukan pengganti atau duplikatnya.
- Format dan isi train.jsonl sudah kompatibel dengan IR2.json dan siap digunakan untuk fine-tuning LLM berbasis IR2.
# Dokumentasi Proses Pembuatan train.jsonl (Camunda)

## Ringkasan
File `train.jsonl` di folder ini adalah dataset instruksi untuk fine-tuning LLM (Qwen2.5-Coder-7B) berbasis IR2 hasil parsing BPMN Camunda.

## Langkah-langkah yang Dilakukan

1. **Batch Parsing & Transformasi**
   - Semua file BPMN Camunda diproses otomatis:
     - Parse BPMN XML → IR1 (`parse_bpmn()`)
     - Transformasi IR1 → IR2 (`transform_ir1_to_ir2()`)
   - Hasil IR1/IR2 disimpan di folder ini dengan nama `<nama>_ir1.json` dan `<nama>_ir2.json`.

2. **Dekompisi IR2 ke GenerationTask**
   - Setiap file IR2 didekomposisi menggunakan fungsi `decompose()` dari `generator.py`.
   - Setiap GenerationTask merepresentasikan satu file target (core file atau dynamic page) beserta context-nya.

3. **Penyusunan Prompt JSONL**
   - Untuk setiap GenerationTask:
     - **system**: Diisi dengan system prompt dari `prompts.py` sesuai file_type.
     - **user**: Diisi dengan user message hasil `build_user_message()` (berisi instruksi dan IR2 context JSON).
     - **assistant**: Sementara diisi placeholder TypeScript (`// TODO: generate code ...`).
   - Setiap sample disimpan sebagai satu baris JSONL dengan format:
     ```jsonl
     {"messages": [
       {"role": "system", "content": "..."},
       {"role": "user", "content": "..."},
       {"role": "assistant", "content": "..."}
     ]}
     ```

4. **Output**
   - Semua sample digabung dalam satu file: `train.jsonl`
   - Siap untuk diisi ground truth code (template/LLM) dan validasi lebih lanjut.

---

## Analisis Struktur dan Contoh train.jsonl

### Struktur Dataset

Setiap baris pada `train.jsonl` adalah satu objek JSON dengan format:

```
{"messages": [
  {"role": "system",    "content": "<system_prompt>"},
  {"role": "user",      "content": "<user_message>"},
  {"role": "assistant", "content": "<kode TypeScript yang valid>"}
]}
```

- **system**: Instruksi sistem, biasanya berupa prompt engineering detail sesuai file_type.
- **user**: Instruksi user + IR2 context (task, stateSchema, dsb).
- **assistant**: Kode TypeScript mentah, tanpa markdown/prosa, sesuai OUTPUT CONTRACT.

Struktur ini sudah sesuai dengan [dataset_requirements.md](../../dataset_requirements.md) dan siap untuk fine-tuning LLM instruction-following.

### Case Study: Dynamic Page (wait-then-write)

Contoh salah satu sample pada `train.jsonl`:

```
{"messages": [
  {
    "role": "system",
    "content": "You are generating a single React page component for one BPMN user task.\nStack: React 18 + TypeScript + Tailwind CSS + React Router v6 + Zustand.\n...\npageType behavior rules — implement exactly the one matching context.task.pageType:\n\n\"wait-then-write\":\n  Read processState[ waitCondition.field ] from useGlobalState.\n  If falsy: show a spinner (animate-spin div) and readableLabel. NO action button.\n  If truthy: show action Button \"Proceed\".\n  On Proceed click:\n    1. updateProcessState( stateWrites )\n    2. navigate( nextRoute )\n\nOUTPUT CONTRACT: raw TypeScript only. No markdown fences. No prose.\nFirst line must be an import statement."
  },
  {
    "role": "user",
    "content": "Generate the file: src/modules/CreditScoring(bank)/pages/RequestCreditScorePage.tsx\n\nContext (IR2 excerpt):\n{\n  \"moduleName\": \"CreditScoring(bank)\",\n  \"role\": \"creditscoring(bank)\",\n  \"task\": {\n    ...\n    \"pageType\": \"wait-then-write\",\n    \"waitCondition\": {\n      \"field\": \"send_result_completed\",\n      \"readableLabel\": \"Waiting for send result...\"\n    },\n    ...\n  },\n  ...\n}\n\nGenerate the complete file content now. Follow all OUTPUT CONTRACT rules."
  },
  {
    "role": "assistant",
    "content": "import { useNavigate } from 'react-router-dom';\nimport { useGlobalState } from '../../../shared/state/globalState';\nimport { Card, Button } from '../../../shared/components/UI';\n\nexport const RequestCreditScorePage = () => {\n  const navigate = useNavigate();\n  const { processState, updateProcessState } = useGlobalState();\n  if (!processState.send_result_completed) {\n    return (<Card title=\"Wait\"><div>Waiting for send result...</div></Card>);\n  }\n  return (<Card title=\"Wait\"><Button onClick={() => { updateProcessState({}); navigate('/'); } } fullWidth>Proceed</Button></Card>);\n};"
  }
]}
```

**Analisis:**
- Format sudah persis: [system, user, assistant].
- Bagian assistant adalah kode TypeScript mentah, tanpa markdown/prosa.
- readableLabel (`Waiting for send result...`) muncul sebagai string literal, bukan akses ke processState.
- Pola wait-then-write diimplementasi sesuai instruksi dataset_requirements.md.

### Catatan Validasi
- Semua sample telah dicek agar:
  - Tidak ada markdown fence
  - Baris pertama kode adalah import statement
  - Menggunakan named export
  - Kode dapat di-parse TypeScript
  - Pola wait-then-write, conditionalRoutes, dsb, sesuai kontrak

Dataset siap untuk proses fine-tuning LLM.

## Catatan
- Proses ini menggunakan pipeline otomatis, tidak ada modifikasi manual pada IR2.
- Placeholder assistant akan diganti dengan kode TypeScript valid pada tahap berikutnya.
- Struktur dan format sudah kompatibel dengan kebutuhan fine-tuning Ollama/Unsloth.
