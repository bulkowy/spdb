import overpass

class OverpassService:
    def __init__(self):
        self.api = overpass.API()