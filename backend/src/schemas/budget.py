from pydantic import BaseModel,Field,model_validator
LIMIT=10**12
class CandidateInput(BaseModel):
 zone:str=Field(min_length=1,max_length=60)
 name:str=Field(min_length=1,max_length=80)
 cost:float=Field(ge=0,le=LIMIT,allow_inf_nan=False)
 saving:float=Field(ge=0,le=LIMIT,allow_inf_nan=False)
class BudgetPlanInput(BaseModel):
 name:str=Field(min_length=2,max_length=120)
 run_id:str
 budget:float=Field(ge=0,le=LIMIT,allow_inf_nan=False)
 target_saving:float=Field(ge=0,le=LIMIT,allow_inf_nan=False)
 candidates:list[CandidateInput]=Field(min_length=1,max_length=2000)
 note:str=Field(default="",max_length=500)
 @model_validator(mode="after")
 def one_row_per_zone_option(self):
  keys=[(c.zone,c.name) for c in self.candidates]
  if len(keys)!=len(set(keys)):
   raise ValueError("同一分区存在重复方案，整批拒绝")
  return self
class BudgetPlanUpdate(BudgetPlanInput):
 pass
