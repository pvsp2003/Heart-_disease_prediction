from django import forms

class HeartForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    age = forms.IntegerField()

    SEX_CHOICES = [(1, 'Male'), (0, 'Female')]
    sex = forms.ChoiceField(choices=SEX_CHOICES, widget=forms.RadioSelect)

    CP_CHOICES = [
        (1, 'Typical Angina'),
        (2, 'Atypical Angina'),
        (3, 'Non-anginal Pain'),
        (4, 'Asymptomatic'),
    ]
    cp = forms.ChoiceField(choices=CP_CHOICES, label="Chest Pain Type")

    trestbps = forms.IntegerField(label="Resting Blood Pressure (mmHg)")
    chol = forms.IntegerField(label="Cholesterol (mg/dl)")

    FBS_CHOICES = [(1, 'True (>=120 mg/dl)'), (0, 'False (<120 mg/dl)')]
    fbs = forms.ChoiceField(choices=FBS_CHOICES, label="Fasting Blood Sugar > 120 mg/dl", widget=forms.RadioSelect)

    RESTECG_CHOICES = [
        (0, 'Normal'),
        (1, 'ST-T Wave Abnormality'),
        (2, 'Left Ventricular Hypertrophy'),
    ]
    restecg = forms.ChoiceField(choices=RESTECG_CHOICES, label="Rest ECG")

    thalach = forms.IntegerField(label="Max Heart Rate Achieved")

    EXANG_CHOICES = [(1, 'Yes'), (0, 'No')]
    exang = forms.ChoiceField(choices=EXANG_CHOICES, widget=forms.RadioSelect, label="Exercise Induced Angina")

    oldpeak = forms.FloatField(label="ST Depression (Oldpeak in mm)")

    NUM_CHOICES = [
        (1, 'Up Sloping'),
        (2, 'Flat'),
        (3, 'Down Sloping'),
    ]
    num = forms.ChoiceField(choices=NUM_CHOICES, label="Peak exercise ST segment")

    def clean(self):
        cleaned_data = super().clean()
        errors = {}

        age = cleaned_data.get('age')
        if age is not None and age > 100:
            errors['age'] = "Age must not exceed 100."

        thalach = cleaned_data.get('thalach')
        if thalach is not None and thalach > 220:
            errors['thalach'] = "Max heart rate should not exceed 220."

        trestbps = cleaned_data.get('trestbps')
        if trestbps is not None and trestbps > 250:
            errors['trestbps'] = "Resting BP must not exceed 250 mmHg."

        chol = cleaned_data.get('chol')
        if chol is not None and chol > 500:
            errors['chol'] = "Cholesterol must not exceed 500 mg/dl."

        oldpeak = cleaned_data.get('oldpeak')
        if oldpeak is not None and oldpeak > 80:
            errors['oldpeak'] = "Oldpeak must not exceed 80 mm."

        # Raise all errors at once
        if errors:
            raise forms.ValidationError(errors)
