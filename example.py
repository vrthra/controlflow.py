def myfunc(x, y):
    if x > y:
       return True
    return False

x=100
y=100
while 1 > myfunc(x,y)+1:
  if x == y:
      continue
  else:
      x = x + 1
  print(0)
  if x is y:
      break
  print(1)
print(2)
