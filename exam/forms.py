from django import forms
from exam.models import Profile

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from string import letters, punctuation, digits
import md5

UNAME_CHARS = letters + "._" + digits
PWD_CHARS = letters + punctuation + digits

class UserRegisterForm(forms.Form):

    drishti_id = forms.CharField(max_length=30)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    mobile_number = forms.CharField(max_length=20)
    email = forms.EmailField()
    institution = forms.CharField(max_length=128)
    semester = forms.CharField(max_length=64)
    team = forms.CharField(widget=forms.Textarea,required=False)
    

    def clean_username(self):
        u_name = self.cleaned_data["drishti_id"]

        if u_name.strip(UNAME_CHARS):
            msg = "Only letters, digits, period and underscore characters are "\
                  "allowed in username"
            raise forms.ValidationError(msg)

        try:
            User.objects.get(username__exact = u_name)
            raise forms.ValidationError("Drishti ID already exists.")
        except User.DoesNotExist:
            return u_name
    
    
    def save(self):
    	u_name = self.cleaned_data["drishti_id"]
        u_name = u_name.lower()
        new_user = User.objects.create_user(u_name)

        new_user.first_name = self.cleaned_data["first_name"]
        new_user.last_name = self.cleaned_data["last_name"]
        new_user.save()

        cleaned_data = self.cleaned_data
        new_profile = Profile(user=new_user)
        new_profile.mobile_number = cleaned_data["mobile_number"]
        new_profile.institution = cleaned_data["institution"]
        new_profile.semester = cleaned_data["semester"]
	new_profile.email = cleaned_data['email']
	new_profile.team = cleaned_data['team']

        new_profile.save()

        return u_name

"""
    def clean_password(self):
        pwd = self.cleaned_data['password']
        if pwd.strip(PWD_CHARS):
            raise forms.ValidationError("Only letters, digits and punctuation are \
                                         allowed in password")
        return pwd

    def clean_confirm_password(self):
        c_pwd = self.cleaned_data['confirm_password']
        pwd = self.data['password']
        if c_pwd != pwd:
            raise forms.ValidationError("Passwords do not match")

        return c_pwd
"""

"""
class UserLoginForm(forms.Form):
    drishti_id = forms.CharField(max_length = 30)
#    password = forms.CharField(max_length=30, widget=forms.PasswordInput())

    def clean(self):
        super(UserLoginForm, self).clean()
        u_name = self.cleaned_data["drishti_id"]
        user = authenticate(username = u_name)

        if not user:
            raise forms.ValidationError("Invalid Drishti ID")

        return user
"""
