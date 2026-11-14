# 沐禾园区 · 用水结构贡献拆解

给沐禾园区10人节水分析组使用的两期驱动复核年鉴。把总用水变化拆为总规模、分区占比与单位强度三部分，分别运行精确Shapley与加法LMDI，保留闭合残差、分区结果、人工意见和CSV归档；并在已完成分解的报告期分区水量之上，做预算约束下的节水方案择优（每区至多一项、两位小数精确对账、等价解稳定、预算调整留痕）。

## 场景与工作日

团队以前在多张Excel里只看用水总量同比。三个痛点是占比变化与单位强度混淆、分解剩余项解释不清、规模和分区口径修改没有记录。上游是分区月度水表和有效作业人日，系统替代口径核查、三因子拆解和复核归档，下游由节水分析组讨论调查方向，不直接声称措施的因果效果。

09:00分析员登录；09:03查阅 muhe_water_202411_202610.json 的8分区×24月=192条模拟观测；09:08选择2026-09和2026-10；09:10服务端核对分区集合、正值和单位；09:12提交后台双方法分解；09:15查看规模/结构/强度瀑布图和闭合残差；09:18切换LMDI并逐区核对；09:22记录人日口径和因果解释边界；09:27管理员接受最新复核后归档；09:30只读复核员下载两种方法共16行分区贡献CSV。

|角色|页面|权限和典型动作|
|---|---|---|
|admin|全部|读写、运行、复核、批准归档|
|analyst|分区观测/两期对照/贡献拆解/驱动复核|导入、建对照、排队运行、提交意见；禁止批准归档|
|viewer|全部只读与报告下载|查看贡献、核对CSV；任何写入后端403|

## 启动与账号

```sh
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```

前端 http://localhost:18218 ，后端 http://localhost:19218/docs ，PostgreSQL映射17718。账号：admin@muhe.demo、analyst@muhe.demo、viewer@muhe.demo，演示密码均为 `Water2026!`。JWT开发密钥应在部署前替换。

五服务frontend/backend/worker/db/redis恰好各一，全部healthcheck。backend依赖PG/Redis健康，worker再等待backend种子完成，frontend等待backend。三命名卷保存PG、Redis AOF和worker心跳产物。结束演示执行 `docker compose down -v --remove-orphans`，会清除本项目演示数据。

SEED_DEMO=true首次建表并填充，固定ID/自然键查重，重跑不会新增或覆盖用户修改。种子由固定seed2209生成2024-11至2026-10的24月×8分区，含真实计算完成的2026-09→10月对照与复核归档，并额外生成一个以2026-10分区水量为基准的演示预算节水方案 `demo-budget`（8分区15个候选，预算1200元、目标180m³）。8分区为研发东区、研发西区、试制中心、装配区、后勤区、培训楼、配套区、检验区。所有数据仅为模拟。

## 实体与功能

ConsumptionDataset保存月份/分区/规模/用水；PeriodComparison固定数据集和两期；DecompositionRun由Redis队列驱动并持久化状态、结果、校验码；DriverReview保留人工判断与解释边界；PublishedReport仅在最新复核为accepted后由admin批准，run唯一；BudgetPlan以某次已完成分解的报告期分区水量为只读基准，保存预算、目标节水量、各分区候选投入与节水、择优结果和预算调整留痕。操作留痕记录操作者、接口、状态和时间，不保存密码、令牌或数据正文。

七业务页：年鉴总览、分区观测、两期对照、贡献拆解、驱动复核、预算节水、操作留痕。两方法可切换瀑布图与逐区贡献，另外展示实际规模/占比/强度、占比和与科学记数法闭合残差。观测页按月份完整展示当月所有分区；空状态提示下一步、错误可以修正重试，提供768/390响应式布局。预算节水页支持试算、保存、修订重算与CSV明细导出。

## 口径与两个算法

设规模为各分区有效作业人日之和S，各区占比 `w_i = s_i/S`，单位用水强度 `I_i=q_i/s_i`，则 `Q=S×Σ(w_i I_i)`，量纲为m³。两期分区必须完全一致；规模和水量必须有限且严格为正，不补零、不剔区、不加epsilon。重复分区月份拒绝。同月不能建立对照，不同月数值相同会真实得到零贡献。

**Shapley三因子**：枚举规模/结构/强度的全部6个排列。从基期开始按排列替换为报告期因素，逐步记录总量与各区的边际变化；每一因子取6个边际变化平均。交互项按该对称口径分摊，三项总和等于总变化，逐区也闭合。

**加法LMDI**：各区用水q_i的对数均值 `L(a,b)=(a-b)/(ln a-ln b)`；a=b取极限a，近等值采用log1p稳定计算。各因子贡献为 `Σ_i L(q_i1,q_i0)×ln(f_i1/f_i0)`，其中f为总规模S、区占比w_i或单位强度I_i。三项贡献之和等于总变化。前后互换各项反号。零负不在本题定义域，直接拒绝。

输出包含基期/报告期水量与规模、两期占比和、总变化、两方法三因子贡献、逐区贡献与闭合残差 `ΔQ-Σ贡献`。浮点残差保留原值，不强行修正为0；前端只负责画真实结果，不在浏览器重新计算贡献。

可复现：相同观测JSON校验码与两期月份给出确定性结果，两算法没有随机参数。输入最多5000条，每个规模/水量≤10亿。导入拒绝0/负/非有限值及重复分区月份；对照拒绝空月份、错区、相同月份；计算再次校验。队列异常和运行错误保留可见状态，可重新创建运行。

## 预算节水择优

以一次**已完成分解**的报告期分区水量作为只读基准（取分区 `observations.water_after`，分解与归档报告本身不被修改）。每个分区可录入若干候选方案（投入金额、节水量），求解时每区最多选一项，并始终保留成本0、节水0的"不选（维持现状）"。

精确对账：金额与节水量统一用 `Decimal` 解析，最多两位小数，内部按"分"和"百分之一立方米"的整数做分组背包，避免浮点误差；所有合计、结余、缺口都按两位小数 HALF_UP 输出。分区节水量不得超过该分区报告期**真实原水量**（保留来源全精度校验，再以两位口径参与求解）。未知分区、超原水量、非有限值、负值、超过两位小数、同分区同名方案，任一不合法即整批 422 拒绝，不写入任何半成品。

择优口径（确定性、等价解稳定）：在预算内枚举各精确总成本的最优组合。若存在总节水≥目标的组合，判定达标，取**总投入最低**，同投入取总节水更高，再按分区选择向量字典序稳定取舍；若预算内无法达标，给出预算内**最大总节水**组合与距目标的节水缺口，同节水取成本更低、再按同一字典序稳定。相同输入反复求解结果一致，不依赖字典或集合遍历顺序。

`BudgetPlan` 保存预算、目标、基准快照、候选、最新结果与 `history`。修改预算、目标或候选并保存时重算，并把调整前的预算、目标、完整结果（组合/投入/节水/缺口/依据）追加到留痕（最多保留50次）；仅改名称或说明不重算、不产生留痕。页面可试算（不落库）、保存、修订重算，并导出含汇总、逐区明细与调整留痕的CSV（带BOM，公式型文本加引号防注入）。viewer 只读可查看与下载，写入接口对 viewer 返回403。

## 技术与开发

|部分|技术|
|---|---|
|前端|React18.3、TypeScript5.7、Vite6、Nginx1.28|
|后端|Python3.11、FastAPI、SQLAlchemy、PyJWT|
|持久化|PostgreSQL16|
|队列|Redis7.4持久化列表、独立Python worker|

frontend/src包含api、stores、types、components/common、hooks、pages、router、utils、constants；backend/src包含routes、controllers、services、models、schemas、middlewares、utils、constants、config；backend/scripts为seed，backend/migrations说明初次模型建表。源码不含截图/日志/TESTING，这些在批次test-artifacts/gb-2209。

本地后端：安装requirements.txt，配置DATABASE_URL/REDIS_URL/JWT_SECRET，在backend执行`uvicorn src.main:app --reload`，另开`python -m src.worker`。前端：`npm ci && npm run dev`；开发时为/api配置指向19218的同源反向代理，Docker默认Nginx已处理前缀。锁文件固定构建依赖，Docker使用npm ci。

环境变量：COMPOSE_PROJECT_NAME=mix-contribution；FRONTEND_PORT=18218；BACKEND_PORT=19218；DB_PORT=17718；JWT_SECRET；SEED_DEMO。DATABASE_URL与REDIS_URL由Compose注入。`.env`忽略，`.env.example`可复制。

共享枚举：角色和运行状态在backend/src/constants/enums.py与frontend/src/constants/enums.ts，权限在controllers/auth.py，运行状态由services/runs.py/worker.py更新、Status组件消费；因子scale/structure/intensity在两端constants同名定义，Shapley/LMDI与Waterfall/ContributionTable消费；复核decision在schemas/review.py与frontend/constants，Reviews页消费。

## 已知边界

这是恒等式分解，不是因果估计；天气、工艺变化、抄表误差等需人工核查。Shapley与LMDI对交互分摊不同，不能跨方法拼接贡献。只接受正值；真实零量场景须另行设计零值分解规则。当前JSON表单导入，无CSV解析器。worker适合单实例，启动恢复queued/running，未实现分布式租约。初次由SQLAlchemy建表，没有生产迁移回滚。Google Fonts加载Noto Sans SC/Noto Serif SC，不可访问时浏览器字体回退。

预算节水方案依附于一次已完成分解，分解未完成或不存在时不能建方案；基准为报告期分区水量快照，历史观测或归档报告不会被预算模块改写。金额与水量按两位小数对账，三位及以上小数一律拒绝；候选最多2000行、单值上限10^12。背包状态以精确总成本为键，极端多候选×大预算下状态数随可行成本组合增长，演示与园区8分区规模下为毫秒级。预算调整留痕仅在应用内保留最近50次，不做独立的留痕归档表。

MIT License。
