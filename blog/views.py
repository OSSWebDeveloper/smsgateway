import json
import os
import threading
import time

from datetime import date, datetime

from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from blog.models import *
from blog.models import SmsConfig
from blog.sms import normalize_phone, send_sms, _post_to_gateway

# Create your views here.

def index(request):
    return render(request, 'blog/index.html')

def home(request):
    return render(request, 'blog/home.html')

def groups(request):
    groups = Group.objects.all().order_by('-created_date')
    return render(request, 'blog/groups.html', {'groups': groups})


ATTENDANCE_LABELS = {
    'absent': " kelmadi",
    'late': "kechikdi",
    'present': "keldi",
}

# Statuses that are worth a text message. Add 'present' here too if you
# want a confirmation text on ordinary days as well.
NOTIFY_STATUSES = {'absent', 'late', 'present'}


def group_detail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    students = group.student_set.all().order_by('-created_date')
    today = date.today()

    if request.method == 'POST':
        # If lesson end button was pressed, update group's end time
        if 'lesson_end' in request.POST:
            now_time = datetime.now().time()

            parent_numbers = [s.parent_phone for s in students]
            send_sms(
                parent_numbers,
                f"Guruhimizda soat {now_time.strftime('%H:%M')}da dars tugadi."
                # f"Farzandingizni olib ketishingiz mumkin."
            )

            messages.success(request, 'Dars tugadi xabari jo\'natildi')
            return redirect('group_detail', group_id=group_id)

        # Collect attendance data, save to DB, queue SMS
        sms_queue = []
        saved_count = 0

        for student in students:
            status = request.POST.get(f'status_{student.id}', '')
            if not status:
                continue

            Attendance.objects.update_or_create(
                student=student,
                date=today,
                defaults={'status': status}
            )
            saved_count += 1

            phone = normalize_phone(student.parent_phone)
            if phone:
                sms_queue.append((
                    phone,
                    f"Hurmatli ota-ona, {student.name} bugungi darsga "
                    f"{ATTENDANCE_LABELS[status]}."
                ))

        # Send SMS sequentially in a background thread
        if sms_queue:
            def send_all(queue):
                for phone, text in queue:
                    _post_to_gateway([phone], text)
                    time.sleep(1)
            threading.Thread(target=send_all, args=(sms_queue,), daemon=False).start()

        messages.success(request, f'Davomat {saved_count} ta talaba uchun tasdiqlandi!')
        return redirect('group_detail', group_id=group_id)

    # Load today's attendance records
    attendance_records = Attendance.objects.filter(
        student__in=students,
        date=today
    ).values('student_id', 'status')
    
    # Create a dictionary for quick lookup
    attendance_map = {rec['student_id']: rec['status'] for rec in attendance_records}
    


    return render(request, 'blog/group_detail.html', {
        'group': group,
        'students': students,
        'attendance_map': attendance_map,
        'today': today,
    })

def group_create(request):
    if request.method == 'POST':
        name = request.POST['name']
        start_time = request.POST['start_time']
        ent_time = request.POST['ent_time']

        group = Group(name=name, start_time=start_time, ent_time=ent_time)
        group.save()
        messages.success(request, 'Group created successfully!')
        return redirect('group_create')

    return render(request, 'blog/group_create.html')


def students(request):
    students = Student.objects.all().order_by('name')
    return render(request, 'blog/students.html', {'students': students})

    
# notification for student create view
def student_create(request):
    if request.method == 'POST':
        name = request.POST['name']
        parent_name = request.POST['parent_name']
        parent_phone = request.POST['parent_phone']
        group_id = request.POST['group']

        group = get_object_or_404(Group, id=group_id)

        student = Student(name=name, parent_name=parent_name, parent_phone=parent_phone, group=group)
        student.save()
        messages.success(request, 'Student created successfully!')
        return redirect('student_create')

    groups = Group.objects.all().order_by('-created_date')
    return render(request, 'blog/student_create.html', {'groups': groups})


def student_remove(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    group_id = student.group_id

    if request.method == 'POST':
        student_name = student.name
        student.delete()
        messages.success(request, f"{student_name} guruhdan o'chirildi!")

    return redirect('group_detail', group_id=group_id)


def student_assessment(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    today = date.today()

    if request.method == 'POST':
        academic = request.POST.get('academic')
        homework = request.POST.get('homework')
        understanding = request.POST.get('understanding')

        if academic and homework and understanding:
            try:
                Assessment.objects.create(
                    student=student,
                    date=today,
                    academic=int(academic),
                    homework=int(homework),
                    understanding=int(understanding)
                )

                send_sms(
                    [student.parent_phone],
                    f"{student.name} bahosi — akademik: {academic}, "
                    f"uy vazifa: {homework}, tushunish: {understanding} (5 balldan)."
                )

                messages.success(request, 'Baholash saqlandi!')
                return redirect('student_assessment', student_id=student_id)
            except Exception:
                messages.error(request, 'Xatolik yuz berdi, iltimos qayta urinib ko\'ring.')
        else:
            messages.error(request, 'Iltimos, barcha bo\'limlarni to\'ldiring.')

    group_students = Student.objects.filter(group=student.group).order_by('name')
    return render(request, 'blog/student_assessment.html', {
        'student': student,
        'points': range(1, 6),
        'group_students': group_students,
    })


def sms_config(request):
    config = SmsConfig.get()

    if request.method == 'POST':
        config.gateway_url = request.POST.get('gateway_url', '').rstrip('/')
        config.username    = request.POST.get('username', '')
        config.password    = request.POST.get('password', '')
        config.save()

        # Also push to settings so the running process uses new values
        # immediately (restart not required for the next SMS send).
        from django.conf import settings
        settings.SMS_GATEWAY_URL      = config.gateway_url
        settings.SMS_GATEWAY_USERNAME = config.username
        settings.SMS_GATEWAY_PASSWORD = config.password

        messages.success(request, 'SMS sozlamalari saqlandi!')
        return redirect('sms_config')

    return render(request, 'blog/sms_config.html', {'config': config})


@require_POST
def sms_test(request):
    """AJAX endpoint called by the Test SMS button."""
    try:
        body  = json.loads(request.body)
        phone = body.get('phone', '').strip()
        text  = body.get('message', '').strip() or "Musoyev School: test SMS"

        if not phone:
            return JsonResponse({'ok': False, 'error': 'Telefon raqami kiritilmagan'}, status=400)

        normalized = normalize_phone(phone)
        if not normalized:
            return JsonResponse({'ok': False, 'error': "Noto'g'ri telefon raqami formati"}, status=400)

        _post_to_gateway([normalized], text)
        return JsonResponse({'ok': True})

    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=502)


def download_apk(request):
    """Serve the SMS Gateway APK file for direct download."""
    from django.conf import settings
    apk_path = os.path.join(settings.BASE_DIR, 'media', 'apk', 'smsgate.apk')
    if not os.path.exists(apk_path):
        raise Http404("APK fayl topilmadi.")
    return FileResponse(
        open(apk_path, 'rb'),
        as_attachment=True,
        filename='SMSGateway.apk',
        content_type='application/vnd.android.package-archive',
    )