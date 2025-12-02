# routers/formlar_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from db import get_db
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, Date  

router = APIRouter(
    prefix="/api/formlar",      # تمام آدرس‌های این فایل با /api/formlar شروع می‌شوند
    tags=["Form İşlemleri"]     # دسته‌بندی در /docs
)

# --- (جدید) API ۱: ثبت کردن فرم خلاصه شده هوش مصنوعی ---
@router.post("/", response_model=schemas.FormBase)
def create_form(form_data: schemas.FormCreate, db: Session = Depends(get_db)):
    """
    Hastanın Gemini ile yaptığı görüşmenin özetini veritabanına kaydeder.
    (خلاصه‌ی گفتگوی بیمار با Gemini را در دیتابیس ذخیره می‌کند.)
    """

    # ۱. چک می‌کنیم که آیا این بلیت قبلاً فرم ثبت کرده است یا نه
    # (چون ستون biletid در دیتابیس UNIQUE است)
    existing_form = db.query(models.SoruCevapFormu).filter(
        models.SoruCevapFormu.biletid == form_data.biletid
    ).first()

    if existing_form:
        raise HTTPException(
            status_code=400,
            detail="Bu bilet için zaten bir form gönderilmiş." 
                   "(برای این بلیت قبلاً یک فرم ارسال شده است.)"
        )

    # ۲. چک می‌کنیم که آیا بلیت اصلاً در جدول فعال وجود دارد یا نه
    bilet_exists = db.query(models.BiletAktif).filter(
        models.BiletAktif.biletid == form_data.biletid
    ).first()

    if not bilet_exists:
        raise HTTPException(
            status_code=404,
            detail="Bu BiletId aktif biletler listesinde bulunamadı."
                   "(این شناسه بلیت در لیست بلیت‌های فعال یافت نشد.)"
        )

    # ۳. فرم جدید را در دیتابیس ایجاد می‌کنیم
    db_form = models.SoruCevapFormu(
        biletid=form_data.biletid,
        ai_ozet=form_data.ai_ozet,
        formverisi_json=form_data.formverisi_json, # (متن کامل چت، اختیاری)
        gonderimtarihi=datetime.datetime.now() # زمان فعلی
    )

    try:
        db.add(db_form)
        db.commit()
        db.refresh(db_form) # داده‌های کامل (شامل FormId) را از دیتابیس می‌گیریم
    except Exception as e:
        db.rollback()
        print(f"Form kaydetme hatası: {e}")
        raise HTTPException(status_code=500, detail="Form kaydedilirken veritabanı hatası oluştu.")

    # ۴. فرم ذخیره شده را برمی‌گردانیم
    return db_form





# routers/formlar_router.py
# ...

# --- (جدید) API 3: دریافت آمار فرم‌های پر شده ---
# آدرس: GET /api/formlar/istatistik/genel
@router.get("/istatistik/genel", response_model=schemas.FormIstatistik)
def get_form_istatistikleri(db: Session = Depends(get_db)):
    """
    Gemini tarafından doldurulan toplam ve günlük form sayısını getirir.
    (تعداد کل و روزانه فرم‌های پر شده توسط Gemini را برمی‌گرداند.)
    """
    
    # ۱. شمارش کل فرم‌ها
    toplam = db.query(func.count(models.SoruCevapFormu.formid)).scalar() or 0
    
    # ۲. شمارش فرم‌های امروز
    bugun = db.query(func.count(models.SoruCevapFormu.formid)).filter(
        func.cast(models.SoruCevapFormu.gonderimtarihi, Date) == datetime.date.today()
    ).scalar() or 0
    
    return {
        "toplam_form_sayisi": toplam,
        "bugunku_form_sayisi": bugun
    }    