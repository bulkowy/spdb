import requests
import os
import copy
from osmtogeojson import osmtogeojson
from . import utils
        
import pprint
pp = pprint.PrettyPrinter(indent=2)

class OverpassService:
    '''
    Main service class
    '''
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
        try:
            return requests.get(self.endpoint, params={'data': query}).json()
        except:
            return {'elements': []}

    def _resolveTags(self, feature):
        '''
        Resolve Tag string from site into Overpass QL compatible one 

        Converts 'Tag1/Tag2' string to '[Tag1=Tag2]'
        Converts 'Tag1/Tag2/Tag3' string to '[Tag1=Tag2][Tag2=Tag3]'
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
        Retrieve and store important data from request body
        '''
        self.tag = self._resolveTags(body['main_feature'])
        self.search_type = body['search_type']

        # set distance value depending on given search type 
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

        # get extra conditions into dict
        for i in range(1, self.extra_count + 1):
            self.extra[i] = {
                "tag": body[f'extra_search_{i}'],
                "dist": body[f'extra_search_dist_{i}'],
            }

    def _prepareQuery(self, body):
        '''
        Prepare Overpass QL string query

        Overpass QL Query template:
        ```
        [out:FORMAT][timeout:TIMEOUT];
        node[TAG1=TAG2](around=VALUE, LAT, LNG);
        way[TAG1=TAG2](around=VALUE, LAT, LNG);
        relation[TAG1=TAG2](around=VALUE, LAT, LNG);
        out body;>;out;
        ```
        '''

        # convert tags into format understood by Overpass API 
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
                if not found:
                    continue
                # if polygon contained tags, pass them to it's first node
                if 'tags' in obj.keys():
                    found['tags'] = obj['tags']
                self.idNode[found['id']] = {'lat': found['lat'], 'lon': found['lon']}
                out.append(found)
                tempNodeJson.remove(found)

            # put node into containers
            else:
                # check if node is in any polygon by any means
                # if yes - dont add it into containers
                in_poly = False
                for poly in self.polyJson:
                    if obj['id'] in poly['nodes']:
                        in_poly = True

                # add node to list if it was not in any polygon
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

        for node in data:
            if node['id'] == polygon['nodes'][0] and not out:
                out = node
                break

        return out, data

    # -- reduce objs by extra conditions --
    def _queryExtra(self, i, obj):
        '''
        Make query for extra conditions
        '''

        # prepare temporary request body to be processed by _prepareQuery
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
        # if logic operator of extra fields is AND 
        if self.logic == 'AND':
            # for every found node in main query
            for obj, latlon in tmp.items():
                # check if node meets ALL requirements
                correct = True
                for i in range(1, self.extra_count + 1):
                    res = self._queryExtra(i, latlon)
                    # if query to Overpass returns no elements 
                    # it means that Node didn't meet requirement
                    if len(res['elements']) == 0:
                        correct = False
                        break

                # add node to container if it met ALL requirements
                if correct:
                    out[obj] = latlon
        
        #if logic operator of extra fields is OR 
        else:
            # for every found node in main query
            for obj, latlon in tmp.items():
                # check if node meets ANY requirement
                correct = False
                for i in range(1, self.extra_count + 1):
                    res = self._queryExtra(i, latlon)
                    # if query to Overpass returns at least one element
                    # it means that Node met requirement
                    if len(res['elements']) > 0:
                        correct = True
                        break

                # add node to container if it met ANY requirement
                if correct:
                    out[obj] = latlon

        self.idNode = out

    # -- filter by time --
    def _isInDistBoundary(self, endpoint):
        # convert latitude and longitude difference between points into distance in meters
        return utils.calculateDist({'lat': self.lat, 'lon': self.lon}, endpoint) <= (float(self.dist_bound) / 100) * float(self.value)

    def _isTimeCorrect(self, data):
        '''
        Check if passed time meets requirement
        '''
        time = float(data['paths'][0]['time']) # ms
        targetTime = float(self.time) * 60000 # min * 60 s/min * 1000 ms/s
        return time < targetTime

    def _makeGraphhopperQuery(self, data):
        '''
        Make query to Graphhopper
        '''
        url = self.GH_endpoint + f'point={self.lat},{self.lon}&point={data["lat"]},{data["lon"]}&vehicle=Car'
        return requests.get(url).json()

    def _filterByTime(self):
        '''
        Filter nodes by travel time
        '''
        tmp = self.idNode
        out = {}

        # for every filtered node
        for obj, latlon in tmp.items():
            # check if it is in distance boundary
            if(self._isInDistBoundary(latlon)):
                # if it is, add to container
                out[obj] = latlon
            else:
                # if it isn't check travel time using Graphhopper
                res = self._makeGraphhopperQuery(latlon)

                # if API return nothing - add it to container (means error by API side)
                if not res:
                    out[obj] = latlon

                # if time meets requirements - add it to container
                elif self._isTimeCorrect(res):
                    out[obj] = latlon

        self.idNode = out

    def _getMainFiltered(self):
        '''
        Filter Main container using filtered idNode container
        '''

        mainObjs = self.mainJson['elements']
        nodes_to_add = []
        out = []

        # for every object in Main cointainer
        for obj in mainObjs:
            # if it is relation - dont add to temporary container
            if obj['type'] == 'relation':
                continue
            # if it is node - add it in containter if it is in idNode container
            elif obj['type'] == 'node':
                if obj['id'] not in self.idNode.keys():
                    continue
                out.append(obj)

        return out


                    
    def query(self, body):
        # resolve request body
        self._resolveRequestBody(body)
        body['value'] = self.value

        # prepare query to Overpass
        qry = self._prepareQuery(body)

        # retrieve main objects' JSON from Overpass API
        self.mainJson = self._queryOverpass(qry)

        # filter nodes and polygons 
        self.nodeJson = self._filterNodes(self.mainJson['elements'])
        self.polyJson = self._filterPolys(self.mainJson['elements'])

        # create IDNodeList and pass only nodes to main objects' JSON
        self.mainJson['elements'] = self._createIDToNodeList()
        
        if self.search_type == 'time' or self.extra_count > 0:
            if self.search_type == 'time':\
                self._filterByTime()
            self._filterByExtra()

            # filter main objects' JSON by IDNode container
            self.mainJson['elements'] = self._getMainFiltered()
        
        # convert main JSON into geoJSON
        self.mainObjects = osmtogeojson.process_osm_json(self.mainJson)
        return self.mainObjects