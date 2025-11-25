# main.py
from fastapi import FastAPI
from db import engine
import models


from routers import sehirler_router, hastalar_router, biletler_router, formlar_router , doktor_router, yonetim_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def read_root():
    return {"Proje": "MESS API", "Durum": "Calisiyor"}



app.include_router(sehirler_router.router)
app.include_router(hastalar_router.router)
app.include_router(biletler_router.router)
app.include_router(formlar_router.router)
app.include_router(doktor_router.router)
app.include_router(yonetim_router.router)