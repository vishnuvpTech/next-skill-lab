import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class AdminUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('role', 'superadmin')
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra)


class AdminUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('interviewer', 'Interviewer'),
        ('viewer', 'Viewer'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    objects = AdminUserManager()

    def __str__(self):
        return f'{self.name} ({self.role})'

    @property
    def can_edit(self):
        return self.role in ('superadmin', 'interviewer')

    @property
    def is_superadmin(self):
        return self.role == 'superadmin'


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def topic_count(self):
        return self.topics.count()

    @property
    def question_count(self):
        return Question.objects.filter(topic__department=self).count()


class Topic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=150)
    created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.department.name} / {self.name}'

    def question_count_by_level(self, level):
        return self.questions.filter(level=level).count()


class Question(models.Model):
    LEVEL_CHOICES = [
        ('basic', 'Basic'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='questions')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    text = models.TextField()
    answer = models.TextField(blank=True)
    created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'[{self.level}] {self.text[:60]}'


class InterviewLink(models.Model):
    LEVEL_CHOICES = Question.LEVEL_CHOICES
    MODE_CHOICES = [('video', 'Video Recording'), ('text', 'Text Entry')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='links')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='video')
    question_count = models.PositiveIntegerField(default=5)
    time_per_question = models.PositiveIntegerField(default=2, help_text='Minutes per question, 0 = no limit')
    created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.topic} [{self.level}] x{self.question_count}'

    @property
    def response_count(self):
        return self.responses.count()

    @property
    def dept_name(self):
        return self.topic.department.name

    @property
    def topic_name(self):
        return self.topic.name


class CandidateResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    link = models.ForeignKey(InterviewLink, on_delete=models.CASCADE, related_name='responses')
    candidate_name = models.CharField(max_length=150)
    candidate_email = models.EmailField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    ai_score = models.FloatField(null=True, blank=True)  # percentage 0-100

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.candidate_name} — {self.link.topic.name}'

    @property
    def dept_name(self):
        return self.link.topic.department.name

    @property
    def topic_name(self):
        return self.link.topic.name

    @property
    def level(self):
        return self.link.level

    @property
    def answered_count(self):
        return self.answers.filter(is_recorded=True).count() + self.answers.exclude(text_answer='').count()


class QuestionAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    response = models.ForeignKey(CandidateResponse, on_delete=models.CASCADE, related_name='answers')
    question_text = models.TextField()
    text_answer = models.TextField(blank=True)
    video_recording = models.FileField(upload_to='recordings/', null=True, blank=True)
    is_recorded = models.BooleanField(default=False)
    ai_score = models.FloatField(null=True, blank=True)   # 0-10
    ai_feedback = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Answer #{self.order} for {self.response}'


class CandidateSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    response = models.ForeignKey(CandidateResponse, on_delete=models.CASCADE, related_name='snapshots')
    image = models.ImageField(upload_to='snapshots/')
    q_num = models.PositiveIntegerField(default=0)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['captured_at']

    def __str__(self):
        return f'Snapshot for {self.response} Q{self.q_num}'


# ─── COURSE MANAGEMENT ──────────────────────────────────────────────────────

class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, related_name='created_courses')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def material_count(self):
        return self.materials.count()

    @property
    def assignment_count(self):
        return self.assignments.count()


def course_material_upload(instance, filename):
    return f'courses/{instance.course_id}/{instance.material_type}/{filename}'


class CourseMaterial(models.Model):
    TYPE_CHOICES = [
        ('video_file', 'Video File'),
        ('pdf', 'PDF'),
        ('doc', 'Document'),
        ('image', 'Image'),
        ('video_link', 'Video Link'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=200)
    material_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    file = models.FileField(upload_to=course_material_upload, null=True, blank=True)
    video_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'{self.course.title} — {self.title}'

    @property
    def type_icon(self):
        return {'video_file': '🎬', 'pdf': '📄', 'doc': '📝', 'image': '🖼', 'video_link': '▶'}.get(self.material_type, '📎')


class CourseAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    user = models.ForeignKey(AdminUser, on_delete=models.CASCADE, related_name='course_assignments')
    assigned_by = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True, related_name='assignments_given')
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('course', 'user')

    def __str__(self):
        return f'{self.user.name} → {self.course.title}'

    @property
    def progress_pct(self):
        total = self.course.materials.count()
        if total == 0:
            return 0
        completed = self.material_progress.filter(completed=True).count()
        return round((completed / total) * 100)

    @property
    def completed_count(self):
        return self.material_progress.filter(completed=True).count()

    @property
    def is_complete(self):
        total = self.course.materials.count()
        return total > 0 and self.completed_count == total


class MaterialProgress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(CourseAssignment, on_delete=models.CASCADE, related_name='material_progress')
    material = models.ForeignKey(CourseMaterial, on_delete=models.CASCADE, related_name='progress_records')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('assignment', 'material')

    def __str__(self):
        return f'{self.assignment} — {self.material.title}'

    def mark_complete(self):
        if not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            self.save()
