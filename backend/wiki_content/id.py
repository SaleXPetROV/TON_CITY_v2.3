# Wiki GRAM City — Bahasa Indonesia.
A = {
    "quick-start": dict(
        t="Mulai cepat",
        s="Lima langkah dari kunjungan pertama sampai punya bisnis sendiri selamanya.",
        b="""GRAM City adalah game ekonomi: bisnis memproduksi sumber daya, Anda menjualnya ke Kota dan ke pemain lain, lalu berkembang.
1. Ambil bisnis gratis: Peta → «Dijual». Bisnis itu milik Anda selama {{lease_days}} hari.
2. Mulai shift — bisnis bekerja {{shift_hours}} jam dan menaruh barang di gudang.
3. Jual barangnya: Perdagangan → «Saya» → «Jual sumber daya».
4. Perbaiki bisnis sebelum daya tahan turun di bawah 50%.
5. Sebelum sewa berakhir, naikkan bisnis ke level 1 — bisnis jadi milik Anda selamanya.
> Di bawah ada pengecekan akun Anda: apa yang sudah selesai dan apa berikutnya.""",
    ),
    "balances": dict(
        t="Mata uang dan saldo",
        s="$CITY, GRAM, dan tiga akun: utama, bonus, dan dibekukan.",
        b="""Semua di game dihitung dalam **$CITY**: 1 GRAM = {{city_per_gram}} $CITY. GRAM adalah koin TON — isi ulang hanya dengan TON.
- Akun **utama** — Anda isi ulang dan tarik dari sini. Penjualan bisnis level 1 ke atas masuk ke sini.
- **Bonus** — hadiah game dan penjualan bisnis level 0. Dipakai di game, tidak bisa ditarik.
- **Dibekukan** — uang untuk transaksi Anda: tender, sewa. Uang kembali atau keluar sesuai transaksi.
> Setiap pembelian memotong akun bonus dulu, lalu akun utama. Bonus terpakai, dan uang yang bisa ditarik tetap milik Anda.""",
        show=["Ketuk saldo — tiga akun serta tombol isi ulang dan tarik terbuka."],
    ),
    "earning": dict(
        t="Cara menghasilkan",
        s="Penjualan, kontrak, sewa, dan pertumbuhan bisnis.",
        b="""- **Menjual sumber daya** di pasar — ke pemain dan ke Kota. Penghasilan utama.
- **Tender** — kesepakatan pasokan harian: sumber daya terkirim sendiri, uang masuk tanpa lot.
- **Sewa** — sewakan bisnis level 1 ke atas per hari.
- **Peningkatan** — makin tinggi level, makin banyak barang per shift.
- **Rantai** — sumber daya tingkat 1 untuk bisnis tingkat 2, dan tingkat 2 untuk tingkat 3. Beli bahan lebih murah, jual lebih mahal.
> Perhatikan pajak: setiap penjualan dikenai pajak sesuai tingkat sumber daya — lihat [[taxes|Pajak]].""",
    ),
    "interface": dict(
        t="Antarmuka",
        s="Menu bawah, menu ☰, dan tombol «?» di layar.",
        b="""Di bawah ada lima bagian:
- **Peta** — kota dan lahan.
- **Gudang** — sumber daya dan penguat Anda.
- **Bisnis** — produksi Anda: shift, perbaikan, peningkatan.
- **Perdagangan** — pasar, lot Anda, tender.
- **Komunitas** — liga, aliansi, obrolan.
Menu ☰ berisi Wiki, Riwayat, Hadiah, Marketplace, Pengaturan, Bantuan, Aturan, dan Peta jalan.
> Setiap layar kecuali «Bisnis» punya tombol «?» di header — membuka artikel tentang layar itu.""",
        show=["Lima bagian game. Di komputer, ada di bilah samping kiri.", "Menu ☰: Wiki, Riwayat, Pengaturan, Bantuan, dan lainnya."],
    ),
    "first-days": dict(
        t='Rencana 3 hari pertama',
        s='Apa yang dilakukan agar bisnis gratis jadi milik Anda selamanya.',
        b="""Bisnis gratis milik Anda selama {{lease_days}} hari. Untuk mempertahankannya:
1. Ambil bisnis di peta.
2. Mulai shift dan dapatkan batch barang pertama.
3. Jual barangnya.
4. Mulai shift setiap {{shift_hours}} jam — kami akan mengingatkan.
5. Perbaiki saat daya tahan turun.
6. Sebelum sewa berakhir, naikkan bisnis ke level 1 dengan $CITY dari akun utama.
> Hadiah rencana adalah satu sumber daya tingkat 3 pilihan Anda. Masuk ke gudang: tidak bisa dijual; aktifkan buff-nya sendiri kapan saja — atau pakai untuk peningkatan.""",
    ),
    "notifications": dict(
        t="Notifikasi dan pengaturan",
        s="Pengingat, jam tenang, bot Telegram, dan bahasa.",
        b="""Di Pengaturan pilih pengingat: akhir shift, keausan di bawah 50%, gudang sebelum pembusukan, harga, penjualan.
- **Jam tenang** — tanpa notifikasi di malam hari.
- **Bot Telegram** — notifikasi juga masuk ke Telegram.
- **«Hari-hari pertama»** — tips untuk pemula, maksimal 3 sehari.
- Bahasa game dan «Ulangi panduan» juga ada di sini.""",
        show=["Nyalakan dan matikan notifikasi per topik di sini."],
    ),
    "maps": dict(
        t="Peta dan kota",
        s="Cara membaca peta: filter, zoom, peta mini, «Dijual».",
        b="""Saat ini yang terbuka adalah **Pulau GRAM**; kota lain sedang dibangun.
- **Filter** menurut jenis bisnis; **★** — terbang ke bisnis Anda; **%** — tampilkan hanya yang dijual.
- **+ / −** — zoom, **⌂** — kembali ke pusat.
- **Peta mini** — ketuk, kamera terbang ke sana.
- **«Dijual»** di bawah — semua bisnis yang bisa diambil atau dibeli sekarang.
- **🌙** — mode malam; pilihan Anda diingat.""",
        show=["Pilih kota — petanya terbuka."],
    ),
    "zero-business": dict(
        t="Bisnis level 0",
        s="Bisnis gratis dari Kota selama {{lease_days}} hari — cara kerjanya.",
        b="""Kota memberi setiap pemula satu bisnis gratis: Peta → «Dijual» → «Ambil gratis».
- Bisnis itu milik Anda selama **{{lease_days}} hari**. Agar menjadi milik selamanya, naikkan ke level 1. Harganya adalah harga bisnis itu di peta, hanya dari akun utama.
- Harga barang adalah **harga sistem** dan tidak bisa diubah. Uang penjualan masuk ke akun bonus.
- Selama level 0, pemain lain bisa membelinya dengan harga peta ×{{zero_mult}}. Lalu bisnis itu menjadi miliknya, dan Anda bisa mengambil yang baru.
- Jika tidak ditingkatkan sampai batas waktu, bisnis kembali ke Kota dan lahannya kosong. Kami mengingatkan 24, 12, dan 2 jam sebelumnya.
> Bisnis gratis hanya bisa diambil jika Anda belum pernah punya bisnis level 1.""",
        show=["Ketuk «Dijual» — daftar bisnis gratis dari Kota terbuka."],
    ),
    "plots": dict(
        t="Lahan",
        s="Setiap bisnis punya tempatnya sendiri di peta.",
        b="""Peta dibagi menjadi tempat-tempat, masing-masing dengan bisnis jenis tertentu. Jenisnya terlihat di peta dan di kartu tempat.
- Tempat kosong bisa diambil (gratis {{lease_days}} hari) atau dibeli.
- Harga tergantung jenis bisnis dan lokasinya: makin dekat ke pusat, makin mahal.
- Kartu menunjukkan apa yang diproduksi dan dipakai bisnis, serta rantai produksinya.""",
    ),
    "buy-business": dict(
        t="Membeli bisnis",
        s="Bisnis level 1 milik Anda selamanya, penghasilan masuk ke akun utama.",
        b="""Beli di peta (tempat kosong) atau di Marketplace (bisnis pemain lain).
- Bisnis yang dibeli langsung level 1 dan milik Anda selamanya.
- Pembayaran: akun bonus dulu, lalu akun utama.
- Selama punya bisnis level 0, Anda tidak bisa membeli yang lain — tingkatkan dulu.
- Pilih menurut rantai: apa yang akan Anda beli sebagai bahan dan siapa yang membeli barang Anda.""",
        show=["Marketplace: bisnis pemain yang dijual, iklan Anda, dan sewa."],
    ),
    "districts": dict(
        t="Distrik dan tempat yang dijual",
        s="Mengapa tidak semua tempat di peta bisa dibeli.",
        b="""Kota dibuka per distrik. Anda hanya bisa membeli tempat di distrik yang terbuka, dan hanya yang sudah dijual.
- Distrik dan tempat baru dibuka bertahap — pantau «Dijual» dan pengumuman.
- Distrik tertutup terlihat di peta, tetapi belum bisa dibeli.""",
    ),
    "tiers": dict(
        t="Tingkat bisnis",
        s="Tingkat 1, 2, dan 3: apa yang diproduksi dan bedanya.",
        b="""Semua bisnis dan sumber daya terbagi dalam tiga tingkat.
- **Tingkat 1** — sumber daya dasar: energi, logam, kuarsa, biomassa, dll. Kota juga membelinya.
- **Tingkat 2** — produk dari sumber daya tingkat 1: chip, model AI, dll. Dibeli pemain.
- **Tingkat 3** — sumber daya langka yang mengaktifkan efek.
Makin tinggi tingkatnya, makin mahal barang dan perbaikan, dan makin banyak tempat gudang yang dipakai.
[[table:taxes]]""",
    ),
    "shift": dict(
        t="Shift",
        s="Bisnis hanya berproduksi selama shift — {{shift_hours}} jam.",
        b="""Tanpa shift, bisnis diam: tidak berproduksi dan tidak aus.
1. Bisnis → kartu bisnis → «Mulai shift».
2. Selama {{shift_hours}} jam bisnis memproduksi barang dan memakai bahan setiap menit.
3. Saat shift selesai kami mengingatkan — mulai shift berikutnya.
> Agar shift mulai sendiri, aktifkan penguat «Mulai shift otomatis» (Gudang → Penguat).""",
        show=["Status bisnis: bekerja atau diam.", "Tombol shift ada di sini."],
    ),
    "raw-materials": dict(
        t="Bahan",
        s="Apa yang dipakai bisnis dan di mana mendapatkannya.",
        b="""Selama shift bisnis memakai bahan — sumber daya bisnis lain. Jumlahnya tertera di kartu, di kanan, «per hari».
- Beli bahan di pasar: Perdagangan → «Beli».
- Atau buat tender — bahan datang sendiri setiap hari.
- Tanpa bahan, produksi berkurang.
> Pemula mendapat bahan untuk satu hari bersama bisnisnya.""",
        show=["Berapa yang diproduksi bisnis per jam.", "Berapa bahan yang dipakai per hari."],
    ),
    "durability": dict(
        t="Daya tahan dan perbaikan",
        s="Batas 50%: di bawahnya barang lebih sedikit dan perbaikan dua kali lipat.",
        b="""Selama shift bangunan aus.
[[table:durability]]
Anda membayar setiap persen yang kurang. Persen di bawah 50% berharga dua kali lipat: dengan 1 $CITY per %, perbaikan dari 46% = 50 + 4×2 = **58 $CITY**.
[[table:repair]]
> Saat daya tahan turun di bawah 50%, Anda mendapat notifikasi — di game dan di Telegram.""",
        show=["Daya tahan bangunan saat ini.", "Tombol perbaikan — bayar hanya persen yang kurang."],
    ),
    "upgrade": dict(
        t='Peningkatan',
        s='Level lebih tinggi, barang dan gudang lebih banyak; di level 1 bisnis milik Anda selamanya.',
        b="""- **Level 0 → 1** seharga bisnis di peta, hanya dari akun utama. Setelah itu bisnis milik Anda selamanya dan penghasilan masuk ke akun utama.
- Lalu level hingga 10: lebih banyak barang per shift dan gudang lebih besar, tetapi juga lebih banyak bahan.
- Peningkatan ke level 2 dan seterusnya juga butuh sumber daya tingkat 3 — tiap jenis bisnis punya sendiri:
[[table:upgrade_res]]
- Sumber daya hadiah yang tidak bisa dijual juga bisa dipakai.
- Harga level berikutnya tertera di tombol «Tingkatkan».
> Bisnis yang disewa tidak bisa ditingkatkan.""",
        show=['Tombol peningkatan dan harganya.'],
    ),
    "chains": dict(
        t="Rantai produksi",
        s="Apa dibuat dari apa.",
        b="""Sumber daya tingkat 1 adalah bahan untuk tingkat 2, dan tingkat 2 untuk tingkat 3.
- Kartu tempat di peta punya «Rantai produksi»: apa yang dipakai bisnis dan ke mana barangnya pergi.
- Bangun mengikuti rantai: beli bahan dari tetangga rantai dan jual ke yang membutuhkan barang Anda.""",
    ),
    "patron-buffs": dict(
        t='Buff bisnis dan pelindung',
        s='Bisnis tingkat 3 bisa menjadi pelindung dan memberi buff kepada bisnis binaannya.',
        b="""Setiap bisnis bisa memilih pelindung — bisnis tingkat 3.
- Pemilik pelindung memilih salah satu buff di bawah untuk bisnis binaannya.
- Pelindung menerima 1% dari penghasilan bisnis binaannya.
- Pelindung hanya bisa diganti setelah jeda.
[[table:patrons]]
- Buff bisnis terlihat di kartunya.
- Buff sumber daya tingkat 3 berbeda: diaktifkan di gudang, lihat [[t3-buffs|Buff sumber daya tingkat 3]].""",
    ),
    "skins": dict(
        t="Skin",
        s="Tampilan lain bisnis di peta.",
        b="""Skin hanya mengubah tampilan bangunan di peta, tidak memengaruhi bisnis.
- Skin didapat dari tugas mitra.
- Dipilih untuk setiap bisnis secara terpisah.
- Bisnis yang disewa tidak bisa ganti skin.""",
    ),
    "business-sale": dict(
        t="Menjual bisnis",
        s="Cara menjual bisnis di Marketplace dan pajaknya.",
        b="""Bisnis level 1 ke atas bisa dipasang di Marketplace dengan harga Anda.
- Penjual membayar pajak sesuai tingkat bisnis:
[[table:taxes]]
- Jika bisnis menjadi jaminan pinjaman, lunasi pinjaman dulu.
- Bisnis yang disewakan tidak bisa dijual selama masa sewa.
> Bisnis level 0 tidak bisa dijual: belum milik Anda sampai ditingkatkan.""",
        show=["Marketplace: tab iklan Anda — di sini bisnis dipasang untuk dijual."],
    ),
    "rental": dict(
        t="Sewa",
        s="Sewakan bisnis per hari atau sewa milik orang lain.",
        b="""Pemilik bisnis level 1 ke atas bisa menyewakannya: harga per hari dan masa hingga {{rent_max_days}} hari.
- Penyewa langsung membekukan sewa untuk seluruh masa plus deposit. Setiap hari pemilik menerima sewa harian dikurangi komisi {{rent_fee}}%.
- Selama sewa, bisnis bekerja untuk penyewa: barang, bahan, dan perbaikan miliknya.
- Bisnis yang disewa tidak bisa dijual, ditingkatkan, atau ganti skin.
- Deposit kembali ke penyewa kecuali bisnis sangat aus.""",
    ),
    "seizure": dict(
        t="Penyitaan",
        s="Kapan Kota mengambil bisnis.",
        b="""Bisnis disita dalam dua kasus.
- **Tidak ada aktivitas.** Dalam {{act_days}} hari mana pun Anda harus membeli {{act_buy}} unit atau menjual {{act_sell}} unit di pasar — lihat [[activity-rule|Aturan aktivitas]].
- **Utang pinjaman.** Pinjaman menunggak dan tidak ada pembayaran selama {{credit_days}} hari. Pembayaran apa pun menghapus tunggakan.
Bisnis yang disita dijual oleh GRAM CITY. Hasil penjualan melunasi utang dulu; sisanya untuk pemilik lama.
> Kami mengingatkan di game dan Telegram 3 hari sebelum penyitaan.""",
    ),
    "resources": dict(
        t="Sumber daya",
        s="Isi gudang dan perbedaan sumber daya.",
        b="""Gudang menyimpan semua yang diproduksi bisnis Anda dan yang Anda beli.
[[table:weights]]
- Di bawah setiap sumber daya — nilainya saat ini.
- Sumber daya tingkat 3 bisa dijual atau diaktifkan sebagai efek.
- Sumber daya dari hadiah disimpan terpisah: tidak bisa dijual.""",
        show=["Gudang: ruang dan nilai sumber daya Anda."],
    ),
    "capacity": dict(
        t="Kapasitas dan bobot",
        s="Berapa banyak yang muat di gudang.",
        b="""Ruang gudang terbatas. Kapasitas adalah jumlah gudang semua bisnis Anda; level lebih tinggi, gudang lebih besar.
[[table:weights]]
- Lot di pasar juga memakai tempat.
- Yang tidak muat membusuk lebih cepat — lihat [[spoilage|Pembusukan]].""",
        show=["Ruang gudang yang terpakai dan kosong."],
    ),
    "warehouse-value": dict(
        t="Perkiraan nilai gudang",
        s="Berapa nilai semua yang Anda miliki.",
        b="""Di atas daftar sumber daya ada perkiraan nilai gudang: berapa harga semua sumber daya Anda dengan harga saat ini.
- Di bawah setiap sumber daya, nilainya.
- Ini perkiraan: harga sebenarnya adalah harga jual Anda.""",
        show=["Perkiraan nilai seluruh gudang."],
    ),
    "spoilage": dict(
        t="Pembusukan pukul {{spoil_time}}",
        s="Setiap hari sebagian barang di gudang membusuk.",
        b="""Setiap hari pukul **{{spoil_time}} waktu Moskow**, **{{spoil_in}}%** barang di gudang membusuk, dan **{{spoil_over}}%** dari yang melebihi batas.
- Pembusukan berlaku sama untuk semua sumber daya.
- Lot di pasar tidak membusuk.
- Penguat «Perlindungan gudang» mencegahnya.
> Jangan menimbun — jual sebelum {{spoil_time}}. Kami kirim pengingat di sore hari.""",
        show=["Gudang: yang ada di sini membusuk pukul {{spoil_time}}."],
    ),
    "boosters": dict(
        t='Penguat',
        s='Mulai shift otomatis, perlindungan gudang, perbaiki semua, XP ×2 — apa efeknya.',
        b="""Penguat diaktifkan di Gudang → Penguat. Tidak bisa dijual.
[[table:boosters]]
- Sumber daya tingkat 3 juga diaktifkan di sini — masing-masing punya buff, lihat [[t3-buffs|Buff sumber daya tingkat 3]].
- Maksimal dua penguat dan buff aktif bersamaan.
> Penguat adalah hadiah City Pass: satu di setiap level, lebih banyak di jalur premium.""",
        show=['Tab «Penguat»: yang Anda punya dan yang aktif.'],
    ),
    "t3-buffs": dict(
        t='Buff sumber daya tingkat 3',
        s='Efek setiap sumber daya tingkat 3 dan cara mengaktifkannya.',
        b="""Setiap sumber daya tingkat 3 bisa diaktifkan sebagai buff — efek sementara untuk semua bisnis Anda.
[[table:t3buffs]]
1. Gudang → Penguat.
2. Ketuk «Aktifkan» di samping sumber daya — 1 unit terpakai.
3. Buff berlaku selama waktu yang tertera; sisa waktunya ada di «Sedang aktif».
- Cara mendapatkan: diproduksi bisnis tingkat 3, dijual pemain di pasar, dan menjadi hadiah City Pass. Satu gratis untuk [[first-days|rencana 3 hari]].
- Sumber daya hadiah tidak bisa dijual, tetapi bisa diaktifkan sebagai buff atau dipakai untuk [[upgrade|peningkatan]] bisnis.
- Buff yang sama tidak bisa berjalan dua kali; maksimal dua penguat dan buff sekaligus.
> Sumber daya tidak pernah aktif sendiri: ia menunggu di gudang sampai Anda mengetuk «Aktifkan».""",
        show=['Tab «Penguat»: sumber daya tingkat 3 dan tombol «Aktifkan».'],
    ),
    "buy": dict(
        t="Membeli sumber daya",
        s="Lot pemain, filter, dan pembayaran.",
        b="""Perdagangan → «Beli» — lot pemain lain dan Kota.
1. Cari sumber daya: filter menurut sumber daya, harga, dan jumlah.
2. Ketuk lot dan isi jumlah — berapa pun unitnya.
3. Periksa total dan konfirmasi.
- Harga **per unit**.
- Pembayaran: akun bonus dulu, lalu akun utama.
- Sumber daya langsung masuk gudang — pastikan ada tempat.""",
        show=["Tab «Beli» — lot pemain.", "Filter: sumber daya, harga, jumlah."],
    ),
    "sell": dict(
        t="Menjual sumber daya",
        s="Lot, harga, pajak, {{lot_hours}} jam.",
        b="""Pasang barang dari gudang — semua pemain melihatnya. Pemain atau Kota bisa membeli.
1. Perdagangan → tab «Saya».
2. «Jual sumber daya» dan pilih barang.
3. Isi jumlah — berapa pun unitnya. Harga per unit; tingkat 1 sampai sen.
4. Periksa harga dan jumlah bersih.
5. «Daftar».
[[table:taxes]]
> Lot yang tidak terjual kembali ke gudang setelah {{lot_hours}} jam. Selama di pasar, lot memakai tempat gudang tetapi tidak membusuk.""",
        show=["Ketuk «Jual sumber daya» — jendela penjualan terbuka."],
    ),
    "edit-lot": dict(
        t="Mengubah atau menarik lot",
        s="Ubah jumlah dan harga tanpa menarik lot.",
        b="""Di tab «Saya» setiap lot punya dua tombol.
- **«Ubah»** — ubah jumlah atau harga. Jumlah bebas mulai 1 unit.
- **«Batal»** — tarik lot; barang kembali ke gudang.
- Jumlah lot terbatas: satu slot per bisnis, satu jika tidak punya bisnis.
> Bisnis level 0 tidak bisa mengubah harga — itu harga sistem.""",
        show=["Lot Anda: «Ubah» dan «Batal»."],
    ),
    "city-market": dict(
        t="Kota di pasar",
        s="Apa yang dibeli Kota dan kapan.",
        b="""Pasar Kota adalah jaring pengaman untuk pemula dan pasar yang sepi. Kota membeli di bawah dan menjual di atas harga acuan — berdagang dengan pemain lebih menguntungkan.
- Kota hanya membeli sumber daya **tingkat 1**.
- Penjualan pertama pemula dibeli hampir seketika.
- Lot bisnis level 0 dibeli dengan harga sistem; uang masuk ke akun bonus.
- Level 1 ke atas: lot dengan harga sama atau di bawah harga Kota; uang masuk ke akun utama.
- Semua yang dibeli Kota dipasang lagi di pasar.""",
    ),
    "tenders": dict(
        t="Tender",
        s="Kesepakatan pasokan harian.",
        b="""Tender adalah pesanan: «butuh X unit sumber daya per hari dengan harga ini».
1. Perdagangan → «Kontrak» → «Pertukaran»: pesanan terbuka pemain.
2. Kirim penawaran. Tanpa jawaban, penawaran ditutup setelah 72 jam.
3. Jika diterima, sumber daya terkirim sendiri setiap hari dan uang masuk tanpa lot (dikurangi pajak).
- «Pembelian» — pesanan Anda, «Pasokan» — kesepakatan Anda.
> Jika sumber daya atau uang kurang, ada 24 jam untuk memperbaiki; setelah itu kesepakatan putus dengan denda.""",
        show=["Buka «Kontrak».", "«Pertukaran» — pesanan terbuka pemain."],
    ),
    "contracts": dict(
        t="Kontrak kerja sama",
        s="Pasokan antarbisnis — dan buff pelindung.",
        b="""Kontrak kerja sama adalah pasokan harian sumber daya dari satu bisnis ke bisnis lain hingga 90 hari.
- Pemasok menentukan sumber daya, jumlah per hari, harga, dan masa.
- Jika pemasok adalah bisnis tingkat 3, buff-nya berlaku pada bisnis penerima selama kontrak berjalan.
- Bisa dibatalkan kapan saja; yang sudah terkirim tetap milik penerima.""",
    ),
    "analytics": dict(
        t="Analitik harga",
        s="Grafik, tren, volume.",
        b="""Analitik — grafik harga setiap sumber daya.
- Di mana lebih untung menjual dan apa yang lebih murah dibeli.
- Berapa yang terjual per hari dan bagaimana harga bergerak.
- Dibuka dengan tombol «Analitik» di layar «Bisnis».""",
        show=["Ketuk «Analitik» — grafik harga terbuka."],
    ),
    "taxes": dict(
        t="Pajak",
        s="Tarif per tingkat dan ke mana pajak pergi.",
        b="""Setiap penjualan sumber daya dikenai pajak sesuai tingkatnya. Tarif ditetapkan pengelola; tarif saat ini ada di bawah.
[[table:taxes]]
- Jumlah bersih terlihat sebelum lot dipasang.
- Sebagian pajak ({{ref_pct}}% dari transaksi) diberikan kepada yang mengundang penjual — penjual tidak rugi.
- Efek sumber daya tingkat 3 bisa menurunkan biaya perdagangan.""",
    ),
    "deposit": dict(
        t="Isi ulang",
        s="Cara memasukkan GRAM ke akun utama.",
        b="""1. Ketuk saldo → «Isi ulang».
2. Hubungkan dompet: Tonkeeper, Telegram Wallet, atau lainnya.
3. Kirim GRAM. **GRAM adalah koin TON — kirim hanya TON.**
4. Uang masuk ke akun utama: 1 GRAM = {{city_per_gram}} $CITY.
> Kirim hanya dari dompet yang terhubung ke akun Anda.""",
        show=["Ketuk saldo — ada «Isi ulang»."],
    ),
    "withdraw": dict(
        t="Penarikan",
        s="Apa yang bisa ditarik dan syaratnya.",
        b="""Hanya akun **utama** yang bisa ditarik; akun bonus tidak.
1. Ketuk saldo → «Tarik».
2. Isi jumlah (mulai {{withdraw_min}} GRAM) dan konfirmasi dengan kode 2FA atau Passkey.
3. Permintaan diperiksa lalu dikirim ke dompet Anda.
- Biayanya {{withdraw_fee}}%. Lewat bank pemain lebih cepat, dengan biaya bank itu sendiri (hingga {{instant_fee_max}}%).""",
        show=["Ketuk saldo — ada «Tarik»."],
    ),
    "security": dict(
        t="Mengapa 2FA dan Passkey",
        s="Tanpanya tidak bisa menarik — ini alasannya.",
        b="""Dompet penarikan diganti di pengaturan. Orang yang masuk ke akun Anda — ponsel, email, atau Telegram — bisa menautkan dompetnya sendiri.
- **2FA** — kode dari aplikasi autentikator.
- **Passkey** — sidik jari atau wajah di perangkat.
Tanpa kode atau Passkey, penarikan tidak akan berhasil.
> Dukungan tidak pernah meminta kode, kata sandi, atau frasa seed.""",
        show=["Aktifkan 2FA — kode dari aplikasi.", "Atau tambahkan Passkey — sidik jari atau wajah."],
    ),
    "history": dict(
        t="Riwayat transaksi",
        s="Setiap pembelian, penjualan, pajak, dan hadiah.",
        b="""Menu ☰ → Riwayat — semua transaksi saldo Anda.
- Filter menurut jenis: pembelian, penjualan, pajak, hadiah, isi ulang, penarikan.
- Setiap transaksi menampilkan jumlah, akun (utama atau bonus), dan waktu.""",
        show=["Filter jenis transaksi."],
    ),
    "credit": dict(
        t="Pinjaman dengan jaminan bisnis",
        s="Uang sekarang, sebagian penghasilan melunasinya.",
        b="""Pinjam $CITY dengan bisnis sebagai jaminan — dari negara atau bank pemain. Sebagian penghasilan melunasinya otomatis.
- Hanya dengan bisnis level 1 ke atas, hingga {{credit_max}}% dari nilainya.
[[table:credit]]
- Tidak ada pembayaran selama {{credit_days}} hari (bank punya batas sendiri) — pinjaman menunggak dan bunga berlipat dua.
- {{credit_days}} hari lagi menunggak tanpa satu pun pembayaran — bisnis disita. Pembayaran apa pun menghapus tunggakan.
- Bisnis yang disita dijual; dari hasilnya diambil pinjaman dan bunga ganda: bunga {{credit_rate}}% → pinjaman × {{credit_back}}. Sisanya milik Anda.""",
        show=["Tombol «Ambil Kredit»."],
    ),
    "banks": dict(
        t="Bank pemain",
        s="GRAM Bank: pinjaman dan penarikan cepat dari pemain.",
        b="""Pemilik bisnis GRAM Bank adalah sebuah bank.
- Meminjamkan ke pemain dengan bunganya sendiri (maksimal {{bank_rate_max}}%).
- Melayani penarikan cepat dengan biayanya sendiri (hingga {{instant_fee_max}}%).
- Hanya bank dengan daya tahan 50% ke atas yang beroperasi.""",
    ),
    "daily-login": dict(
        t="Login harian",
        s="Hadiah naik {{daily_days}} hari berturut-turut.",
        b="""Masuk setiap hari — hadiah naik: dari {{daily_first}} sampai {{daily_last}} $CITY di hari ke-{{daily_days}}.
- Untuk mengklaimnya, selesaikan satu target harian.
- Terlewat sehari, rangkaian mulai dari awal. Perisai rangkaian menyelamatkan satu hari yang terlewat.
- Hadiah masuk ke akun bonus.""",
        show=["Kartu login harian."],
    ),
    "quests": dict(
        t="Tugas dan target",
        s="Jalur pemula, target harian dan mingguan.",
        b="""- **Jalur pemula** — 7 target berturut-turut: bisnis, shift, pembelian, lot, penjualan, perbaikan, peningkatan.
- **Target harian** — 3 setiap hari, **target mingguan** — 3 lagi.
- Progres dihitung sendiri — tinggal ketuk «Klaim».
- Hadiah masuk ke akun bonus dan XP City Pass. Semua target mingguan memberi perisai rangkaian.""",
        show=["Target hari ini."],
    ),
    "partner-tasks": dict(
        t="Tugas mitra",
        s="Langganan dan aksi di mitra — untuk $CITY dan skin.",
        b="""Tugas → «Mitra»: berlangganan kanal, membuka aplikasi mitra, dll.
- Hadiahnya $CITY ke akun bonus, kadang skin.
- Beberapa tugas memerlukan Telegram yang terhubung.""",
        show=["Tab tugas mitra."],
    ),
    "city-pass": dict(
        t="City Pass",
        s="Musim {{pass_levels}} level: XP dan hadiah.",
        b="""City Pass adalah musim dengan {{pass_levels}} level.
- XP didapat dari target harian dan mingguan, shift, perbaikan, penjualan ke pemain, dan rangkaian login.
- **Jalur gratis** — hadiah di setiap level: penguat, sumber daya tingkat 3, perisai.
- **Premium** — hadiah tambahan di level 1, 5, 10…; dibeli dari akun utama.
- Ambil hadiah dengan tombol «Klaim».""",
        show=["Level dan XP musim Anda."],
    ),
    "referrals": dict(
        t="Referral",
        s="Undang teman — dapatkan bagian pajak dari penjualan mereka.",
        b="""Tombol 👥 di atas layar «Bisnis» berisi tautan Anda.
- Teman bermain lewat tautan Anda — Anda mendapat {{ref_pct}}% dari jumlah penjualannya di pasar.
- Itu bagian dari pajak: teman Anda tidak rugi.
- Daftar yang diundang dan hasilnya juga ada di sana.""",
        show=["Ketuk 👥 — tautan dan teman Anda terbuka."],
    ),
    "chat": dict(
        t="Obrolan",
        s="Obrolan umum dan obrolan aliansi.",
        b="""Obrolan umum semua pemain dan obrolan aliansi Anda.
- Sepakati transaksi dan bagikan tips.
- Setiap pesan bisa diterjemahkan dengan tombol.
- Jangan buka tautan orang asing dan jangan pernah bagikan kode — lihat [[safety|Keamanan]].""",
        show=["Kanal obrolan: umum dan aliansi."],
    ),
    "leagues": dict(
        t="Liga",
        s="Kompetisi mingguan antarpemain setara.",
        b="""Setiap minggu Anda masuk grup pemain dengan kekuatan setara.
- Poin dari target, shift, perbaikan, penjualan ke pemain, dan rangkaian login.
- Yang terbaik naik: Perunggu → Perak → Emas → Platinum → Berlian.
- **‹ ›** — liga lain, **«Seluruh divisi»** — semua pemain, pencarian, dan teman.
- Hadiah mingguan — $CITY ke akun bonus dan perisai rangkaian.
> Penjualan ke Kota dan antarakun tertaut tidak dihitung.""",
        show=["Geser liga dengan panah.", "Pengalih peringkat."],
    ),
    "alliances": dict(
        t="Aliansi",
        s="Tim pemain: kas, obrolan, level.",
        b="""Aliansi adalah tim pemain: kas bersama, obrolan, dan level.
- Bisa langsung bergabung — terbuka, lewat permintaan, atau undangan.
- Untuk membuat: City Pass level {{alliance_level}}, satu bisnis, dan {{alliance_cost}} $CITY.
- XP aliansi = 10% XP City Pass anggota; Anda tidak kehilangan apa pun.
- Pembayaran dari kas masuk ke akun bonus.""",
        show=["Tab «Aliansi»."],
    ),
    "leaderboard": dict(
        t="Peringkat",
        s="Pemain teratas menurut saldo, penghasilan, bisnis, dan perdagangan.",
        b="""Peringkat menampilkan pemain teratas. Urutkan:
- menurut saldo, penghasilan, jumlah bisnis, jumlah lahan, volume perdagangan.
- Posisi Anda tampil di bawah daftar.""",
    ),
    "profile": dict(
        t="Profil pemain",
        s="Statistik, aliansi, Founder Pass.",
        b="""Ketuk avatar Anda — profil terbuka: statistik, aliansi, level City Pass.
- Profil pemain lain dibuka dari obrolan dan peringkat.""",
        show=["Profil Anda."],
    ),
    "activity-rule": dict(
        t="Aturan aktivitas",
        s="Kota mengambil bisnis dari yang tidak berdagang.",
        b="""Dalam **{{act_days}} hari** mana pun Anda harus **membeli {{act_buy}} unit** atau **menjual {{act_sell}} unit** di pasar — salah satu sudah cukup.
- Jika tersisa 3 hari sebelum penyitaan, kami mengingatkan di game dan Telegram.
- Di bawah — angka Anda dalam {{act_days}} hari terakhir.""",
    ),
    "zero-limits": dict(
        t="Batasan level 0",
        s="Apa yang tidak bisa selama bisnis level 0.",
        b="""Selama Anda punya bisnis level 0:
- tidak bisa membeli bisnis lain atau mengambil pinjaman;
- harga barang adalah harga sistem, uang penjualan masuk ke akun bonus;
- tidak bisa menjual atau menyewakan bisnis;
- pemain lain bisa membelinya dengan harga peta ×{{zero_mult}}.
Naik ke level 1 menghapus semua batasan.""",
    ),
    "safety": dict(
        t="Keamanan dan penipuan",
        s="Agar tidak kehilangan akun dan uang.",
        b="""- Dukungan **tidak pernah** meminta kode 2FA, kata sandi, atau frasa seed.
- Jangan buka tautan dari pesan pribadi «dari administrasi».
- Aktifkan 2FA atau Passkey — tanpanya tidak bisa menarik.
- Bertransaksi hanya lewat pasar dan tender: «kirim uang dulu, nanti saya kirim sumber daya» adalah penipuan.
> Pesan mencurigakan? Laporkan di obrolan atau hubungi dukungan.""",
    ),
    "faq": dict(
        t="Pertanyaan umum",
        s="Jawaban singkat untuk hal utama.",
        b="""# Mengapa barang saya hilang?
Setiap hari pukul {{spoil_time}} waktu Moskow sebagian membusuk — lihat [[spoilage|Pembusukan]]. Lot yang tidak terjual kembali ke gudang setelah {{lot_hours}} jam.
# Mengapa bisnis saya tidak berproduksi?
Tidak ada shift, tidak ada bahan, atau daya tahan 0%.
# Mengapa bonus tidak bisa ditarik?
Akun bonus hanya dipakai di game.
# Mengapa Kota tidak membeli lot saya?
Kota hanya membeli tingkat 1, dan hanya dengan harga sama atau di bawah harganya.
# Ke mana bisnis gratis saya?
Sewa {{lease_days}} hari berakhir tanpa peningkatan, atau pemain lain membelinya.""",
    ),
    "glossary": dict(
        t="Glosarium",
        s="Istilah game dalam bahasa sederhana.",
        b="""= Akun bonus | Hadiah game: dipakai di game, tidak bisa ditarik
= Akun utama | Uang yang bisa diisi ulang dan ditarik
= Aliansi | Tim pemain dengan kas dan obrolan
= Ambil gratis | Mengambil bisnis level 0 gratis selama {{lease_days}} hari
= Buff | Keuntungan sementara: lebih banyak barang atau biaya lebih rendah
= Escrow | Uang yang dibekukan untuk transaksi
= Harga sistem | Harga tetap barang bisnis level 0
= Lot | Iklan penjualan sumber daya Anda di pasar
= Pelindung | Bisnis tingkat 3 yang buff-nya berlaku pada mitra kontrak
= Pembusukan | Hilangnya sebagian barang setiap hari pukul {{spoil_time}} waktu Moskow
= Penguat | Efek sementara: mulai shift otomatis, perlindungan gudang, dll.
= Penyitaan | Kota mengambil bisnis karena tidak aktif atau utang
= Shift | {{shift_hours}} jam saat bisnis berproduksi dan aus
= Tender | Pesanan pasokan harian sumber daya
= Tingkat | Kelompok bisnis dan sumber daya: 1, 2, atau 3
= GRAM | Koin TON di dalam game
= $CITY | Mata uang game: 1 GRAM = {{city_per_gram}} $CITY""",
    ),
    "support": dict(
        t="Dukungan",
        s="Willy GRAM dan agen manusia.",
        b="""Menu ☰ → Bantuan — obrolan dukungan.
- Pertama menjawab **Willy GRAM** — asisten yang bekerja dengan basis jawaban. Ia memeriksa akun Anda dan mengirim tautan artikel.
- Jika perlu, manusia mengambil alih.
- Tulis dalam bahasa Anda — jawabannya datang dalam bahasa yang sama.
> Dukungan tidak pernah meminta kode atau frasa seed.""",
        show=["Menu ☰ — ada «Bantuan»."],
    ),
}
