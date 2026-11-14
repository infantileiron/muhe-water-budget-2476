import {useMemo,useState} from 'react';
import type {Workspace} from '../stores/workspace';
import type {BudgetPlan,BudgetResult} from '../types/domain';
import {PageHeading} from '../components/common/PageHeading';
import {Notice} from '../components/common/Notice';
import {Empty} from '../components/common/Empty';
import {BudgetSummary} from '../components/BudgetSummary';
import {useAsync} from '../hooks/useAsync';
import * as api from '../api/budgets';
import {number,date} from '../utils/format';
interface Draft{zone:string;name:string;cost:string;saving:string}
const blank:Draft={zone:'',name:'',cost:'',saving:''};
export function Budgets({data,canWrite,refresh}:{data:Workspace;canWrite:boolean;refresh:()=>Promise<void>}){
 const completed=data.runs.filter(r=>r.status==='completed');
 const [runId,setRunId]=useState('');
 const run=completed.find(r=>r.id===runId)||completed[0];
 const [planName,setPlanName]=useState('');
 const [budget,setBudget]=useState('1000');
 const [target,setTarget]=useState('10');
 const [note,setNote]=useState('');
 const [drafts,setDrafts]=useState<Draft[]>([{...blank}]);
 const [trial,setTrial]=useState<BudgetResult|null>(null);
 const [editingId,setEditingId]=useState<string|null>(null);
 const task=useAsync();
 const zones=useMemo(()=>run?run.result.observations.map(o=>o.zone):[],[run]);
 const baselineMap=useMemo(()=>{const m:Record<string,number>={};run?.result.observations.forEach(o=>{m[o.zone]=o.water_after});return m},[run]);
 const comparisonName=(id:string)=>data.comparisons.find(c=>c.id===id)?.name||id;
 function patch(i:number,key:keyof Draft,val:string){setDrafts(ds=>ds.map((d,j)=>j===i?{...d,[key]:val}:d))}
 function loadPlan(plan:BudgetPlan){
  setEditingId(plan.id);setPlanName(plan.name);setRunId(plan.run_id);
  setBudget(plan.budget.toFixed(2));setTarget(plan.target_saving.toFixed(2));setNote(plan.note);
  setDrafts(plan.candidates.map(c=>({zone:c.zone,name:c.name,cost:c.cost.toFixed(2),saving:c.saving.toFixed(2)})));
  setTrial(plan.result);
 }
 function resetForm(){
  setEditingId(null);setPlanName('');setBudget('1000');setTarget('10');setNote('');
  setDrafts([{...blank}]);setTrial(null);
 }
 function switchRun(id:string){
  setRunId(id);setTrial(null);
  if(editingId)resetForm();
 }
 function buildPayload():api.BudgetPayload|null{
  if(!run)return null;
  const candidates:api.BudgetPayload['candidates']=[];
  for(const d of drafts){
   if(!d.zone&&!d.name&&!d.cost&&!d.saving)continue;
   if(!d.zone||!d.name.trim()){task.fail('请补全候选方案的分区与名称');return null}
   const cost=Number(d.cost),saving=Number(d.saving);
   if(!Number.isFinite(cost)||!Number.isFinite(saving)){task.fail('投入与节水量必须是有效数字');return null}
   candidates.push({zone:d.zone,name:d.name.trim(),cost,saving});
  }
  const b=Number(budget),t=Number(target);
  if(!Number.isFinite(b)||!Number.isFinite(t)){task.fail('预算与目标必须是有效数字');return null}
  if(!candidates.length){task.fail('请至少录入一个分区候选方案');return null}
  return {name:planName.trim()||('预算节水方案 · '+(run.result.period_after)),run_id:run.id,budget:b,target_saving:t,candidates,note:note.trim()};
 }
 const doTrial=()=>task.execute(async()=>{const p=buildPayload();if(p)setTrial(await api.trial(p))});
 const doSave=()=>task.execute(async()=>{
  const p=buildPayload();if(!p)return;
  const saved=editingId?await api.update(editingId,p):await api.create(p);
  setEditingId(saved.id);setTrial(saved.result);await refresh();
 });
 const editingPlan=data.budgets.find(b=>b.id===editingId)||null;
 return <>
  <PageHeading label="06 / BUDGET WATER PLAN" title="预算内达标，取总投入最低的组合。">以已完成分解的报告期分区水量为基准，录入各区候选投入与节水量，每区最多选一项。<br/>达不到时给出预算内最大节水与缺口；金额和水量按两位小数对账。</PageHeading>
  {!completed.length?<Empty>请先完成一次两期分解，再据此编制预算节水方案。</Empty>:<>
  <section className="paper">
   <div className="section-heading"><h2>{editingId?'修订预算方案':'编制预算节水方案'}</h2>
    <div className="filters">
     <select aria-label="选择已完成分解" value={run?.id||''} onChange={e=>switchRun(e.target.value)}>
      {completed.map(r=><option key={r.id} value={r.id}>{comparisonName(r.comparison_id)} · 报告期 {r.result.period_after}</option>)}
     </select>
     {editingId&&<button type="button" className="secondary" onClick={resetForm}>＋ 新建方案</button>}
    </div>
   </div>
   <div className="data-caption"><b>基准：报告期 {run?.result.period_after} 分区水量（只读，来自已归档口径的分解）</b><span>{zones.length} 个分区</span><span>总量 {number(run?.result.water_after)} m³</span></div>
   <div className="baseline-chips">{zones.map(z=><span key={z} className="chip">{z}<b>{number(baselineMap[z])}</b>m³</span>)}</div>
   {canWrite?<form className="budget-form" onSubmit={e=>{e.preventDefault();doTrial()}}>
    <div className="grid-form">
     <label>方案名称<input value={planName} onChange={e=>setPlanName(e.target.value)} placeholder="如：2026年四季度节水预算组合" minLength={2}/></label>
     <label>说明（可选）<input value={note} onChange={e=>setNote(e.target.value)} placeholder="口径与适用范围"/></label>
     <label>预算金额 / 元<input inputMode="decimal" value={budget} onChange={e=>setBudget(e.target.value)} aria-label="预算金额"/></label>
     <label>目标节水量 / m³<input inputMode="decimal" value={target} onChange={e=>setTarget(e.target.value)} aria-label="目标节水量"/></label>
    </div>
    <h3 className="candidate-title">分区候选方案（每区可录多项，择优时每区最多选一项）</h3>
    <div className="candidate-rows">
     {drafts.map((d,i)=><div className="candidate-row" key={i}>
      <select aria-label="分区" value={d.zone} onChange={e=>patch(i,'zone',e.target.value)}>
       <option value="">选择分区</option>{zones.map(z=><option key={z} value={z}>{z}（基准 {number(baselineMap[z])}）</option>)}
      </select>
      <input aria-label="方案名称" value={d.name} onChange={e=>patch(i,'name',e.target.value)} placeholder="方案名称"/>
      <input aria-label="投入金额" inputMode="decimal" value={d.cost} onChange={e=>patch(i,'cost',e.target.value)} placeholder="投入 / 元"/>
      <input aria-label="节水量" inputMode="decimal" value={d.saving} onChange={e=>patch(i,'saving',e.target.value)} placeholder="节水 / m³"/>
      <button type="button" className="secondary row-del" disabled={drafts.length===1} onClick={()=>setDrafts(ds=>ds.filter((_,j)=>j!==i))}>删</button>
     </div>)}
    </div>
    <button type="button" className="secondary add-cand" onClick={()=>setDrafts(ds=>[...ds,{...blank}])}>＋ 添加候选方案</button>
    {task.error&&<Notice error>{task.error}</Notice>}
    <div className="form-actions">
     <button type="submit" disabled={task.busy}>试算（不保存）</button>
     <button type="button" className="secondary" disabled={task.busy} onClick={doSave}>{editingId?'保存修订并留痕':'保存方案'}</button>
     {editingPlan&&<button type="button" className="secondary" disabled={task.busy} onClick={()=>task.execute(()=>api.downloadPlan(editingPlan.id))}>导出明细 CSV　↓</button>}
    </div>
   </form>:<Notice>只读账号可查看已保存方案与下载明细，录入与试算需分析员或管理员。</Notice>}
  </section>
  {trial&&<section className="paper"><h2>{editingId?'当前试算结果':'试算结果'}</h2><BudgetSummary result={trial}/></section>}
  {editingPlan&&editingPlan.history.length>0&&<section className="paper">
   <h2>预算调整留痕 · 旧方案与依据保留</h2>
   <p className="caption">修改预算、目标或候选并保存后重算；下表逐次保留调整前的方案组合、投入、节水与缺口，原分解与归档报告不变。</p>
   <div className="table-scroll"><table>
    <thead><tr><th>调整时间</th><th>当时预算 / 元</th><th>当时目标 / m³</th><th>是否达标</th><th>当时总投入 / 元</th><th>当时总节水 / m³</th><th>节水缺口 / m³</th></tr></thead>
    <tbody>{[...editingPlan.history].reverse().map((h,i)=><tr key={i}>
     <td>{date(h.changed_at)}</td><td>{number(h.budget)}</td><td>{number(h.target_saving)}</td>
     <td><span className={'status '+(h.result.met?'accepted':'failed')}>{h.result.met?'达标':'未达标'}</span></td>
     <td>{number(h.result.total_cost)}</td><td>{number(h.result.total_saving)}</td><td>{number(h.result.saving_gap)}</td></tr>)}</tbody>
   </table></div>
  </section>}
  <section className="paper">
   <h2>已保存的预算方案</h2>
   {data.budgets.length?data.budgets.map(p=><article className="report-row" key={p.id}>
    <div><h3>{p.name}</h3><small>{date(p.updated_at)} · {p.created_by} · 报告期 {p.period} · 留痕 {p.history.length} 次</small>
     <p className="caption" style={{marginTop:8}}>{p.result.met?'达标组合':'未达标（最大节水）'}：总投入 {number(p.result.total_cost)} 元 / 总节水 {number(p.result.total_saving)} m³ / 缺口 {number(p.result.saving_gap)} m³</p></div>
    <div className="row-actions">
     {canWrite&&<button className="secondary" disabled={task.busy} onClick={()=>loadPlan(p)}>修订 / 重算</button>}
     <button className="secondary" disabled={task.busy} onClick={()=>task.execute(()=>api.downloadPlan(p.id))}>导出 CSV　↓</button>
    </div></article>):<Empty>录入候选方案并试算后，保存为可追溯、可导出的预算节水组合。</Empty>}
  </section>
  </>}
 </>;
}
