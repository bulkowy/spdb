from django.shortcuts import render
from django.http import HttpResponse
import geojson
import json
from . import services, forms, utils

def index(request):
    '''
    Main view which is in charge of rendering map and form with data that will be passed to service
    '''
    if request.method == 'POST':
        form = forms.SearchForm(request.POST, extra=request.POST.get('extra_field_count'))
    else:
        form = forms.SearchForm()

    return render(request, 'spdb/index.html', {'form': form})


def getMap(request):
    '''
    Service endpoint
    '''

    # load and convert request body to Python dict
    body = json.loads(request.body)
    body = utils.toPythonDict(body)

    # retrieve GeoJSON from services response
    srv = geojson.dumps(services.OverpassService().query(body))
    return HttpResponse(srv)
