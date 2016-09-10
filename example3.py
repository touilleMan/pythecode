def k(x, a=1, b=2, c=3):
    print(x, a, b, c)
    d = (a + b) * c
    return 'res', d, x

print(k(10, 20))
