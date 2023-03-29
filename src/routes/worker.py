# stdlib
import os

from syft import Worker, deserialize, enable_external_lib, serialize
from syft.core.node.new.client import Routes
from syft.core.node.new.credentials import SyftVerifyKey
from syft.core.node.worker import NodeType

from fastapi import APIRouter, Depends, Request, Response  # isort: skipAPIRoute


router = APIRouter(tags=["worker"])
enable_external_lib("oblv")
os.environ["ENABLE_OBLV"] = "true"


worker: Worker = Worker(node_type=NodeType.ENCLAVE)


async def get_body(request: Request):
    return await request.body()


@router.post(f"{Routes.ROUTE_API_CALL.value}")
def syft_api_call(data: bytes = Depends(get_body)) -> Response:
    obj_msg = deserialize(blob=data, from_bytes=True)
    result = worker.handle_api_call(api_call=obj_msg)
    return Response(
        serialize(result, to_bytes=True),
        media_type="application/octet-stream",
    )


@router.get(f"{Routes.ROUTE_API.value}")
def syft_new_api(verify_key: str) -> Response:
    user_verify_key: SyftVerifyKey = SyftVerifyKey.from_string(verify_key)
    return Response(
        serialize(worker.get_api(user_verify_key), to_bytes=True),
        media_type="application/octet-stream",
    )
