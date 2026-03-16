import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import Pipeline, PipelineRun, Stage


# ─── Log Templates ────────────────────────────────────────────────

SOURCE_LOGS_SUCCESS = """[2024-03-15 10:00:01] INFO  Initializing source checkout
[2024-03-15 10:00:01] INFO  Connecting to GitHub repository
[2024-03-15 10:00:02] INFO  Fetching refs from origin
[2024-03-15 10:00:03] INFO  HEAD is now at {commit}
[2024-03-15 10:00:03] INFO  Checking out branch: {branch}
[2024-03-15 10:00:04] INFO  Submodules initialized (0 found)
[2024-03-15 10:00:04] INFO  Workspace cleaned and ready
[2024-03-15 10:00:04] SUCCESS Source checkout completed in {duration}s"""

BUILD_LOGS_SUCCESS = """[2024-03-15 10:00:05] INFO  Starting Docker build
[2024-03-15 10:00:05] INFO  Build context: . (12.3 MB)
[2024-03-15 10:00:06] INFO  Step 1/8 : FROM node:18-alpine
[2024-03-15 10:00:08] INFO  Step 2/8 : WORKDIR /app
[2024-03-15 10:00:08] INFO  Step 3/8 : COPY package*.json ./
[2024-03-15 10:00:09] INFO  Step 4/8 : RUN npm ci --only=production
[2024-03-15 10:00:24] INFO  npm warn deprecated: 2 packages
[2024-03-15 10:00:31] INFO  Added 847 packages in 22s
[2024-03-15 10:00:31] INFO  Step 5/8 : COPY . .
[2024-03-15 10:00:32] INFO  Step 6/8 : RUN npm run build
[2024-03-15 10:00:45] INFO  Build output: dist/ (4.2 MB)
[2024-03-15 10:00:45] INFO  Step 7/8 : EXPOSE 3000
[2024-03-15 10:00:45] INFO  Step 8/8 : CMD ["node", "dist/server.js"]
[2024-03-15 10:00:46] INFO  Tagging image: {pipeline}:latest
[2024-03-15 10:00:46] SUCCESS Docker image built successfully in {duration}s"""

BUILD_LOGS_FAILED = """[2024-03-15 10:00:05] INFO  Starting Docker build
[2024-03-15 10:00:05] INFO  Build context: . (12.3 MB)
[2024-03-15 10:00:06] INFO  Step 1/8 : FROM node:18-alpine
[2024-03-15 10:00:08] INFO  Step 3/8 : COPY package*.json ./
[2024-03-15 10:00:09] INFO  Step 4/8 : RUN npm ci --only=production
[2024-03-15 10:00:24] ERROR npm ERR! code ERESOLVE
[2024-03-15 10:00:24] ERROR npm ERR! ERESOLVE unable to resolve dependency tree
[2024-03-15 10:00:24] ERROR npm ERR! peer dep missing: react@^17, got react@18.2.0
[2024-03-15 10:00:24] ERROR npm ERR! Fix the upstream dependency conflict
[2024-03-15 10:00:25] FATAL Build failed with exit code 1"""

TEST_LOGS_SUCCESS = """[2024-03-15 10:01:00] INFO  Starting test suite
[2024-03-15 10:01:00] INFO  Test runner: Jest v29.5.0
[2024-03-15 10:01:01] INFO  Loading test configuration...
[2024-03-15 10:01:02] INFO  Collecting test files...
[2024-03-15 10:01:03] INFO  Found 47 test suites
[2024-03-15 10:01:10] PASS  tests/unit/auth.test.js (12 tests)
[2024-03-15 10:01:14] PASS  tests/unit/pipeline.test.js (8 tests)
[2024-03-15 10:01:18] PASS  tests/integration/api.test.js (23 tests)
[2024-03-15 10:01:22] PASS  tests/e2e/deploy.test.js (4 tests)
[2024-03-15 10:01:30] INFO  Coverage: 87.3% statements, 82.1% branches
[2024-03-15 10:01:31] SUCCESS All 47 tests passed in {duration}s"""

TEST_LOGS_FAILED = """[2024-03-15 10:01:00] INFO  Starting test suite
[2024-03-15 10:01:00] INFO  Test runner: Jest v29.5.0
[2024-03-15 10:01:03] INFO  Found 47 test suites
[2024-03-15 10:01:10] PASS  tests/unit/auth.test.js (12 tests)
[2024-03-15 10:01:14] FAIL  tests/unit/pipeline.test.js
[2024-03-15 10:01:14] ERROR   ● PipelineService › should handle concurrent runs
[2024-03-15 10:01:14] ERROR     Expected: resolved
[2024-03-15 10:01:14] ERROR     Received: TypeError: Cannot read properties of undefined (reading 'id')
[2024-03-15 10:01:14] ERROR     at PipelineService.trigger (src/services/pipeline.js:45:18)
[2024-03-15 10:01:15] INFO  Test Suites: 1 failed, 46 passed
[2024-03-15 10:01:15] FATAL 3 tests failed. Pipeline aborted."""

PUSH_LOGS_SUCCESS = """[2024-03-15 10:02:00] INFO  Pushing image to Amazon ECR
[2024-03-15 10:02:00] INFO  AWS Region: eu-west-1
[2024-03-15 10:02:01] INFO  Authenticating with ECR registry
[2024-03-15 10:02:02] INFO  Login Succeeded
[2024-03-15 10:02:03] INFO  Tagging: {pipeline}:latest → 123456789.dkr.ecr.eu-west-1.amazonaws.com/{pipeline}:latest
[2024-03-15 10:02:03] INFO  Pushing layer: sha256:a3ed95ca...
[2024-03-15 10:02:15] INFO  Pushing layer: sha256:f71b0a57...
[2024-03-15 10:02:28] INFO  Push complete: digest sha256:9c5f32e1
[2024-03-15 10:02:29] SUCCESS Image pushed to ECR in {duration}s"""

DEPLOY_LOGS_SUCCESS = """[2024-03-15 10:03:00] INFO  Starting deployment to EC2
[2024-03-15 10:03:00] INFO  Target: i-0a1b2c3d4e5f6789 (t3.medium)
[2024-03-15 10:03:01] INFO  Connecting via SSH to ec2-54-12-34-56.eu-west-1.compute.amazonaws.com
[2024-03-15 10:03:02] INFO  SSH connection established
[2024-03-15 10:03:02] INFO  Pulling latest image from ECR...
[2024-03-15 10:03:14] INFO  docker pull complete
[2024-03-15 10:03:15] INFO  Stopping existing container: {pipeline}-prod
[2024-03-15 10:03:16] INFO  Starting new container with zero-downtime swap
[2024-03-15 10:03:20] INFO  Health check: GET /health → 200 OK
[2024-03-15 10:03:21] INFO  Health check passed after 1 attempt
[2024-03-15 10:03:22] INFO  Old container removed
[2024-03-15 10:03:22] SUCCESS Deployment completed successfully in {duration}s
[2024-03-15 10:03:22] INFO  App live at: https://{pipeline}.example.com"""

DEPLOY_LOGS_FAILED = """[2024-03-15 10:03:00] INFO  Starting deployment to EC2
[2024-03-15 10:03:00] INFO  Target: i-0a1b2c3d4e5f6789 (t3.medium)
[2024-03-15 10:03:01] INFO  Connecting via SSH...
[2024-03-15 10:03:06] ERROR Connection timeout after 5s
[2024-03-15 10:03:06] INFO  Retrying (1/3)...
[2024-03-15 10:03:12] ERROR Connection timeout after 5s
[2024-03-15 10:03:12] INFO  Retrying (2/3)...
[2024-03-15 10:03:18] ERROR Connection timeout after 5s
[2024-03-15 10:03:18] FATAL Max retries exceeded. Check EC2 security group rules and instance health.
[2024-03-15 10:03:18] FATAL Deployment failed. Rolling back..."""


# ─── Seed Data ────────────────────────────────────────────────────

PIPELINES_DATA = [
    {
        'name': 'e-commerce-app',
        'repo_url': 'https://github.com/acme-corp/e-commerce-app',
        'branch': 'main',
        'trigger': 'push',
        'environment': 'production',
        'runs': [
            {'status': 'success', 'author': 'sarah.dev',  'commit_message': 'feat: add cart persistence with Redis',        'days_ago': 1,  'total_duration': 187},
            {'status': 'success', 'author': 'james.ops',  'commit_message': 'fix: resolve checkout race condition',         'days_ago': 3,  'total_duration': 204},
            {'status': 'failed',  'author': 'alice.eng',  'commit_message': 'refactor: migrate auth to JWT tokens',         'days_ago': 5,  'fail_stage': 'test',   'total_duration': 95},
            {'status': 'success', 'author': 'sarah.dev',  'commit_message': 'perf: optimize product image loading',         'days_ago': 7,  'total_duration': 178},
            {'status': 'success', 'author': 'james.ops',  'commit_message': 'chore: update dependencies to latest',         'days_ago': 10, 'total_duration': 221},
            {'status': 'failed',  'author': 'bob.dev',    'commit_message': 'feat: add Stripe webhook handler',             'days_ago': 12, 'fail_stage': 'deploy', 'total_duration': 165},
            {'status': 'success', 'author': 'alice.eng',  'commit_message': 'fix: null pointer in order service',           'days_ago': 15, 'total_duration': 192},
            {'status': 'success', 'author': 'sarah.dev',  'commit_message': 'feat: wishlist feature v2',                    'days_ago': 18, 'total_duration': 210},
            {'status': 'failed',  'author': 'bob.dev',    'commit_message': 'wip: experimental GraphQL layer',              'days_ago': 22, 'fail_stage': 'build',  'total_duration': 48},
            {'status': 'success', 'author': 'james.ops',  'commit_message': 'chore: upgrade Node.js to 20 LTS',             'days_ago': 28, 'total_duration': 198},
        ]
    },
    {
        'name': 'auth-service',
        'repo_url': 'https://github.com/acme-corp/auth-service',
        'branch': 'develop',
        'trigger': 'push',
        'environment': 'staging',
        'runs': [
            {'status': 'running', 'author': 'carlos.sec', 'commit_message': 'feat: OAuth2 PKCE flow implementation',        'days_ago': 0,  'total_duration': None},
            {'status': 'success', 'author': 'carlos.sec', 'commit_message': 'fix: token refresh edge case',                 'days_ago': 2,  'total_duration': 143},
            {'status': 'success', 'author': 'diana.arch', 'commit_message': 'feat: multi-factor authentication support',    'days_ago': 5,  'total_duration': 167},
            {'status': 'failed',  'author': 'carlos.sec', 'commit_message': 'refactor: session store to Redis cluster',     'days_ago': 8,  'fail_stage': 'test',   'total_duration': 88},
            {'status': 'success', 'author': 'diana.arch', 'commit_message': 'chore: rotate JWT signing keys',               'days_ago': 11, 'total_duration': 155},
            {'status': 'success', 'author': 'carlos.sec', 'commit_message': 'fix: CORS headers on preflight',               'days_ago': 14, 'total_duration': 139},
            {'status': 'success', 'author': 'diana.arch', 'commit_message': 'perf: cache user permissions in Redis',        'days_ago': 20, 'total_duration': 162},
            {'status': 'success', 'author': 'carlos.sec', 'commit_message': 'feat: audit log for auth events',              'days_ago': 26, 'total_duration': 174},
        ]
    },
    {
        'name': 'monitoring-stack',
        'repo_url': 'https://github.com/acme-corp/monitoring-stack',
        'branch': 'main',
        'trigger': 'scheduled',
        'environment': 'production',
        'runs': [
            {'status': 'success', 'author': 'ops-bot',    'commit_message': 'ci: scheduled nightly deploy',                 'days_ago': 1,  'total_duration': 132},
            {'status': 'success', 'author': 'elena.sre',  'commit_message': 'feat: add Grafana dashboard for EC2 metrics',  'days_ago': 4,  'total_duration': 148},
            {'status': 'failed',  'author': 'ops-bot',    'commit_message': 'ci: scheduled nightly deploy',                 'days_ago': 7,  'fail_stage': 'deploy', 'total_duration': 112},
            {'status': 'success', 'author': 'elena.sre',  'commit_message': 'fix: Prometheus scrape interval',              'days_ago': 11, 'total_duration': 127},
            {'status': 'success', 'author': 'ops-bot',    'commit_message': 'ci: scheduled nightly deploy',                 'days_ago': 15, 'total_duration': 135},
            {'status': 'success', 'author': 'elena.sre',  'commit_message': 'feat: alerting rules for p99 latency spike',   'days_ago': 20, 'total_duration': 141},
        ]
    },
]


def make_stage_logs(stage_name, pipeline_name, branch, commit_hash, status, duration):
    templates = {
        'source': SOURCE_LOGS_SUCCESS,
        'build':  BUILD_LOGS_SUCCESS if status == 'success' else BUILD_LOGS_FAILED,
        'test':   TEST_LOGS_SUCCESS  if status == 'success' else TEST_LOGS_FAILED,
        'push':   PUSH_LOGS_SUCCESS,
        'deploy': DEPLOY_LOGS_SUCCESS if status == 'success' else DEPLOY_LOGS_FAILED,
    }
    template = templates.get(stage_name, '')
    return template.format(
        commit=commit_hash[:8],
        branch=branch,
        pipeline=pipeline_name,
        duration=duration or 0,
    )


class Command(BaseCommand):
    help = 'Seed the database with realistic pipeline data'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Seeding PipelineIQ database...\n')

        Stage.objects.all().delete()
        PipelineRun.objects.all().delete()
        Pipeline.objects.all().delete()
        self.stdout.write('  ✓ Cleared existing data\n')

        stage_durations = {
            'source': (3, 8),
            'build':  (35, 65),
            'test':   (25, 50),
            'push':   (15, 30),
            'deploy': (20, 45),
        }
        stage_order = ['source', 'build', 'test', 'push', 'deploy']

        for pipeline_data in PIPELINES_DATA:
            runs_data = pipeline_data.pop('runs')
            pipeline = Pipeline.objects.create(**pipeline_data)
            self.stdout.write(f'  📦 Created pipeline: {pipeline.name}\n')

            for run_num, run_data in enumerate(reversed(runs_data), start=1):
                fail_stage     = run_data.pop('fail_stage', None)
                days_ago       = run_data.pop('days_ago')
                total_duration = run_data.pop('total_duration')

                commit_hash = ''.join(random.choices('0123456789abcdef', k=40))
                started_at  = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 6))

                finished_at = None
                if run_data['status'] not in ('running', 'pending') and total_duration:
                    finished_at = started_at + timedelta(seconds=total_duration)

                run = PipelineRun.objects.create(
                    pipeline=pipeline,
                    run_number=run_num,
                    commit_hash=commit_hash,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration=total_duration,
                    **run_data,
                )

                for order, stage_name in enumerate(stage_order):
                    min_d, max_d = stage_durations[stage_name]
                    stage_dur = random.randint(min_d, max_d)

                    if run_data['status'] == 'running' and order == 0:
                        stage_status = 'running'
                        stage_start  = started_at
                        stage_end    = None
                        stage_dur    = None
                    elif run_data['status'] == 'running' and order > 0:
                        stage_status = 'pending'
                        stage_start  = None
                        stage_end    = None
                        stage_dur    = None
                    elif fail_stage == stage_name:
                        stage_status = 'failed'
                        stage_start  = started_at + timedelta(seconds=order * 20)
                        stage_end    = stage_start + timedelta(seconds=stage_dur)
                    elif fail_stage and stage_order.index(stage_name) > stage_order.index(fail_stage):
                        stage_status = 'skipped'
                        stage_start  = None
                        stage_end    = None
                        stage_dur    = None
                    else:
                        stage_status = 'success'
                        offset       = sum(random.randint(*stage_durations[s]) for s in stage_order[:order])
                        stage_start  = started_at + timedelta(seconds=offset)
                        stage_end    = stage_start + timedelta(seconds=stage_dur)

                    logs = make_stage_logs(
                        stage_name, pipeline.name, pipeline.branch,
                        commit_hash, stage_status, stage_dur
                    )

                    Stage.objects.create(
                        pipeline_run=run,
                        name=stage_name,
                        status=stage_status,
                        started_at=stage_start,
                        finished_at=stage_end,
                        duration=stage_dur,
                        logs=logs,
                        order=order,
                    )

            self.stdout.write(f'    ✓ Created {len(runs_data)} runs with stages\n')

        self.stdout.write(f'\n✅ Seeding complete!\n')
        self.stdout.write(f'   Pipelines : {Pipeline.objects.count()}\n')
        self.stdout.write(f'   Runs      : {PipelineRun.objects.count()}\n')
        self.stdout.write(f'   Stages    : {Stage.objects.count()}\n')