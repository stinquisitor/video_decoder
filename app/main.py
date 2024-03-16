import io

from fastapi import FastAPI, Body, status, HTTPException
from fastapi.responses import JSONResponse
import minio
import json


import os
from dotenv import load_dotenv
import hashlib

from app.logic.audio import (
    process_audio_file,
)
from app.logic.json_processing import json_rework

from whisperx import (
    load_model,
    DiarizationPipeline,
    load_align_model,
    align,
    assign_word_speakers,
)


from app.logic.context import tmp_image_folder
from app.logic.utils import create_doc

load_dotenv()


DEVICE = os.getenv('DEVICE', 'cuda')

DEFAULT_LANG = os.getenv('DEFAULT_LANG', 'ru')

transcribe_model = load_model(
        os.getenv('WHISPER_MODEL', 'large-v3'),
        DEVICE,
        compute_type=os.getenv('COMPUTE_TYPE', 'float16'),
        language=DEFAULT_LANG,
        task="transcribe",
        # threads=os.getenv("WHISPER_THREADS", 4)
)

align_model, align_metadata = load_align_model(
    language_code=DEFAULT_LANG, device=DEVICE
)

diarize_model = DiarizationPipeline(use_auth_token=os.getenv('HF_TOKEN'), device=DEVICE)


app = FastAPI()
client = minio.Minio(
    endpoint=os.getenv('MINIO_ENDPOINT', 'minio:9000'),
    # endpoint='127.0.0.1:9000',
    access_key=os.getenv('MINIO_ACCESS_KEY', 'cjKMqPAaGfpnsIdRzNZG'),
    secret_key=os.getenv('MINIO_SECRET_KEY', 'WjNFiKfpZAVBDScjhp6w4KzFSy7jRkuB50EhoVl3'),
    secure=False
)


MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'my-bucket')



# декодирование входного файла в текст
# filename будет иметь формат ./{user_id}/{file_id}/{filename}
@app.post("/full_processing")
def full_processing(data=Body()):
    user_id = data['user_id']
    file_id = data['file_id']
    file_name = data['filename']
    file_path = f'/{user_id}/{file_id}/{file_name}'

    try:


        response = client.get_object(MINIO_BUCKET, file_path)



        with tmp_image_folder() as tmp_dir:
            tmp_file_path = f'{tmp_dir}/{file_name}'
            with open(tmp_file_path, 'wb') as f:
                for d in response.stream(32 * 1024):
                    f.write(d)
            audio = process_audio_file(tmp_file_path)
            result_transcribe = transcribe_model.transcribe(
                audio=audio, batch_size=16, language=DEFAULT_LANG
            )
            result_align = align(result_transcribe["segments"], align_model, align_metadata, audio, DEVICE, return_char_alignments=False)
            diarize_segments = diarize_model(audio)

            result = assign_word_speakers(diarize_segments, result_align)
            result = json_rework(result)


    except ValueError:
        return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Файл не найден"}
        )
    finally:
        response.close()
        response.release_conn()

    if result is not None and result['data'] is not None:
        value_as_bytes = str(result).encode('utf-8')
        new_file_name = str(hashlib.md5(value_as_bytes).hexdigest())
        res_filename_json = f'/{user_id}/{file_id}/'+ new_file_name+'.json'
        res_filename_docx = f'/{user_id}/{file_id}/'+ new_file_name+'.docx'

        res_data = io.BytesIO(value_as_bytes)

        client.put_object(bucket_name=MINIO_BUCKET, object_name=f'{res_filename_json}', data=res_data,
                          length=len(value_as_bytes))

        with tmp_image_folder() as tmp_dir:
            tmp_file_path = f'{tmp_dir}/{new_file_name}'
            doc = create_doc(result)
            doc.save(tmp_file_path)
            client.fput_object(bucket_name=MINIO_BUCKET, object_name=f'{res_filename_docx}', file_path=tmp_file_path)


        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'result': res_filename_json})

    return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Отсутствует результат декодирования"})

def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
