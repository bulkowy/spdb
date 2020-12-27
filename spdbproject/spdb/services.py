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
        pass

    def query(self, body):
        qry = self._prepareMainQuery(body)
        r = requests.get(self.endpoint, params={'data': qry})
        self.mainObjects = osmtogeojson.process_osm_json(r.json())
        return self.mainObjects