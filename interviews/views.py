import csv
import io
import json
import random
import uuid
import urllib.request
import urllib.error
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Avg, Count, Sum

from .models import (
    AdminUser, Department, Topic, Question,
    InterviewLink, CandidateResponse, QuestionAnswer, CandidateSnapshot,
    Course, CourseMaterial, CourseAssignment, MaterialProgress,
)


# ─── helpers ────────────────────────────────────────────────────────────────
def superadmin_required(fn):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superadmin:
            messages.error(request, 'Super Admin access required.')
            return redirect('dashboard')
        return fn(request, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

def editor_required(fn):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.can_edit:
            messages.error(request, 'You need Interviewer or Super Admin access.')
            return redirect('dashboard')
        return fn(request, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


# ─── AUTH ───────────────────────────────────────────────────────────────────
def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        # Distinguish "pending approval" from wrong credentials
        pending = AdminUser.objects.filter(email=email, is_active=False).exists()
        if pending:
            messages.error(request, 'Your account is pending admin approval.')
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'auth/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        if not name or not email or len(password) < 6:
            messages.error(request, 'Please fill all fields (min 6 char password).')
            return render(request, 'auth/register.html')
        if AdminUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'auth/register.html')
        AdminUser.objects.create_user(
            email=email, password=password, name=name,
            role='viewer', is_active=False,
        )
        return render(request, 'auth/register.html', {'pending': True})
    return render(request, 'auth/register.html')


# ─── DASHBOARD ──────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    recent = CandidateResponse.objects.select_related('link__topic__department').order_by('-submitted_at')[:5]
    avg_score = CandidateResponse.objects.filter(ai_score__isnull=False).aggregate(avg=Avg('ai_score'))['avg']

    # ── Course analytics ──────────────────────────────────────────────────
    course_count = Course.objects.count()
    assignment_count = CourseAssignment.objects.count()
    active_learners = CourseAssignment.objects.values('user').distinct().count()

    total_assigned_slots = (
        CourseAssignment.objects
        .annotate(mat_count=Count('course__materials'))
        .aggregate(total=Sum('mat_count'))['total'] or 0
    )
    completed_materials = MaterialProgress.objects.filter(completed=True).count()
    completion_rate = round((completed_materials / total_assigned_slots) * 100) if total_assigned_slots else 0

    # Top courses by assignment count with completion %
    top_courses_qs = (
        Course.objects
        .annotate(assign_count=Count('assignments', distinct=True))
        .prefetch_related('materials')
        .order_by('-assign_count')[:6]
    )
    course_stat_data = []
    for c in top_courses_qs:
        mat_count = c.materials.count()
        a_count = c.assign_count
        if mat_count and a_count:
            done = MaterialProgress.objects.filter(assignment__course=c, completed=True).count()
            pct = round((done / (mat_count * a_count)) * 100)
        else:
            pct = 0
        course_stat_data.append({'course': c, 'pct': pct, 'assign_count': a_count, 'mat_count': mat_count})

    # Recent material completions
    recent_completions = (
        MaterialProgress.objects
        .filter(completed=True, completed_at__isnull=False)
        .select_related('assignment__user', 'assignment__course', 'material')
        .order_by('-completed_at')[:5]
    )

    # Current user's assigned courses
    my_assignments = (
        CourseAssignment.objects
        .filter(user=request.user)
        .select_related('course')
        .prefetch_related('material_progress', 'course__materials')
        .order_by('-assigned_at')[:4]
    )
    my_course_data = []
    for a in my_assignments:
        total = a.course.materials.count()
        done = a.material_progress.filter(completed=True).count()
        pct = round((done / total) * 100) if total else 0
        my_course_data.append({'assignment': a, 'pct': pct, 'total': total, 'completed': done})

    ctx = {
        'dept_count': Department.objects.count(),
        'topic_count': Topic.objects.count(),
        'question_count': Question.objects.count(),
        'link_count': InterviewLink.objects.count(),
        'response_count': CandidateResponse.objects.count(),
        'avg_score': round(avg_score, 1) if avg_score else None,
        'recent_responses': recent,
        # course analytics
        'course_count': course_count,
        'assignment_count': assignment_count,
        'active_learners': active_learners,
        'completion_rate': completion_rate,
        'course_stat_data': course_stat_data,
        'recent_completions': recent_completions,
        'my_course_data': my_course_data,
        'active_panel': 'dashboard',
    }
    return render(request, 'admin/dashboard.html', ctx)


# ─── DEPARTMENTS ────────────────────────────────────────────────────────────
@login_required
def departments(request):
    depts = Department.objects.prefetch_related('topics').all()
    return render(request, 'admin/departments.html', {'departments': depts, 'active_panel': 'departments'})

@editor_required
def add_department(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        desc = request.POST.get('description', '').strip()
        if not name:
            messages.error(request, 'Department name is required.')
        else:
            Department.objects.create(name=name, description=desc, created_by=request.user)
            messages.success(request, f'Department "{name}" created.')
        return redirect('departments')
    return redirect('departments')

@editor_required
def delete_department(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    dept.delete()
    messages.success(request, f'Department "{dept.name}" deleted.')
    return redirect('departments')


# ─── TOPICS ─────────────────────────────────────────────────────────────────
@login_required
def topics(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    topic_list = dept.topics.prefetch_related('questions').all()
    topic_data = []
    for t in topic_list:
        topic_data.append({
            'topic': t,
            'basic_count': t.questions.filter(level='basic').count(),
            'intermediate_count': t.questions.filter(level='intermediate').count(),
            'advanced_count': t.questions.filter(level='advanced').count(),
        })
    return render(request, 'admin/topics.html', {
        'dept': dept, 'topic_data': topic_data, 'active_panel': 'questions'
    })

@editor_required
def add_topic(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Topic name required.')
        else:
            Topic.objects.create(department=dept, name=name, created_by=request.user)
            messages.success(request, f'Topic "{name}" added.')
    return redirect('topics', dept_id=dept_id)

@editor_required
def delete_topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    dept_id = topic.department.id
    topic.delete()
    messages.success(request, f'Topic "{topic.name}" deleted.')
    return redirect('topics', dept_id=dept_id)


# ─── QUESTIONS ──────────────────────────────────────────────────────────────
@login_required
def questions_home(request):
    """Show department selection for questions."""
    depts = Department.objects.all()
    return render(request, 'admin/questions_home.html', {
        'departments': depts, 'active_panel': 'questions'
    })


@login_required
def questions(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    level = request.GET.get('level', 'basic')
    all_qs = topic.questions.filter(level=level)
    return render(request, 'admin/questions.html', {
        'topic': topic,
        'questions': all_qs,
        'current_level': level,
        'basic_count': topic.questions.filter(level='basic').count(),
        'intermediate_count': topic.questions.filter(level='intermediate').count(),
        'advanced_count': topic.questions.filter(level='advanced').count(),
        'active_panel': 'questions',
    })

@editor_required
def add_question(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        level = request.POST.get('level', 'basic')
        answer = request.POST.get('answer', '').strip()
        if not text:
            messages.error(request, 'Question text required.')
        else:
            Question.objects.create(topic=topic, text=text, level=level, answer=answer, created_by=request.user)
            messages.success(request, 'Question added.')
    return redirect('questions', topic_id=topic_id)

def _resolve_field(mapping, candidates):
    """Return the value for the first matching key (case-insensitive) from candidates."""
    normalised = {k.strip().lower(): v for k, v in mapping.items()}
    for key in candidates:
        if key in normalised:
            return normalised[key]
    return ''

_QUESTION_KEYS = ['question text', 'question_text', 'question', 'text']
_ANSWER_KEYS   = ['answer text', 'answer_text', 'answer', 'expected answer', 'expected_answer']
_LEVEL_KEYS    = ['level', 'difficulty']

@editor_required
def bulk_add_questions(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    if request.method != 'POST':
        return redirect('questions', topic_id=topic_id)

    uploaded = request.FILES.get('file')
    if not uploaded:
        messages.error(request, 'No file selected.')
        return redirect('questions', topic_id=topic_id)

    filename = uploaded.name.lower()
    valid_levels = {'basic', 'intermediate', 'advanced'}
    rows = []

    try:
        if filename.endswith('.csv'):
            text = uploaded.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(text))
            for i, row in enumerate(reader, start=2):
                level = _resolve_field(row, _LEVEL_KEYS).strip().lower()
                question_text = _resolve_field(row, _QUESTION_KEYS).strip()
                answer_text = _resolve_field(row, _ANSWER_KEYS).strip()
                if not question_text:
                    messages.error(request, f'Row {i}: missing question text.')
                    return redirect('questions', topic_id=topic_id)
                if level not in valid_levels:
                    messages.error(request, f'Row {i}: invalid level "{level}". Use basic, intermediate, or advanced.')
                    return redirect('questions', topic_id=topic_id)
                rows.append({'level': level, 'text': question_text, 'answer': answer_text})

        elif filename.endswith('.json'):
            data = json.loads(uploaded.read().decode('utf-8'))
            if not isinstance(data, list):
                messages.error(request, 'JSON file must contain a list of objects.')
                return redirect('questions', topic_id=topic_id)
            for i, item in enumerate(data, start=1):
                level = _resolve_field(item, _LEVEL_KEYS).strip().lower()
                question_text = _resolve_field(item, _QUESTION_KEYS).strip()
                answer_text = _resolve_field(item, _ANSWER_KEYS).strip()
                if not question_text:
                    messages.error(request, f'Item {i}: missing question text.')
                    return redirect('questions', topic_id=topic_id)
                if level not in valid_levels:
                    messages.error(request, f'Item {i}: invalid level "{level}". Use basic, intermediate, or advanced.')
                    return redirect('questions', topic_id=topic_id)
                rows.append({'level': level, 'text': question_text, 'answer': answer_text})

        else:
            messages.error(request, 'Unsupported file type. Upload a .csv or .json file.')
            return redirect('questions', topic_id=topic_id)

    except Exception as e:
        messages.error(request, f'Failed to parse file: {e}')
        return redirect('questions', topic_id=topic_id)

    if not rows:
        messages.error(request, 'File is empty or has no valid rows.')
        return redirect('questions', topic_id=topic_id)

    Question.objects.bulk_create([
        Question(topic=topic, level=r['level'], text=r['text'], answer=r['answer'], created_by=request.user)
        for r in rows
    ])
    messages.success(request, f'{len(rows)} question{"s" if len(rows) != 1 else ""} added.')
    return redirect('questions', topic_id=topic_id)


@editor_required
def delete_question(request, q_id):
    q = get_object_or_404(Question, id=q_id)
    topic_id = q.topic.id
    level = q.level
    q.delete()
    messages.success(request, 'Question deleted.')
    return redirect(f'/admin-panel/questions/{topic_id}/?level={level}')


# ─── LINKS ──────────────────────────────────────────────────────────────────
@login_required
def links(request):
    all_links = InterviewLink.objects.select_related('topic__department').order_by('-created_at')
    depts = Department.objects.prefetch_related('topics').all()
    return render(request, 'admin/links.html', {
        'links': all_links, 'departments': depts, 'active_panel': 'links'
    })

@editor_required
def add_link(request):
    if request.method == 'POST':
        topic_id = request.POST.get('topic_id')
        level = request.POST.get('level', 'basic')
        count = int(request.POST.get('question_count', 5))
        time_per_q = int(request.POST.get('time_per_question', 2))
        if not topic_id:
            messages.error(request, 'Please select a topic.')
            return redirect('links')
        topic = get_object_or_404(Topic, id=topic_id)
        available = topic.questions.filter(level=level).count()
        if available == 0:
            messages.error(request, f'No {level} questions available for {topic.name}.')
            return redirect('links')
        actual_count = min(count, available)
        mode = request.POST.get('mode', 'video')
        if mode not in ('video', 'text'):
            mode = 'video'
        InterviewLink.objects.create(
            topic=topic, level=level, mode=mode, question_count=actual_count,
            time_per_question=time_per_q, created_by=request.user
        )
        messages.success(request, 'Interview link created.')
    return redirect('links')

@editor_required
def delete_link(request, link_id):
    link = get_object_or_404(InterviewLink, id=link_id)
    link.delete()
    messages.success(request, 'Link deleted.')
    return redirect('links')


# ─── RESPONSES ──────────────────────────────────────────────────────────────
@login_required
def responses(request):
    search = request.GET.get('q', '')
    qs = CandidateResponse.objects.select_related('link__topic__department').order_by('-submitted_at')
    if search:
        qs = qs.filter(candidate_name__icontains=search) | CandidateResponse.objects.filter(
            candidate_email__icontains=search).union(qs.filter(candidate_name__icontains=search))
        qs = CandidateResponse.objects.select_related('link__topic__department').filter(
            candidate_name__icontains=search
        ) | CandidateResponse.objects.select_related('link__topic__department').filter(
            candidate_email__icontains=search
        )
        qs = qs.order_by('-submitted_at')
    return render(request, 'admin/responses.html', {
        'responses': qs, 'search': search, 'active_panel': 'responses'
    })

@login_required
def response_detail(request, resp_id):
    resp = get_object_or_404(CandidateResponse.objects.prefetch_related('answers'), id=resp_id)
    return render(request, 'admin/response_detail.html', {
        'response': resp, 'active_panel': 'responses'
    })


# ─── USERS ──────────────────────────────────────────────────────────────────
@superadmin_required
def users(request):
    active_users = AdminUser.objects.filter(is_active=True).order_by('created_at')
    pending_users = AdminUser.objects.filter(is_active=False).order_by('created_at')
    return render(request, 'admin/users.html', {
        'user_list': active_users,
        'pending_users': pending_users,
        'active_panel': 'users',
    })


@superadmin_required
def approve_user(request, user_id):
    u = get_object_or_404(AdminUser, id=user_id)
    action = request.POST.get('action', 'approve')
    if action == 'reject':
        u.delete()
        messages.success(request, f'{u.name} has been rejected and removed.')
    else:
        u.is_active = True
        u.save()
        messages.success(request, f'{u.name} approved and can now log in.')
    return redirect('users')


@superadmin_required
def admin_add_user(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('role', 'viewer')
        if not name or not email or len(password) < 6:
            messages.error(request, 'All fields required (min 6 char password).')
            return redirect('users')
        if AdminUser.objects.filter(email=email).exists():
            messages.error(request, f'Email {email} is already registered.')
            return redirect('users')
        if role not in ('superadmin', 'interviewer', 'viewer'):
            role = 'viewer'
        AdminUser.objects.create_user(
            email=email, password=password, name=name,
            role=role, is_active=True,
            is_staff=(role == 'superadmin'), is_superuser=(role == 'superadmin'),
        )
        messages.success(request, f'User {name} created successfully.')
    return redirect('users')

@superadmin_required
def change_role(request, user_id):
    if request.method == 'POST':
        u = get_object_or_404(AdminUser, id=user_id)
        new_role = request.POST.get('role')
        if new_role in ('superadmin', 'interviewer', 'viewer'):
            u.role = new_role
            u.save()
            messages.success(request, f'Role updated to {new_role}.')
    return redirect('users')

@superadmin_required
def delete_user(request, user_id):
    u = get_object_or_404(AdminUser, id=user_id)
    if u == request.user:
        messages.error(request, "You can't delete your own account.")
    else:
        u.delete()
        messages.success(request, f'User {u.name} removed.')
    return redirect('users')


# ─── COURSES (admin) ────────────────────────────────────────────────────────

@login_required
def course_list(request):
    courses = Course.objects.prefetch_related('materials', 'assignments').order_by('-created_at')
    return render(request, 'admin/courses.html', {
        'courses': courses, 'active_panel': 'courses',
    })


@editor_required
def create_course(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        if not title:
            messages.error(request, 'Course title is required.')
            return redirect('course_list')
        Course.objects.create(title=title, description=description, created_by=request.user)
        messages.success(request, f'Course "{title}" created.')
    return redirect('course_list')


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    materials = course.materials.all()
    assignments = course.assignments.select_related('user').prefetch_related('material_progress').all()
    all_users = AdminUser.objects.exclude(
        id__in=assignments.values_list('user_id', flat=True)
    ).order_by('name')
    # Annotate progress on each assignment
    total_materials = materials.count()
    assignment_data = []
    for a in assignments:
        completed = a.material_progress.filter(completed=True).count()
        pct = round((completed / total_materials) * 100) if total_materials else 0
        assignment_data.append({'assignment': a, 'completed': completed, 'total': total_materials, 'pct': pct})
    return render(request, 'admin/course_detail.html', {
        'course': course,
        'materials': materials,
        'assignment_data': assignment_data,
        'all_users': all_users,
        'active_panel': 'courses',
    })


@editor_required
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    course.delete()
    messages.success(request, 'Course deleted.')
    return redirect('course_list')


@editor_required
def add_material(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        material_type = request.POST.get('material_type', '')
        video_url = request.POST.get('video_url', '').strip()
        order = int(request.POST.get('order', 0) or 0)
        uploaded_file = request.FILES.get('file')

        if not title:
            messages.error(request, 'Material title is required.')
            return redirect('course_detail', course_id=course_id)
        if material_type == 'video_link' and not video_url:
            messages.error(request, 'Video URL is required for video links.')
            return redirect('course_detail', course_id=course_id)
        if material_type != 'video_link' and not uploaded_file:
            messages.error(request, 'File is required for this material type.')
            return redirect('course_detail', course_id=course_id)

        mat = CourseMaterial(course=course, title=title, material_type=material_type,
                             video_url=video_url, order=order)
        if uploaded_file:
            mat.file = uploaded_file
        mat.save()
        messages.success(request, f'"{title}" added.')
    return redirect('course_detail', course_id=course_id)


@editor_required
def delete_material(request, course_id, material_id):
    mat = get_object_or_404(CourseMaterial, id=material_id, course_id=course_id)
    mat.delete()
    messages.success(request, 'Material removed.')
    return redirect('course_detail', course_id=course_id)


@editor_required
def assign_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        user_ids = request.POST.getlist('user_ids')
        due_date = request.POST.get('due_date') or None
        count = 0
        for uid in user_ids:
            user = AdminUser.objects.filter(id=uid).first()
            if user:
                _, created = CourseAssignment.objects.get_or_create(
                    course=course, user=user,
                    defaults={'assigned_by': request.user, 'due_date': due_date},
                )
                if created:
                    count += 1
        messages.success(request, f'Course assigned to {count} user(s).')
    return redirect('course_detail', course_id=course_id)


@editor_required
def unassign_course(request, course_id, assignment_id):
    a = get_object_or_404(CourseAssignment, id=assignment_id, course_id=course_id)
    a.delete()
    messages.success(request, f'{a.user.name} removed from course.')
    return redirect('course_detail', course_id=course_id)


# ─── COURSES (user / my learning) ────────────────────────────────────────────

@login_required
def my_courses(request):
    assignments = (CourseAssignment.objects
                   .filter(user=request.user)
                   .select_related('course')
                   .prefetch_related('material_progress', 'course__materials')
                   .order_by('-assigned_at'))
    data = []
    for a in assignments:
        total = a.course.materials.count()
        completed = a.material_progress.filter(completed=True).count()
        pct = round((completed / total) * 100) if total else 0
        data.append({'assignment': a, 'total': total, 'completed': completed, 'pct': pct})
    return render(request, 'user/my_courses.html', {'data': data, 'active_panel': 'my_courses'})


@login_required
def my_course_detail(request, assignment_id):
    assignment = get_object_or_404(CourseAssignment, id=assignment_id, user=request.user)
    materials = assignment.course.materials.all()
    progress_map = {
        p.material_id: p
        for p in MaterialProgress.objects.filter(assignment=assignment)
    }
    items = []
    for mat in materials:
        prog = progress_map.get(mat.id)
        items.append({'material': mat, 'progress': prog, 'completed': prog.completed if prog else False})
    total = len(items)
    completed_count = sum(1 for i in items if i['completed'])
    pct = round((completed_count / total) * 100) if total else 0
    return render(request, 'user/my_course_detail.html', {
        'assignment': assignment,
        'items': items,
        'total': total,
        'completed_count': completed_count,
        'pct': pct,
        'active_panel': 'my_courses',
    })


def _embed_url(url):
    """Convert YouTube watch/short URLs to embed URL."""
    import re
    yt = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)', url)
    if yt:
        return f'https://www.youtube.com/embed/{yt.group(1)}'
    return url


@login_required
def view_material(request, assignment_id, material_id):
    assignment = get_object_or_404(CourseAssignment, id=assignment_id, user=request.user)
    material = get_object_or_404(CourseMaterial, id=material_id, course=assignment.course)

    prog, _ = MaterialProgress.objects.get_or_create(assignment=assignment, material=material)

    materials_list = list(assignment.course.materials.all())
    idx = next((i for i, m in enumerate(materials_list) if m.id == material.id), 0)
    prev_mat = materials_list[idx - 1] if idx > 0 else None
    next_mat = materials_list[idx + 1] if idx < len(materials_list) - 1 else None

    embed_url = _embed_url(material.video_url) if material.material_type == 'video_link' else ''

    return render(request, 'user/material_view.html', {
        'assignment': assignment,
        'material': material,
        'progress': prog,
        'prev_mat': prev_mat,
        'next_mat': next_mat,
        'embed_url': embed_url,
        'active_panel': 'my_courses',
    })


@login_required
@require_POST
def mark_material_complete(request, assignment_id, material_id):
    assignment = get_object_or_404(CourseAssignment, id=assignment_id, user=request.user)
    material = get_object_or_404(CourseMaterial, id=material_id, course=assignment.course)
    prog, _ = MaterialProgress.objects.get_or_create(assignment=assignment, material=material)
    prog.mark_complete()
    return JsonResponse({'ok': True, 'pct': assignment.progress_pct})


# ─── AJAX APIs ──────────────────────────────────────────────────────────────
@login_required
def api_topics_for_dept(request, dept_id):
    topics = Topic.objects.filter(department_id=dept_id).values('id', 'name')
    return JsonResponse({'topics': list(topics)})

@login_required
def api_question_count(request):
    topic_id = request.GET.get('topic_id')
    level = request.GET.get('level', 'basic')
    if not topic_id:
        return JsonResponse({'count': 0})
    count = Question.objects.filter(topic_id=topic_id, level=level).count()
    return JsonResponse({'count': count})


# ─── CANDIDATE FLOW ─────────────────────────────────────────────────────────
def candidate_landing(request, link_id):
    link = get_object_or_404(InterviewLink, id=link_id, is_active=True)
    return render(request, 'candidate/landing.html', {'link': link})

def candidate_start(request, link_id):
    link = get_object_or_404(InterviewLink, id=link_id, is_active=True)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        if not name or not email or '@' not in email:
            messages.error(request, 'Please enter valid name and email.')
            return redirect('candidate_landing', link_id=link_id)

        # Sample random questions
        pool = list(link.topic.questions.filter(level=link.level))
        selected = random.sample(pool, min(link.question_count, len(pool)))

        # Create response + blank answers
        resp = CandidateResponse.objects.create(
            link=link, candidate_name=name, candidate_email=email
        )
        for i, q in enumerate(selected):
            QuestionAnswer.objects.create(
                response=resp, question_text=q.text, order=i
            )

        request.session[f'interview_{resp.id}'] = {'started': True}
        return redirect('candidate_question', resp_id=resp.id, q_num=0)

    return redirect('candidate_landing', link_id=link_id)


def candidate_question(request, resp_id, q_num):
    resp = get_object_or_404(CandidateResponse.objects.prefetch_related('answers'), id=resp_id)
    answers = list(resp.answers.order_by('order'))
    if q_num >= len(answers):
        return redirect('submit_interview', resp_id=resp_id)
    answer = answers[q_num]
    total = len(answers)
    link = resp.link
    return render(request, 'candidate/question.html', {
        'resp': resp,
        'answer': answer,
        'q_num': q_num,
        'total': total,
        'progress_pct': round((q_num / total) * 100),
        'is_last': q_num == total - 1,
        'link': link,
    })


@csrf_exempt
def save_answer(request, resp_id, q_num):
    """AJAX endpoint to save video blob or text answer"""
    resp = get_object_or_404(CandidateResponse, id=resp_id)
    answers = list(resp.answers.order_by('order'))
    if q_num >= len(answers):
        return JsonResponse({'ok': False, 'error': 'Invalid question number'})
    answer = answers[q_num]

    if request.method == 'POST':
        video_file = request.FILES.get('video')
        text = request.POST.get('text_answer', '').strip()
        if video_file:
            answer.video_recording = video_file
            answer.is_recorded = True
        if text:
            answer.text_answer = text
        answer.save()
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False})


@csrf_exempt
def save_snapshot(request, resp_id):
    """AJAX endpoint: saves a camera snapshot (base64 JPEG) for text-mode interviews."""
    if request.method != 'POST':
        return JsonResponse({'ok': False})
    resp = get_object_or_404(CandidateResponse, id=resp_id)
    import base64
    from django.core.files.base import ContentFile
    data = request.POST.get('image', '')
    q_num = int(request.POST.get('q_num', 0))
    if not data:
        return JsonResponse({'ok': False, 'error': 'No image data'})
    try:
        if ',' in data:
            data = data.split(',', 1)[1]
        image_bytes = base64.b64decode(data)
        snapshot = CandidateSnapshot(response=resp, q_num=q_num)
        snapshot.image.save(f'{resp_id}_{q_num}_{uuid.uuid4().hex[:8]}.jpg', ContentFile(image_bytes), save=True)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


def submit_interview(request, resp_id):
    resp = get_object_or_404(CandidateResponse, id=resp_id)
    return render(request, 'candidate/scoring.html', {'resp': resp})


def interview_results(request, resp_id):
    resp = get_object_or_404(
        CandidateResponse.objects.prefetch_related('answers'), id=resp_id
    )
    # If not scored yet, score now via AI
    if resp.ai_score is None:
        _score_with_ai(resp)
        resp.refresh_from_db()

    answers = list(resp.answers.order_by('order'))
    total_pts = sum(a.ai_score or 0 for a in answers)
    max_pts = len(answers) * 10
    pct = round((total_pts / max_pts) * 100) if max_pts else 0

    if pct >= 90:   grade = 'A+'
    elif pct >= 80: grade = 'A'
    elif pct >= 70: grade = 'B+'
    elif pct >= 60: grade = 'B'
    elif pct >= 50: grade = 'C'
    else:           grade = 'D'

    grade_color = ('var(--teal)' if pct >= 70 else 'var(--amber)' if pct >= 50 else 'var(--rose)')

    return render(request, 'candidate/results.html', {
        'resp': resp,
        'answers': answers,
        'total_pts': round(total_pts, 1),
        'max_pts': max_pts,
        'pct': pct,
        'grade': grade,
        'grade_color': grade_color,
    })


def _score_with_ai(resp: CandidateResponse):
    """Call Anthropic API to score all answers and save to DB."""
    answers = list(resp.answers.order_by('order'))
    lines = []
    for i, a in enumerate(answers):
        if a.is_recorded:
            ans_text = '[Candidate submitted a video response]'
        else:
            ans_text = a.text_answer or 'No answer provided'
        lines.append(f'Q{i+1}: {a.question_text}\nA{i+1}: {ans_text}')

    prompt = (
        f'You are an expert interview evaluator for {resp.dept_name} department, '
        f'{resp.topic_name} topic, {resp.level} level.\n\n'
        'Evaluate each interview response and provide a score out of 10 and one concise feedback sentence.\n\n'
        'Questions and Answers:\n' + '\n\n'.join(lines) + '\n\n'
        'Respond ONLY with a JSON array (no markdown, no extra text):\n'
        '[{"score": <0-10>, "feedback": "<one sentence>"}, ...]'
    )

    payload = json.dumps({
        'model': 'claude-sonnet-4-20250514',
        'max_tokens': 1000,
        'messages': [{'role': 'user', 'content': prompt}]
    }).encode()

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        text = ''
        for block in data.get('content', []):
            if block.get('type') == 'text':
                text = block['text']
                break
        text = text.replace('```json', '').replace('```', '').strip()
        scored = json.loads(text)

        total = 0
        for i, a in enumerate(answers):
            if i < len(scored):
                a.ai_score = float(scored[i].get('score', 0))
                a.ai_feedback = scored[i].get('feedback', '')
                a.save()
                total += a.ai_score

        max_pts = len(answers) * 10
        resp.ai_score = round((total / max_pts) * 100, 1) if max_pts else 0
        resp.save()
    except Exception as e:
        print(f'AI scoring error: {e}')
