# def main() -> None:
#     print("Hello from api!")

from fastapi import FastAPI

app = FastAPI(title="Ideal Electric API")


@app.get("/health")
def health_check():
    return {"status": "ok"}
