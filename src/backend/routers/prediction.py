import logging

from fastapi import APIRouter, Request, Response, status

from backend.agent.graph import compiled_graph
from backend.agent.prompt import SYSTEM_PROMPT
from backend.api_schema import ChatRequest, ChatResponse, ErrorResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={
        status.HTTP_200_OK: {"description": "Success", "model": ChatResponse},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Unprocessable Entity"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal Server Error",
            "model": ErrorResponse,
        },
    },
)


@router.post(
    "/ask_agent",
    description="Chat with the data analyst agent",
    status_code=status.HTTP_200_OK,
)
def ask_agent(request: Request, body: ChatRequest, response: Response):
    # Check if the first message is a system message
    if body.messages[0]["role"] != "system":
        body.messages = [{"role": "system", "content": SYSTEM_PROMPT}] + body.messages

    result = compiled_graph.invoke(
        {
            "messages": body.messages,
            "data": None,
            "visual_created": body.visual_created,
            "follow_up_question": body.follow_up_question,
        },
        {"recursion_limit": 50},
    )
    response = ChatResponse(
        messages=result["messages"],
        result=result["messages"][-1].content,
        follow_up_question=result["follow_up_question"],
    )
    return response


# @router.post(
#     "/get_item_ledgercode/",
#     description="Get ledger code as per item from a receipt",
#     status_code=status.HTTP_200_OK,
# )
# def predict_ledgercode(request: Request, body: PredictionRequest, response: Response):
#     pipeline = request.app.state.model

#     try:
#         # accountvalue, vatpercent, bodyid, name_bse
#         bodyid = body.sessionInfo.companyId
#         name_bse = body.transactionDetails.businessName.candidates[0].value
#         accountvalue = (
#             body.transactionDetails.priceRows.candidates[0].value[0].vatIncludedPrice
#         )
#         vat_percent = body.transactionDetails.priceRows.candidates[0].value[0].taxRate

#         account_values = [
#             price_row.vatIncludedPrice
#             for price_row in body.transactionDetails.priceRows.candidates[0].value
#         ]
#         vat_percentages = [
#             price_row.taxRate
#             for price_row in body.transactionDetails.priceRows.candidates[0].value
#         ]
#         n_predictions = len(account_values)

#         object_id = str(uuid.uuid4().hex)
#         object_ids = [object_id for _i in range(n_predictions)]
#         prediction_ids = [str(uuid.uuid4().hex) for x in range(n_predictions)]

#         X = pd.DataFrame(
#             {
#                 "accountvalue": account_values,
#                 "vatpercent": vat_percentages,
#                 "bodyid": [bodyid] * n_predictions,
#                 "name_bse": [name_bse] * n_predictions,
#                 "object_id": object_ids,
#                 "prediction_id": prediction_ids,
#             }
#         )

#         X_transformed = pipeline.named_steps["preprocessor"].transform(X)

#         results = pipeline.named_steps["classifier"].predict_company_code(
#             X_transformed, X
#         )
#         predictions = []
#         for _i, items in enumerate(
#             zip(results, object_ids, prediction_ids, strict=True)
#         ):
#             suggestions = []
#             for result_item in items[0]:
#                 price_row_obj = PriceRowPredction(
#                     prediction_id=items[2],
#                     object_id=items[1],
#                     vatIncludedPrice=accountvalue,
#                     taxRate=vat_percent,
#                     ledger_code=result_item["pred"],
#                     confidence=result_item["confidence"],
#                 )
#                 suggestions.append(price_row_obj)
#             predictions.append(suggestions)

#     except ValidationError as e:
#         response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#         return ErrorResponse(DETAIL=str(e))
#     except CoAForBodyidNotFound as e:
#         response.status_code = status.HTTP_501_NOT_IMPLEMENTED
#         return ErrorResponse(DETAIL=str(e))

#     response = PredictionResponse(prediction=predictions)

#     return response
