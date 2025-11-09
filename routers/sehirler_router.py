# routers/sehirler_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from db import get_db


router = APIRouter(
    prefix="/api/konum", 
    tags=["Konum İşlemleri"] 
)


@router.get("/sehirler", response_model=List[schemas.SehirBase])
def get_sehirler(db: Session = Depends(get_db)):

    sehirler = db.query(models.Sehir).order_by(models.Sehir.sehiradi).all()
    return sehirler

# آدرس نهایی: GET /api/konum/hastaneler/{sehir_kodu}
@router.get("/hastaneler/{sehir_kodu}", response_model=List[schemas.HastaneBase])
def get_hastaneler_by_sehir(sehir_kodu: str, db: Session = Depends(get_db)):
  
    sehir = db.query(models.Sehir).filter(models.Sehir.sehirkodu == sehir_kodu).first()
    if not sehir:
        raise HTTPException(status_code=404, detail="شهر مورد نظر یافت نشد.")

    hastaneler = db.query(models.Hastane).filter(models.Hastane.sehirid == sehir.sehirid).all()
    return hastaneler

@router.get("/konum/{sehir_kodu}/{hastane_kodu}/poliklinikler", response_model=List[schemas.PoliklinikBase])
def get_poliklinikler_by_hastane(sehir_kodu: str, hastane_kodu: str, db: Session = Depends(get_db)):
    """
    Verilen şehir ve hastane koduna ait tüm poliklinikleri getirir.
    (تمام پلی‌کلینیک‌های متعلق به کد شهر و کد بیمارستان داده شده را برمی‌گرداند.)
    """

    # ۱. ابتدا بیمارستان را بر اساس هر دو کد پیدا کن تا مطمئن شویم معتبر است
    hastane = db.query(models.Hastane).join(models.Sehir).filter(
        models.Sehir.sehirkodu == sehir_kodu,
        models.Hastane.hastanekodu == hastane_kodu
    ).first()

    if not hastane:
        raise HTTPException(status_code=404, detail="Bu şehirde böyle bir hastane bulunamadı.")

    # ۲. حالا پلی‌کلینیک‌ها را بر اساس hastaneid پیدا شده فیلتر کن
    poliklinikler = db.query(models.Poliklinik).filter(
        models.Poliklinik.hastaneid == hastane.hastaneid
    ).order_by(models.Poliklinik.poliklinikadi).all()

    return poliklinikler

@router.get("/konum/doktorlar/{poliklinik_kodu}", response_model=List[schemas.DoktorBase])
def get_doktorlar_by_poliklinik(poliklinik_kodu: str, db: Session = Depends(get_db)):
    """
    Verilen poliklinik koduna ('01' gibi) ait tüm doktorları getirir.
    (تمام پزشکان متعلق به کد پلی‌کلینیک داده شده (مثلاً '01') را برمی‌گرداند.)
    """

    # ۱. ابتدا پلی‌کلینیک را بر اساس کد آن پیدا کن
    poliklinik = db.query(models.Poliklinik).filter(
        models.Poliklinik.poliklinikkodu == poliklinik_kodu
    ).first()

    if not poliklinik:
        raise HTTPException(status_code=404, detail="Poliklinik bulunamadı.")

    # ۲. حالا پزشکان را بر اساس poliklinikid پیدا شده فیلتر کن
    doktorlar = db.query(models.Doktor).filter(
        models.Doktor.poliklinikid == poliklinik.poliklinikid
    ).order_by(models.Doktor.adsoyad).all()

    return doktorlar