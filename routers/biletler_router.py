# routers/biletler_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, Date, and_
import models, schemas
from db import get_db
import datetime

router = APIRouter(
    prefix="/api/biletler",
    tags=["Bilet İşlemleri"]
)

# =================================================================
# API 1: ایجاد بلیت هوشمند (Sıra Alma)
# =================================================================
@router.post("/", response_model=schemas.BiletBase)
def create_bilet(bilet_data: schemas.BiletCreate, db: Session = Depends(get_db)):
    """
    Yeni bir sıra bileti oluşturur.
    - Hasta TC Kimlik numarası ile bulunur.
    - Aynı doktordan "Bekliyor" durumunda aktif bileti varsa izin vermez.
    - Geçmiş randevular (Tamamlandi/Gelmeyen) yeni randevuya engel olmaz.
    - 65 yaş üstü önceliği uygulanır (Sıra No 1-99 arası).
    """

    # --- 1. پیدا کردن بیمار با TC Kimlik ---
    hasta = db.query(models.Hasta).filter(models.Hasta.tckimlik == bilet_data.tckimlik).first()
    
    if not hasta:
        raise HTTPException(status_code=404, detail="Bu TC Kimlik numarasına sahip hasta bulunamadı. Lütfen önce kayıt olun.")
    
    # --- 2. بررسی نوبت تکراری فعال ---
    # فقط چک می‌کنیم آیا نوبتی دارد که هنوز "منتظر" (Bekliyor) است؟
    nوبت_تکراری = db.query(models.BiletAktif).filter(
        models.BiletAktif.hastaid == hasta.hastaid,
        models.BiletAktif.doktorid == bilet_data.doktorid,
        models.BiletAktif.durum == 'Bekliyor' # نوبت‌های تمام شده مهم نیستند
    ).first()

    if nوبت_تکراری:
        raise HTTPException(
            status_code=400, 
            detail=f"Siz zaten bu doktordan sıra aldınız. Mevcut Bilet Kodunuz: {nوبت_تکراری.baglantikodu}"
        )

    # --- 3. محاسبه سن برای اولویت‌بندی ---
    bugun = datetime.date.today()
    dogum = hasta.dogumtarihi
    yas = bugun.year - dogum.year - ((bugun.month, bugun.day) < (dogum.month, dogum.day))
    is_oncelikli = (yas >= 65) 

    # --- 4. دریافت کدهای دکتر, پلی‌کلینیک, بیمارستان و شهر ---
    try:
        doktor_ve_kodlar = db.query(
            models.Doktor.doktorid, models.Doktor.poliklinikid, models.Doktor.odakodu,
            models.Poliklinik.poliklinikkodu, models.Hastane.hastanekodu, models.Sehir.sehirkodu
        ).join(
            models.Poliklinik, models.Doktor.poliklinikid == models.Poliklinik.poliklinikid
        ).join(
            models.Hastane, models.Poliklinik.hastaneid == models.Hastane.hastaneid
        ).join(
            models.Sehir, models.Hastane.sehirid == models.Sehir.sehirid
        ).filter(
            models.Doktor.doktorid == bilet_data.doktorid
        ).first()
        
        if not doktor_ve_kodlar:
            raise HTTPException(status_code=404, detail="Doktor veya ilişkili kodlar bulunamadı.")
            
    except Exception as e:
        print(f"Kod hatasi: {e}")
        raise HTTPException(status_code=500, detail="Kodları alırken veritabanı hatası oluştu.")

    # --- 5. محاسبه شماره نوبت هوشمند (بر اساس سن) ---
    yeni_sira_numarasi = 0
    
    if is_oncelikli:
        # === اولویت دار (65+) ===
        # آخرین شماره در بازه 1 تا 99 را پیدا کن
        son_sira = db.query(func.max(models.BiletAktif.siranumarasi)).filter(
            models.BiletAktif.poliklinikid == doktor_ve_kodlar.poliklinikid,
            func.cast(models.BiletAktif.olusturmatarihi, Date) == datetime.date.today(),
            models.BiletAktif.siranumarasi < 100 # زیر 100
        ).scalar()
        
        yeni_sira_numarasi = (son_sira or 0) + 1
    else:
        # === عادی (زیر 65) ===
        # آخرین شماره در بازه 100 به بالا را پیدا کن
        son_sira = db.query(func.max(models.BiletAktif.siranumarasi)).filter(
            models.BiletAktif.poliklinikid == doktor_ve_kodlar.poliklinikid,
            func.cast(models.BiletAktif.olusturmatarihi, Date) == datetime.date.today(),
            models.BiletAktif.siranumarasi >= 100 # بالای 100
        ).scalar()
        
        yeni_sira_numarasi = (son_sira or 100) + 1

    # --- 6. ساخت کد 11 رقمی ---
    sira_kodu_3_hane = f"{yeni_sira_numarasi:03d}" 
    
    yeni_baglanti_kodu = (
        f"{doktor_ve_kodlar.sehirkodu}"
        f"{doktor_ve_kodlar.hastanekodu}"
        f"{doktor_ve_kodlar.poliklinikkodu}"
        f"{doktor_ve_kodlar.odakodu}"
        f"{sira_kodu_3_hane}"
    )
    
    # محاسبه زمان تخمینی
    tahmini_sure = f"Yaklaşık {yeni_sira_numarasi * 5} Dakika" 
    if is_oncelikli:
         tahmini_sure = "Öncelikli Sıra (Yaklaşık 5 Dakika)"

    # --- 7. ذخیره در دیتابیس ---
    yeni_bilet = models.BiletAktif(
        baglantikodu=yeni_baglanti_kodu,
        hastaid=hasta.hastaid, # استفاده از ID بیماری که پیدا کردیم
        doktorid=bilet_data.doktorid,
        poliklinikid=doktor_ve_kodlar.poliklinikid,
        siranumarasi=yeni_sira_numarasi,
        durum="Bekliyor",
        olusturmatarihi=datetime.datetime.now(), 
        eskibiletid=None,
        tahminibeklemesuresi=tahmini_sure 
    )
    
    try:
        db.add(yeni_bilet)
        db.commit()
        db.refresh(yeni_bilet) 
    except Exception as e:
        db.rollback()
        print(f"Kayit hatasi: {e}")
        # اگر خطای Unique رخ داد (احتمال کم)، یک خطای عمومی برگردان
        raise HTTPException(status_code=400, detail="Bir hata oluştu. Lütfen tekrar deneyin.")
    
    return yeni_bilet


# =================================================================
# API 2: ردیابی بلیت (Sıra Takibi)
# =================================================================
@router.post("/takip/", response_model=schemas.SiraTakipDetay)
def get_bilet_detay(giris_data: schemas.BiletTakipGiris, db: Session = Depends(get_db)):
    """
    Bilet Kodu VE Telefon Numarası ile sıra takip detaylarını getirir.
    """
    
    # 1. دریافت اطلاعات بلیت و بیمار
    bilet_ana_bilgi = db.query(
        models.BiletAktif.biletid,
        models.BiletAktif.siranumarasi.label("sizin_numaraniz"),
        models.BiletAktif.durum,
        models.BiletAktif.olusturmatarihi.label("giris_zamani"),
        models.BiletAktif.tahminibeklemesuresi.label("tahmini_bekleme_suresi"),
        models.Poliklinik.poliklinikadi.label("bolum_adi"),
        models.Doktor.adsoyad.label("doktor_adi"),
        models.BiletAktif.poliklinikid,
        models.Hasta.telefon 
    ).join(
        models.Doktor, models.BiletAktif.doktorid == models.Doktor.doktorid
    ).join(
        models.Poliklinik, models.BiletAktif.poliklinikid == models.Poliklinik.poliklinikid
    ).join(
        models.Hasta, models.BiletAktif.hastaid == models.Hasta.hastaid 
    ).filter(
        models.BiletAktif.baglantikodu == giris_data.baglantikodu
    ).first()

    if not bilet_ana_bilgi:
        raise HTTPException(status_code=404, detail="Bu koda ait aktif bir bilet bulunamadı.")
    
    # 2. چک کردن شماره موبایل
    if giris_data.telefon not in bilet_ana_bilgi.telefon:
            raise HTTPException(status_code=403, detail="Telefon numarası bilet ile eşleşmiyor.") 
    
    # 3. محاسبه "نوبت فعلی" (کسی که الان داخل اتاق است)
    mevcut_sira_raw = db.query(func.min(models.BiletAktif.siranumarasi)).filter(
        models.BiletAktif.poliklinikid == bilet_ana_bilgi.poliklinikid,
        models.BiletAktif.durum == "Cagirildi",
        func.cast(models.BiletAktif.olusturmatarihi, Date) == datetime.date.today()
    ).scalar()
    
    mevcut_sira = mevcut_sira_raw or 0 
    
    # 4. محاسبه دقیق "نفرات باقی‌مانده"
    # (شمارش تعداد افرادی که در صف "Bekliyor" هستند و نوبتشان از شما جلوتر است)
    kalan_kisi_sayisi = db.query(func.count(models.BiletAktif.biletid)).filter(
        models.BiletAktif.poliklinikid == bilet_ana_bilgi.poliklinikid,
        models.BiletAktif.durum == "Bekliyor",
        
        # شرط مهم برای سیستم اولویت‌دار:
        # اگر شماره من 101 است، تمام شماره‌های 1 تا 99 (پیرمردها) + 100 (جوان قبلی) جلوترند.
        models.BiletAktif.siranumarasi < bilet_ana_bilgi.sizin_numaraniz
    ).scalar()

    response_data = schemas.SiraTakipDetay(
        biletid=bilet_ana_bilgi.biletid,
        sizin_numaraniz=bilet_ana_bilgi.sizin_numaraniz,
        durum=bilet_ana_bilgi.durum,
        giris_zamani=bilet_ana_bilgi.giris_zamani,
        tahmini_bekleme_suresi=bilet_ana_bilgi.tahmini_bekleme_suresi,
        bolum_adi=bilet_ana_bilgi.bolum_adi,
        doktor_adi=bilet_ana_bilgi.doktor_adi,
        mevcut_sira=mevcut_sira,
        kalan_hasta=kalan_kisi_sayisi 
    )
    
    return response_data