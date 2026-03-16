from django.urls import path
from . import views

urlpatterns = [
    # Pipeline endpoints
    path('pipelines/', views.pipeline_list, name='pipeline-list'),
    path('pipelines/<int:pk>/', views.pipeline_detail, name='pipeline-detail'),
    path('pipelines/<int:pk>/runs/', views.pipeline_runs, name='pipeline-runs'),
    path('pipelines/<int:pk>/trigger/', views.pipeline_trigger, name='pipeline-trigger'),

    # Run endpoints
    path('runs/', views.all_runs, name='all-runs'),
    path('runs/<int:pk>/', views.run_detail, name='run-detail'),

    # Metrics endpoint
    path('metrics/', views.metrics, name='metrics'),
]
