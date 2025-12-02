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

# --- API 1: فراخوانی بیمار (Çağır) ---
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

    # ۶. بازگرداندن اطلاعات
    return {
        "biletid": bilet.biletid,
        "adsoyad": hasta.adsoyad,
        "tckimlik": hasta.tckimlik,
        "yas": yas,
        "siranumarasi": bilet.siranumarasi,
        "ai_ozet": ai_metni
    }
    
# --- API 2: لیست انتظار دکتر (Bekleyenler) ---
@router.get("/bekleyenler/{doktor_id}", response_model=list[schemas.DoktorBekleyenHasta])
def get_bekleyen_hastalar(doktor_id: int, db: Session = Depends(get_db)):
    """
    Doktorun kapısında 'Bekliyor' durumunda olan hastaların listesini getirir.
    """
    bekleyenler = db.query(
        models.BiletAktif.baglantikodu,
        models.BiletAktif.siranumarasi,
        models.Hasta.adsoyad
    ).select_from(models.BiletAktif) \
     .join(models.Hasta, models.BiletAktif.hastaid == models.Hasta.hastaid) \
     .filter(
        models.BiletAktif.doktorid == doktor_id,
        models.BiletAktif.durum == 'Bekliyor',
        # (برای تست، فیلتر تاریخ را فعلا غیرفعال نگه داشتم)
        # func.cast(models.BiletAktif.olusturmatarihi, Date) == datetime.date.today()
    ).order_by(models.BiletAktif.siranumarasi).all()
    
    return bekleyenler

# --- API 3: پایان ویزیت (Tamamla) ---
@router.post("/tamamla/{bilet_id}", response_model=schemas.Message)
def muayene_tamamla(bilet_id: int, db: Session = Depends(get_db)):
    """
    Doktor muayeneyi bitirdiğinde bu endpoint çağrılır.
    Biletin durumunu 'Tamamlandi' yapar.
    """
    
    # ۱. پیدا کردن بلیت با شناسه
    bilet = db.query(models.BiletAktif).filter(models.BiletAktif.biletid == bilet_id).first()
    
    if not bilet:
        raise HTTPException(status_code=404, detail="Bilet bulunamadı.")
    
    # ۲. تغییر وضعیت
    bilet.durum = "Tamamlandi"
    
    # ۳. ذخیره در دیتابیس
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata oluştu: {e}")
    
    return {"detail": "Muayene tamamlandı"}


# --- (جدید) API 4: بیمار نیامد (Gelmedi) ---
# آدرس: POST /api/doktor/gelmedi/{bilet_id}
@router.post("/gelmedi/{bilet_id}", response_model=schemas.Message)
def hasta_gelmedi(bilet_id: int, db: Session = Depends(get_db)):
    """
    Hasta sırası geldiği halde odada yoksa bu endpoint çağrılır.
    Biletin durumunu 'Gelmeyen' yapar.
    (اگر بیمار در نوبتش حاضر نبود، وضعیت را به 'Gelmeyen' تغییر می‌دهد.)
    """
    
    # ۱. پیدا کردن بلیت با شناسه
    bilet = db.query(models.BiletAktif).filter(models.BiletAktif.biletid == bilet_id).first()
    
    if not bilet:
        raise HTTPException(status_code=404, detail="Bilet bulunamadı.")
    
    # ۲. تغییر وضعیت به 'Gelmeyen'
    bilet.durum = "Gelmeyen"
    
    # ۳. ذخیره در دیتابیس
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hata oluştu: {e}")
    
    return {"detail": "Hasta durumu 'Gelmeyen' olarak güncellendi."}
# routers/doktor_router.py
# ...

# --- (جدید) API 5: افزودن دکتر جدید (پنل ادمین) ---
# آدرس: POST /api/doktor/ekle
@router.post("/ekle", response_model=schemas.Message)
def doktor_ekle(doktor_data: schemas.DoktorCreate, db: Session = Depends(get_db)):
    """
    Yeni bir doktor kaydeder. (Admin Paneli için)
    """
    
    # ۱. چک می‌کنیم که پلی‌کلینیک وجود داشته باشد
    poliklinik = db.query(models.Poliklinik).filter(
        models.Poliklinik.poliklinikid == doktor_data.poliklinikid
    ).first()
    
    if not poliklinik:
        raise HTTPException(status_code=404, detail="Seçilen poliklinik bulunamadı.")

    # ۲. ساخت آبجکت دکتر جدید
    yeni_doktor = models.Doktor(
        adsoyad=doktor_data.adsoyad,
        uzmanlikalani=doktor_data.uzmanlikalani,
        poliklinikid=doktor_data.poliklinikid,
        odakodu=doktor_data.odakodu
    )
    
    # ۳. ذخیره در دیتابیس
    try:
        db.add(yeni_doktor)
        db.commit()
        db.refresh(yeni_doktor)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Doktor kaydedilemedi: {e}")
        
    return {"detail": f"Doktor '{yeni_doktor.adsoyad}' başarıyla eklendi."}    