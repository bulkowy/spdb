import math

def toPythonDict(l):
    '''
    Convert list from web application into Python dict
    '''
    d = {}
    for elem in l:
        d[elem['name']] = elem['value']
    return d

def calculateDist(p1, p2):
    '''
    Calculate distance in meters between Points using their latitudes and longitudes
    '''
    lat1, lon1 = float(p1['lat']), float(p1['lon'])
    lat2, lon2 = float(p2['lat']), float(p2['lon'])
    p = math.pi/180
    a = 0.5 - math.cos((lat2-lat1)*p)/2 + math.cos(lat1*p) * math.cos(lat2*p) * (1-math.cos((lon2-lon1)*p))/2
    return 6378137 * 2 * math.asin(math.sqrt(a))