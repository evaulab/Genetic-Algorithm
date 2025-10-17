# -*- coding: utf-8 -*-
"""
Created on Fri Oct 17 20:25:24 2025

@author: evrim
"""
import pandas as pd
import numpy as np

# 1️⃣ Dosya Yolları: Ana veri dosyalarının konumlarını belirle
kumas_path = "CC:/Users/evrim/OneDrive/Masaüstü/depoyogunluk.xlsx"
raf_path   = "C:/Users/evrim/OneDrive/Masaüstü/RAFVE YERLEŞİM.xlsx"
rule1_path = "C:/Users/evrim/OneDrive/Masaüstü/rule1.xlsx"
rule2_path = "C:/Users/evrim/OneDrive/Masaüstü/rule2.xlsx"
konum_path = "C:/Users/evrim/OneDrive/Masaüstü/rafs.xlsx"  # Mesafe için kullanılacak dosya

# 2️⃣ Excel'den Sayfa Adlarını Bul: Dosyadaki tüm sayfa isimlerini al
kumas_xls = pd.ExcelFile(kumas_path)
raf_xls = pd.ExcelFile(raf_path)

# 3️⃣ Verileri Yükle: İlgili sayfaları oku (kumas1: Sayfa1, kumas2: Sayfa2)
kumas2 = kumas_xls.parse(kumas_xls.sheet_names[1])
kumas1 = kumas_xls.parse(kumas_xls.sheet_names[0])
raf_df = raf_xls.parse(raf_xls.sheet_names[2])
rule1_df = pd.read_excel(rule1_path)
rule2_df = pd.read_excel(rule2_path)

# 4️⃣ Sütunları Normalize Et: Tüm dataframe'lerdeki sütun adlarını sadeleştir ve standardize et
def normalize_columns(df):
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore").str.decode("ascii")
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.replace(r"_+", "", regex=True)
        .str.strip("_")
        .str.upper()
    )
    return df

kumas2 = normalize_columns(kumas2)
kumas1 = normalize_columns(kumas1)
raf_df = normalize_columns(raf_df)
rule1_df = normalize_columns(rule1_df)
rule2_df = normalize_columns(rule2_df)

# 5️⃣ Dönüş Hızı Hesaplama ve Sayfa1'e Ekleme: Her kumaş için giriş/çıkıştan dönüş hızını hesapla ve ekle
if "GIREN_KG" in kumas1.columns and "CIKAN_KG" in kumas1.columns:
    kumas1["DONUS_HIZI"] = kumas1["CIKAN_KG"] / kumas1["GIREN_KG"]
else:
    raise ValueError("GIREN_KG veya CIKAN_KG sütunu eksik!")

# 6️⃣ Sayfa2'de kalan miktarı/topu sıfırdan büyük olanları seç: Sadece depoda kalanı olan kumaşlar kalsın
if "KALAN_TOP_SAYISI_2" in kumas2.columns:
    kalan_top_col = "KALAN_TOP_SAYISI_2"
else:
    # Kalan top sütununu dinamik bul (isim değişse de çalışır)
    kalan_top_col = [c for c in kumas2.columns if "KALAN" in c and "TOP" in c][0]

kumas2 = kumas2[kumas2[kalan_top_col] > 0].copy()

# 7️⃣ Sayfa1'den ek bilgileri Sayfa2'ye ekle: (ABC_ANALIZI, BEKLEME vs., ve DÖNÜŞ_HIZI)
merge_cols = ["KUMAS_CINS_RENK"]
ek_bilgiler = ["ABC_ANALIZI", "BEKLEME_GUN_ORT", "KULLANIM_SEFERI", "TEDARIK_SEFERI", "DONUS_HIZI"]
ek_bilgiler = [c for c in ek_bilgiler if c in kumas1.columns]

kumas2 = pd.merge(
    kumas2,
    kumas1[merge_cols + ek_bilgiler],
    on="KUMAS_CINS_RENK",
    how="left"
)

# 8️⃣ Raf Konumlarını Oku ve Sözlüğe Aktar (MESAFE için GEREKLİ BLOK)
konum_df = pd.read_excel(konum_path, sheet_name="konum")
konum_df = normalize_columns(konum_df)

# Dosyada raf numarası sütunu "NO" ya da "RAF_NO" olabilir, kontrol et
raf_no_col = "RAF_NO" if "RAF_NO" in konum_df.columns else "NO"

# Her bir raf için (X, Y, Z) koordinatlarını sakla
raf_koordinat = {}
for _, row in konum_df.iterrows():
    raf_no = int(row[raf_no_col])
    x = float(row["X"])
    y = float(row["Y"])
    z = float(row["Z"])
    raf_koordinat[raf_no] = (x, y, z)

# 9️⃣ Başlangıç noktasını tanımla (ör: depo giriş/çıkış)
baslangic_nokta = (-22, 21, 1)  # Burayı kendi sistemine göre değiştirebilirsin

# 🔟 Her rafın başlangıç noktasına uzaklığını hesapla ve sözlükte sakla
raf_mesafe_baslangic = {}
for raf_no, coord in raf_koordinat.items():
    raf_mesafe_baslangic[raf_no] = np.linalg.norm(np.array(coord) - np.array(baslangic_nokta))

# 1️⃣1️⃣ İki raf arası mesafe fonksiyonu (ileride fitness fonksiyonunda da kullanılabilir)
def iki_raf_arasi_mesafe(raf1, raf2):
    return np.linalg.norm(np.array(raf_koordinat[raf1]) - np.array(raf_koordinat[raf2]))


# 8️⃣ Her topun kg'sini hesapla: KALAN_KG_2 / KALAN_TOP_SAYISI_2
if "KALAN_KG_2" not in kumas2.columns:
    raise ValueError("KALAN_KG_2 sütunu yok!")
kumas2["BIR_TOP_KG"] = kumas2["KALAN_KG_2"] / kumas2[kalan_top_col]

# 9️⃣ Her topu ayrı satır haline getir (her top bir satır olacak şekilde veri büyütülüyor)
expanded_rows = []
for idx, row in kumas2.iterrows():
    top_sayisi = int(row[kalan_top_col])
    for i in range(top_sayisi):
        new_row = row.copy()
        new_row["TOP_INDEX"] = i+1
        new_row["TOP_KG"] = row["BIR_TOP_KG"]
        expanded_rows.append(new_row)
kumas_top_df = pd.DataFrame(expanded_rows)

print("Hazırlanan top bazlı kumaş tablosu:")
print(kumas_top_df[["KUMAS_CINS_RENK", "TOP_INDEX", "TOP_KG"] + [c for c in ek_bilgiler if c != "KUMAS_CINS_RENK"]].head())

# 1️⃣ Raf bilgilerini sözlüklere çevir (raf no anahtar, değer olarak ilgili özellik)
raf_kapasite = raf_df.set_index("RAF_NO")["KAPASITE_KG"].to_dict()
raf_puan     = raf_df.set_index("RAF_NO")["PUAN"].to_dict()
raf_kat      = raf_df.set_index("RAF_NO")["KAT_BILGISI"].to_dict()
raf_alan     = raf_df.set_index("RAF_NO")["ALAN"].to_dict()
raf_erisim   = raf_df.set_index("RAF_NO")["ERISIM_KOLAYLIGI"].to_dict()

# 2️⃣ Kumaş bilgisini sözlüğe çevir (her kumaş_cins_renk için tekil özellik seti)
kumas_info = kumas_top_df.drop_duplicates(subset="KUMAS_CINS_RENK", keep="last").set_index("KUMAS_CINS_RENK").to_dict(orient="index")

# 3️⃣ Birliktelik kurallarını set olarak topla (hem ileri hem geri yönde, iki tablodan)
def get_birliktelik_kumesi(df):
    return set(tuple(row) for row in df[["PREMISES", "CONCLUSION"]].dropna().values)

birliktelik_kurallari_rule1 = get_birliktelik_kumesi(rule1_df)
birliktelik_kurallari_rule2 = get_birliktelik_kumesi(rule2_df)
rev_rule1 = {(b, a) for (a, b) in birliktelik_kurallari_rule1}
rev_rule2 = {(b, a) for (a, b) in birliktelik_kurallari_rule2}
tum_birliktelik_kurallari = (
    birliktelik_kurallari_rule1
    | birliktelik_kurallari_rule2
    | rev_rule1
    | rev_rule2
)


print("Raf kapasite örneği:", list(raf_kapasite.items())[:3])
print("Birliktelik kuralı örneği:", list(tum_birliktelik_kurallari)[:3])

import random
from collections import defaultdict

def akilli_birey_uret(
    kumaslar_df, raf_kapasite, raf_puan, raf_kat, raf_alan, raf_erisim, kumas_info
):
    """
    Her bir topu (satırı) akıllı şekilde uygun rafa yerleştirir.
    1️⃣ Öncelik: Aynı kumaş bir önceki rafta ise, mümkünse yine oraya yerleştir.
    2️⃣ Alternatif: Tüm uygun raflar için puan (raf_puan + doluluk + kat/alan/erişim/ABC)
    3️⃣ Hiçbiri olmazsa rastgele raf seç.
    """
    birey = []
    raf_doluluk = defaultdict(float)
    kumas_raf_map = defaultdict(set)

    for idx, row in kumaslar_df.iterrows():
        kg = row["TOP_KG"]
        kumas_key = row["KUMAS_CINS_RENK"]

        # 1️⃣ Öncelik: Daha önce aynı kumaş bir rafa yerleştiyse oraya yerleştir
        onceki_raf = next(
            (a["RAF_NO"] for a in birey if a["KUMAS_CINS_RENK"] == kumas_key), None
        )
        if onceki_raf and raf_kapasite[onceki_raf] - raf_doluluk[onceki_raf] >= kg:
            birey.append({
                "KUMAS_CINS_RENK": kumas_key,
                "TOP_INDEX": row["TOP_INDEX"],
                "RAF_NO": onceki_raf,
                "KG": kg
            })
            raf_doluluk[onceki_raf] += kg
            kumas_raf_map[kumas_key].add(onceki_raf)
            continue

        # 2️⃣ Alternatif: Uygun rafları skorla (raf puanı + doluluk oranı + alan/kat/easy access)
        raf_skors = []
        for raf_no, kapasite in raf_kapasite.items():
            bosluk = kapasite - raf_doluluk[raf_no]
            if bosluk < kg:
                continue

            skor = 0
            skor += raf_puan.get(raf_no, 0)
            kat = raf_kat.get(raf_no, "")
            alan = raf_alan.get(raf_no, "")
            erisim = raf_erisim.get(raf_no, "")
            abc = kumas_info.get(kumas_key, {}).get("ABC_ANALIZI", "")

            # ABC ve fiziksel alan kuralları
            if abc == "A" and kat == "ALT_KAT":
                skor += 2
            if abc == "C" and kat == "UST_KAT":
                skor += 2
            if erisim == "KOLAY":
                skor += 1
            if alan == "ON_ALAN":
                skor += 1

            oran = raf_doluluk[raf_no] / kapasite if kapasite > 0 else 0
            if 0.6 <= oran <= 0.9:
                skor += 1
            elif oran < 0.3:
                skor -= 1

            raf_skors.append((raf_no, skor))

        # 3️⃣ Seçim: En yüksek skorlu uygun raf ya da random seçim
        if raf_skors:
            raf_skors.sort(key=lambda x: -x[1])  # En yüksek skorlu
            sec_raf = raf_skors[0][0]
        else:
            # Uygun raf yok, rastgele at
            sec_raf = random.choice(list(raf_kapasite.keys()))

        birey.append({
            "KUMAS_CINS_RENK": kumas_key,
            "TOP_INDEX": row["TOP_INDEX"],
            "RAF_NO": sec_raf,
            "KG": kg
        })
        raf_doluluk[sec_raf] += kg
        kumas_raf_map[kumas_key].add(sec_raf)

    return birey

# Fonksiyonu test edelim
ornek_birey = akilli_birey_uret(
    kumas_top_df, raf_kapasite, raf_puan, raf_kat, raf_alan, raf_erisim, kumas_info
)
print("Birey uzunluğu (top sayısı):", len(ornek_birey))
print("İlk 3 atama örneği:", ornek_birey[:3])


from collections import defaultdict
import numpy as np

def fitness_hesapla(
    birey,
    raf_kapasite,
    raf_kat,
    raf_alan,
    raf_erisim,
    raf_puan,
    kumas_info,
    tum_birliktelik_kurallari,
    raf_mesafe_baslangic,     # ← EKLENDİ: Her rafa olan mesafeleri içeren sözlük
    mesafe_ceza_katsayi=0.02  # ← EKLENDİ: Ceza katsayısı (deneme/ayarlama ile artırıp azaltabilirsin)
):
    fitness = 0
    raf_agirlik = defaultdict(float)
    kumas_raf_haritasi = defaultdict(list)
    parcalanma = defaultdict(set)
    katlar     = defaultdict(set)
    alanlar    = defaultdict(set)
    toplam_mesafe = 0  # ← EKLENDİ

    for atama in birey:
        raf_no    = atama["RAF_NO"]
        kg        = atama["KG"]
        kumas_key = atama["KUMAS_CINS_RENK"]
        kumas     = kumas_info.get(kumas_key, {})

        # ---- 1️⃣ Temel: Raf puanı
        fitness += raf_puan.get(raf_no, 0) * (kg / 200)
        raf_agirlik[raf_no] += kg
        kumas_raf_haritasi[kumas_key].append(raf_no)
        parcalanma[kumas_key].add(raf_no)
        katlar[kumas_key].add(raf_kat.get(raf_no, ""))
        alanlar[kumas_key].add(raf_alan.get(raf_no, ""))

        # ---- 🟢 MESAFE CEZASI (her top için)
        mesafe = raf_mesafe_baslangic.get(raf_no, 0)
        toplam_mesafe += mesafe * kg  # İster kg, ister top sayısı ile çarpabilirsin

        # ---- 2️⃣ Soft Kısıtlar / Katkılar
        abc          = kumas.get("ABC_ANALIZI", "")
        bekleme      = kumas.get("BEKLEME_GUN_ORT", 0)
        kullanilan   = kumas.get("KULLANIM_SEFERI", 0)
        tedarik      = kumas.get("TEDARIK_SEFERI", 0)
        donus_hizi   = kumas.get("DONUS_HIZI", 0)
        giren_kg     = kumas.get("GIREN_KG", 0)
        cikan_kg     = kumas.get("CIKAN_KG", 0)
        top_sayisi   = kumas.get("KALAN_TOP_SAYISI_2", kumas.get("KALAN_TOP", 1))
        alan         = raf_alan.get(raf_no, "")
        kat          = raf_kat.get(raf_no, "")
        erisim       = raf_erisim.get(raf_no, "")

        # ... (diğer katkı ve ceza blokları olduğu gibi korunuyor)

        if abc == "A":
            if kat == "ALT_KAT":    fitness += 2
            if erisim == "KOLAY":   fitness += 2
            if alan == "ON_ALAN":   fitness += 2
            if kat == "UST_KAT":    fitness -= 1
            if erisim == "ZOR":     fitness -= 1
            if alan == "ARKA_ALAN": fitness -= 1
        elif abc == "C":
            if kat == "UST_KAT":    fitness += 2
            if erisim == "ZOR":     fitness += 2
            if alan == "ARKA_ALAN": fitness += 2
            if kat == "ALT_KAT":    fitness -= 1
            if erisim == "KOLAY":   fitness -= 1
            if alan == "ON_ALAN":   fitness -= 1
        elif abc == "B":
            if kat == "ORTA_KAT":   fitness += 1
            if erisim == "ORTA":    fitness += 1
            if alan == "ORTA_ALAN": fitness += 1

        # ... (kalan tüm bloklar olduğu gibi devam ediyor)

        if bekleme >= 900 and kat == "UST_KAT":
            fitness += 2
        if bekleme <= 200 and kat == "ALT_KAT":
            fitness += 2

        fark = kullanilan - tedarik
        if fark >= 3:
            if kat == "ALT_KAT":    fitness += 2
            elif kat == "UST_KAT":  fitness -= 2
        elif fark <= -3:
            if kat == "UST_KAT":    fitness += 2
            elif kat == "ALT_KAT":  fitness -= 2

        if donus_hizi >= 0.7:
            if kat == "ALT_KAT" and alan == "ON_ALAN" and erisim == "KOLAY":
                fitness += 3
            elif kat == "UST_KAT" or alan == "ARKA_ALAN":
                fitness -= 2
        elif donus_hizi < 0.3:
            if kat == "UST_KAT" or alan == "ARKA_ALAN":
                fitness += 2
            elif kat == "ALT_KAT" or alan == "ON_ALAN":
                fitness -= 2
        elif 0.3 <= donus_hizi < 0.7:
            if kat == "ORTA_KAT":
                fitness += 1

        if erisim == "KOLAY" and (abc == "A" or donus_hizi >= 0.7):
            fitness += 1
        if erisim == "ZOR" and (abc == "C" or donus_hizi < 0.3):
            fitness += 1

        if kg >= 400 and kat == "ALT_KAT":
            fitness += 2
        elif kg >= 300 and kat == "ORTA_KAT":
            fitness += 1

        if giren_kg >= 1000 or top_sayisi >= 5:
            if kat == "ALT_KAT":  fitness += 2
            if alan == "ON_ALAN": fitness += 2
        elif giren_kg >= 500 or top_sayisi >= 3:
            if kat == "ALT_KAT":  fitness += 1
            if alan == "ON_ALAN": fitness += 1

    # ---- 🔟 Parçalanma/kat/alan cezası
    for k in parcalanma:
        if len(parcalanma[k]) > 1:
            fitness -= (len(parcalanma[k]) - 1) * 5
        if len(katlar[k]) > 1:
            fitness -= (len(katlar[k]) - 1) * 3
        if len(alanlar[k]) > 1:
            fitness -= (len(alanlar[k]) - 1) * 3

    # ---- 1️⃣1️⃣ Raf kapasite ve dengesiz doluluk cezası
    for r, toplam_kg in raf_agirlik.items():
        kapasite = raf_kapasite.get(r, 1)
        if toplam_kg > kapasite:
            fitness -= (toplam_kg - kapasite) * 2
        oran = toplam_kg / kapasite
        if oran > 0.9 or oran < 0.1:
            fitness -= 5

    # ---- 1️⃣2️⃣ Birliktelik kuralları
    for (k1, k2) in tum_birliktelik_kurallari:
        if k1 in kumas_raf_haritasi and k2 in kumas_raf_haritasi:
            raf1 = set(kumas_raf_haritasi[k1])
            raf2 = set(kumas_raf_haritasi[k2])
            if raf1 & raf2:  # Aynı rafta buluşmuşlarsa
                fitness += 6
            elif katlar[k1] & katlar[k2] or alanlar[k1] & alanlar[k2]:
                fitness += 3
            else:
                fitness -= 5

    # ---- 🟢 MESAFE CEZASINI EN SON EKLE (fitness'tan çıkar)
    fitness -= mesafe_ceza_katsayi * toplam_mesafe

    return fitness


skor = fitness_hesapla(
    ornek_birey,                # <-- burada birey'in adı neyse onu kullan
    raf_kapasite,
    raf_kat,
    raf_alan,
    raf_erisim,
    raf_puan,
    kumas_info,
    tum_birliktelik_kurallari,
    raf_mesafe_baslangic,
    mesafe_ceza_katsayi=0.02
)

def populasyon_olustur(
    kumaslar_df, raf_kapasite, raf_puan, raf_kat, raf_alan, raf_erisim, kumas_info, birey_sayisi=50
):
    """
    Akıllı birey üretici fonksiyonunu çağırarak popülasyon oluşturur.
    """
    return [
        akilli_birey_uret(
            kumaslar_df, raf_kapasite, raf_puan, raf_kat, raf_alan, raf_erisim, kumas_info
        )
        for _ in range(birey_sayisi)
    ]

def secilim(populasyon, fitnessler, elit_sayi=10):
    """
    Elit seçim: Popülasyondan fitness'i en yüksek olan ilk N bireyi seçer.
    """
    sirali = sorted(zip(populasyon, fitnessler), key=lambda x: x[1], reverse=True)
    elitler = [kopya[0] for kopya in sirali[:elit_sayi]]
    return elitler

def turnuva_secimi(populasyon, fitnessler, turnuva_boyutu=3):
    """
    Turnuva seçimi: Rastgele N adaydan en iyi fitness'e sahip olanı döndürür.
    """
    aday_list = list(zip(populasyon, fitnessler))
    mevcut_boyut = min(turnuva_boyutu, len(aday_list))
    adaylar = random.sample(aday_list, mevcut_boyut)
    adaylar.sort(key=lambda x: x[1], reverse=True)
    return adaylar[0][0]  # fitness'i en yüksek olanı döndür

import copy
from collections import defaultdict

def caprazla(baba, anne, raf_kapasite):
    """
    Çaprazlama işlemi: Baba ve anneden karışık olarak çocuk birey üretir.
    Her kumaş cins-renk için, random ebeveynden atamayı alır,
    raf kapasitesini aşmaz.
    """
    cocuk = []
    raf_doluluk = defaultdict(float)
    tum_kumaslar = set([a["KUMAS_CINS_RENK"] for a in baba] + [a["KUMAS_CINS_RENK"] for a in anne])
    for kumas in tum_kumaslar:
        kaynak = random.choice([baba, anne])
        secilen = [atama for atama in kaynak if atama["KUMAS_CINS_RENK"] == kumas]
        for atama in secilen:
            raf = atama["RAF_NO"]
            kg = atama["KG"]
            if raf_doluluk[raf] + kg <= raf_kapasite[raf]:
                cocuk.append(copy.deepcopy(atama))
                raf_doluluk[raf] += kg
    return cocuk

def mutasyon(birey, raf_kapasite, oran=0.1):
    """
    Mutasyon işlemi: Belirli olasılıkla rastgele bir topu farklı bir uygun rafa taşır.
    """
    birey = copy.deepcopy(birey)
    if len(birey) == 0:
        return birey
    if random.random() < oran:
        idx = random.randint(0, len(birey) - 1)
        atama = birey[idx]
        kg = atama["KG"]
        mevcut_raf = atama["RAF_NO"]
        uygun_raflar = [r for r, kapasite in raf_kapasite.items() if kapasite >= kg and r != mevcut_raf]
        if uygun_raflar:
            yeni_raf = random.choice(uygun_raflar)
            birey[idx]["RAF_NO"] = yeni_raf
    return birey

def yeni_jenerasyon(populasyon, fitnessler, raf_kapasite, elit_sayi=10, mutasyon_orani=0.1, birey_sayisi=50):
    """
    Yeni jenerasyon üretir:
    - Elitler korunur (elit_sayi kadar)
    - Geri kalanlar çaprazlama+mutasyon ile doldurulur
    """
    yeni_pop = secilim(populasyon, fitnessler, elit_sayi)
    while len(yeni_pop) < birey_sayisi:
        ebeveyn1 = turnuva_secimi(populasyon, fitnessler)
        ebeveyn2 = turnuva_secimi(populasyon, fitnessler)
        cocuk = caprazla(ebeveyn1, ebeveyn2, raf_kapasite)
        cocuk = mutasyon(cocuk, raf_kapasite, oran=mutasyon_orani)
        yeni_pop.append(cocuk)
    return yeni_pop

# --- GA PARAMETRELERİ ---
populasyon_boyutu = 50
jenerasyon_sayisi = 100
elit_sayi = 10
mutasyon_orani = 0.1

# --- Popülasyon Oluştur ---
populasyon = populasyon_olustur(
    kumas_top_df, raf_kapasite, raf_puan, raf_kat, raf_alan, raf_erisim, kumas_info,
    birey_sayisi=populasyon_boyutu
)

en_iyi_birey = None
en_iyi_skor = float("-inf")
temel_mutasyon_orani = 0.1
maks_carpan          = 3.0
stagnasyon_limiti    = 7
stagnasyon_log       = []
degisme_sayaci       = 0
onceki_en_iyi        = float("-inf")
mutasyon_orani       = temel_mutasyon_orani

for jenerasyon in range(jenerasyon_sayisi):
    fitnessler = [
        fitness_hesapla(
            birey, raf_kapasite, raf_kat, raf_alan, raf_erisim,
            raf_puan, kumas_info, tum_birliktelik_kurallari,
            raf_mesafe_baslangic,           # ← Mesafe cezası için eklendi
            mesafe_ceza_katsayi=0.02        # ← Cezayı artırıp azaltabilirsin
        )
        for birey in populasyon
    ]
    max_fit = max(fitnessler)
    en_idx = fitnessler.index(max_fit)

    if max_fit <= onceki_en_iyi + 1e-6:
        degisme_sayaci += 1
    else:
        degisme_sayaci = 0
        onceki_en_iyi = max_fit

    if degisme_sayaci > stagnasyon_limiti:
        faktor = min(maks_carpan, 1 + (degisme_sayaci - stagnasyon_limiti) * 0.2)
        mutasyon_orani = min(0.5, temel_mutasyon_orani * faktor)
    else:
        mutasyon_orani = temel_mutasyon_orani

    stagnasyon_log.append({
        "Jenerasyon": jenerasyon+1,
        "Stagnasyon_Sayisi": degisme_sayaci,
        "Mutasyon_Orani": mutasyon_orani
    })

    if max_fit > en_iyi_skor:
        en_iyi_birey = populasyon[en_idx]
        en_iyi_skor = max_fit

    print(f"Jenerasyon {jenerasyon+1}: En iyi fitness: {max_fit:.2f} (Mutasyon {mutasyon_orani:.2f})")

    populasyon = yeni_jenerasyon(
        populasyon, fitnessler, raf_kapasite,
        elit_sayi=elit_sayi, mutasyon_orani=mutasyon_orani,
        birey_sayisi=populasyon_boyutu
    )

print("\nEn iyi birey fitness skoru:", en_iyi_skor)
yerlesim_df = pd.DataFrame(en_iyi_birey)

# GA bittikten hemen sonra! (en_iyi_birey güncellenmiş olacak)

# --- Yerleşmeyenleri GA sonrası yeniden yerleştir ---
yerlesen_kumastoplar = set((a["KUMAS_CINS_RENK"], a["TOP_INDEX"]) for a in en_iyi_birey)
tum_kumastoplar = set((row["KUMAS_CINS_RENK"], row["TOP_INDEX"]) for _, row in kumas_top_df.iterrows())
yerlesmeyenler = tum_kumastoplar - yerlesen_kumastoplar

if yerlesmeyenler:
    print("\nGA sonrası yerleşmeyen toplar tekrar yerleştiriliyor...")
    for (k, t) in yerlesmeyenler:
        top_row = kumas_top_df[
            (kumas_top_df["KUMAS_CINS_RENK"] == k) & (kumas_top_df["TOP_INDEX"] == t)
        ].iloc[0]
        kg = top_row["TOP_KG"]
        # En boş uygun rafı bul (veya ilk bulduğunu kullan)
        uygun_raf = None
        for raf_no, kapasite in raf_kapasite.items():
            dolu = sum(a["KG"] for a in en_iyi_birey if a["RAF_NO"] == raf_no)
            if kapasite - dolu >= kg:
                uygun_raf = raf_no
                break
        if uygun_raf is not None:
            yeni_atama = {
                "KUMAS_CINS_RENK": k,
                "TOP_INDEX": t,
                "RAF_NO": uygun_raf,
                "KG": kg
            }
            en_iyi_birey.append(yeni_atama)
            print(f"- {k} top {t} → raf {uygun_raf}")
        else:
            print(f"UYARI! {k} top {t} için uygun raf YOK (kapasite dolmuş)!")
else:
    print("GA sonrası tüm kumaşlar yerleşti (boşta top yok)")

# 5️⃣ Kumaş skor detayları (her topun ayrı skorunu hesapla, isteğe bağlı):
kumas_skorlar = []
for atama in en_iyi_birey:
    tek_birey = [atama]
    skor = fitness_hesapla(
        tek_birey, raf_kapasite, raf_kat, raf_alan, raf_erisim,
        raf_puan, kumas_info, tum_birliktelik_kurallari,
        raf_mesafe_baslangic,      # <- GA'da neyle çağırdıysan buraya da ekle
        mesafe_ceza_katsayi=0.02
    )
    kumas_skorlar.append({
        "KUMAS_CINS_RENK": atama["KUMAS_CINS_RENK"],
        "TOP_INDEX": atama["TOP_INDEX"],
        "RAF_NO": atama["RAF_NO"],
        "KG": atama["KG"],
        "Fitness_Skoru": skor
    })
kumas_skor_detay_df = pd.DataFrame(kumas_skorlar)

# (Excel'e eklemek için:)
# kumas_skor_detay_df.to_excel(writer, sheet_name="Top Bazlı Skorlar", index=False)

print("\nÖrnek Top Bazlı Fitness Skorları:")
print(kumas_skor_detay_df.head())



# GA sonrası en_iyi_birey ile
yerlesen_kumastoplar = set((a["KUMAS_CINS_RENK"], a["TOP_INDEX"]) for a in en_iyi_birey)
tum_kumastoplar = set((row["KUMAS_CINS_RENK"], row["TOP_INDEX"]) for _, row in kumas_top_df.iterrows())
yerlesmeyenler = tum_kumastoplar - yerlesen_kumastoplar

if yerlesmeyenler:
    print(f"\nYerleşemeyen kumaş/top kombinasyonları ({len(yerlesmeyenler)} adet):")
    for k, t in yerlesmeyenler:
        print(f"- Kumaş: {k}, Top No: {t}")
else:
    print("Tüm kumaşlar başarıyla yerleştirildi!")



# 1️⃣ En iyi bireyi DataFrame'e çevir
yerlesim_df = pd.DataFrame(en_iyi_birey)

# 2️⃣ Raf doluluk özeti
raf_doluluk = yerlesim_df.groupby("RAF_NO")["KG"].sum().reset_index()
raf_doluluk.columns = ["RAF_NO", "DOLULUK_KG"]
raf_bilgisi = pd.merge(raf_df.copy(), raf_doluluk, on="RAF_NO", how="left")
raf_bilgisi["DOLULUK_KG"] = raf_bilgisi["DOLULUK_KG"].fillna(0)
raf_bilgisi["BOS_KAPASITE"] = raf_bilgisi["KAPASITE_KG"] - raf_bilgisi["DOLULUK_KG"]

# 3️⃣ Yerleşim özeti (her kumaşın hangi rafa, kaç top ve toplam kaç kg gittiği)
yerlesim_ozet = (
    yerlesim_df
    .groupby(['RAF_NO', 'KUMAS_CINS_RENK'])
    .agg(
        YERLESEN_TOP=('KG', 'count'),
        YERLESEN_KG=('KG', 'sum')
    )
    .reset_index()
    .sort_values(['RAF_NO', 'KUMAS_CINS_RENK'])
)

# 4️⃣ Boş veya çok az dolu raflar (isteğe bağlı)
bos_raf_df = raf_bilgisi[raf_bilgisi["DOLULUK_KG"] < 1]

# 5️⃣ Kumaş skor detayları (her kumaşın hangi raflarda olduğunu görmek istersen)
kumas_skor_df = (
    yerlesim_df.groupby("KUMAS_CINS_RENK")
    .agg(
        YERLESEN_TOP=('KG', 'count'),
        TOPLAM_KG=('KG', 'sum'),
        RAFLAR=('RAF_NO', lambda x: ','.join(str(r) for r in sorted(set(x))))
    )
    .reset_index()
)

# 6️⃣ Verim özeti (her rafın doluluk oranı, boş kapasitesi vs.)
verim_ozeti_df = raf_bilgisi[["RAF_NO", "KAPASITE_KG", "DOLULUK_KG", "BOS_KAPASITE"]].copy()
verim_ozeti_df["DOLULUK_ORAN"] = verim_ozeti_df["DOLULUK_KG"] / verim_ozeti_df["KAPASITE_KG"]

import time

isim = f"C:/Users/HP/Desktop/kurallar/raf_yerlesim_sonuclari_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
with pd.ExcelWriter(isim, engine="openpyxl", mode="w") as writer:
    raf_bilgisi.to_excel(writer, sheet_name="Raf Doluluk Özeti", index=False)
    yerlesim_ozet.to_excel(writer, sheet_name="Kumaş Yerleşimi", index=False)
    bos_raf_df.to_excel(writer, sheet_name="Boş Raflar", index=False)
    kumas_skor_df.to_excel(writer, sheet_name="Kumaş Skor Detay", index=False)
    verim_ozeti_df.to_excel(writer, sheet_name="Verim Özeti", index=False)
    yerlesim_df.to_excel(writer, sheet_name="Yerleşim Ham Veri", index=False)
    kumas_skor_detay_df.to_excel(writer, sheet_name="Top Bazlı Skorlar", index=False)


print(f"Excel çıktısı başarıyla oluşturuldu: {isim}")