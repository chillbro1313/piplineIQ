from rest_framework import serializers
from .models import Pipeline, PipelineRun, Stage


class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = ['id', 'name', 'status', 'started_at', 'finished_at', 'duration', 'logs', 'order']


class PipelineRunSerializer(serializers.ModelSerializer):
    stages = StageSerializer(many=True, read_only=True)
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)

    class Meta:
        model = PipelineRun
        fields = [
            'id', 'pipeline', 'pipeline_name', 'status',
            'started_at', 'finished_at', 'duration',
            'commit_hash', 'commit_message', 'author',
            'run_number', 'stages'
        ]


class PipelineRunListSerializer(serializers.ModelSerializer):
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)

    class Meta:
        model = PipelineRun
        fields = [
            'id', 'pipeline', 'pipeline_name', 'status',
            'started_at', 'finished_at', 'duration',
            'commit_hash', 'commit_message', 'author', 'run_number'
        ]


class PipelineSerializer(serializers.ModelSerializer):
    latest_run = PipelineRunListSerializer(read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    total_runs = serializers.SerializerMethodField()

    class Meta:
        model = Pipeline
        fields = [
            'id', 'name', 'repo_url', 'branch', 'trigger',
            'environment', 'created_at', 'updated_at',
            'latest_run', 'success_rate', 'total_runs'
        ]

    def get_total_runs(self, obj):
        return obj.runs.count()


class PipelineCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pipeline
        fields = ['id', 'name', 'repo_url', 'branch', 'trigger', 'environment', 'created_at']