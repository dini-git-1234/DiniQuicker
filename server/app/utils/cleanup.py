import time
import shutil

def schedule_cleanup(background_tasks, folder):
    background_tasks.add_task(_cleanup, folder)

def _cleanup(folder):
    time.sleep(300)
    shutil.rmtree(folder, ignore_errors=True)
