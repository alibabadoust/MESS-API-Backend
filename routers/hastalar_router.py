# routers/hastalar_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_ 
from typing import List
import models, schemas
from db import get_db



router = APIRouter(
    prefix="/api/hastalar",
    tags=["Hasta İşlemleri"] 
)


@router.post("/", response_model=schemas.Message) 
def create_hasta(hasta: schemas.HastaCreate, db: Session = Depends(get_db)):

    conditions = [
        models.Hasta.tckimlik == hasta.tckimlik,
        models.Hasta.adsoyad == hasta.adsoyad
    ]
    if hasta.email:
        conditions.append(models.Hasta.email == hasta.email)

    existing_hasta = db.query(models.Hasta).filter(or_(*conditions)).first()

    if existing_hasta:
        raise HTTPException(
            status_code=400,
            detail="Bu kayıt daha önceden yapılmış."
        )


    db_hasta = models.Hasta(
        adsoyad=hasta.adsoyad,
        tckimlik=hasta.tckimlik,
        sifre=hasta.sifre,
        email=hasta.email,
        telefon=hasta.telefon,
        dogumtarihi=hasta.dogumtarihi
    )
    db.add(db_hasta)
    db.commit()
    db.refresh(db_hasta)

    return {"detail": "Kayıt başarıyla yapıldı."}
@router.get("/", response_model=List[schemas.HastaBase]) 
def get_all_hastalar(db: Session = Depends(get_db)):

    hastalar = db.query(models.Hasta).all()
    return hastalar