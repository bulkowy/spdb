import requests
from osmtogeojson import osmtogeojson

class OverpassService:
    def __init__(self):
        self.timeout = 600
        self.format = 'json'
        self.endpoint = 'https://lz4.overpass-api.de/api/interpreter'

    def _resolveTags(self, feature):
        tags = feature.split('/')

        tagStr = ''
        for i in range(1, len(tags)):
            tagStr += f'["{tags[i-1]}"="{tags[i]}"]'

        return tagStr

    def _resolveRequestBody(self, body):
        self.tag = self._resolveTags(body['main_feature'])
        self.search_type = body['search_type']
        if self.search_type == 'distance':
            self.value = body['value']
        else:
            self.value = str(int(14000/6 * float(body['value'])))
        self.lat = body['lat']
        self.lng = body['lng']

        self.extra_count = int(body['extra_field_count'])
        self.extra = {}

        for i in range(1, self.extra_count + 1):
            self.extra[i] = {
                "tag": self._resolveTags(body[f'extra_search_{i}']),
                "dist": body[f'extra_search_dist_{i}'],
            }

    def _prepareMainQuery(self, body):
        self._resolveRequestBody(body)
        qry = f'[out:{self.format}][timeout:{self.timeout}];'
        around = f'{self.tag}(around:{self.value}, {self.lat}, {self.lng});'
        qry += f'(\nnode{around}\nway{around}\nrelation{around}\n);'
        qry += f'out body;>;out;'
        return qry

    def _createIDToNodeList(self):
        tempNodeJson = self.nodeJson
        self.idNode = {}
        test = []

        for obj in self.mainJson['elements']:
            if obj['type'] == 'relation':
                continue
            elif obj['type'] != 'node':
                found, tempNodeJson = self._polygonGetFirstNode(obj, tempNodeJson)
                self.idNode[found['id']] = {'lat': found['lat'], 'lon': found['lon']}
                test.append(found)
                tempNodeJson.remove(found)
            else:
                in_poly = False
                for poly in self.polyJson:
                    if obj['id'] in poly['nodes']:
                        in_poly = True

                if not in_poly:
                    self.idNode[obj['id']] = {'lat': obj['lat'], 'lon': obj['lon']}
                    test.append(obj)
                    tempNodeJson.remove(obj)

        return test

    def _filterNodes(self, json):
        json = list(filter(lambda elem: elem['type'] == 'node', json))
        return json

    def _filterPolys(self, json):
        json = list(filter(lambda elem: elem['type'] not in ['node', 'relation'], json))
        return json

    def _polygonGetFirstNode(self, polygon, json):
        out = {}
        to_remove = []
        for node in json:
            if node['id'] == polygon['nodes'][0] and not out:
                out = node

            if node['id'] in polygon['nodes'][1:-1]:
                to_remove.append(node)
        
        for node in to_remove:
            json.remove(node)

        return out, json

        

    def query(self, body):
        qry = self._prepareMainQuery(body)
        r = requests.get(self.endpoint, params={'data': qry})
        self.mainJson = r.json()
        
        import pprint
        pp = pprint.PrettyPrinter(indent=2)
        #pp.pprint(self.mainJson)

        self.nodeJson = self._filterNodes(self.mainJson['elements'])
        self.polyJson = self._filterPolys(self.mainJson['elements'])
        #pp.pprint(self.nodeJson)
        
        self.mainObjects = osmtogeojson.process_osm_json(self.mainJson)
        test = self.mainJson
        test['elements'] = self._createIDToNodeList()
        test = osmtogeojson.process_osm_json(test)
        return self.mainObjects