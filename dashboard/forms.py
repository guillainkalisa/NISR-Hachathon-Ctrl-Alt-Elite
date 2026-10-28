from django import forms

from pipeline.features import PMT_FEATURES


class HouseholdForm(forms.Form):
    """Built from features.PMT_FEATURES so the form always matches the model's inputs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in PMT_FEATURES:
            if f["kind"] == "bool":
                field = forms.BooleanField(required=False)
            elif f["kind"] == "choice":
                field = forms.TypedChoiceField(choices=f["choices"], coerce=int)
            elif f["kind"] == "int":
                field = forms.IntegerField(min_value=f["min"], max_value=f["max"])
            else:
                field = forms.FloatField(min_value=f["min"], max_value=f["max"],
                                         widget=forms.NumberInput(attrs={"step": "0.1"}))
            field.label = f["label"]
            self.fields[f["name"]] = field

    def model_values(self):
        return {k: float(v) for k, v in self.cleaned_data.items()}
