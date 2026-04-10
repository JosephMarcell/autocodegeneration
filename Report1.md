# Report 1 — Review Akurasi main.py: Ekstraksi BPMN Dispatch-of-goods

**File BPMN:** `dataset/BPMN_Camunda/Dispatch-of-goods.bpmn`  
**Pipeline:** BPMN XML → IR1 (`ir1.json`) → IR2 (`ir2.json`)  
**Parser:** `parser/main.py` (v4)

---

## 1. Gambaran Umum Pipeline

`main.py` mengimplementasikan transformasi dua tahap:

| Tahap | Input | Output | Tujuan |
|-------|-------|--------|--------|
| Step 1 | BPMN XML | IR1 (JSON) | Representasi abstrak elemen BPMN: pool, lane, task, event, gateway, sequence flow |
| Step 2 | IR1 | IR2 (JSON) | Manifest prompt terstruktur per-task untuk generate file React/TypeScript |

---

## 2. Struktur BPMN Dispatch-of-goods (Ground Truth)

Berdasarkan analisis langsung file XML:

- **1 Pool:** "Dispatch of goods Computer Hardware Shop" (`Participant_0ygkg4f`)
- **3 Lane:** Logistics, Secretary, Warehouse
- **7 Task** (semua tipe generic `<bpmn:task>`):
  - *Logistics:* Insure parcel
  - *Secretary:* Clarify shipment method, Get 3 offers from logistic companies, Write package label, Select logistic company and place order
  - *Warehouse:* Package goods, Prepare for picking up goods
- **2 Event:** StartEvent "Ship goods" (Secretary), EndEvent "Shipment prepared" (Warehouse)
- **6 Gateway:**
  - `ExclusiveGateway_1mpgzhg` — "Special sandling?" (Diverging/split, Secretary)
  - `ExclusiveGateway_1ouv9kf` — tanpa nama (Converging/join, Secretary)
  - `ExclusiveGateway_0z5sib0` — tanpa nama (Converging/join, Warehouse)
  - `ParallelGateway_02fgrfq` — tanpa nama (Diverging/split, Secretary)
  - `InclusiveGateway_0p2e5vq` — tanpa nama (Diverging/split, Secretary)
  - `InclusiveGateway_1dgb4sg` — tanpa nama (Converging/join, Secretary)
- **17 Sequence Flow** dengan kondisi: "yes", "no", "If insurance necessary", "always"

---

## 3. Analisis Akurasi IR1

### 3.1 Elemen yang Diekstrak dengan Benar ✓

**Process & Participants**
IR1 berhasil mengidentifikasi `Process_1` sebagai tipe `"collaboration"` dan menangkap satu-satunya peserta (`Participant_0ygkg4f`) dengan nama dan `processRef` yang tepat.

**Tasks (7/7 akurat)**
Seluruh 7 task diekstrak lengkap. Assignment lane ke field `role` pada setiap task akurat sesuai BPMN (Insure parcel → Logistics, Package goods → Warehouse, dst). `interactionHint` diset `"action"` pada semua task karena semua task bertipe generik `<bpmn:task>` — ini benar sesuai mapping `TASK_INTERACTION_HINTS`.

**Events (2/2 akurat)**
StartEvent "Ship goods" (role: Secretary) dan EndEvent "Shipment prepared" (role: Warehouse) terekam dengan benar. Field `trigger` kosong sesuai karena tidak ada event definition di BPMN ini.

**Gateways (6/6 akurat)**
Ini adalah keunggulan signifikan main.py. Tiga gateway (`ExclusiveGateway_1ouv9kf`, `ExclusiveGateway_0z5sib0`, `InclusiveGateway_1dgb4sg`) tidak memiliki atribut `gatewayDirection` dalam XML, namun main.py berhasil **menginfer arah** dari in-degree dan out-degree:
- in-degree > out-degree → Converging (join) ✓
- out-degree > in-degree → Diverging (split) ✓

Semua tipe gateway (exclusive, parallel, inclusive), arah, controlHint (split/join), dan assignment role ke lane sudah tepat.

**Sequence Flows (17/17 akurat)**
Seluruh 17 aliran urutan diekstrak dengan `source`, `target`, dan `condition` yang benar. Kondisi berlabel ("yes", "no", "If insurance necessary", "always") terekam dari atribut `name` di XML.

**stateSchema**
Menghasilkan 8 field: 7 boolean completion flag per task + 1 string result (`special_sandling_result`) untuk gateway bernama. Schema ini konsisten dengan kebutuhan state management di React.

---

### 3.2 Ketidakakuratan dan Keterbatasan IR1

**[I1] Field `process.name` kosong**
```json
"process": { "id": "Process_1", "name": "", ... }
```
Proses BPMN memang tidak memiliki atribut `name` secara eksplisit, namun nama participant (`"Dispatch of goods Computer Hardware Shop"`) seharusnya dapat dipropagasi ke sini. Ini menyebabkan field `name` pada proses tetap kosong meskipun informasinya tersedia.

**[I2] Array `roles` tidak merepresentasikan lane sebagai entitas role**
```json
"roles": [
  { "id": "Participant_0ygkg4f", "name": "Dispatch of goods\nComputer Hardware Shop", ... }
]
```
Array `roles` di tingkat atas hanya berisi entri participant/pool, bukan lane individual (Logistics, Secretary, Warehouse). Lane sebetulnya adalah *peran pengguna* yang berinteraksi dengan sistem. Meskipun role per-task sudah benar di field `task.role`, ketidaklengkapan `roles` di level root membuat IR1 tidak cukup untuk menderivasi daftar peran secara mandiri.

**[I3] stateSchema hanya mencatat gateway bernama**
Dari 6 gateway, hanya `ExclusiveGateway_1mpgzhg` ("Special sandling?") yang menghasilkan field di `stateSchema` (`special_sandling_result`). Gateway lain (parallel split, inclusive split, dll.) tidak memiliki representasi state, padahal kondisi aliran ("If insurance necessary" vs "always") merupakan informasi keputusan yang berpotensi relevan untuk state tracking.

**[I4] Newline dalam nama task**
Beberapa nama task mengandung karakter newline literal, misalnya `"Write package\nlabel"`. Ini adalah artefak langsung dari BPMN XML (`&#10;`) dan bukan error parser, namun dapat menyebabkan inkonsistensi pada proses downstream (key generation, slug, dsb.).

---

## 4. Analisis Akurasi IR2

### 4.1 Elemen yang Dihasilkan dengan Benar ✓

**Roles dari Lane**
IR2 memperbaiki keterbatasan [I2] IR1 — array `sharedContext.roles` memuat tiga entri role terpisah (Logistics, Secretary, Warehouse) lengkap dengan `display`, `value`, `internal`, dan `pool`. Transformasi dari lane → role sudah benar.

**defaultRoutesPerRole**
```json
"logistics": "/logistics/insure-parcel",
"secretary": "/secretary/clarify-shipment-method",
"warehouse": "/warehouse/package-goods"
```
Masing-masing role diarahkan ke task pertama di lane-nya berdasarkan urutan BFS dari start event. Ini akurat sesuai alur BPMN.

**allRoutes (7/7 akurat)**
Seluruh 7 halaman task terdaftar dengan route, role, component name (PascalCase), dan `allowedRoles` yang tepat. Penamaan komponen menggunakan konvensi konsisten (`*Page`).

**Routing Kondisional — ClarifyShipmentMethodPage**
Ini bagian paling kompleks. IR2 berhasil memodelkan dua lapis gateway:
```
ClarifyShipmentMethod → ExclusiveGateway ("Special sandling?")
  ├── "yes" → Get3OffersFromLogisticCompanies
  └── "no" → InclusiveGateway_0p2e5vq
        ├── "If insurance necessary" → InsureParcel (Logistics) [parallelTrigger]
        └── "always" → WritePackageLabel
```
`conditionalRoutes` menangkap path Secretary ("no > always" dan "yes"), sementara `parallelTriggers` mengidentifikasi branch Logistics ("no > If insurance necessary") yang berjalan secara independen oleh role lain. Desain ini pragmatis dan benar secara semantik.

**Routing Konvergensi**
Semua path yang berakhir di `ExclusiveGateway_0z5sib0` (konvergensi Warehouse) dinavigasikan langsung ke `/warehouse/prepare-for-picking-up-goods`:
- InsureParcelPage → `/warehouse/prepare-for-picking-up-goods` ✓
- WritePackageLabelPage → `/warehouse/prepare-for-picking-up-goods` ✓
- SelectLogisticCompanyAndPlaceOrderPage → `/warehouse/prepare-for-picking-up-goods` ✓
- PackageGoodsPage → `/warehouse/prepare-for-picking-up-goods` ✓

**File generation tasks (12 tasks)**
Struktur 5 shared files (globalState, Layout, ProtectedRoute, LoginPage, App.tsx) + 7 module pages sudah lengkap dan tepat.

---

### 4.2 Ketidakakuratan dan Keterbatasan IR2

**[I5] Sinkronisasi parallel gateway tidak dimodelkan**
`ParallelGateway_02fgrfq` dalam BPMN adalah *AND-split* — kedua branch (Secretary dan Warehouse) harus berjalan **secara bersamaan** dan `ExclusiveGateway_0z5sib0` adalah *join* yang menunggu keduanya selesai. Namun di IR2, setiap role berjalan independen: role Warehouse bisa saja menyelesaikan PackageGoods dan langsung ke PrepareForPickingUpGoods sebelum branch Secretary selesai. Tidak ada mekanisme sinkronisasi antar-role dalam stateSchema yang dihasilkan.

**[I6] Condition string "no > always" adalah kompresi dua gateway**
Kondisi `"no > always"` pada `conditionalRoutes` merepresentasikan dua hop gateway sekaligus (ExclusiveGateway "no" → InclusiveGateway "always"). Secara semantik ini benar, namun menyembunyikan keberadaan `InclusiveGateway_0p2e5vq` sebagai entitas tersendiri. Bila ada kondisi "If insurance necessary" yang tidak terpenuhi (InclusiveGateway tidak mengeluarkan branch Logistics), kondisi ini tidak secara eksplisit tercermin di IR2.

**[I7] Ketergantungan cross-role tidak memiliki waitingFor hint**
Field `waitingFor` diset `null` untuk semua halaman, termasuk PrepareForPickingUpGoodsPage yang dalam BPMN sebenarnya menunggu dua branch (Secretary + Warehouse) selesai. IR2 mendokumentasikan bahwa fitur ini ada (`waitingFor` hint untuk intermediate event), namun tidak diaplikasikan untuk gateway-join synchronization.

**[I8] Rute InsureParcelPage melompati lane boundary tanpa konteks**
InsureParcelPage (Logistics) menavigasikan langsung ke `/warehouse/prepare-for-picking-up-goods`. Meskipun secara alur BPMN benar (Insure parcel → InclusiveGateway_1dgb4sg → ExclusiveGateway_1ouv9kf → ExclusiveGateway_0z5sib0 → PrepareForPickingUpGoods), perpindahan lintas-lane yang langsung ini bisa membingungkan LLM yang generate kode karena Logistics role mengakses route Warehouse.

---

## 5. Ringkasan Penilaian

| Aspek | Akurasi | Catatan |
|-------|---------|---------|
| Ekstraksi task (IR1) | **100%** | 7/7 task, nama, tipe, role, dan flow benar |
| Ekstraksi event (IR1) | **100%** | 2/2 event, trigger, dan role benar |
| Ekstraksi gateway (IR1) | **100%** | 6/6 gateway, tipe dan direction-inference benar |
| Ekstraksi sequence flow (IR1) | **100%** | 17/17 aliran dengan kondisi benar |
| Representasi roles (IR1) | **Parsial** | Lane assignment per-task ✓, tapi array `roles` hanya muat participant |
| Process name (IR1) | **Kurang** | Field `name` kosong meski data tersedia di participant |
| Roles di IR2 | **100%** | Lane → role mapping lengkap dan benar |
| Routing page (IR2) | **95%** | Navigasi per-task akurat; lompatan cross-lane kurang konteks |
| Routing kondisional (IR2) | **90%** | Gateway condition chains benar, tapi kompresi two-hop kurang eksplisit |
| Sinkronisasi paralel (IR2) | **Tidak dimodelkan** | Parallel join semantics hilang; single-user workaround tanpa penanda |
| Kelengkapan file tasks (IR2) | **100%** | 12 generate tasks sudah mencakup seluruh kebutuhan aplikasi |

### Kesimpulan

`main.py` mengekstrak elemen-elemen struktural BPMN (task, event, gateway, sequence flow, lane assignment) dengan **akurasi sangat tinggi**. Kemampuan inferensi `gatewayDirection` dari in/out-degree adalah fitur yang mengatasi ketidaklengkapan atribut BPMN dengan tepat. Transformasi ke IR2 berhasil memindahkan semantik BPMN ke dalam konteks React: role-based routing, conditional navigation, dan identifikasi parallel branches semua sudah benar.

Keterbatasan utama yang perlu ditangani adalah **tidak adanya mekanisme sinkronisasi multi-role** untuk BranchParallel dan InclusiveGateway-join, serta ketidaklengkapan array `roles` di IR1 yang hanya menyimpan participant bukan lane. Untuk kasus BPMN sederhana dengan satu pool dan lane sebagai role, pipeline ini sudah cukup handal sebagai dasar code generation.
