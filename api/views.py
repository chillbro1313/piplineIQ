import random
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Pipeline, PipelineRun, Stage
from .serializers import (
    PipelineSerializer, PipelineCreateSerializer,
    PipelineRunSerializer, PipelineRunListSerializer
)


def random_commit_hash():
    return ''.join(random.choices('0123456789abcdef', k=40))


# ─── PIPELINE ENDPOINTS ───────────────────────────────────────────

@api_view(['GET', 'POST'])
def pipeline_list(request):
    if request.method == 'GET':
        pipelines = Pipeline.objects.all()
        serializer = PipelineSerializer(pipelines, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = PipelineCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def pipeline_detail(request, pk):
    try:
        pipeline = Pipeline.objects.get(pk=pk)
    except Pipeline.DoesNotExist:
        return Response({'error': 'Pipeline not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = PipelineSerializer(pipeline)
    return Response(serializer.data)


@api_view(['GET'])
def pipeline_runs(request, pk):
    try:
        pipeline = Pipeline.objects.get(pk=pk)
    except Pipeline.DoesNotExist:
        return Response({'error': 'Pipeline not found'}, status=status.HTTP_404_NOT_FOUND)

    runs = pipeline.runs.all()

    status_filter = request.query_params.get('status')
    if status_filter:
        runs = runs.filter(status=status_filter)

    limit = request.query_params.get('limit')
    if limit:
        runs = runs[:int(limit)]

    serializer = PipelineRunListSerializer(runs, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def pipeline_trigger(request, pk):
    try:
        pipeline = Pipeline.objects.get(pk=pk)
    except Pipeline.DoesNotExist:
        return Response({'error': 'Pipeline not found'}, status=status.HTTP_404_NOT_FOUND)

    last_run = pipeline.runs.first()
    run_number = (last_run.run_number + 1) if last_run else 1

    run = PipelineRun.objects.create(
        pipeline=pipeline,
        status='running',
        started_at=timezone.now(),
        commit_hash=random_commit_hash(),
        commit_message='feat: triggered via API',
        author='api-user',
        run_number=run_number,
    )

    stage_names = ['source', 'build', 'test', 'push', 'deploy']
    for i, name in enumerate(stage_names):
        Stage.objects.create(
            pipeline_run=run,
            name=name,
            status='running' if i == 0 else 'pending',
            order=i,
            started_at=timezone.now() if i == 0 else None,
        )

    serializer = PipelineRunSerializer(run)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ─── RUN ENDPOINTS ────────────────────────────────────────────────

@api_view(['GET'])
def run_detail(request, pk):
    try:
        run = PipelineRun.objects.get(pk=pk)
    except PipelineRun.DoesNotExist:
        return Response({'error': 'Run not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = PipelineRunSerializer(run)
    return Response(serializer.data)


@api_view(['GET'])
def all_runs(request):
    runs = PipelineRun.objects.select_related('pipeline').all()

    status_filter = request.query_params.get('status')
    if status_filter:
        runs = runs.filter(status=status_filter)

    pipeline_id = request.query_params.get('pipeline_id')
    if pipeline_id:
        runs = runs.filter(pipeline_id=pipeline_id)

    search = request.query_params.get('search')
    if search:
        runs = runs.filter(
            Q(commit_message__icontains=search) |
            Q(author__icontains=search) |
            Q(pipeline__name__icontains=search)
        )

    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    total = runs.count()
    start = (page - 1) * page_size
    end = start + page_size

    serializer = PipelineRunListSerializer(runs[start:end], many=True)
    return Response({
        'results': serializer.data,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
    })


# ─── METRICS ENDPOINT ─────────────────────────────────────────────

@api_view(['GET'])
def metrics(request):
    now = timezone.now()

    total_pipelines = Pipeline.objects.count()
    total_runs = PipelineRun.objects.count()
    success_runs = PipelineRun.objects.filter(status='success').count()
    overall_success_rate = round((success_runs / total_runs * 100), 1) if total_runs > 0 else 0
    avg_duration = PipelineRun.objects.filter(
        status='success', duration__isnull=False
    ).aggregate(avg=Avg('duration'))['avg'] or 0
    active_runs = PipelineRun.objects.filter(status='running').count()

    # Daily success vs failure (last 30 days)
    daily_data = []
    for i in range(29, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_runs = PipelineRun.objects.filter(started_at__gte=day_start, started_at__lt=day_end)
        daily_data.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'success': day_runs.filter(status='success').count(),
            'failed': day_runs.filter(status='failed').count(),
            'total': day_runs.count(),
        })

    # Average build duration per pipeline
    pipeline_durations = []
    for pipeline in Pipeline.objects.all():
        avg = pipeline.runs.filter(
            status='success', duration__isnull=False
        ).aggregate(avg=Avg('duration'))['avg'] or 0
        pipeline_durations.append({
            'name': pipeline.name,
            'avg_duration': round(avg),
        })

    # Deployment frequency (last 30 days)
    deploy_freq = []
    for i in range(29, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = PipelineRun.objects.filter(
            started_at__gte=day_start,
            started_at__lt=day_end,
            status='success'
        ).count()
        deploy_freq.append({'date': day_start.strftime('%m/%d'), 'deploys': count})

    # Most common failure stage
    failure_stages = Stage.objects.filter(status='failed').values('name').annotate(
        count=Count('id')
    ).order_by('-count')
    failure_stage_data = [{'stage': s['name'], 'count': s['count']} for s in failure_stages]

    return Response({
        'summary': {
            'total_pipelines': total_pipelines,
            'total_runs': total_runs,
            'success_rate': overall_success_rate,
            'avg_duration': round(avg_duration),
            'active_runs': active_runs,
        },
        'daily_runs': daily_data,
        'pipeline_durations': pipeline_durations,
        'deploy_frequency': deploy_freq,
        'failure_stages': failure_stage_data,
    })