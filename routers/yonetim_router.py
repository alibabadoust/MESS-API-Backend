# routers/yonetim_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text # برای اجرای دستورات SQL خام
from db import get_db

router = APIRouter(
    prefix="/api/yonetim",
    tags=["Yönetim (Admin) İşlemleri"]
)

# --- API: پایان روز (Gün Sonu) ---
@router.post("/gun-sonu")
def gun_sonu_islemi(db: Session = Depends(get_db)):
    """
    **DİKKAT:** Bu işlem 'Gün Sonu' temizliğidir.
    1. Aktif biletleri Arşiv tablosuna taşır.
    2. İlgili formları siler.
    3. Aktif biletler tablosunu tamamen boşaltır.
    Bu işlemden sonra sayaçlar sıfırlanır ve yarın için temiz bir başlangıç yapılır.
    """
    try:
        # 1. کپی کردن بلیت‌ها به آرشیو
        # (دقیقا همان منطق SQL که قبلاً تست کردیم)
        sql_archive = text("""
            INSERT INTO sirabiletleri_arsiv 
            (biletid, baglantikodu, hastaid, doktorid, poliklinikid, siranumarasi, durum, olusturmatarihi, eskibiletid, tahminibeklemesuresi, kapanistarihi)
            SELECT 
                biletid, baglantikodu, hastaid, doktorid, poliklinikid, siranumarasi, durum, olusturmatarihi, eskibiletid, tahminibeklemesuresi, NOW()
            FROM sirabiletleri_aktiftablosu;
        """)
        db.execute(sql_archive)

        # 2. حذف فرم‌های وابسته (برای جلوگیری از خطای کلید خارجی)
        sql_delete_forms = text("""
            DELETE FROM sorucevapformlaritablosu
            WHERE biletid IN (SELECT biletid FROM sirabiletleri_aktiftablosu);
        """)
        db.execute(sql_delete_forms)

        # 3. خالی کردن جدول بلیت‌های فعال
        sql_truncate = text("DELETE FROM sirabiletleri_aktiftablosu;")
        db.execute(sql_truncate)

        # ذخیره نهایی تغییرات
        db.commit()
        
        return {"detail": "Gün sonu işlemi başarıyla tamamlandı. Sistem yarına hazır."}

    except Exception as e:
        db.rollback() # اگر خطایی رخ داد، همه چیز را به حالت قبل برگردان
        print(f"Gün sonu hatası: {e}")
        raise HTTPException(status_code=500, detail=f"İşlem sırasında hata oluştu: {str(e)}")