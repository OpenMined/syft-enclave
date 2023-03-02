import uvicorn

from app import app
import sys


port = int(sys.argv[1]) if len(sys.argv)==2 else 3030


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="info", reload=True)
