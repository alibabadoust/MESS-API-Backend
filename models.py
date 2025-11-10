# models.py
from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, ForeignKey, JSON
from sqlalchemy.orm import relationship
from db import Base 


class Sehir(Base):
    __tablename__ = "sehirlertablosu"

    sehirid = Column(Integer, primary_key=True, index=True)
    sehiradi = Column(String)
    sehirkodu = Column(String(2))


class Hastane(Base):
    __tablename__ = "hastaneaditablosu"

    hastaneid = Column(Integer, primary_key=True, index=True)
    hastaneadi = Column(String)
    hastanekodu = Column(String(2))
    sehirid = Column(Integer, ForeignKey("sehirlertablosu.sehirid"))
class Poliklinik(Base):
    __tablename__ = "polikilinikaditablosu" 

    poliklinikid = Column(Integer, primary_key=True, index=True)
    poliklinikadi = Column(String)
    poliklinikkodu = Column(String(2))
    hastaneid = Column(Integer, ForeignKey("hastaneaditablosu.hastaneid"))

class Hasta(Base):
    __tablename__ = "hastalartablosu"

    hastaid = Column(Integer, primary_key=True, index=True)
    adsoyad = Column(String)
    telefon = Column(String)
    dogumtarihi = Column(Date)
    tckimlik = Column(String(11), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    sifre = Column(String(255), nullable=False) 

class Doktor(Base):
    __tablename__ = "doktorlartablosu" # نام دقیق جدول شما

    doktorid = Column(Integer, primary_key=True, index=True)
    adsoyad = Column(String)
    uzmanlikalani = Column(String) # تخصص
    poliklinikid = Column(Integer, ForeignKey("polikilinikaditablosu.poliklinikid"))
    odakodu = Column(String(2))
# 6. Arşiv Biletleri Tablo Modeli
class BiletArsiv(Base):
    __tablename__ = "sirabiletleri_arsiv"

    biletid = Column(Integer, primary_key=True, index=True) # Bu SERIAL DEĞİL, Aktif'ten gelecek
    baglantikodu = Column(String(100))
    hastaid = Column(Integer, ForeignKey("hastalartablosu.hastaid"))
    doktorid = Column(Integer, ForeignKey("doktorlartablosu.doktorid"))
    poliklinikid = Column(Integer, ForeignKey("polikilinikaditablosu.poliklinikid"))
    siranumarasi = Column(Integer)
    durum = Column(String(20))
    olusturmatarihi = Column(TIMESTAMP)
    kapanistarihi = Column(TIMESTAMP)
    eskibiletid = Column(Integer) # Bu FK değil, sadece sayıyı tutar
    tahminibeklemesuresi = Column(String(50))

# 7. Aktif Biletler Tablo Modeli
class BiletAktif(Base):
    __tablename__ = "sirabiletleri_aktiftablosu"

    biletid = Column(Integer, primary_key=True, index=True) # Bu SERIAL
    baglantikodu = Column(String(100), unique=True)
    hastaid = Column(Integer, ForeignKey("hastalartablosu.hastaid"))
    doktorid = Column(Integer, ForeignKey("doktorlartablosu.doktorid"))
    poliklinikid = Column(Integer, ForeignKey("polikilinikaditablosu.poliklinikid"))
    siranumarasi = Column(Integer)
    durum = Column(String(20))
    olusturmatarihi = Column(TIMESTAMP)
    eskibiletid = Column(Integer, ForeignKey("sirabiletleri_arsiv.biletid"), nullable=True) # Bu FK
    tahminibeklemesuresi = Column(String(50))    

# models.py

# ... (کلاس‌های Sehir, Hastane, Hasta, Poliklinik, Doktor, BiletArsiv, BiletAktif در بالا هستند) ...

# --- (کد جدید) ---
# ۸. مدل جدول فرم‌های پرسش و پاسخ
class SoruCevapFormu(Base):
    __tablename__ = "sorucevapformlaritablosu" # نام دقیق جدول شما

    formid = Column(Integer, primary_key=True, index=True)
    # (JSONB در PostgreSQL با JSON در SQLAlchemy کار می‌کند)
    # ما می‌توانیم کل متن گفتگو را در اینجا ذخیره کنیم (برای سوابق)
    formverisi_json = Column(JSON, nullable=True) 

    # خلاصه‌ای که Gemini می‌سازد در اینجا ذخیره می‌شود
    ai_ozet = Column(String) 
    gonderimtarihi = Column(TIMESTAMP)

    # اتصال یک-به-یک به بلیت فعال
    biletid = Column(Integer, ForeignKey("sirabiletleri_aktiftablosu.biletid"), unique=True)   