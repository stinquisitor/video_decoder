from fastapi import FastAPI
import minio


app = FastAPI()


@app.post("/decode")
def decode():
    pass
    return {"result": ','}


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
