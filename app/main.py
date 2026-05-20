from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from deepface import DeepFace
from prometheus_fastapi_instrumentator import Instrumentator
import shutil
import os
from datetime import datetime

app = FastAPI()
Instrumentator().instrument(app).expose(app)

os.makedirs("faces", exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clientes = []


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clientes.append(ws)

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        clientes.remove(ws)


async def notificar(data):
    remover = []

    for cliente in clientes:
        try:
            await cliente.send_json(data)
        except:
            remover.append(cliente)

    for c in remover:
        clientes.remove(c)


@app.get("/")
def root():
    return {"status": "online"}


@app.post("/register")
async def register(nome: str = Form(...), file: UploadFile = File(...)):
    path = f"faces/{nome}.jpg"

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"success": True}


@app.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    temp_path = "temp.jpg"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    for face_file in os.listdir("faces"):
        db_path = f"faces/{face_file}"

        try:
            result = DeepFace.verify(
                img1_path=temp_path,
                img2_path=db_path,
                enforce_detection=False
            )

            if result["verified"]:
                nome = face_file.replace(".jpg", "")

                evento = {
                    "tipo": "aprovado",
                    "nome": nome,
                    "hora": datetime.now().strftime("%H:%M:%S")
                }

                await notificar(evento)

                return {
                    "match": True,
                    "nome": nome
                }

        except:
            pass

    evento = {
        "tipo": "negado",
        "nome": "Desconhecido",
        "hora": datetime.now().strftime("%H:%M:%S")
    }

    await notificar(evento)

    return {"match": False}