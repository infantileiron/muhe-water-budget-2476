import type {BudgetResult} from '../types/domain';
import {number} from '../utils/format';
export function BudgetSummary({result}:{result:BudgetResult}){
 return <div className="budget-result">
  <div className={'budget-status '+(result.met?'ok':'gap')}>
   <b>{result.met?'达标 · 预算内总投入最低组合':'未达标 · 预算内最大节水组合'}</b>
   <span>{result.rule}</span>
  </div>
  <div className="budget-metrics">
   <div><small>预算金额 / 元</small><strong>{number(result.budget)}</strong></div>
   <div><small>总投入 / 元</small><strong>{number(result.total_cost)}</strong></div>
   <div><small>预算结余 / 元</small><strong>{number(result.budget_remaining)}</strong></div>
   <div><small>目标节水 / m³</small><strong>{number(result.target_saving)}</strong></div>
   <div><small>总节水 / m³</small><strong className={result.met?'':'warn'}>{number(result.total_saving)}</strong></div>
   <div><small>节水缺口 / m³</small><strong className={result.saving_gap>0?'warn':''}>{number(result.saving_gap)}</strong></div>
  </div>
  <div className="table-scroll">
   <table>
    <thead><tr><th>分区</th><th>报告期水量 / m³</th><th>入选方案</th><th>投入 / 元</th><th>节水量 / m³</th><th>节余后水量 / m³</th></tr></thead>
    <tbody>{result.decisions.map(d=><tr key={d.zone}>
     <td>{d.zone}</td><td>{number(d.baseline_water)}</td>
     <td>{d.option.startsWith('不选')?<span className="muted-opt">{d.option}</span>:d.option}</td>
     <td>{number(d.cost)}</td><td>{number(d.saving)}</td><td>{number(d.residual_water)}</td></tr>)}</tbody>
   </table>
  </div>
  <p className="caption">报告期 {result.period} 总水量 {number(result.baseline_total)} m³ · 金额与水量均按两位小数精确对账 · 求解时间 {result.solved_at.slice(0,19).replace('T',' ')}</p>
 </div>;
}
