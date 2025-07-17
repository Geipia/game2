from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()

# Example job functions

def start_tournament():
    print('Tournament started!')

def start_round():
    print('New round started!')

def end_tournament():
    print('Tournament ended!')

# Schedule jobs
scheduler.add_job(start_tournament, 'cron', day_of_week='mon', hour=20, minute=0)
scheduler.add_job(start_round, 'interval', hours=4)
scheduler.add_job(end_tournament, 'cron', day_of_week='sun', hour=20, minute=0)

def start_scheduler():
    scheduler.start()
