import uuid,csv,io
from sqlalchemy import select
from fastapi import HTTPException
from src.models import BudgetPlan
from src.services.runs import require_completed
from src.utils.time import now
from src.utils.serialization import serialize
from src.utils.csv import safe_cell
from src.utils import decimals as D
from src.services.budget_solver import solve
DO_NOTHING="不选（维持现状）"
def baseline_from_run(run):
 return {o["zone"]:D.baseline_water(o["water_after"],"报告期水量") for o in run.result["observations"]}
def raw_baseline_from_run(run):
 return {o["zone"]:D.raw_decimal(o["water_after"],"报告期水量") for o in run.result["observations"]}
def _reject_unknown_zones(payload,known):
 unknown=sorted({c.zone for c in payload.candidates if c.zone not in known})
 if unknown:
  raise HTTPException(422,"存在未知分区 "+"、".join(unknown)+"，整批拒绝")
def _validated(payload,baseline,raw_baseline):
 budget=D.money(payload.budget,"预算")
 target=D.water(payload.target_saving,"目标节水量")
 groups=[];seen=set()
 for zone,cap in baseline.items():
  if zone in seen:
   raise HTTPException(422,f"分区{zone}重复")
  seen.add(zone)
  options=[{"key":zone,"name":DO_NOTHING,"cost":0,"saving":0}]
  names={DO_NOTHING}
  for cand in payload.candidates:
   if cand.zone!=zone:
    continue
   cost=D.money(cand.cost,f"{zone}·方案投入")
   saving=D.water(cand.saving,f"{zone}·方案节水量")
   if D.quantize_two(D.Decimal(str(cand.saving)))>raw_baseline[zone]:
    raise HTTPException(422,f"{zone}的方案「{cand.name}」节水量 {cand.saving:.2f} 超过该分区报告期原水量 {D.to_float(cap):.2f}，整批拒绝")
   if cand.name in names:
    raise HTTPException(422,f"{zone}存在同名方案「{cand.name}」，整批拒绝")
   names.add(cand.name)
   options.append({"key":zone,"name":cand.name,"cost":cost,"saving":saving})
  groups.append(options)
 if not groups:
  raise HTTPException(422,"没有可用分区基准，无法试算")
 return budget,target,groups
def _build_result(run,groups,budget,target,baseline):
 outcome=solve(groups,budget,target)
 decisions=[]
 for grp in groups:
  zone=grp[0]["key"];cap=baseline[zone]
  chosen=next((s for s in outcome["selections"] if s["key"]==zone),grp[0])
  decisions.append({"zone":zone,"baseline_water":D.to_float(cap),"option":chosen["name"],
   "cost":D.to_float(chosen["cost"]),"saving":D.to_float(chosen["saving"]),
   "residual_water":D.to_float(cap-chosen["saving"])})
 total_baseline=sum(baseline.values())
 return {"solved_at":now(),"period":run.result["period_after"],"met":outcome["met"],
  "budget":D.to_float(budget),"target_saving":D.to_float(target),
  "total_cost":D.to_float(outcome["total_cost"]),"total_saving":D.to_float(outcome["total_saving"]),
  "budget_remaining":D.to_float(budget-outcome["total_cost"]),
  "saving_gap":D.to_float(max(0,target-outcome["total_saving"])),
  "baseline_total":D.to_float(total_baseline),"decisions":decisions,
  "rule":("预算内达成目标，取总投入最低；同投入按总节水量更高、再按分区选择字典序稳定取舍。" if outcome["met"]
   else "预算内无法达成目标，取预算内最大总节水量，并给出距目标的节水缺口。")}
def _persisted_candidates(payload):
 return [{"zone":c.zone,"name":c.name,"cost":float(c.cost),"saving":float(c.saving)} for c in payload.candidates]
def prepare(run,payload):
 baseline=baseline_from_run(run)
 raw_baseline=raw_baseline_from_run(run)
 _reject_unknown_zones(payload,set(baseline))
 budget,target,groups=_validated(payload,baseline,raw_baseline)
 result=_build_result(run,groups,budget,target,baseline)
 return baseline,budget,target,result
def create(db,payload,user):
 run=require_completed(db,payload.run_id)
 if db.scalar(select(BudgetPlan).where(BudgetPlan.name==payload.name)):
  raise HTTPException(409,"预算方案名称已存在")
 baseline,budget,target,result=prepare(run,payload)
 plan=BudgetPlan(id=str(uuid.uuid4()),name=payload.name,run_id=run.id,period=run.result["period_after"],
  budget=D.to_float(budget),target_saving=D.to_float(target),
  baseline=[{"zone":z,"water_after":D.to_float(v)} for z,v in baseline.items()],
  candidates=_persisted_candidates(payload),result=result,history=[],note=payload.note,
  created_by=user["email"],created_at=now(),updated_at=now())
 db.add(plan);db.commit();return serialize(plan)
def _snapshot(plan):
 return {"budget":plan.budget,"target_saving":plan.target_saving,"result":plan.result,"changed_at":plan.updated_at}
def update(db,id,payload,user):
 plan=db.get(BudgetPlan,id)
 if not plan:
  raise HTTPException(404,"预算方案不存在")
 run=require_completed(db,plan.run_id)
 baseline,budget,target,new_result=prepare(run,payload)
 recalc=(budget!=D.money(plan.budget,"旧预算")
  or target!=D.water(plan.target_saving,"旧目标")
  or _candidates_changed(plan,payload))
 history=list(plan.history)
 if recalc:
  history.append(_snapshot(plan));history=history[-50:]
  result=new_result
 else:
  result=plan.result
 plan.name=payload.name;plan.budget=D.to_float(budget);plan.target_saving=D.to_float(target)
 plan.candidates=_persisted_candidates(payload);plan.result=result;plan.history=history
 plan.note=payload.note;plan.updated_at=now()
 db.commit();return serialize(plan)
def _candidates_changed(plan,payload):
 old=sorted((c["zone"],c["name"],D.money(c["cost"],"旧投入"),D.water(c["saving"],"旧节水")) for c in plan.candidates)
 new=sorted((c.zone,c.name,D.money(c.cost,"投入"),D.water(c.saving,"节水")) for c in payload.candidates)
 return old!=new
def trial(db,payload):
 run=require_completed(db,payload.run_id)
 return prepare(run,payload)[3]
def export(db,id):
 plan=db.get(BudgetPlan,id)
 if not plan:
  raise HTTPException(404,"预算方案不存在")
 buf=io.StringIO();w=csv.writer(buf);r=plan.result
 w.writerow(["沐禾园区预算节水方案明细"])
 w.writerow(["方案名称",safe_cell(plan.name),"报告期",r["period"],"求解时间",r["solved_at"]])
 w.writerow(["预算金额(元)",f"{plan.budget:.2f}","目标节水量(m3)",f"{plan.target_saving:.2f}","是否达标","是" if r["met"] else "否"])
 w.writerow(["总投入(元)",f'{r["total_cost"]:.2f}',"总节水量(m3)",f'{r["total_saving"]:.2f}',"预算结余(元)",f'{r["budget_remaining"]:.2f}'])
 w.writerow(["节水缺口(m3)",f'{r["saving_gap"]:.2f}',"报告期总水量(m3)",f'{r["baseline_total"]:.2f}',"择优口径",safe_cell(r["rule"])])
 w.writerow([])
 w.writerow(["分区","报告期水量(m3)","入选方案","投入(元)","节水量(m3)","节余后水量(m3)"])
 for d in r["decisions"]:
  w.writerow([safe_cell(d["zone"]),f'{d["baseline_water"]:.2f}',safe_cell(d["option"]),f'{d["cost"]:.2f}',f'{d["saving"]:.2f}',f'{d["residual_water"]:.2f}'])
 if plan.history:
  w.writerow([]);w.writerow(["预算调整留痕（保留旧方案及依据）"])
  w.writerow(["调整时间","当时预算(元)","当时目标(m3)","是否达标","当时总投入(元)","当时总节水(m3)","节水缺口(m3)"])
  for h in plan.history:
   hr=h["result"]
   w.writerow([h["changed_at"],f'{h["budget"]:.2f}',f'{h["target_saving"]:.2f}',"是" if hr["met"] else "否",f'{hr["total_cost"]:.2f}',f'{hr["total_saving"]:.2f}',f'{hr["saving_gap"]:.2f}'])
 return "\ufeff"+buf.getvalue()
