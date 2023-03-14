from fastapi import APIRouter, Depends, Request, Response  # isort: skipAPIRouter
from syft import Worker, deserialize, serialize
from syft.core.node.new.client import Routes
from syft.core.node.worker import NodeType

router = APIRouter(tags=["worker"])
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
def syft_new_api() -> Response:
    return Response(
        serialize(worker.get_api(), to_bytes=True),
        media_type="application/octet-stream",
    )
