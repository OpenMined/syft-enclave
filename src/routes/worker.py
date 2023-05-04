# stdlib
import os

from syft import Worker, enable_external_lib
from syft.abstract_node import NodeType
from syft.node.routes import make_routes

enable_external_lib("oblv")
os.environ["ENABLE_OBLV"] = "true"

worker: Worker = Worker(node_type=NodeType.ENCLAVE)

router = make_routes(worker=worker)
