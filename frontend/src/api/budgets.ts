import {request,post} from './client';import type {BudgetPlan,BudgetResult} from '../types/domain';
export interface BudgetPayload{name:string;run_id:string;budget:number;target_saving:number;candidates:{zone:string;name:string;cost:number;saving:number}[];note:string}
export const list=()=>request<BudgetPlan[]>('/budgets');
export const trial=(data:BudgetPayload)=>post<BudgetResult>('/budgets/trial',data);
export const create=(data:BudgetPayload)=>post<BudgetPlan>('/budgets',data);
export const update=(id:string,data:BudgetPayload)=>request<BudgetPlan>('/budgets/'+id,{method:'PUT',body:JSON.stringify(data)});
export async function downloadPlan(id:string){
 const r=await fetch('/api/budgets/'+id+'/csv',{headers:{Authorization:'Bearer '+localStorage.getItem('mix-token')}});
 if(!r.ok)throw new Error('下载失败');
 const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download='budget-water-plan.csv';a.click();URL.revokeObjectURL(url);
}
