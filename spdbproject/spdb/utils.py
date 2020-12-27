def toPythonDict(l):
    d = {}
    for elem in l:
        d[elem['name']] = elem['value']
    return d