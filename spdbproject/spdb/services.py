import requests
import os
import copy
from osmtogeojson import osmtogeojson
from . import utils
        
import pprint
pp = pprint.PrettyPrinter(indent=2)

class OverpassService:
    def __init__(self):
        self.timeout = 600
        self.format = 'json'
        self.endpoint = 'https://lz4.overpass-api.de/api/interpreter'
        self.GH_api_key = os.environ.get('GRAPHHOPPER_KEY')
        self.GH_endpoint = f'https://graphhopper.com/api/1/route?calc_points=false&key={self.GH_api_key}&'

    def _queryOverpass(self, query):
        '''
        Make Query to OverPass API based on passed query param
        '''
        return requests.get(self.endpoint, params={'data': query}).json()

    def _resolveTags(self, feature):
        '''
        Resolve Tag string from site into Overpass QL compatible one 
        '''
        tags = feature.split('/')

        tagStr = ''
        for i in range(1, len(tags)):
            tagStr += f'["{tags[i-1]}"="{tags[i]}"]'

        return tagStr

    def _getDistBound(self, dist_bound):
        '''
        Min/Max value of Distance Boundary
        '''
        if dist_bound <= 0 :
            return 0
        elif dist_bound >= 100:
            return 100
        else:
            return dist_bound

    def _resolveRequestBody(self, body):
        '''
        Get important values from main query body
        '''
        self.tag = self._resolveTags(body['main_feature'])
        self.search_type = body['search_type']
        if self.search_type == 'distance':
            # distance in Meters
            self.value = body['value']
        else:
            # transform time into distance in Meters (140000km/60min * time(min))
            self.time = body['value']
            self.value = str(int(14000/6 * float(self.time)))
        self.lat = body['lat']
        self.lon = body['lng']
        self.dist_bound = self._getDistBound(float(body['distance_bound_percentage']))
        self.logic = body['extra_fields_logic_function']

        self.extra_count = int(body['extra_field_count'])
        self.extra = {}

        # get extra conditions
        for i in range(1, self.extra_count + 1):
            self.extra[i] = {
                "tag": body[f'extra_search_{i}'],
                "dist": body[f'extra_search_dist_{i}'],
            }

    def _prepareQuery(self, body):
        '''
        Prepare Overpass QL string query
        '''
        tags = self._resolveTags(body["main_feature"])
        qry = f'[out:{self.format}][timeout:{self.timeout}];'
        around = f'{tags}(around:{body["value"]}, {body["lat"]}, {body["lng"]});'
        qry += f'(\nnode{around}\nway{around}\nrelation{around}\n);'
        qry += f'out body;>;out;'
        return qry

    # -- retrieve id - node latlon map
    def _createIDToNodeList(self):
        '''
        Retrieve all Node information and put into ID - Node LatLon map
        '''
        tempNodeJson = copy.deepcopy(self.nodeJson)
        self.idNode = {}
        out = []

        for obj in self.mainJson['elements']:
            # relations are not of interest
            if obj['type'] == 'relation':
                continue
            # if they are not relation and node, they are polygons
            # retrieve first node of polygon and put it in containers
            elif obj['type'] != 'node':
                found, tempNodeJson = self._polygonGetFirstNode(obj, tempNodeJson)
                self.idNode[found['id']] = {'lat': found['lat'], 'lon': found['lon']}
                out.append(found)
                tempNodeJson.remove(found)
            # put node into containers
            else:
                # check if node is in container by any means
                # if yes - dont add it into containers
                in_poly = False
                for poly in self.polyJson:
                    if obj['id'] in poly['nodes']:
                        in_poly = True

                if not in_poly:
                    self.idNode[obj['id']] = {'lat': obj['lat'], 'lon': obj['lon']}
                    out.append(obj)
                    tempNodeJson.remove(obj)

        return out

    def _filterNodes(self, data):
        '''
        Retrieve only nodes from JSON
        '''
        data = list(filter(lambda obj: obj['type'] == 'node', data))
        return data

    def _filterPolys(self, data):
        '''
        Retrieve only polygons from JSON
        '''
        data = list(filter(lambda obj: obj['type'] not in ['node', 'relation'], data))
        return data

    def _polygonGetFirstNode(self, polygon, data):
        '''
        Retrieve first node of Polygon
        Remove rest of Polygon nodes from temporary container
        '''
        out = {}
        to_remove = []
        for node in data:
            if node['id'] == polygon['nodes'][0] and not out:
                out = node

            if node['id'] in polygon['nodes'][1:-1]:
                to_remove.append(node)
        
        for node in to_remove:
            data.remove(node)

        return out, data

    # -- reduce objs by extra conditions --
    def _queryExtra(self, i, obj):
        '''
        Make query for extra conditions
        '''
        tmp_body = {
            'main_feature': self.extra[i]['tag'],
            'value': self.extra[i]['dist'],
            'lat': obj['lat'],
            'lng': obj['lon']
        }
        qry = self._prepareQuery(tmp_body)
        return self._queryOverpass(qry)

    def _filterByExtra(self):
        '''
        Filter idNode map by conditions
        '''
        tmp = self.idNode
        if self.extra_count == 0:
            return
        
        out = {}
        if self.logic == 'AND':
            for obj, latlon in tmp.items():
                correct = True
                for i in range(1, self.extra_count + 1):
                    res = self._queryExtra(i, latlon)
                    if len(res['elements']) == 0:
                        correct = False
                        break
                if correct:
                    out[obj] = latlon
        else:
            for obj, latlon in tmp.items():
                correct = False
                for i in range(1, self.extra_count + 1):
                    res = self._queryExtra(i, latlon)
                    if len(res['elements']) > 0:
                        correct = True
                        break
                if correct:
                    out[obj] = latlon

        self.idNode = out

    # -- filter by time --
    def _isInDistBoundary(self, endpoint):
        return utils.calculateDist({self.lat, self.lon}, endpoint) <= (self.dist_bound / 100) * self.value

    def _isTimeCorrect(self, data):
        time = int(data['paths'][0]['time']) # ms
        targetTime = self.time * 60000 # min * 60 s/min * 1000 ms/s
        return time < targetTime

    def _makeGraphhopperQuery(self, data):
        url = self.GH_endpoint + f'point={self.lat},{self.lon}&point={data["lat"]},{data["lon"]}&vehicle=Car'
        return requests.get(url).json()

    def _filterByTime(self):
        tmp = self.idNode
        out = {}

        for obj, latlon in tmp.items():
            if(self._isInDistBoundary(latlon)):
                out[obj] = latlon
            else:
                res = self._makeGraphhopperQuery(latlon)
                if not res:
                    out[obj] = latlon
                elif self._isTimeCorrect(res):
                    out[obj] = latlon

        self.idNode = out

    def _getMainFiltered(self):
        mainObjs = self.mainJson['elements']
        nodes_to_add = []
        out = []

        for obj in mainObjs:
            if obj['type'] == 'relation':
                out.append(obj)
            elif obj['type'] == 'node':
                if obj['id'] not in self.idNode.keys():
                    continue

                in_poly = False
                for poly in self.polyJson:
                    if obj['id'] in poly['nodes']:
                        out.append(poly)
                        nodes_to_add.extend(poly['nodes'])
                        in_poly = True
                        continue

                if not in_poly:
                    out.append(obj)
        
        for node in nodes_to_add:
            for nodeObj in self.nodeJson:
                if node == nodeObj['id']:
                    out.append(nodeObj)

        return out
                    
    def query(self, body):
        self._resolveRequestBody(body)
        body['value'] = self.value

        qry = self._prepareQuery(body)

        self.mainJson = self._queryOverpass(qry)

        self.nodeJson = self._filterNodes(self.mainJson['elements'])
        self.polyJson = self._filterPolys(self.mainJson['elements'])
        
        if self.search_type == 'time' or self.extra_count > 0:
            idnode_out = self._createIDToNodeList()
            self._filterByExtra()
            if self.search_type == 'time':
                self._filterByTime()

            self.mainJson['elements'] = self._getMainFiltered()
        
        pp.pprint(self.mainJson)
        self.mainObjects = osmtogeojson.process_osm_json(self.mainJson)
        #test = self.mainJson
        #test['elements'] = self._createIDToNodeList()
        #test = osmtogeojson.process_osm_json(test)
        return self.mainObjects