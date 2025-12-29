from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
import os

# .env dosyasından veya ortam değişkenlerinden verileri okumak için Ayarlar sınıfı
class Settings(BaseSettings):
    # Tüm veritabanı bağlantı adresi (ConnectionString) için tek bir değişken
    DATABASE_URL: str 

    class Config:
        env_file = ".env" 
        # Fazladan değişken varsa hata vermemesi için ignore kullanıyoruz
        extra = "ignore" 

settings = Settings()

# Veritabanı bağlantı URL'sini al
DATABASE_URL = settings.DATABASE_URL

# SQLAlchemy bağlantı motorunu (engine) oluştur
# Not: Neon.tech gibi serverless servislerde Connection String doğrudan kullanılır
engine = create_engine(DATABASE_URL)

# Veritabanı oturumlarını yönetmek için SessionLocal oluştur
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modellerin türetileceği temel sınıf (ORM için)
Base = declarative_base()

# API endpoint'lerinde veritabanı oturumu açıp kapatmak için yardımcı fonksiyon
# FastAPI'de 'Dependency Injection' olarak kullanılır
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()