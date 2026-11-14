from sqlalchemy import String,JSON,ForeignKey,Text
from sqlalchemy.orm import Mapped,mapped_column
from src.config.database import Base
class BudgetPlan(Base):
 __tablename__="budget_plans"
 id:Mapped[str]=mapped_column(String,primary_key=True)
 name:Mapped[str]=mapped_column(String,unique=True)
 run_id:Mapped[str]=mapped_column(ForeignKey("decomposition_runs.id"))
 period:Mapped[str]=mapped_column(String)
 budget:Mapped[float]=mapped_column()
 target_saving:Mapped[float]=mapped_column(default=0.0)
 baseline:Mapped[list]=mapped_column(JSON,default=list)
 candidates:Mapped[list]=mapped_column(JSON,default=list)
 result:Mapped[dict]=mapped_column(JSON,default=dict)
 history:Mapped[list]=mapped_column(JSON,default=list)
 note:Mapped[str]=mapped_column(String,default="")
 created_by:Mapped[str]=mapped_column(String)
 created_at:Mapped[str]=mapped_column(String)
 updated_at:Mapped[str]=mapped_column(String)
