from flask import (Blueprint, g, render_template, request, current_app)
from vmonAuth import login_required
import redis
from rq import Queue
import httpx

class vmonQueue(object):
    def __init__(self, queue):
        self.redis = redis.from_url(current_app.config['REDIS_URL'])
        self.queue = queue

    # list registries
    def get_registries(self):
        q = Queue(self.queue,connection=self.redis)
        return {
            'started':   q.started_job_registry,
            'deferred':  q.deferred_job_registry,
            'finished':  q.finished_job_registry,
            'failed':    q.failed_job_registry,
            'scheduled': q.scheduled_job_registry,
        }

    # add job
    def add_job(self,task,**kwargs):
        q = Queue(self.queue,is_async=True,connection=self.redis)
        job = q.enqueue(task,**kwargs)
        return job.get_status()

    # list jobs
    def get_jobs(self):
        q = Queue(self.queue,connection=self.redis)
        return q.jobs

    # get job
    def get_job(self,id):
        q = Queue(self.queue,connection=self.redis)
        return q.fetch_job(id)

# Blueprints
bp = Blueprint('vmonJobs', __name__, url_prefix='/jobs')

# index view to return base layout + connections info
@bp.route('/', methods=('GET',))
@login_required
def index():
    return render_template('jobs/index.html')

# Task TEST
def rq_test(**kwargs):
    print('toto')
    return 'OK'
    #return [f'arg {a}={kwargs[a]}' for a in kwargs.keys()].join(',')

# Task HTTP GET
def rq_http_get(**kwargs):
    try:
        r = None
        with httpx.Client(timeout=kwargs['timeout'], verify=kwargs['verify'], headers=kwargs['headers'], cookies=kwargs['cookies']) as client:
            r = client.get(kwargs['url'], params=kwargs['params'])
    except:
        status = 'error'
    if r.status_code == httpx.codes.OK:
        status = 'success'
    else:
        status = 'error'
    return f'rq_http_get {kwargs["url"]} : {status} {r.status_code}'
