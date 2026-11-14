import random,math,json
from sqlalchemy import select,func
from src.config.database import Base,engine,Session
from src.models import User,ConsumptionDataset,PeriodComparison,DecompositionRun,DriverReview,PublishedReport,BudgetPlan
from src.services.analysis import analyze
from src.services import budgets as budget_service
from src.schemas.budget import BudgetPlanInput,CandidateInput
from src.utils.security import hash_password
from src.utils.time import now
def seed():
 Base.metadata.create_all(engine)
 with Session() as db:
  for role in ("admin","analyst","viewer"):
   if not db.get(User,role):db.add(User(id=role,email=role+"@muhe.demo",password=hash_password("Water2026!"),role=role))
  rng=random.Random(2209);zones=["研发东区","研发西区","试制中心","装配区","后勤区","培训楼","配套区","检验区"];rows=[]
  for m in range(24):
   index=2024*12+10+m;year,month=divmod(index,12);period=f"{year}-{month+1:02}"
   for i,z in enumerate(zones):
    scale=round((1800+i*170)*(1+.012*m)*(1+.06*math.sin(m/2+i))+rng.uniform(-50,50),2)
    intensity=(.085+i*.016)*(1-.004*m)*(1+.08*math.cos(m/3+i))
    rows.append({"zone":z,"period":period,"scale":scale,"water":round(scale*intensity,3)})
  if not db.get(ConsumptionDataset,"demo-data"):db.add(ConsumptionDataset(id="demo-data",name="沐禾园区·24月分区水量与作业规模",source="muhe_water_202411_202610.json",rows=rows,created_at=now()));db.flush()
  if not db.get(PeriodComparison,"demo-comparison"):db.add(PeriodComparison(id="demo-comparison",name="2026年9月至10月·口径一致对照",dataset_id="demo-data",period_before="2026-09",period_after="2026-10",created_at=now()));db.flush()
  if not db.get(DecompositionRun,"demo-run"):db.add(DecompositionRun(id="demo-run",comparison_id="demo-comparison",status="completed",result=analyze(rows,"2026-09","2026-10"),error="",created_at=now()));db.flush()
  if not db.get(DriverReview,"demo-review"):db.add(DriverReview(id="demo-review",run_id="demo-run",note="两期均含8个分区，规模采用有效作业人日。归因是恒等式分解，不能直接当作节水措施的因果证据。",decision="accepted",author="analyst@muhe.demo",created_at=now()));db.flush()
  if not db.get(PublishedReport,"demo-report"):db.add(PublishedReport(id="demo-report",run_id="demo-run",title="10月用水结构·驱动复核年鉴",published_by="admin@muhe.demo",created_at=now()))
  if not db.get(BudgetPlan,"demo-budget"):
   demo_run=db.get(DecompositionRun,"demo-run")
   demo_candidates=[
    ("研发东区","节水器具改造",120.0,25.0),("研发东区","漏损巡检修复",70.0,18.0),
    ("研发西区","冷却水循环",180.0,40.0),("研发西区","计量分区改造",90.0,22.0),
    ("试制中心","工艺水循环",260.0,60.0),("试制中心","高压清洗替代",140.0,35.0),
    ("装配区","节水龙头与喷淋",80.0,20.0),("装配区","中水回用",220.0,55.0),
    ("后勤区","绿化滴灌",60.0,15.0),("后勤区","雨水收集",160.0,38.0),
    ("培训楼","节水洁具全覆盖",110.0,28.0),
    ("配套区","锅炉冷凝水回收",240.0,58.0),("配套区","夜间调压减漏",100.0,26.0),
    ("检验区","纯水机尾水回收",200.0,48.0),("检验区","清洗工艺优化",130.0,32.0)]
   payload=BudgetPlanInput(name="2026年四季度·预算节水组合",run_id="demo-run",budget=1200.0,target_saving=180.0,
    candidates=[CandidateInput(zone=z,name=n,cost=c,saving=s) for z,n,c,s in demo_candidates],
    note="以2026-10报告期分区水量为基准的演示候选，金额与水量均按两位小数对账；分解与归档报告保持不变。")
   _,budget_scaled,target_scaled,result=budget_service.prepare(demo_run,payload)
   db.add(BudgetPlan(id="demo-budget",name=payload.name,run_id="demo-run",period=demo_run.result["period_after"],
    budget=budget_service.D.to_float(budget_scaled),target_saving=budget_service.D.to_float(target_scaled),
    baseline=[{"zone":z,"water_after":v} for z,v in budget_service.baseline_from_run(demo_run).items()],
    candidates=[{"zone":z,"name":n,"cost":c,"saving":s} for z,n,c,s in demo_candidates],
    result=result,history=[],note=payload.note,created_by="analyst@muhe.demo",created_at=now(),updated_at=now()))
  db.commit();return {m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in (User,ConsumptionDataset,PeriodComparison,DecompositionRun,DriverReview,PublishedReport,BudgetPlan)}
if __name__=="__main__":print(json.dumps(seed(),ensure_ascii=False))
