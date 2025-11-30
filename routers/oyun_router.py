# routers/oyun_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
import models, schemas
from db import get_db
import datetime
import traceback

router = APIRouter(
    prefix="/api/oyun",
    tags=["Oyun & Gamification"]
)


# ------------------ 1) ثبت امتیاز ------------------
@router.post("/skor", response_model=schemas.Message)
def kayit_skor(skor_data: schemas.SkorCreate, db: Session = Depends(get_db)):
    """
    Oyun bitince skoru kaydeder.
    """

    # Validate اولیه
    if skor_data.skor < 0:
        raise HTTPException(status_code=400, detail="Skor negatif olamaz.")

    # Check وجود بیمار
    hasta = db.query(models.Hasta).filter(models.Hasta.hastaid == skor_data.hastaid).first()
    if not hasta:
        raise HTTPException(status_code=404, detail="Bu hasta mevcut değil.")

    yeni_skor = models.OyunSkoru(
        hastaid=skor_data.hastaid,
        oyunadi=skor_data.oyunadi,
        skor=skor_data.skor,
        tarih=datetime.datetime.now()
    )

    try:
        db.add(yeni_skor)
        db.commit()
    except Exception as e:
        db.rollback()
        print("\n--- DATABASE ERROR ---")
        traceback.print_exc()
        print("--- END ERROR ---\n")
        raise HTTPException(status_code=500, detail=f"Skor kaydedilemedi: {e}")

    return {"detail": "Skor başarıyla kaydedildi!"}


# ------------------ 2) دریافت لیدربورد ------------------
@router.get("/liderler/{oyun_adi}", response_model=list[schemas.SkorBase])
def get_liderler(oyun_adi: str, db: Session = Depends(get_db)):
    """
    Bir oyun için en yüksek 10 skoru getirir.
    """

    try:
        liderler = (
            db.query(
                models.Hasta.adsoyad.label("adsoyad"),
                models.OyunSkoru.skor.label("skor"),
                models.OyunSkoru.tarih.label("tarih")
            )
            .join(models.Hasta, models.OyunSkoru.hastaid == models.Hasta.hastaid)
            .filter(models.OyunSkoru.oyunadi == oyun_adi)
            .order_by(desc(models.OyunSkoru.skor))
            .limit(10)
            .all()
        )
    except Exception as e:
        print("\n--- DATABASE ERROR ---")
        traceback.print_exc()
        print("--- END ERROR ---\n")
        raise HTTPException(status_code=500, detail="Liderboard alınamadı.")

    return liderler
