# Dataset Study: BPMN Structural Characteristics Across Sources

## 1. Tujuan

Dokumen ini menganalisis karakteristik struktural file BPMN dari tiga sumber berbeda (**BPMN_Camunda**, **BPMN_ITS**, **BPMN_ProcessMind**) untuk menilai:

- Perbedaan pola struktur XML (namespace, arsitektur, elemen)
- Kompatibilitas dengan parser saat ini (`bpmn_ir1.py`) dan transformer (`ir1_ir2.py`)
- Risiko dan keputusan sebelum ground truth generation

---

## 2. Ringkasan Per-Source

### 2.1 BPMN_Camunda (4 file, namespace `bpmn:`)

| File | Arsitektur | Lanes | Gateway Types | Event Subtypes | messageFlows | Task Types |
|---|---|---|---|---|---|---|
| `Dispatch-of-goods.bpmn` | 1 participant (pool) | 3 lanes (Logistics, Secretary, Warehouse) | exclusive, parallel, inclusive | startEvent, endEvent saja | Tidak ada | Generic `task` |
| `credit-scoring-synchronous.bpmn` | 3 participants (pools) | Tidak ada | exclusive | intermediateCatchEvent + `messageEventDefinition` | 6 messageFlows | Generic `task` |
| `self-service-restaurant.bpmn` | 3 participants (pools) | Tidak ada | exclusive | intermediateCatchEvent + `messageEventDefinition`, startEvent + `conditionalEventDefinition` | 10+ messageFlows | Generic `task` |
| `recourse.bpmn` | 1 participant (pool) | Tidak ada | exclusive, **eventBasedGateway** | intermediateCatchEvent + `timerEventDefinition` + `messageEventDefinition`, multiple endEvents | 2 messageFlows | Generic `task` |

**Karakteristik utama:**
- Namespace prefix `bpmn:` — URI `http://www.omg.org/spec/BPMN/20100524/MODEL`
- Arsitektur bervariasi: single-pool+lanes maupun multi-pool+messageFlows
- Gateway diversity paling tinggi: exclusive, parallel, inclusive, eventBased
- Memiliki event subtype yang kompleks: timer, message, conditional
- Satu file (`credit-scoring`) memiliki **empty process** (pool tanpa task — hanya frontend placeholder)

### 2.2 BPMN_ITS (67 folder, namespace bare / Bizagi)

| Aspek | Pola Konsisten |
|---|---|
| Namespace | Bare (default ns): `xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"` |
| Arsitektur | Multiple `<process>` tanpa `<collaboration>` / `<participant>` |
| Lanes | Selalu ada: `<laneSet>` → `<lane>` (umumnya 2: Administrator/System atau Officer/System) |
| Gateway types | **Hanya** `<exclusiveGateway>` — selalu dengan atribut `gatewayDirection="Diverging"` atau `"Converging"` |
| Event types | Hanya `<startEvent>` dan `<endEvent>` — tidak ada intermediate events |
| messageFlows | **Tidak ada** (single-process flows) |
| Task types | **Hanya** generic `<task>` |
| Data elements | `<dataStore>` + `<dataStoreReference>` (contoh: User, Account, Member, Unit work, Cash) |
| Extensions | Bizagi-specific styling properties (`bgColor`, `borderColor`, dll) |

**Karakteristik utama:**
- Pola paling **homogen dan sederhana** — semua 67 file mengikuti template yang sama
- Lane info adalah **satu-satunya sumber role information** — tanpa participant/pool
- Gateway direction **eksplisit** (tidak perlu infer dari incoming/outgoing count)
- `dataStore` menunjukkan entitas persistent tapi tidak di-parse oleh `bpmn_ir1.py`
- Task names deskriptif (contoh: "Reads user information", "Displays the user management form")

**Sample files yang diperiksa:**
- `1.Employee cooperative (main).User management/Diagram 2.bpmn` — 2 lanes (Administrator, System), exclusiveGateway, dataStore(User)
- `2.Employee cooperative (main).Add new member/Diagram 2.bpmn` — 2 lanes (Officer, System), 4 exclusiveGateway, dataStore(Member, Unit work)
- `10.Employee cooperative (main).Login/employee_coop.bpmn` — 2 lanes (User, System), dataStore(Account)
- `11/Diagram 2.bpmn` — 2 lanes (Officer, System), dataStore(Unit work, Cash, mandatory Savings)

### 2.3 BPMN_ProcessMind (4 file, namespace `bpmn2:`)

| File | Arsitektur | Lanes | Gateway Types | Event Subtypes | messageFlows | Task Types |
|---|---|---|---|---|---|---|
| `Car-Wash.bpmn` | 2 participants | Tidak ada | exclusive | tidak ada intermediate | 3 messageFlows | Generic `task` |
| `Pizza-Store.bpmn` | 2 participants | 3 lanes di vendor (clerk, pizza chef, delivery boy) | exclusive, **eventBasedGateway**, **parallel** | intermediateCatchEvent + `timerEventDefinition` + `messageEventDefinition`, intermediateThrowEvent + `messageEventDefinition`, endEvent + `terminateEventDefinition` | 6 messageFlows | Generic `task` |
| `Smart-Parking.bpmn` | 3 participants | Tidak ada | exclusive | startEvent + `messageEventDefinition`, endEvent + `messageEventDefinition`, intermediateCatchEvent + `timerEventDefinition`, intermediateThrowEvent + `messageEventDefinition` | 8+ messageFlows | Generic `task` |
| `Recruitment-and-Selection.bpmn` | 3 participants | 2 lanes (Manager, HR) | exclusive, **parallel** | startEvent + `messageEventDefinition`, endEvent (normal) | 1 messageFlow | **Typed**: `userTask`, `serviceTask`, `sendTask` + `multiInstanceLoopCharacteristics` + `dataObjectReference` |

**Karakteristik utama:**
- Namespace `bpmn2:` — URI yang sama, kompatibel dengan parser
- Kompleksitas bervariasi: Car-Wash sederhana, Pizza-Store/Smart-Parking kompleks
- **Paling beragam** dalam task typing dan event subtypes
- Loop-back flows ada (Pizza-Store: customer ask → eventBasedGateway → timeout → ask again)
- `multiInstanceLoopCharacteristics` ada di Recruitment (batch interview subprocess)
- `terminateEventDefinition` pada endEvent (Pizza-Store vendor)

---

## 3. Perbandingan Lintas-Sumber

| Aspek | BPMN_Camunda | BPMN_ITS | BPMN_ProcessMind |
|---|---|---|---|
| **Jumlah file** | 4 | 67 | 4 |
| **Namespace** | `bpmn:` (prefixed) | Bare (default) | `bpmn2:` (prefixed) |
| **Collaboration/Participant** | ✅ Ya | ❌ Tidak | ✅ Ya |
| **Lanes** | 1 dari 4 file | ✅ Semua file | 2 dari 4 file |
| **Gateway diversity** | Tinggi (4 jenis) | Rendah (1 jenis) | Sedang (3 jenis) |
| **Event subtypes** | Tinggi | Tidak ada | Tinggi |
| **messageFlows** | ✅ (2-10+) | ❌ | ✅ (1-8+) |
| **Typed tasks** | ❌ Semua generic | ❌ Semua generic | 1 dari 4 file |
| **Data elements** | ❌ | ✅ (dataStore) | Sebagian (dataStore, dataObject) |
| **Kompleksitas rata-rata** | Medium-High | Low-Medium | Medium-High |
| **Homogenitas** | Rendah (setiap file berbeda) | Sangat tinggi (template sama) | Rendah |

---

## 4. Analisis Kompatibilitas Parser

### 4.1 `bpmn_ir1.py` — BPMN XML → IR1

Parser saat ini menangani:
- ✅ Tiga varian namespace (`bpmn:`, `bpmn2:`, bare) — semua menggunakan URI yang sama
- ✅ `collaboration` / `participant` extraction
- ✅ Semua 8 task types (task, userTask, serviceTask, sendTask, receiveTask, manualTask, businessRuleTask, scriptTask)
- ✅ 5 gateway types (exclusive, parallel, inclusive, complex, eventBased)
- ✅ 5 event types (startEvent, endEvent, intermediateCatchEvent, intermediateThrowEvent, boundaryEvent)
- ✅ sequenceFlow dan messageFlow extraction
- ✅ Auto-derived stateSchema dari task names dan gateway names

**Yang BELUM ditangani:**

| Elemen | Status | Dampak |
|---|---|---|
| `laneSet` / `lane` | ❌ Tidak di-parse | Lane info hilang — di ITS, **satu-satunya** role info; di Camunda/ProcessMind, lanes menunjukkan sub-roles dalam pool |
| Event sub-definitions (`messageEventDefinition`, `timerEventDefinition`, `conditionalEventDefinition`, `terminateEventDefinition`) | ❌ Tidak di-extract | Parser tahu ada `intermediateCatchEvent` tapi tidak tahu tipe trigger-nya |
| `multiInstanceLoopCharacteristics` | ❌ Tidak di-parse | Tidak tahu task mana yang batch/loop |
| `dataStore` / `dataStoreReference` / `dataObjectReference` | ❌ Tidak di-parse | Kehilangan info entitas data persistent |
| `ioSpecification` / `dataInputAssociation` | ❌ Tidak di-parse | Data flow antara task dan dataStore tidak terlacak |

### 4.2 `ir1_ir2.py` — IR1 → IR2

Transformer saat ini hanya menangani **exclusive gateway** pattern:

| Pola | Status | Catatan |
|---|---|---|
| Task → exclusive diverging gateway → conditional branches | ✅ Ditangani | `conditionalRoutes` di-generate |
| Converging gateway → continue | ✅ Ditangani | Skip converging, lanjut ke task berikutnya |
| **Parallel gateway** (fork/join) | ❌ Tidak ditangani | Parallel fork → semua branch harus dieksekusi; tidak bisa di-map ke conditionalRoutes |
| **Inclusive gateway** | ❌ Tidak ditangani | Inclusive = any-N-of-M branches — di antara exclusive (1) dan parallel (all) |
| **EventBased gateway** | ❌ Tidak ditangani | EventBased = wait for first event — perlu page type baru yang listen ke multiple events |
| `messageFlow`-triggered wait | Parsial — `waitCondition` sudah ada | Tapi hanya berdasarkan incoming messageFlow ke task, bukan ke events |
| Timer-based wait | ❌ Tidak ditangani | Tidak ada pageType yang menunggu timer |
| Loop-back flows | ⚠️ Risiko infinite loop | `task_order()` menggunakan topological sort — cycle bisa menyebabkan loop tak terbatas |

---

## 5. Risk Matrix

| BPMN Element | `bpmn_ir1.py` | `ir1_ir2.py` | Source yang Terdampak | Severity |
|---|---|---|---|---|
| `laneSet` / `lane` | ❌ NOT parsed | ❌ NOT handled | ITS (semua 67), Camunda (1), ProcessMind (2) | **HIGH** — 70 dari 75 file |
| `parallelGateway` handling | Parsed ✅ | ❌ NOT handled | Camunda (1), ProcessMind (2) | MEDIUM — 3 file |
| `inclusiveGateway` handling | Parsed ✅ | ❌ NOT handled | Camunda (1) | LOW — 1 file |
| `eventBasedGateway` handling | Parsed ✅ | ❌ NOT handled | Camunda (1), ProcessMind (1) | MEDIUM — 2 file |
| `timerEventDefinition` | ❌ NOT recognized | ❌ NOT handled | Camunda (1), ProcessMind (2) | MEDIUM — 3 file |
| `messageEventDefinition` on events | ❌ NOT recognized | ❌ NOT handled | Camunda (2), ProcessMind (3) | MEDIUM — 5 file |
| `conditionalEventDefinition` | ❌ NOT recognized | ❌ NOT handled | Camunda (1) | LOW — 1 file |
| `terminateEventDefinition` | ❌ NOT recognized | ❌ NOT handled | ProcessMind (1) | LOW — 1 file |
| `multiInstanceLoopCharacteristics` | ❌ NOT parsed | ❌ NOT handled | ProcessMind (1) | LOW — 1 file |
| `dataStore` / `dataObjectReference` | ❌ NOT parsed | ❌ NOT handled | ITS (semua), ProcessMind (1) | LOW — info saja |
| Empty process (0 tasks) | Parsed ✅ (empty) | Generates 0 pages | Camunda (1) | LOW — non-blocking |
| Loop-back sequence flows | Parsed ✅ | ⚠️ Potential infinite loop | ProcessMind (1) | MEDIUM — crash risk |

---

## 6. Klasifikasi File: Safe vs Needs Patch

### ✅ Safe to Process (sekarang)

| File | Source | Alasan |
|---|---|---|
| `Car-Wash.bpmn` | ProcessMind | Study case yang sudah terbukti berjalan; 2 pools, exclusive gateway, messageFlows |
| **67 file ITS** | ITS | Exclusive-only, no messageFlows, no intermediate events — **CATATAN: lane info akan hilang → role default ke process name** |

> **Total: 68 dari 75 file** aman diproses — meskipun ITS kehilangan lane role info.

### ⚠️ Needs Parser Patch

| File | Source | Elemen yang Tidak Didukung | Patch yang Diperlukan |
|---|---|---|---|
| `Dispatch-of-goods.bpmn` | Camunda | `inclusiveGateway`, `parallelGateway`, lanes | Lane parsing + parallel/inclusive handling |
| `credit-scoring-synchronous.bpmn` | Camunda | `messageEventDefinition` pada events, empty pool process | Event subtype extraction |
| `self-service-restaurant.bpmn` | Camunda | `conditionalEventDefinition` | Event subtype extraction |
| `recourse.bpmn` | Camunda | `eventBasedGateway`, `timerEventDefinition` | Event subtype + eventBased handling |
| `Pizza-Store.bpmn` | ProcessMind | `eventBasedGateway`, `timerEventDefinition`, `parallelGateway`, `terminateEventDefinition`, loop-back | Multiple patches + cycle detection |
| `Smart-Parking.bpmn` | ProcessMind | `timerEventDefinition`, `messageEventDefinition` pada start/end events | Event subtype extraction |
| `Recruitment-and-Selection.bpmn` | ProcessMind | `parallelGateway`, `multiInstanceLoopCharacteristics` | Parallel handling + multi-instance |

> **Total: 7 dari 75 file** memerlukan patch — tapi ini file dengan kompleksitas tertinggi dan paling beragam.

---

## 7. Rekomendasi Prioritas

### Priority 1: Lane Parsing di `bpmn_ir1.py` (Impact: 70 file)

**Problem:** Lane info tidak di-extract. ITS files kehilangan satu-satunya role information. Camunda/ProcessMind files kehilangan sub-role info.

**Solusi:** Tambahkan extraction di `parse_bpmn()` setelah bagian participant extraction (~line 86):
- Parse `<laneSet>` → `<lane>` children per process
- Collect `<flowNodeRef>` per lane → map node ID ke lane name
- Store sebagai `ir1["lanes"]` dan `ir1["node_to_lane"]`
- Gunakan lane name sebagai `participantName` fallback jika tidak ada participant/collaboration

**File yang harus dimodifikasi:** `code/study_case_carwash/bpmn_ir1.py`

### Priority 2: Event Subtype Extraction di `bpmn_ir1.py` (Impact: 7 file)

**Problem:** Parser mendeteksi event types (startEvent, intermediateCatchEvent, dll) tapi tidak tahu trigger type-nya (message/timer/conditional).

**Solusi:** Dalam loop event extraction (~line 124):
- Cek child elements: `messageEventDefinition`, `timerEventDefinition`, `conditionalEventDefinition`, `terminateEventDefinition`
- Store sebagai field `eventDefinitionType` pada setiap event object

**File yang harus dimodifikasi:** `code/study_case_carwash/bpmn_ir1.py`

### Priority 3: Parallel Gateway Handling di `ir1_ir2.py` (Impact: 3 file)

**Problem:** `ir1_ir2.py` hanya menangani exclusive gateway semantics. Parallel fork = **semua** branch harus dieksekusi, tidak pilih salah satu.

**Solusi:** Di `find_next_route()` (~line 243):
- Jika outgoing → parallel diverging gateway: generate semua branches sebagai independent pages tanpa conditionalRoutes (setiap page auto-navigate ke next)
- Jika incoming dari parallel converging gateway: implementasi wait-for-all logic (semua branch selesai sebelum lanjut)
- Bisa di-approximate sebagai sequential execution dari semua branches

**File yang harus dimodifikasi:** `code/study_case_carwash/ir1_ir2.py`

### Priority 4: EventBased Gateway Handling di `ir1_ir2.py` (Impact: 2 file)

**Problem:** `eventBasedGateway` = wait for first event dari beberapa kemungkinan (timer timeout, message received, etc.). Tidak bisa di-map ke conditionalRoutes biasa.

**Solusi:** Map ke pageType baru (contoh: `event-wait-then-route`) yang menampilkan waiting UI dan react ke event pertama yang terjadi. Untuk web app, timer bisa di-simulate dengan setTimeout, message bisa di-simulate dengan state change dari pool lain.

**File yang harus dimodifikasi:** `code/study_case_carwash/ir1_ir2.py`

### Deferred (Low ROI)

| Elemen | Alasan Ditunda |
|---|---|
| `conditionalEventDefinition` | Hanya 1 file; bisa di-approximate sebagai message event |
| `multiInstanceLoopCharacteristics` | Hanya 1 file; bisa di-generate sebagai single task |
| `dataStore` / `dataObjectReference` | Info-only; tidak mempengaruhi page generation |
| `inclusiveGateway` | Hanya 1 file; bisa di-approximate sebagai exclusive |
| `terminateEventDefinition` | Hanya 1 file; end event behavior sudah handle |

---

## 8. Kesimpulan

| Metrik | Nilai |
|---|---|
| Total BPMN files | 75 |
| Safe to process now | 68 (90.7%) — 1 ProcessMind + 67 ITS |
| Needs patch | 7 (9.3%) — 4 Camunda + 3 ProcessMind |
| Priority 1 patch unlocks | 70 files with proper role info |
| All 4 patches combined unlock | Semua 75 files |

**Strategi yang disarankan:**
1. Implement Priority 1 (lane parsing) → unlock 67 ITS files dengan role info yang benar
2. Implement Priority 2 (event subtypes) → foundation untuk semantic handling
3. Implement Priority 3+4 (parallel + eventBased) → unlock sisa 7 file
4. Generate ground truth dari **ITS files duluan** (paling homogen, paling banyak, lowest risk)
5. Kemudian Camunda + ProcessMind setelah parser dipatch

