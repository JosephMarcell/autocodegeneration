# Dokumentasi Dataset ITS (IR1 & IR2)

## Ringkasan

- **Jumlah file ITS diproses:** 67 BPMN (x2: IR1 & IR2, total 134 file)
- **Lokasi:** Semua file hasil batch processing ITS dipindahkan ke folder ini (`dataset_ITS/`)
- **Format:**
  - `<nama>__Diagram 2_ir1.json` — hasil parse BPMN → IR1
  - `<nama>__Diagram 2_ir2.json` — hasil transformasi IR1 → IR2
- **Sumber:** dataset/BPMN_ITS/*/*.bpmn
- **Pipeline:**
  1. BPMN XML → parse_bpmn() → IR1
  2. IR1 → transform_ir1_to_ir2() → IR2
- **Status parser/transformer:**
  - Lane parsing: ✓
  - Event subtype extraction: ✓
  - Parallel gateway: ✗
  - EventBased gateway: ✗

## Statistik

- **Total file IR1:** 67
- **Total file IR2:** 67
- **Distribusi file:** 1 pasang IR1/IR2 per BPMN ITS
- **Contoh nama file:**
  - `1.Employee cooperative (main).User management__Diagram 2_ir1.json`
  - `1.Employee cooperative (main).User management__Diagram 2_ir2.json`

## Catatan
- File IR1/IR2 ini siap untuk tahap selanjutnya: dekomposisi GenerationTask dan pembuatan ground truth code.
- Validasi IR2 dan statistik task/pageType dapat dilakukan dengan script lanjutan.
- Jika ada patch baru pada parser/transformer, batch processing perlu diulang.
