# schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime # <-- مطمئن شوید 'datetime' وارد شده
from typing import Optional, Any

# =================================================================
# ۱. مدل پیام
# =================================================================
class Message(BaseModel):
    detail: str

# =================================================================
# ۲. مدل‌های بیماران (Hasta)
# =================================================================
class HastaCreate(BaseModel):
    adsoyad: str
    tckimlik: str
    sifre: str = Field(..., min_length=10, max_length=72)
    email: Optional[EmailStr] = None
    telefon: Optional[str] = None
    dogumtarihi: Optional[date] = None

class HastaBase(BaseModel):
    hastaid: int
    adsoyad: str
    tckimlik: str
    email: Optional[EmailStr] = None
    telefon: Optional[str] = None
    dogumtarihi: Optional[date] = None
    class Config:
        from_attributes = True

# =================================================================
# ۳. مدل‌های موقعیت (Konum)
# =================================================================
class SehirBase(BaseModel):
    sehirid: int
    sehiradi: str
    sehirkodu: str
    class Config:
        from_attributes = True

class HastaneBase(BaseModel):
    hastaneid: int
    hastaneadi: str
    hastanekodu: str
    sehirid: int
    class Config:
        from_attributes = True

class PoliklinikBase(BaseModel):
    poliklinikid: int
    poliklinikadi: str
    poliklinikkodu: str
    hastaneid: int
    class Config:
        from_attributes = True

class DoktorBase(BaseModel):
    doktorid: int
    adsoyad: str
    uzmanlikalani: Optional[str] = None
    poliklinikid: int
    odakodu: Optional[str] = None
    class Config:
        from_attributes = True

# =================================================================
# ۴. مدل‌های بلیت (Bilet)
# =================================================================
class BiletCreate(BaseModel):
    hastaid: int
    doktorid: int

class BiletBase(BaseModel):
    biletid: int
    baglantikodu: str
    hastaid: int
    doktorid: int
    poliklinikid: int
    siranumarasi: int
    durum: str
    olusturmatarihi: datetime
    tahminibeklemesuresi: str
    class Config:
        from_attributes = True

# =================================================================
# ۵. مدل ورودی برای صفحه "ردیابی صف"
# =================================================================
class BiletTakipGiris(BaseModel):
    baglantikodu: str
    telefon: str

# =================================================================
# ۶. مدل خروجی برای صفحه "ردیابی صف" (این کلاس جا افتاده بود)
# =================================================================
class SiraTakipDetay(BaseModel):
    biletid: int
    sizin_numaraniz: int
    durum: str
    giris_zamani: datetime
    tahmini_bekleme_suresi: str
    bolum_adi: str
    doktor_adi: str
    mevcut_sira: int
    kalan_hasta: int

    class Config:
        from_attributes = True

# =================================================================
# ۷. مدل‌های فرم پرسش و پاسخ (Soru-Cevap)
# =================================================================
class FormCreate(BaseModel):
    biletid: int
    ai_ozet: str
    formverisi_json: Optional[Any] = None

class FormBase(BaseModel):
    formid: int
    biletid: int
    ai_ozet: str
    gonderimtarihi: datetime

    class Config:
        from_attributes = True