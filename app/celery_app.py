from flask import Flask
from celery import Celery

def make_celery(app: Flask) -> Celery:
    """Create a Celery object tied to a Flask app's context.
    Uses app.config['CELERY_BROKER_URL'] and 'CELERY_RESULT_BACKEND'."""
    celery = Celery(app.import_name, broker=app.config.get('CELERY_BROKER_URL'), backend=app.config.get('CELERY_RESULT_BACKEND'))
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        """Run tasks within Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super().__call__(*args, **kwargs)

    celery.Task = ContextTask
    return celery
