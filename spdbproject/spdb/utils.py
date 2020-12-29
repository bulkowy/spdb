import math

def toPythonDict(l):
    d = {}
    for elem in l:
        d[elem['name']] = elem['value']
    return d

def calculateDist(p1, p2):
    # https://gis.stackexchange.com/questions/215267/get-distance-in-meters-between-lat-lng-coordinates-divided-in-north-and-east-di
    R = 6378137
    p1_lat, p1_lon = float(p1['lat']), float(p1['lon'])
    p2_lat, p2_lon = float(p2['lat']), float(p2['lon'])
    x1 = p1_lat * math.pi / 180
    y1 = p1_lon
    x2 = p2_lat * math.pi / 180
    y2 = p2_lon
    d_lat = (x1 - x2) * math.pi / 180
    d_lon = (y1 - y2) * math.pi / 180
    a = (math.sin(d_lat / 2) ** 2) + (math.cos(x1) * math.cos(x2) * (math.sin(d_lon) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


