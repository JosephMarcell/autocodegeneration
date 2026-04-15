# System Plan — Teknik Prompting untuk Pipeline BPMN → React Code Generation

## Konteks Pemilihan

Pipeline ini memiliki karakteristik yang mempengaruhi pilihan teknik prompting:

- Model target: `qwen2.5-coder:7b` (model kecil, parameter terbatas)
- Output: source code TypeScript/TSX yang harus **syntactically valid dan structurally consistent**
- Input: IR2 — manifest terstruktur per file dengan schema, constraints, dan routing sudah terdefinisi
- Strategi: satu LLM call per file (per-file generation)

Karena model adalah 7b dan outputnya adalah kode (bukan teks naratif), teknik prompting harus fokus pada **presisi struktur** bukan kreativitas.

---

## Teknik yang Direkomendasikan

### 1. Few-Shot Prompting ⭐ (Prioritas Tertinggi)

**Apa:** Menyertakan 1–2 contoh kode konkret dalam prompt sebelum meminta LLM menulis file target.

**Mengapa cocok:** Model 7b sangat bergantung pada *pattern matching* dari contoh. Tanpa contoh, model cenderung menghasilkan kode yang secara logika benar tetapi tidak mengikuti konvensi proyek (misal: menggunakan `useState` langsung alih-alih `useGlobalState`, atau membungkus layout sendiri).

**Implementasi dalam proyek:**
Sertakan contoh satu dynamic page yang sederhana di system prompt, bukan di output_example yang minimal saat ini:

```
EXAMPLE — dynamic_page (action type):
// src/modules/ExampleParticipant/pages/DoSomethingPage.tsx
import { useNavigate } from 'react-router-dom';
import { useGlobalState } from '../../../../shared/state/globalState';

export default function DoSomethingPage() {
  const navigate = useNavigate();
  const { updateWorkflow } = useGlobalState();

  const handleComplete = () => {
    updateWorkflow('do_something_completed', true);
    navigate('/exampleparticipant/next-task');
  };

  return (
    <div className="max-w-lg mx-auto mt-8 bg-white rounded-xl shadow p-6">
      <h1 className="text-xl font-bold mb-4">Do Something</h1>
      <button onClick={handleComplete}
        className="w-full bg-blue-600 text-white py-2 rounded-lg">
        Complete
      </button>
    </div>
  );
}
```

**Dampak:** Meningkatkan konsistensi `import depth`, pola `updateWorkflow`, dan struktur JSX di seluruh 15+ dynamic page.

---

### 2. Output Contract Prompting ⭐ (Sudah Diterapkan, Perlu Diperkuat)

**Apa:** Menyatakan kontrak output secara eksplisit — format, panjang, apa yang dilarang, nama export yang harus ada.

**Mengapa cocok:** Model kecil tanpa instruksi eksplisit akan menambahkan prose, markdown fences, atau komentar yang tidak diperlukan. Output contract menekan perilaku ini.

**Status saat ini:** IR2 sudah memiliki `constraints.max_lines`, `schema.exports`, dan `forbidden` list. Ini adalah output contract yang solid.

**Yang perlu ditambahkan:**
```
OUTPUT CONTRACT:
- Return ONLY raw TypeScript source code
- No markdown fences (```tsx ... ```)  
- No prose explanation before or after the code
- File MUST compile without errors if imports are resolved
- First line must be an import statement
```

Menegaskan bahwa **baris pertama adalah import** mencegah LLM menulis komentar seperti `// Here is the generated file for...` yang kemudian menyebabkan build error.

---

### 3. Role + Context Prompting (System Prompt Engineering)

**Apa:** Menetapkan persona spesifik di system prompt yang relevan dengan file yang sedang di-generate.

**Mengapa cocok:** Alih-alih satu system prompt generik untuk semua file, setiap *file type* mendapat persona berbeda. Ini sudah dirancang di notebook `generate_per_file.ipynb` dengan `detect_file_type()`.

**Pola yang diterapkan:**
| File Type | Persona System Prompt |
|-----------|----------------------|
| `dynamic_page` | "You are generating a single BPMN task page..." |
| `app_root` | "You are generating src/App.tsx (BrowserRouter root)..." |
| `layout` | "You are generating the Layout shell..." |

**Kunci:** Setiap persona hanya menyertakan aturan yang relevan untuk file tersebut, bukan semua aturan sekaligus. Ini mengurangi *instruction dilution* — fenomena di mana model 7b mengabaikan aturan yang terkubur di tengah prompt panjang.

---

### 4. Decomposition Prompting (Task Decomposition)

**Apa:** Memecah satu tugas besar (generate semua file) menjadi sub-tugas independen yang diselesaikan satu per satu.

**Mengapa cocok:** Ini adalah inti dari perubahan arsitektur dari `main.py` (single call) ke notebook (per-file call). Setiap sub-tugas memiliki:
- Scope yang jelas (`path` satu file)
- Context yang terfokus (hanya info yang dibutuhkan file tersebut)
- Validasi terpisah (dapat diulang tanpa mempengaruhi file lain)

**Urutan generate yang tepat** juga penting — berurutan dari *shared* ke *module*:
```
1. globalState.ts     ← dependensi semua file
2. ProtectedRoute.tsx ← dependensi App.tsx
3. Layout.tsx         ← dependensi App.tsx
4. LoginPage.tsx      ← dependensi App.tsx
5. App.tsx            ← membutuhkan semua di atas
6. [dynamic pages]    ← independen satu sama lain
```

---

### 5. Self-Correction / Iterative Refinement Prompting

**Apa:** Jika output tidak valid, kirimkan kembali output + daftar masalah ke LLM dengan instruksi "perbaiki masalah ini."

**Mengapa cocok:** Model 7b lebih baik dalam *memperbaiki* kode yang hampir benar daripada *menulis dari scratch* untuk kasus yang kompleks. Retry dengan feedback lebih efektif daripada retry dengan prompt yang sama.

**Pola prompt retry:**
```
Previous attempt had the following issues:
- MISSING_EXPORT: 'DoublePolishPage' tidak ada di output
- FORBIDDEN: <Route> di dalam conditional JSX

Fix these issues and regenerate the file.
[original spec...]
```

**Batas retry yang wajar:** 2 kali. Jika setelah 3 total attempt masih gagal, kemungkinan ada masalah di IR2 (spec ambigu) bukan di model.

---

### 6. Constrained / Schema-Guided Prompting

**Apa:** Menyertakan schema eksplisit (nama fungsi, signature, field) yang *wajib* ada di output.

**Mengapa cocok:** Untuk file seperti `globalState.ts` yang di-import oleh hampir semua file lain, konsistensi nama export (`useGlobalState`, `updateWorkflow`) adalah syarat hard constraint — bukan preferensi.

**Implementasi:**
```
Must export:
  export interface GlobalState
  export const useGlobalState: () => GlobalState & GlobalActions

Actions signature (exact):
  login(userName: string, role: string, token?: string): void
  logout(): void
  updateWorkflow(key: string, value: boolean | string): void
```

Menuliskan *exact signature* (bukan hanya nama) mencegah model 7b membuat variasi seperti `updateWorkflowState()` atau `setWorkflow()` yang merusak semua file yang bergantung padanya.

---

## Teknik yang Tidak Direkomendasikan

| Teknik | Alasan Tidak Cocok |
|--------|--------------------|
| **Chain-of-Thought (CoT)** | Mendorong model menulis reasoning sebelum kode — memboroskan token dan menghasilkan prose yang harus distrip |
| **Tree-of-Thoughts** | Overhead terlalu besar untuk model 7b, tidak proporsional dengan kompleksitas tugas |
| **ReAct (Reason + Act)** | Butuh multi-turn dengan tool use; Ollama lokal tidak mendukung ini secara native |
| **Zero-Shot CoT ("think step by step")** | Menghasilkan komentar verbose di dalam kode, bukan kode bersih |

---

## Rekomendasi Prioritas Implementasi

```
[SEGERA]
  ✅ Output Contract (sudah ada, perlu perkuat "first line = import")
  ✅ Role + Context per file type (sudah di notebook)
  ✅ Decomposition (sudah diimplementasikan)
  ✅ Self-Correction retry dengan feedback (sudah di notebook)

[SELANJUTNYA]
  ⬜ Few-Shot: tambahkan 1 kode contoh per file type di system prompt
  ⬜ Schema-Guided: tulis exact function signature untuk globalState.ts
  ⬜ Urutan generate yang benar (shared → App → modules)
```

Few-shot adalah satu-satunya teknik dengan dampak terbesar yang **belum** diterapkan di sistem saat ini dan paling mudah ditambahkan ke prompt yang sudah ada.
