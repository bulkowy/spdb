from django import forms

FEATURES = (
    ("amenity/bar", "bar"),
    ("amenity/restaurant", "restaurant"),
    ("amenity/cafe", "cafe"),
    ("amenity/fast_food", "fast food"),
    ("amenity/food_court", "food court"),
    ("amenity/pub", "pub"),
    ("amenity/bicycle_rental", "bicycle rental"),
    ("amenity/fuel", "fuel"),
    ("amenity/parking", "parking"),
    ("amenity/cinema", "cinema"),
    ("amenity/theatre", "theatre"),
    ("natural/water/lake", "lake"),
    ("natural/water/river", "river"),
    ("natural/water/pond", "pond"),
    ("natural/beach", "beach"),
    ("natural/pond", "pond"),
    ("tourism/apartment", "apartment"),
    ("tourism/attraction", "attraction"),
    ("tourism/hotel", "hotel"),
    ("tourism/charlet", "charlet"),
    ("tourism/museum", "museum"),
    ("tourism/information", "information"),
    ("tourism/viewpoint", "viewpoint"),
    ("highway/bus_stop", "bus_stop"),
)

SEARCH_TYPE = (
    ("distance", "distance (meters)"),
    ("time", "time (minutes)"),
)

class SearchForm(forms.Form):
    main_feature = forms.ChoiceField(choices = FEATURES)
    search_type = forms.ChoiceField(choices = SEARCH_TYPE)
    value = forms.FloatField()
    lat = forms.FloatField(widget = forms.HiddenInput())
    lng = forms.FloatField(widget = forms.HiddenInput())
    extra_field_count = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        extra_fields = kwargs.pop('extra', 0)
        super(SearchForm, self).__init__(*args, **kwargs)
        self.fields['extra_field_count'].initial = extra_fields

        for idx in range(int(extra_fields)):
            self.fields['extra_search_{}'.format(idx)] = forms.ChoiceField(choices = FEATURES)
            self.fields['extra_search_dist_{}'.format(idx)] = forms.FloatField()

