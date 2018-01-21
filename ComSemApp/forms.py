from django import forms
from django.forms import ModelForm
from .models import Course, CourseType, Session, SessionType, Teacher, Student
from django.contrib.auth.models import User

from .models import Institution



class SignupForm(ModelForm):
    first_name = forms.CharField(label="First Name", max_length=100)
    last_name = forms.CharField(label="Last Name", max_length=100)
    email = forms.EmailField()

    class Meta:
        model = Institution
        fields = ['name', 'city', 'state_province', 'country']
        labels = {
            "name": "Organization / Institution",
            "state_province": "State or Province"
        }



# MODEL FORMS FOR ADMIN SIDE
class CourseForm(ModelForm):
    class Meta:
        model = Course
        fields = ['session', 'course_type', 'teachers', 'students', 'section']

    def __init__(self, *args, **kwargs):
        institution = args[1]
        new_args = [args[0]]
        super(CourseForm, self).__init__(*new_args, **kwargs)
        self.fields['session'].queryset = Session.objects.filter(session_type__institution=institution)
        self.fields['course_type'].queryset = CourseType.objects.filter(institution=institution)
        self.fields['teachers'].queryset = Teacher.objects.filter(institution=institution)
        self.fields['students'].queryset = Student.objects.filter(institution=institution)


class CourseTypeForm(ModelForm):
    class Meta:
        model = CourseType
        fields = ['name', 'verbose_name']


class SessionForm(ModelForm):
    class Meta:
        model = Session
        fields = ['session_type', 'start_date', 'end_date']

    def __init__(self, *args, **kwargs):
        institution = args[1]
        new_args = [args[0]]
        super(SessionForm, self).__init__(*new_args, **kwargs)
        self.fields['session_type'].queryset = SessionType.objects.filter(institution=institution)



class SessionTypeForm(ModelForm):
    class Meta:
        model = SessionType
        fields = ['name', 'order']

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
