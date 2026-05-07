from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_redirect, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    path('admin-panel/', views.dashboard, name='dashboard'),
    path('admin-panel/departments/', views.departments, name='departments'),
    path('admin-panel/departments/add/', views.add_department, name='add_department'),
    path('admin-panel/departments/<uuid:dept_id>/delete/', views.delete_department, name='delete_department'),

    path('admin-panel/topics/<uuid:dept_id>/', views.topics, name='topics'),
    path('admin-panel/topics/<uuid:dept_id>/add/', views.add_topic, name='add_topic'),
    path('admin-panel/topics/<uuid:topic_id>/delete/', views.delete_topic, name='delete_topic'),

    path('admin-panel/questions/', views.questions_home, name='questions_home'),
    path('admin-panel/questions/<uuid:topic_id>/', views.questions, name='questions'),
    path('admin-panel/questions/<uuid:topic_id>/add/', views.add_question, name='add_question'),
    path('admin-panel/questions/<uuid:topic_id>/bulk-add/', views.bulk_add_questions, name='bulk_add_questions'),
    path('admin-panel/questions/<uuid:q_id>/delete/', views.delete_question, name='delete_question'),

    path('admin-panel/links/', views.links, name='links'),
    path('admin-panel/links/add/', views.add_link, name='add_link'),
    path('admin-panel/links/<uuid:link_id>/delete/', views.delete_link, name='delete_link'),

    path('admin-panel/responses/', views.responses, name='responses'),
    path('admin-panel/responses/<uuid:resp_id>/', views.response_detail, name='response_detail'),

    path('admin-panel/users/', views.users, name='users'),
    path('admin-panel/users/add/', views.admin_add_user, name='admin_add_user'),
    path('admin-panel/users/<uuid:user_id>/approve/', views.approve_user, name='approve_user'),
    path('admin-panel/users/<uuid:user_id>/role/', views.change_role, name='change_role'),
    path('admin-panel/users/<uuid:user_id>/delete/', views.delete_user, name='delete_user'),

    # Course management (admin)
    path('admin-panel/courses/', views.course_list, name='course_list'),
    path('admin-panel/courses/create/', views.create_course, name='create_course'),
    path('admin-panel/courses/<uuid:course_id>/', views.course_detail, name='course_detail'),
    path('admin-panel/courses/<uuid:course_id>/delete/', views.delete_course, name='delete_course'),
    path('admin-panel/courses/<uuid:course_id>/materials/add/', views.add_material, name='add_material'),
    path('admin-panel/courses/<uuid:course_id>/materials/<uuid:material_id>/delete/', views.delete_material, name='delete_material'),
    path('admin-panel/courses/<uuid:course_id>/assign/', views.assign_course, name='assign_course'),
    path('admin-panel/courses/<uuid:course_id>/assignments/<uuid:assignment_id>/remove/', views.unassign_course, name='unassign_course'),

    # My Learning (user)
    path('my-courses/', views.my_courses, name='my_courses'),
    path('my-courses/<uuid:assignment_id>/', views.my_course_detail, name='my_course_detail'),
    path('my-courses/<uuid:assignment_id>/material/<uuid:material_id>/', views.view_material, name='view_material'),
    path('my-courses/<uuid:assignment_id>/material/<uuid:material_id>/complete/', views.mark_material_complete, name='mark_material_complete'),

    path('api/topics-for-dept/<uuid:dept_id>/', views.api_topics_for_dept, name='api_topics_for_dept'),
    path('api/question-count/', views.api_question_count, name='api_question_count'),

    path('interview/<uuid:link_id>/', views.candidate_landing, name='candidate_landing'),
    path('interview/<uuid:link_id>/start/', views.candidate_start, name='candidate_start'),
    path('interview/session/<uuid:resp_id>/question/<int:q_num>/', views.candidate_question, name='candidate_question'),
    path('interview/session/<uuid:resp_id>/save/<int:q_num>/', views.save_answer, name='save_answer'),
    path('interview/session/<uuid:resp_id>/snapshot/', views.save_snapshot, name='save_snapshot'),
    path('interview/session/<uuid:resp_id>/submit/', views.submit_interview, name='submit_interview'),
    path('interview/session/<uuid:resp_id>/results/', views.interview_results, name='interview_results'),
]
