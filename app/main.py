import datetime
import io

from fastapi import FastAPI, Body, status
from fastapi.responses import JSONResponse
import minio
import whisper
import numpy as np

import torch
import os
from dotenv import load_dotenv
import hashlib

load_dotenv()

# Check if NVIDIA GPU is available
torch.cuda.is_available()
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# TODO: Тут грузим модель (чтобы не перегружать при каждом запросе)
model = whisper.load_model("base", device=DEVICE)

app = FastAPI()
client = minio.Minio(
    endpoint=os.getenv('MINIO_ENDPOINT', 'minio:9000'),
    access_key=os.getenv('MINIO_ACCESS_KEY', 'cjKMqPAaGfpnsIdRzNZG'),
    secret_key=os.getenv('MINIO_SECRET_KEY', 'WjNFiKfpZAVBDScjhp6w4KzFSy7jRkuB50EhoVl3'),
    secure=False
)
MINIO_BUCKET = 'my-bucket'


# декодирование входного файла в текст
# filename будет иметь формат ./{user_id}/{file_id}/{filename}
@app.post("/decode")
def decode(data=Body()):
    user_id = data['user_id']
    file_id = data['file_id']
    file_path = data['filename']
    try:
        response = client.get_object(MINIO_BUCKET, f'/{user_id}/{file_id}/{file_path}')
        file = response.read()
    except ValueError:
        return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Файл не найден"}
        )
    finally:
        response.close()
        response.release_conn()
    # TODO: Тут делаем ML-магию
    # тест на mp3
    aud_array = np.frombuffer(file, np.int8).flatten().astype(np.float32) / 32768.0
    result = model.transcribe(aud_array)

    # Теперь записываем результат в minio и отдаём ссылку на него.
    # Чтобы получить уникальный - делаем хэш результата и добавляем
    if result is not None and result['text'] is not None:
        value_as_bytes = str(result).encode('utf-8')
        res_filename = f'/{user_id}/{file_id}/'+str(hashlib.md5(value_as_bytes).hexdigest())+'.json'

        res_data = io.BytesIO(value_as_bytes)

        client.put_object(bucket_name=MINIO_BUCKET, object_name=f'{res_filename}', data=res_data,
                          length=len(value_as_bytes))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'result': res_filename})

    return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Отсутствует результат декодирования"})


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
