import uvicorn

from app import app

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=3030, log_level="info", reload=True)
