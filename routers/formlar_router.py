# routers/formlar_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from db import get_db
import datetime

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