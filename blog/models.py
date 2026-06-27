from django.db import models
from django.conf import settings


class Group(models.Model):
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    ent_time = models.TimeField()
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Student(models.Model):
    name = models.CharField(max_length=100)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    parent_name = models.CharField(max_length=100)
    parent_phone = models.CharField(max_length=200)
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10)  # 'present', 'absent', 'late'
    sended_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.name} - {self.date} - {self.status}"


class Assessment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    academic = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    homework = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    understanding = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    sended_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.name} - {self.date}"


class SmsConfig(models.Model):
    gateway_url = models.CharField(max_length=200)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'SMS sozlamalari'

    def __str__(self):
        return self.gateway_url

    @classmethod
    def get(cls):
        """Return the singleton row, seeding from settings.py on first use."""
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'gateway_url': getattr(settings, 'SMS_GATEWAY_URL', ''),
                'username':    getattr(settings, 'SMS_GATEWAY_USERNAME', ''),
                'password':    getattr(settings, 'SMS_GATEWAY_PASSWORD', ''),
            },
        )
        return obj