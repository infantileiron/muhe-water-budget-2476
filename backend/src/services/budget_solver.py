def solve(groups,budget,target):
 # groups: 每分区一组选项，options[0] 为不选；option 含 key/name/cost(分)/saving(百分之一m3)
 # 以精确总成本为状态：cost -> (总节水量, 选择向量)
 states={0:(0,())}
 for zone_options in groups:
  nxt={}
  ordered=sorted(zone_options,key=lambda o:(o["cost"],-o["saving"],o["name"]))
  for cost,(saving,vector) in states.items():
   for idx,option in enumerate(ordered):
    nc=cost+option["cost"]
    if nc>budget:
     continue
    nv=vector+(idx,)
    cand=(saving+option["saving"],nv)
    prev=nxt.get(nc)
    if prev is None or (cand[0],cand[1])>(prev[0],prev[1]):
     nxt[nc]=(cand[0],cand[1])
  states=nxt
 feasible=[(c,s,v) for c,(s,v) in states.items() if c<=budget]
 target_hits=[x for x in feasible if x[1]>=target]
 if target_hits:
  # 达标：总投入最低优先；同投入取节水更高；再取选择向量字典序更大（等价时优先让靠前分区采取措施）
  best=min(target_hits,key=lambda x:(x[0],-x[1],tuple(-i for i in x[2])))
  met=True
 else:
  # 不达标：预算内总节水最大；同节水取成本更低；再取选择向量字典序更大，保证等价解稳定
  best=max(feasible,key=lambda x:(x[1],-x[0],x[2]))
  met=False
 cost,saving,vector=best
 selections=[]
 for zone_options,idx in zip(groups,vector):
  ordered=sorted(zone_options,key=lambda o:(o["cost"],-o["saving"],o["name"]))
  selections.append(ordered[idx])
 return {"met":met,"total_cost":cost,"total_saving":saving,"target":target,"budget":budget,"selections":selections}
