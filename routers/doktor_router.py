# routers/doktor_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, Date
import models, schemas
from db import get_db
import datetime

router = APIRouter(
    prefix="/api/doktor",
    tags=["Doktor İşlemleri"]
)

# --- API: فراخوانی بیمار با کد ۱۱ رقمی ---
@router.post("/cagir/{baglanti_kodu}", response_model=schemas.DoktorEkraniDetay)
def hasta_cagir(baglanti_kodu: str, db: Session = Depends(get_db)):
    """
    1. 11 haneli bilet kodunu alır.
    2. Bileti bulur ve durumunu 'Cagirildi' yapar.
    3. Hasta bilgilerini ve AI özetini döndürür.
    """
    
    # ۱. پیدا کردن بلیت
    bilet = db.query(models.BiletAktif).filter(models.BiletAktif.baglantikodu == baglanti_kodu).first()
    
    if not bilet:
        raise HTTPException(status_code=404, detail="Bu koda ait bilet bulunamadı.")
    
    # ۲. تغییر وضعیت به 'Cagirildi'
    bilet.durum = "Cagirildi"
    db.commit()
    
    # ۳. دریافت اطلاعات بیمار
    hasta = db.query(models.Hasta).filter(models.Hasta.hastaid == bilet.hastaid).first()
    
    # ۴. محاسبه سن
    bugun = datetime.date.today()
    dogum = hasta.dogumtarihi
    yas = bugun.year - dogum.year - ((bugun.month, bugun.day) < (dogum.month, dogum.day))

    # ۵. دریافت فرم هوش مصنوعی
    form = db.query(models.SoruCevapFormu).filter(
        models.SoruCevapFormu.biletid == bilet.biletid
    ).first()
    
    ai_metni = "Hasta ön bilgi formu doldurmadı."
    if form and form.ai_ozet:
        ai_metni = form.ai_ozet 

    # ۶. بازگرداندن اطلاعات (اصلاح شده: اضافه کردن biletid)
    return {
        "biletid": bilet.biletid,  # <--- این خط جا افتاده بود
        "adsoyad": hasta.adsoyad,
        "tckimlik": hasta.tckimlik,
        "yas": yas,
        "siranumarasi": bilet.siranumarasi,
        "ai_ozet": ai_metni
    }
   
@router.get("/bekleyenler/{doktor_id}", response_model=list[schemas.DoktorBekleyenHasta])
def get_bekleyen_hastalar(doktor_id: int, db: Session = Depends(get_db)):
    """
    Doktorun kapısında 'Bekliyor' durumunda olan hastaların listesini getirir.
    """
    bekleyenler = db.query(
        models.BiletAktif.baglantikodu,
        models.BiletAktif.siranumarasi,
        models.Hasta.adsoyad
    ).join(
        models.Hasta, models.BiletAktif.hastaid == models.Hasta.hastaid
    ).filter(
        models.BiletAktif.doktorid == doktor_id,
        models.BiletAktif.durum == 'Bekliyor', # فقط کسانی که منتظرند
        # (اختیاری: فقط امروز)
        func.cast(models.BiletAktif.olusturmatarihi, Date) == datetime.date.today()
    ).order_by(models.BiletAktif.siranumarasi).all()
    
    return bekleyenler   