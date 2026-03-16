from django.db import models
from django.utils import timezone


class Pipeline(models.Model):
    TRIGGER_CHOICES = [
        ('push', 'Push'),
        ('manual', 'Manual'),
        ('scheduled', 'Scheduled'),
    ]
    ENV_CHOICES = [
        ('dev', 'Development'),
        ('staging', 'Staging'),
        ('production', 'Production'),
    ]

    name = models.CharField(max_length=200)
    repo_url = models.URLField(max_length=500)
    branch = models.CharField(max_length=100, default='main')
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default='push')
    environment = models.CharField(max_length=20, choices=ENV_CHOICES, default='dev')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.branch})"

    @property
    def success_rate(self):
        total = self.runs.count()
        if total == 0:
            return 0
        success = self.runs.filter(status='success').count()
        return round((success / total) * 100, 1)


class PipelineRun(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='runs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    commit_hash = models.CharField(max_length=40, blank=True, default='')
    commit_message = models.TextField(blank=True, default='')
    author = models.CharField(max_length=100, blank=True, default='')
    run_number = models.IntegerField(default=1)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.pipeline.name} #{self.run_number} - {self.status}"


class Stage(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    NAME_CHOICES = [
        ('source', 'Source'),
        ('build', 'Build'),
        ('test', 'Test'),
        ('push', 'Push to ECR'),
        ('deploy', 'Deploy to EC2'),
    ]

    pipeline_run = models.ForeignKey(PipelineRun, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=50, choices=NAME_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    logs = models.TextField(blank=True, default='')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.pipeline_run} - {self.name}"