from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('home/', views.home, name='home'),
    path('groups/', views.groups, name='groups'),
    path('students/', views.students, name='students'),
    path('students/add/', views.student_create, name='student_create'),
    path('groups/<int:group_id>/', views.group_detail, name='group_detail'),
    path('groups/add/', views.group_create, name='group_create'),
    path('students/<int:student_id>/assessment/', views.student_assessment, name='student_assessment'),
    path('students/<int:student_id>/remove/', views.student_remove, name='student_remove'),
    path('sms-config/',  views.sms_config,   name='sms_config'),
    path('sms-test/',    views.sms_test,     name='sms_test'),
    path('download/smsgate.apk', views.download_apk, name='download_apk'),
]