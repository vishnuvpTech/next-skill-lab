import uuid
import interviews.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interviews', '0003_interviewlink_mode_candidatesnapshot'),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_courses', to='interviews.adminuser',
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='CourseMaterial',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('material_type', models.CharField(
                    choices=[('video_file','Video File'),('pdf','PDF'),('doc','Document'),('image','Image'),('video_link','Video Link')],
                    max_length=20,
                )),
                ('file', models.FileField(blank=True, null=True, upload_to=interviews.models.course_material_upload)),
                ('video_url', models.URLField(blank=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='materials', to='interviews.course',
                )),
            ],
            options={'ordering': ['order', 'created_at']},
        ),
        migrations.CreateModel(
            name='CourseAssignment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('course', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assignments', to='interviews.course',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='course_assignments', to='interviews.adminuser',
                )),
                ('assigned_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assignments_given', to='interviews.adminuser',
                )),
            ],
            options={'unique_together': {('course', 'user')}},
        ),
        migrations.CreateModel(
            name='MaterialProgress',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('completed', models.BooleanField(default=False)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('assignment', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='material_progress', to='interviews.courseassignment',
                )),
                ('material', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='progress_records', to='interviews.coursematerial',
                )),
            ],
            options={'unique_together': {('assignment', 'material')}},
        ),
    ]
