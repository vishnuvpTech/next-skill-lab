import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interviews', '0002_add_answer_to_question'),
    ]

    operations = [
        migrations.AddField(
            model_name='interviewlink',
            name='mode',
            field=models.CharField(
                choices=[('video', 'Video Recording'), ('text', 'Text Entry')],
                default='video',
                max_length=10,
            ),
        ),
        migrations.CreateModel(
            name='CandidateSnapshot',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('image', models.ImageField(upload_to='snapshots/')),
                ('q_num', models.PositiveIntegerField(default=0)),
                ('captured_at', models.DateTimeField(auto_now_add=True)),
                ('response', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='snapshots',
                    to='interviews.candidateresponse',
                )),
            ],
            options={'ordering': ['captured_at']},
        ),
    ]
