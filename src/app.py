import logging

from fastapi import FastAPI, Response
from fastapi.openapi.utils import get_openapi

from routes import hello, tensor, worker

app = FastAPI()
logger = logging.getLogger()


@app.middleware("http")
async def log_request(request, call_next):
    logger.info(f"{request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Status code: {response.status_code}")
    body = b""
    async for chunk in response.body_iterator:
        body += chunk
    print("body")
    try:
        print(body.decode("UTF-8"))
    except Exception as e:
        print(e)
    # do something with body ...
    return Response(
        content=body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )


@app.get("/")
async def root():
    return {"message": "FastAPI service running"}


# Adding routes for each example in the repo
app.include_router(hello.router, prefix="/hello")
app.include_router(tensor.router, prefix="/tensor")
app.include_router(worker.router)

# This is only here to customize the swagger :)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="OBLV-PySyft 💖 FastAPI",
        version="0.1.0",
        description="This is the Oblivious-FastAPI sample repo for PySyft.",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {"url": "https://oblv.io/oblv-hearts-fastapi"}
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
