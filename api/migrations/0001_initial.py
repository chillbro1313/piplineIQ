from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Pipeline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('repo_url', models.URLField(max_length=500)),
                ('branch', models.CharField(default='main', max_length=100)),
                ('trigger', models.CharField(choices=[('push', 'Push'), ('manual', 'Manual'), ('scheduled', 'Scheduled')], default='push', max_length=20)),
                ('environment', models.CharField(choices=[('dev', 'Development'), ('staging', 'Staging'), ('production', 'Production')], default='dev', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PipelineRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('success', 'Success'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('duration', models.IntegerField(blank=True, null=True)),
                ('commit_hash', models.CharField(blank=True, default='', max_length=40)),
                ('commit_message', models.TextField(blank=True, default='')),
                ('author', models.CharField(blank=True, default='', max_length=100)),
                ('run_number', models.IntegerField(default=1)),
                ('pipeline', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='api.pipeline')),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
        migrations.CreateModel(
            name='Stage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('source', 'Source'), ('build', 'Build'), ('test', 'Test'), ('push', 'Push to ECR'), ('deploy', 'Deploy to EC2')], max_length=50)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('success', 'Success'), ('failed', 'Failed'), ('skipped', 'Skipped')], default='pending', max_length=20)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('duration', models.IntegerField(blank=True, null=True)),
                ('logs', models.TextField(blank=True, default='')),
                ('order', models.IntegerField(default=0)),
                ('pipeline_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stages', to='api.pipelinerun')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
    ]