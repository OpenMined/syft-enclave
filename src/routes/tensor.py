import json
from typing import Any, List, Union
from uuid import uuid4

from fastapi import (APIRouter, BackgroundTasks, File, Form, Header,
                     HTTPException, Query, Request, UploadFile)
import syft as sy
from syft import Tensor
from syft.core.adp.data_subject_ledger import DataSubjectLedger
from syft.core.adp.ledger_store import DictLedgerStore

from models.tensor_models import *

router = APIRouter(tags=["tensor"])


router.datasets = []
router.data_owners = []
router.uploaded_datasets = []
router.result_datasets = []
router.query_list = []
router.publish_queries = []

async def get_body(request: Request):
    return await request.body()


@router.get("/dataset/list")
def list_datasets(
    x_oblv_user_name: str = Header(default=None),
    x_oblv_user_role: str = Header(default=None),
):
    result = [
        {"id": x["dataset_id"], "owner": x["owner"]} for x in router.uploaded_datasets
    ]
    return result


@router.post("/dataset/add")
async def add_dataset(
    input: UploadFile = File(...),
    dataset_id: str = Form(...),
    x_oblv_user_name: str = Header(default=None),
    x_oblv_user_role: str = Header(default=None),
):
    if x_oblv_user_role != "domain":
        raise HTTPException(403, f"Path only available for domain role.")
    data_bytes = await input.read()
    data = sy.deserialize(data_bytes,from_bytes=True)
    uploaded_dataset = {
        "owner": x_oblv_user_name,
        "tensor": data,
        "dataset_id": dataset_id,
    }
    if [
        x
        for x in router.uploaded_datasets
        if uploaded_dataset["owner"] == x["owner"]
        and uploaded_dataset["dataset_id"] == x["dataset_id"]
    ].__len__() > 0:
        raise HTTPException(400, f"Dataset with given id already uploaded")
    router.uploaded_datasets.append(uploaded_dataset)
    return "Success"


@router.post("/action")
async def perform_operation(
    # input: InputPerformOpertation,
    inputs: str = Form(...),
    args: str = Form(...),
    kwargs: str = Form(...),
    op: str = Query(default=None),
    file: UploadFile = File(default=None, description="Bytes if second operand is of type torch.Tensor or numpy.ndarray"),
    x_oblv_user_name: str = Header(default=None),
    x_oblv_user_role: str = Header(default=None),
):
    if x_oblv_user_role != "user":
        raise HTTPException(403, f"Path only available for user role.")
    inputs = json.loads(inputs)
    args = json.loads(args)
    kwargs = json.loads(kwargs)
    input_args = []
    query_args = []
    if len(inputs)==0 or len(inputs)>=3:
        raise HTTPException(400,"Invalid count of arguments provided")
    if inputs[0]["type"]!="wrapper":
        raise HTTPException(400,"First argument should be of type OblvTensorWrapper")
    for v in inputs:
        if v["type"] == "wrapper":
            arg = [
                x["tensor"]
                for x in router.uploaded_datasets + router.result_datasets
                if x["dataset_id"] == v["value"]
            ]
            if arg.__len__() == 0:
                raise HTTPException(
                    400, "Dataset/Result with given id {} not found".format(v["value"])
                )
            else:
                query_args.append(v["value"])
                input_args.append(arg[0])
        elif v["type"] == "tensor":
            if file==None:
                raise HTTPException(400, "Bytes not provided for type tensor")
            data_bytes = await file.read()
            obj = sy.deserialize(data_bytes,from_bytes=True)
            query_args.append(obj)
            input_args.append(obj)
        else:
            query_args.append(v["value"])
            input_args.append(v["value"])
    if hasattr(Tensor, op):
        method = getattr(Tensor, op)
        result_id = "r-" + uuid4().__str__()
        query = {"op": op, "args": query_args, "result_dataset_id": result_id}
        ##Add check in query_list to find already existing query
        router.query_list.append(query)
        try:
            result = method(*input_args,*args, **kwargs)
        except Exception as e:
            if e.__str__().__contains__("missing") and e.__str__().__contains__(
                "argument"
            ):
                raise HTTPException(400, "Missing arguments for {}".format(op))
            elif type(e) == AttributeError:
                raise HTTPException(400, "Invalid argument passed")
            raise HTTPException(400, e.__str__())
        result_dataset = {
            "tensor": result,
            "dataset_id": result_id,
            "owner": x_oblv_user_name,
        }
        router.result_datasets.append(result_dataset)
    else:
        raise HTTPException(400, "Invalid operation")
    return result_dataset["dataset_id"]



@router.post("/publish/request")
def publish_request(
    input: InputPublishRequest,
    x_oblv_user_name: str = Header(default=None),
    x_oblv_user_role: str = Header(default=None),
):
    print(input.sigma)
    if x_oblv_user_role != "user":
        raise HTTPException(403, f"Path only available for user role.")
    dataset = None
    for x in [*router.result_datasets,*router.uploaded_datasets]:
        if x["dataset_id"]==input.dataset_id:
            dataset = x
            break
    if dataset == None:
        raise HTTPException(
            400, "Dataset/Result with given id {} not found".format(input.dataset_id)
        )
    publish_request_id = "p-" + uuid4().__str__()
    ledger_store = DictLedgerStore()
    user_key = b"1231"
    ledger = DataSubjectLedger.get_or_create(store=ledger_store, user_key=user_key)
    if input.dataset_id.startswith("r-"):
        request_obj = {
            "request_id": publish_request_id,
            "owners": [],
            "dataset": dataset["tensor"],
            "result": None,
            "budget_needed": None,
            "sigma": input.sigma,
            "ledger": ledger
        }
        owner_list = find_owners(input.dataset_id)
        owner_list = set(owner_list)
        for o in owner_list:
            request_obj["owners"].append(
                {
                    "owner": o,
                    "current_budget": None,
                    "budget_deducted": False,
                }
            )
        router.publish_queries.append(request_obj)
    else:
        router.publish_queries.append(
            {
                "request_id": publish_request_id,
                "owners": [
                    {
                        "owner": dataset["owner"],
                        "current_budget": None,
                        "budget_deducted": False,
                    }
                ],
                "dataset": dataset["tensor"],
                "result": None,
                "budget_needed": None,
                "sigma": input.sigma,
                "ledger": ledger
            }
        )
    # print(router.publish_queries)
    return publish_request_id


def find_owners(result_id, owner_list=[]):
    query = [x for x in router.query_list if x["result_dataset_id"] == result_id]
    if query.__len__() == 0:
        # This is a uploaded dataset
        query = [x for x in router.uploaded_datasets if x["dataset_id"] == result_id]
        if query.__len__() == 0:
            print("The query dataset id not found")
            raise HTTPException(500, "Something went wrong")
        return [query[0]["owner"]]
    for x in query[0]["args"]:
        if type(x) == str:
            owner_list = owner_list + find_owners(x, owner_list)
    return owner_list


@router.post("/publish/current_budget")
def publish_current_budget(
    background_tasks: BackgroundTasks,
    input: InputPublishRequestCurrentBudget,
    x_oblv_user_name: str = Header(default=None),
    x_oblv_user_role: str = Header(default=None)
):
    print("budget received called for {}".format(x_oblv_user_name))
    if x_oblv_user_role != "domain":
        raise HTTPException(403, f"Path only available for domain role.")
    request = [x for x in router.publish_queries if x["request_id"]==input.publish_request_id]
    if request.__len__()==0:
        raise HTTPException(400,"Publish request id not found")
    flag = False
    for x in request[0]["owners"]:
        if x["owner"]==x_oblv_user_name:
            flag = True
            x["current_budget"] = input.current_budget
            break
    background_tasks.add_task(
        check_all_budgets_received, input.publish_request_id)
    if flag:
        return "Success"
    else:
        raise HTTPException(400,"User not involved in the approval process")

@router.get("/publish/result_ready")
def publish_check_result_status(
    publish_request_id: str,
    x_oblv_user_name: str = Header(default=None),
    x_oblv_user_role: str = Header(default=None)
):
    request = [x for x in router.publish_queries if x["request_id"]==publish_request_id]
    if request.__len__()==0:
        raise HTTPException(400,"Publish request id not found")
    if request[0].get("error","")!="":
        raise HTTPException(400,request[0].get("error"))
    if request[0]["result"] is None:
        return "Result not yet ready"
    else:
        min_available_budget = min([x["current_budget"] for x in request[0]["owners"]])
        print([x["current_budget"] for x in request[0]["owners"]])
        print("Budget_needed : {}\nmin_available_budget: {}".format(request[0]["budget_needed"],min_available_budget))
        if request[0]["budget_needed"]>min_available_budget:
            raise HTTPException(400, "Not enough budget available. Ask the domain owners for more budget and request again.")
        return request[0]["budget_needed"]

@router.post("/publish/budget_deducted")
def publish_approval(
    input: InputPublishRequestApproval,
    x_oblv_user_name: str = Header(default=None),
    x_oblv_user_role: str = Header(default=None),
):
    if x_oblv_user_role != "domain":
        raise HTTPException(403, f"Path only available for user role.")
    request = [x for x in router.publish_queries if x["request_id"]==input.publish_request_id]
    if request.__len__()==0:
        raise HTTPException(400,"Publish request id not found")
    flag = False
    for x in request[0]["owners"]:
        if x["owner"]==x_oblv_user_name:
            flag = True
            if x["budget_deducted"]==True:
                return "Already Deducted"
            x["budget_deducted"] = input.budget_deducted
            break
    if flag:
        return "Success"
    else:
        raise HTTPException(400,"User not involved in the publish process")

PUBLISH_REQUEST_ID = ""

def get_budget_for_user(*args: Any, **kwargs: Any) -> float:
    return 999999

def deduct_epsilon_for_user(verify_key ,old_budget ,epsilon_spend) -> bool:
    for x in router.publish_queries:
        if x["request_id"]==PUBLISH_REQUEST_ID:
            x["budget_needed"] = epsilon_spend
    return True

@router.get("/publish/result")
def publish_result(
    request_id: str = Query(...),
    x_oblv_user_name: str = Header(default=None),
    x_oblv_user_role: str = Header(default=None),
):
    
    request = [x for x in router.publish_queries if x["request_id"]==request_id]
    if request.__len__()==0:
        raise HTTPException(400,"Publish request id not found")
    if not check_all_budgets_received(request_id,False):
        raise HTTPException(400, "Budgets not yet received from all the domains yet")
    if request[0]["result"] is None:
        raise HTTPException(400, "Result not yet ready")
    min_available_budget = min([x["current_budget"] for x in request[0]["owners"]])
    if request[0]["budget_needed"]>min_available_budget:
        raise HTTPException(400, "Not enough budget available. Ask the domain owners for more budget and request again.")
    if any(x["budget_deducted"] is False for x in request[0]["owners"]):
        raise HTTPException(400, "Budget not deducted from all owners yet")
    return request[0]["result"].tolist()








def prepare_result(publish_request_id):
    print("prepare result called")
    ## To calculate the result of the reqest
    global PUBLISH_REQUEST_ID
    for x in router.publish_queries:
        if x["request_id"]==publish_request_id:
            try:
                PUBLISH_REQUEST_ID = publish_request_id
                # print(x["dataset"])
                data = x["dataset"].publish(get_budget_for_user=get_budget_for_user, deduct_epsilon_for_user=deduct_epsilon_for_user, ledger=x["ledger"], sigma=x["sigma"],private=True)
                x["result"] = data
                print("result is set")
                PUBLISH_REQUEST_ID = ""
            except Exception as e:
                print(e)
                x["error"] = f"Failed to prepare the result for this request due to exception: {e}"
            
            # x["result"] = [1,2,3,4,5]
            # x["budget_needed"]=100
    
    return

def check_all_budgets_received(publish_request_id, prepare_result_bool = True):
    print("check_all_budgets_received called")
    request = [x for x in router.publish_queries if x["request_id"]==publish_request_id]
    if request.__len__()==0:
        # raise HTTPException(400,"Publish request id not found")
        print("False")
        return False
    for x in request[0]["owners"]:
        print(x["owner"] + ": "+str(x["current_budget"]))
        if x["current_budget"]==None:
            return False
    if prepare_result_bool == False:
        return True
    prepare_result(publish_request_id)

@router.delete("/all")
def clear_all():
    router.datasets = []
    router.data_owners = []
    router.uploaded_datasets = []
    router.result_datasets = []
    router.query_list = []
    router.publish_queries = []
    return
