# simple example

def fibo(a):
    if a in (0, 1):
        ret = a
    else:
        ret = fibo(a-1) + fibo(a-2)
    return ret

print(fibo(0))
print(fibo(3))
print(fibo(10))
