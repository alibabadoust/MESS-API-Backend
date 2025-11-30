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
    - Tahmini süre: Önündeki kişi sayısı * 5 dakika olarak hesaplanır.
    """

    # 1. پیدا کردن بیمار
    hasta = db.query(models.Hasta).filter(models.Hasta.tckimlik == bilet_data.tckimlik).first()
    if not hasta:
        raise HTTPException(status_code=404, detail="Bu TC Kimlik numarasına sahip hasta bulunamadı.")
    
    # 2. محاسبه سن
    bugun = datetime.date.today()
    dogum = hasta.dogumtarihi
    yas = bugun.year - dogum.year - ((bugun.month, bugun.day) < (dogum.month, dogum.day))
    is_oncelikli = (yas >= 65) 

    # 3. دریافت کدها
    # ... (این بخش کدها که دکتر و پلی‌کلینیک را می‌گیرد بدون تغییر است - کپی کنید) ...
    # (برای خلاصه کردن اینجا ننوشتم، اما کد قبلی خود را اینجا بگذارید)
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
            raise HTTPException(status_code=404, detail="Doktor bulunamadı.")
    except Exception:
        raise HTTPException(status_code=500, detail="Veritabanı hatası.")


    # 4. محاسبه شماره نوبت
    yeni_sira_numarasi = 0
    if is_oncelikli:
        son_sira = db.query(func.max(models.BiletAktif.siranumarasi)).filter(
            models.BiletAktif.poliklinikid == doktor_ve_kodlar.poliklinikid,
            func.cast(models.BiletAktif.olusturmatarihi, Date) == datetime.date.today(),
            models.BiletAktif.siranumarasi < 100 
        ).scalar()
        yeni_sira_numarasi = (son_sira or 0) + 1
    else:
        son_sira = db.query(func.max(models.BiletAktif.siranumarasi)).filter(
            models.BiletAktif.poliklinikid == doktor_ve_kodlar.poliklinikid,
            func.cast(models.BiletAktif.olusturmatarihi, Date) == datetime.date.today(),
            models.BiletAktif.siranumarasi >= 100 
        ).scalar()
        yeni_sira_numarasi = (son_sira or 100) + 1

    # 5. ساخت کد 11 رقمی
    sira_kodu_3_hane = f"{yeni_sira_numarasi:03d}" 
    yeni_baglanti_kodu = (
        f"{doktor_ve_kodlar.sehirkodu}{doktor_ve_kodlar.hastanekodu}"
        f"{doktor_ve_kodlar.poliklinikkodu}{doktor_ve_kodlar.odakodu}{sira_kodu_3_hane}"
    )
    
    # ==============================================================================
    # --- (اصلاح شده) 6. محاسبه دقیق زمان تخمینی ---
    # ==============================================================================
    
    # تعداد کل افرادی که همین الان در صف "Bekliyor" هستند را می‌شماریم
    kisi_sayisi_sorgusu = db.query(func.count(models.BiletAktif.biletid)).filter(
        models.BiletAktif.poliklinikid == doktor_ve_kodlar.poliklinikid,
        models.BiletAktif.durum == "Bekliyor"
    )
    
    if is_oncelikli:
        # اگر من پیرمرد هستم: فقط کسانی که شماره‌شان از من کمتر است (پیرمردهای قبلی) جلوی من هستند
        # جوان‌ها (۱۰۱+) پشت سر من می‌مانند
        kisi_sayisi_sorgusu = kisi_sayisi_sorgusu.filter(
            models.BiletAktif.siranumarasi < yeni_sira_numarasi
        )
    else:
        # اگر من جوان هستم: همه پیرمردها (۱-۹۹) + جوان‌های قبلی (کمتر از ۱۰۱) جلوی من هستند
        # (پس کل کسانی که الان منتظرند، جلوی من هستند)
        pass 

    bekleyen_kisi_sayisi = kisi_sayisi_sorgusu.scalar() or 0
    
    # زمان هر ویزیت = ۵ دقیقه
    dakika = bekleyen_kisi_sayisi * 5
    
    if dakika == 0:
        tahmini_sure = "Hemen (Sıra Sizde)"
    else:
        tahmini_sure = f"Yaklaşık {dakika} Dakika"
    # ==============================================================================

    # 7. ذخیره در دیتابیس
    yeni_bilet = models.BiletAktif(
        baglantikodu=yeni_baglanti_kodu,
        hastaid=hasta.hastaid, 
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
        raise HTTPException(status_code=500, detail="Bilet kaydedilirken hata oluştu.")
    
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
        models.BiletAktif.hastaid,
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
        hastaid=bilet_ana_bilgi.hastaid,
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
# --- (REWRITTEN AND FIXED) API 3: مدیریت تاخیر یا لغو نوبت ---
# routers/biletler_router.py

# ... (کدهای قبلی ثابت هستند) ...

@router.post("/ertele/", response_model=schemas.BiletBase)
def ertele_veya_iptal_et(ertele_data: schemas.BiletErteleme, db: Session = Depends(get_db)):
    
    # 1. پیدا کردن بلیت فعلی
    eski_bilet = db.query(models.BiletAktif).filter(
        models.BiletAktif.baglantikodu == ertele_data.baglantikodu,
        models.BiletAktif.durum == 'Bekliyor'
    ).first()
    
    if not eski_bilet:
        raise HTTPException(status_code=404, detail="Aktif bilet bulunamadı veya zaten işlem yapılmış.")

    # --- سناریوی ۱: لغو کامل ---
    if ertele_data.aksiyon == 'iptal':
        eski_bilet.durum = "IptalEdildi"
        db.commit()
        return eski_bilet

    # --- سناریوی ۲: تاخیر ---
    elif ertele_data.aksiyon in ['15_dk', '30_dk', '45_dk']:
        try:
            # الف) کپی اطلاعات
            eski_id = eski_bilet.biletid
            eski_hasta_id = eski_bilet.hastaid
            eski_doktor_id = eski_bilet.doktorid
            eski_poliklinik_id = eski_bilet.poliklinikid
            
            # ب) ایجاد آرشیو
            bilet_arsiv = models.BiletArsiv(
                biletid=eski_bilet.biletid,
                baglantikodu=eski_bilet.baglantikodu,
                hastaid=eski_bilet.hastaid,
                doktorid=eski_bilet.doktorid,
                poliklinikid=eski_bilet.poliklinikid,
                siranumarasi=eski_bilet.siranumarasi,
                durum="Ertelendi",
                olusturmatarihi=eski_bilet.olusturmatarihi,
                kapanistarihi=datetime.datetime.now(),
                eskibiletid=eski_bilet.eskibiletid,
                tahminibeklemesuresi=eski_bilet.tahminibeklemesuresi
            )
            db.add(bilet_arsiv)
            
            # ==================================================================
            # ج) *** حذف مستقیم و اجباری فرم ***
            # (این خط هر فرمی که biletid آن برابر با بلیت فعلی باشد را بدون سوال پاک می‌کند)
            db.query(models.SoruCevapFormu).filter(
                models.SoruCevapFormu.biletid == eski_id
            ).delete()
            
            db.flush() # اعمال آنی حذف فرم
            # ==================================================================
            
            # د) حذف بلیت از جدول فعال
            db.delete(eski_bilet) 
            db.flush() # اعمال آنی حذف بلیت

            # ه) محاسبه شماره نوبت جدید
            hasta = db.query(models.Hasta).filter(models.Hasta.hastaid == eski_hasta_id).first()
            bugun = datetime.date.today()
            dogum = hasta.dogumtarihi
            yas = bugun.year - dogum.year - ((bugun.month, bugun.day) < (dogum.month, dogum.day))
            is_oncelikli = (yas >= 65)

            yeni_sira_numarasi = 0
            if is_oncelikli:
                son_sira = db.query(func.max(models.BiletAktif.siranumarasi)).filter(
                    models.BiletAktif.poliklinikid == eski_poliklinik_id,
                    func.cast(models.BiletAktif.olusturmatarihi, Date) == bugun,
                    models.BiletAktif.siranumarasi < 100
                ).scalar()
                yeni_sira_numarasi = (son_sira or 0) + 1
            else:
                son_sira = db.query(func.max(models.BiletAktif.siranumarasi)).filter(
                    models.BiletAktif.poliklinikid == eski_poliklinik_id,
                    func.cast(models.BiletAktif.olusturmatarihi, Date) == bugun,
                    models.BiletAktif.siranumarasi >= 100
                ).scalar()
                yeni_sira_numarasi = (son_sira or 100) + 1

            sira_kodu_3_hane = f"{yeni_sira_numarasi:03d}"
            
            # و) ساخت کد جدید (با رفع ابهام JOIN)
            doktor_info = db.query(
                 models.Doktor.odakodu, models.Poliklinik.poliklinikkodu, 
                 models.Hastane.hastanekodu, models.Sehir.sehirkodu
            ).select_from(models.Doktor)\
             .join(models.Poliklinik, models.Doktor.poliklinikid == models.Poliklinik.poliklinikid)\
             .join(models.Hastane, models.Poliklinik.hastaneid == models.Hastane.hastaneid)\
             .join(models.Sehir, models.Hastane.sehirid == models.Sehir.sehirid)\
             .filter(models.Doktor.doktorid == eski_doktor_id).first()

            if not doktor_info:
                 raise HTTPException(status_code=500, detail="Doktor bilgileri bulunamadı.")

            yeni_baglanti_kodu = (
                f"{doktor_info.sehirkodu}"
                f"{doktor_info.hastanekodu}"
                f"{doktor_info.poliklinikkodu}"
                f"{doktor_info.odakodu}"
                f"{sira_kodu_3_hane}"
            )
            
            # ز) محاسبه زمان و ثبت
            eklenen_dakika = int(ertele_data.aksiyon.split('_')[0])
            tahmini_sure = f"Ertelendi (+{eklenen_dakika} dk). Yaklaşık {yeni_sira_numarasi * 5} Dakika"
            if is_oncelikli:
                 tahmini_sure = f"Öncelikli - Ertelendi (+{eklenen_dakika} dk). Yaklaşık 5 Dakika"

            yeni_bilet = models.BiletAktif(
                baglantikodu=yeni_baglanti_kodu,
                hastaid=eski_hasta_id,
                doktorid=eski_doktor_id,
                poliklinikid=eski_poliklinik_id,
                siranumarasi=yeni_sira_numarasi,
                durum="Bekliyor",
                olusturmatarihi=datetime.datetime.now(),
                eskibiletid=eski_id, 
                tahminibeklemesuresi=tahmini_sure
            )
            
            db.add(yeni_bilet)
            db.commit()
            db.refresh(yeni_bilet)
            
            return yeni_bilet

        except Exception as e:
            db.rollback()
            print(f"ERTELEME HATASI: {e}")
            raise HTTPException(status_code=500, detail=f"İşlem sırasında bir hata oluştu: {e}")

    else:
        raise HTTPException(status_code=400, detail="Geçersiz işlem türü.")