from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from src.config.database import db_session
from src.controllers.auth import current_user,writer
from src.models import BudgetPlan
from src.schemas.budget import BudgetPlanInput,BudgetPlanUpdate
from src.services import budgets as service
from src.utils.serialization import rows,serialize
router=APIRouter(prefix="/budgets")
@router.get("")
def listing(db=Depends(db_session),user=Depends(current_user)):
 return rows(db.scalars(select(BudgetPlan).order_by(BudgetPlan.updated_at.desc())))
@router.post("/trial")
def trial(payload:BudgetPlanInput,db=Depends(db_session),user=Depends(writer)):
 return service.trial(db,payload)
@router.post("")
def create(payload:BudgetPlanInput,db=Depends(db_session),user=Depends(writer)):
 return service.create(db,payload,user)
@router.get("/{id}")
def detail(id:str,db=Depends(db_session),user=Depends(current_user)):
 item=db.get(BudgetPlan,id)
 if not item:
  raise HTTPException(404,"预算方案不存在")
 return serialize(item)
@router.put("/{id}")
def update(id:str,payload:BudgetPlanUpdate,db=Depends(db_session),user=Depends(writer)):
 return service.update(db,id,payload,user)
@router.get("/{id}/csv")
def download(id:str,db=Depends(db_session),user=Depends(current_user)):
 return Response(service.export(db,id),media_type="text/csv; charset=utf-8",
  headers={"Content-Disposition":"attachment; filename=budget-water-plan.csv"})
