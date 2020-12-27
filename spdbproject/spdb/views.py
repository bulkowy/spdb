from django.shortcuts import render
from django.http import HttpResponse
import geojson
import json
from . import services, forms, utils

# Create your views here.
def index(request):
    if request.method == 'POST':
        form = forms.SearchForm(request.POST, extra=request.POST.get('extra_field_count'))
    else:
        form = forms.SearchForm()

    return render(request, 'spdb/index.html', {'form': form})


def getMap(request):
    body = json.loads(request.body)
    body = utils.toPythonDict(body)
    srv = geojson.dumps(services.OverpassService().query(body))
    #if request.method == 'POST':
    return HttpResponse(srv)
