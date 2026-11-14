from decimal import Decimal,ROUND_HALF_UP,InvalidOperation
from fastapi import HTTPException
CENT=Decimal("0.01")
def to_decimal(value,field):
 try:
  d=Decimal(str(value))
 except (InvalidOperation,ValueError):
  raise HTTPException(422,f"{field}数值无效，请填写有限数字")
 if not d.is_finite():
  raise HTTPException(422,f"{field}必须为有限数值")
 return d
def require_non_negative(d,field):
 if d<0:
  raise HTTPException(422,f"{field}不能为负数")
 return d
def require_two_places(d,field):
 if d.as_tuple().exponent is not None and d.as_tuple().exponent<-2:
  raise HTTPException(422,f"{field}最多保留两位小数，需按两位小数精确对账")
 return d
def quantize_two(d):
 return d.quantize(CENT,rounding=ROUND_HALF_UP)
def scaled_int(d):
 return int(quantize_two(d)*100)
def money(value,field):
 d=require_two_places(require_non_negative(to_decimal(value,field),field),field)
 return scaled_int(d)
def water(value,field):
 d=require_two_places(require_non_negative(to_decimal(value,field),field),field)
 return scaled_int(d)
def baseline_water(value,field):
 return scaled_int(to_decimal(value,field))
def raw_decimal(value,field):
 # 真实原水量（保留来源精度），仅用于"节水量不得超原水量"的硬性校验
 return to_decimal(value,field)
def to_float(scaled):
 return float(Decimal(scaled)/100)
