from django import forms

# Possible combinations (OverPass Tags, Description)
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

# Possible combinations of search type
SEARCH_TYPE = (
    ("distance", "distance (meters)"),
    ("time", "time (minutes)"),
)

# Possible extra field logic
LOGIC_FUNCTION = {
    ("OR", "OR"),
    ("AND", "AND"),
}

class SearchForm(forms.Form):
    main_feature = forms.ChoiceField(choices = FEATURES)
    search_type = forms.ChoiceField(choices = SEARCH_TYPE)
    value = forms.FloatField()
    distance_bound_percentage = forms.FloatField(min_value=0.0, max_value=100.0)
    extra_fields_logic_function = forms.ChoiceField(choices = LOGIC_FUNCTION)
    lat = forms.FloatField(widget = forms.HiddenInput())
    lng = forms.FloatField(widget = forms.HiddenInput())
    extra_field_count = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        # get information if there are any extra fields defined in view
        extra_fields = kwargs.pop('extra', 0)

        super(SearchForm, self).__init__(*args, **kwargs)
        
        # initialize `extra_field_count` with count of extra fields 
        self.fields['extra_field_count'].initial = extra_fields

        # for every extra field
        for idx in range(int(extra_fields)):
            
            # retrieve Overpass tags
            self.fields['extra_search_{}'.format(idx)] = forms.ChoiceField(choices = FEATURES)

            # retrieve search radius for given tags
            self.fields['extra_search_dist_{}'.format(idx)] = forms.FloatField()

