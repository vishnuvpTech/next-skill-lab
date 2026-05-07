# TalentLens — Mock Interview Platform

A Django application for conducting mock interviews with video recording, AI scoring, and multi-admin role management.

## Features

- **Multi-Admin Auth** — Super Admin, Interviewer, Viewer roles
- **Department → Topic → Question** hierarchy with Basic / Intermediate / Advanced levels
- **Interview Link Generator** — choose topic, level, question count, timer
- **Video Recording** — candidate records each answer via webcam (MediaRecorder API)
- **AI Scoring** — instant results via Anthropic Claude after submission
- **Response Review** — admins view video responses + AI scores and feedback

## Quick Start

### 1. Install dependencies
```bash
pip install django
```

### 2. Run migrations
```bash
python manage.py migrate
```

### 3. Start the server
```bash
python manage.py runserver
```

### 4. Open in browser
- Admin panel: http://127.0.0.1:8000/login/
- Default credentials:
  - Super Admin: `superadmin@demo.com` / `demo123`
  - Interviewer: `interviewer@demo.com` / `demo123`

## User Roles

| Role | Permissions |
|------|-------------|
| Super Admin | Full access, user management, change roles |
| Interviewer | Manage departments/topics/questions, generate links, view responses |
| Viewer | Read-only access to all panels |

## Workflow

1. **Admin**: Create departments → add topics → add questions (Basic/Intermediate/Advanced)
2. **Admin**: Go to Links → Generate Link (select topic + level + count + timer)
3. **Share**: Copy the generated URL and send to candidates
4. **Candidate**: Opens link → enters name/email → records video for each question
5. **AI Scoring**: After submission, Claude scores each answer instantly
6. **Admin**: Reviews responses with video playback + AI scores in Responses panel

## Project Structure

```
talentlens/
├── interviews/
│   ├── models.py          # AdminUser, Department, Topic, Question, InterviewLink, CandidateResponse, QuestionAnswer
│   ├── views.py           # All views (auth, admin panel, candidate flow, AI scoring)
│   ├── urls.py            # URL routing
│   └── admin.py           # Django admin registration
├── templates/
│   ├── base.html          # Base template
│   ├── base_admin.html    # Admin layout with sidebar
│   ├── auth/              # Login, Register
│   ├── admin/             # Dashboard, Departments, Topics, Questions, Links, Responses, Users
│   └── candidate/         # Landing, Question (video), Scoring, Results
├── static/
│   └── css/main.css       # All styles
├── media/                 # Uploaded video recordings
└── manage.py
```

## AI Scoring

The app calls the Anthropic API (`claude-sonnet-4-20250514`) after interview submission to score each answer 0-10 and provide one-line feedback. Results are displayed instantly to the candidate.

To use AI scoring, ensure the server can reach `api.anthropic.com`. The API key is read from the request headers in the HTML version; in the Django version, scoring happens server-side.

**Note**: For production, add your Anthropic API key to settings:
```python
# talentlens/settings.py
ANTHROPIC_API_KEY = 'your-key-here'
```
And update `_score_with_ai()` in views.py to use it in the Authorization header.
