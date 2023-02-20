from fastapi import APIRouter, Depends, Request, Response  # isort: skipAPIRouter
from syft import Worker, deserialize, serialize

router = APIRouter(tags=["worker"])

def yaml_config() -> dict:
    try:
        with open('/usr/runtime.yaml', 'r') as f:
            config_data = yaml.safe_load(f)["runtime_args"]
    except:
        config_data = {}
    return config_data


worker: Worker = Worker()


async def get_body(request: Request):
    return await request.body()


@router.post("/syft_api_call")
def syft_api_call(data: bytes = Depends(get_body)) -> Response:
    obj_msg = deserialize(blob=data, from_bytes=True)
    result = worker.handle_api_call(api_call=obj_msg)
    return Response(
        serialize(result, to_bytes=True),
        media_type="application/octet-stream",
    )


@router.get("/api")
def syft_new_api() -> Response:
    return Response(
        serialize(worker.get_api(), to_bytes=True),
        media_type="application/octet-stream",
    )
