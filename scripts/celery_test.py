import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ml_service')))

from celery_app import retrain_models_task

print("Enqueueing retrain_models_task...")
# Enqueue the task with dummy authorization
result = retrain_models_task.delay("Bearer DUMMY_TOKEN_FOR_TESTING")

print(f"Task enqueued. Task ID: {result.id}")
print("Waiting for task to complete...")

# Wait up to 30 seconds for the result
for _ in range(30):
    if result.ready():
        break
    time.sleep(1)

if result.ready():
    print(f"Task completed with status: {result.status}")
    if result.successful():
        print(f"Result: {result.get()}")
    else:
        print(f"Exception: {result.info}")
else:
    print("Task did not complete within 30 seconds. Ensure the celery worker is running.")
