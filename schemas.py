# schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import Optional

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
    sifre: str
    email: Optional[EmailStr] = None
    telefon: Optional[str] = None
    dogumtarihi: Optional[date] = None

class HastaBase(BaseModel):
    hastaid: int
    adsoyad: str
    tckimlik: str
    sifre: str
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

# --- (کد جدید) ---
# =================================================================
# ۵. مدل خروجی برای صفحه "ردیابی صف"
# =================================================================
class SiraTakipDetay(BaseModel):
    # اطلاعات بلیت
    sizin_numaraniz: int         # مثال: 26
    durum: str                   # مثال: "Bekliyor"
    giris_zamani: datetime       # مثال: "2025-11-08T..."
    tahmini_bekleme_suresi: str  # مثال: "Yaklaşık 5 Dakika"

    # اطلاعات لینک‌شده (Joined)
    bolum_adi: str               # مثال: "Genel Muayene"
    doktor_adi: str              # مثال: "Dr. Ahmet Yılmaz"

    # اطلاعات محاسباتی
    mevcut_sira: int             # مثال: 23
    kalan_hasta: int             # مثال: 3

    class Config:
        from_attributes = True


class BiletTakipGiris(BaseModel):
    baglantikodu: str 
    telefon: str            