from datetime import datetime, timedelta, time
from database import (
    get_classes_by_day, get_free_slots, get_all_tasks,
    schedule_task, create_notification
)
from config import DEFAULT_USER_ID, DAYS_OF_WEEK


def calculate_priority_score(task):
    """Calculate priority score for task scheduling"""
    priority_weights = {
        'Urgent': 100,
        'High': 75,
        'Medium': 50,
        'Low': 25
    }
    
    base_score = priority_weights.get(task['priority'], 25)
    
    # Add urgency based on due date
    if task['due_date']:
        due_date = task['due_date']
        if isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date)
        
        days_until_due = (due_date - datetime.now()).days
        
        if days_until_due < 0:
            # Overdue - highest priority
            urgency_bonus = 50
        elif days_until_due == 0:
            # Due today
            urgency_bonus = 40
        elif days_until_due == 1:
            # Due tomorrow
            urgency_bonus = 30
        elif days_until_due <= 3:
            # Due within 3 days
            urgency_bonus = 20
        elif days_until_due <= 7:
            # Due within a week
            urgency_bonus = 10
        else:
            urgency_bonus = 0
        
        base_score += urgency_bonus
    
    return base_score


def find_best_time_slot(task, day_of_week, user_id=DEFAULT_USER_ID):
    """Find the best time slot for a task on a given day"""
    duration = task.get('estimated_duration', 60)  # Default 60 minutes
    free_slots = get_free_slots(day_of_week, duration, user_id)
    
    if not free_slots:
        return None
    
    # Prefer slots in the afternoon (14:00-18:00) for study tasks
    # Morning slots (09:00-12:00) are second choice
    # Evening slots are last resort
    
    scored_slots = []
    for slot in free_slots:
        hour = slot['start'].hour
        
        # Scoring based on time of day
        if 14 <= hour < 18:
            time_score = 10  # Afternoon - best for focused work
        elif 9 <= hour < 12:
            time_score = 8   # Morning - good for classes
        elif 12 <= hour < 14:
            time_score = 6   # Lunch time - okay
        elif 18 <= hour < 21:
            time_score = 5   # Evening - acceptable
        else:
            time_score = 2   # Early morning/late evening
        
        # Prefer slots that aren't too long (avoid huge gaps)
        duration_score = 10 - min(abs(slot['duration'] - duration) / 30, 10)
        
        total_score = time_score + duration_score
        
        scored_slots.append({
            'slot': slot,
            'score': total_score
        })
    
    # Return the best scored slot
    best_slot = max(scored_slots, key=lambda x: x['score'])
    return best_slot['slot']


def auto_schedule_tasks(user_id=DEFAULT_USER_ID):
    """Automatically schedule unscheduled tasks"""
    # Get all incomplete, unscheduled tasks
    tasks = get_all_tasks(user_id, include_completed=False)
    unscheduled_tasks = [t for t in tasks if not t['scheduled_date']]
    
    if not unscheduled_tasks:
        return []
    
    # Sort tasks by priority score
    sorted_tasks = sorted(unscheduled_tasks, 
                         key=calculate_priority_score, 
                         reverse=True)
    
    scheduled = []
    today = datetime.now().date()
    
    # Try to schedule each task in the next 7 days
    for task in sorted_tasks:
        task_scheduled = False
        
        # Determine optimal scheduling window
        if task['due_date']:
            due_date = task['due_date']
            if isinstance(due_date, str):
                due_date = datetime.fromisoformat(due_date).date()
            
            # Don't schedule past due date
            max_date = min(due_date, today + timedelta(days=7))
        else:
            max_date = today + timedelta(days=7)
        
        # Try each day until we find a slot
        for day_offset in range((max_date - today).days + 1):
            schedule_date = today + timedelta(days=day_offset)
            day_of_week = schedule_date.weekday()  # 0 = Monday
            
            # Find best time slot for this day
            best_slot = find_best_time_slot(task, day_of_week, user_id)
            
            if best_slot:
                # Calculate end time
                start_datetime = datetime.combine(schedule_date, best_slot['start'])
                duration = task.get('estimated_duration', 60)
                end_datetime = start_datetime + timedelta(minutes=duration)
                
                # Schedule the task
                schedule_task(
                    task['task_id'],
                    schedule_date,
                    best_slot['start'],
                    end_datetime.time()
                )
                
                scheduled.append({
                    'task': task,
                    'date': schedule_date,
                    'start': best_slot['start'],
                    'end': end_datetime.time()
                })
                
                task_scheduled = True
                break
        
        if not task_scheduled:
            # Could not find a slot - notify user
            create_notification(
                user_id,
                'schedule_conflict',
                'Task Scheduling Issue',
                f'Could not find a suitable time slot for task: {task["title"]}',
                related_task_id=task['task_id']
            )
    
    return scheduled


def suggest_alternative_slots_for_cancelled_class(class_id, user_id=DEFAULT_USER_ID):
    """Suggest alternative time slots when a class is cancelled"""
    # Get the cancelled class info
    from database import execute_single
    
    class_info = execute_single(
        "SELECT * FROM timetable WHERE class_id = %s",
        (class_id,)
    )
    
    if not class_info:
        return []
    
    cancelled_day = class_info['day_of_week']
    start_time = class_info['start_time']
    end_time = class_info['end_time']
    
    # Calculate duration in minutes
    start_dt = datetime.combine(datetime.today(), start_time)
    end_dt = datetime.combine(datetime.today(), end_time)
    duration = int((end_dt - start_dt).total_seconds() / 60)
    
    # Find free slots on the same day
    free_slots = get_free_slots(cancelled_day, duration, user_id)
    
    suggestions = []
    
    # Get pending high-priority tasks that could use this time
    tasks = get_all_tasks(user_id, include_completed=False)
    high_priority_tasks = [
        t for t in tasks 
        if t['priority'] in ['High', 'Urgent'] and not t['scheduled_date']
    ]
    
    # Sort by priority
    high_priority_tasks.sort(key=calculate_priority_score, reverse=True)
    
    for slot in free_slots[:3]:  # Top 3 suggestions
        suggestions.append({
            'day': DAYS_OF_WEEK[cancelled_day],
            'start': slot['start'],
            'end': slot['end'],
            'duration': slot['duration'],
            'suggested_tasks': high_priority_tasks[:3]  # Top 3 tasks
        })
    
    return suggestions


def detect_scheduling_conflicts(user_id=DEFAULT_USER_ID):
    """Detect and report scheduling conflicts"""
    conflicts = []
    
    # Check each day
    for day in range(7):
        classes = get_classes_by_day(day, user_id)
        
        # Sort by start time
        sorted_classes = sorted(classes, key=lambda x: x['start_time'])
        
        # Check for overlaps
        for i in range(len(sorted_classes) - 1):
            current = sorted_classes[i]
            next_class = sorted_classes[i + 1]
            
            if current['end_time'] > next_class['start_time']:
                conflicts.append({
                    'day': DAYS_OF_WEEK[day],
                    'class1': current,
                    'class2': next_class,
                    'type': 'overlap'
                })
    
    # Create notifications for conflicts
    for conflict in conflicts:
        create_notification(
            user_id,
            'schedule_conflict',
            'Scheduling Conflict Detected',
            f"Conflict on {conflict['day']}: {conflict['class1']['subject_name']} "
            f"overlaps with {conflict['class2']['subject_name']}"
        )
    
    return conflicts


def optimize_weekly_schedule(user_id=DEFAULT_USER_ID):
    """Optimize the entire weekly schedule"""
    # Get all unscheduled tasks
    tasks = get_all_tasks(user_id, include_completed=False)
    unscheduled = [t for t in tasks if not t['scheduled_date']]
    
    # Auto-schedule them
    scheduled_tasks = auto_schedule_tasks(user_id)
    
    # Check for conflicts
    conflicts = detect_scheduling_conflicts(user_id)
    
    return {
        'scheduled_tasks': scheduled_tasks,
        'conflicts': conflicts,
        'summary': {
            'total_tasks': len(tasks),
            'scheduled': len([t for t in tasks if t['scheduled_date']]),
            'unscheduled': len(unscheduled),
            'conflicts_found': len(conflicts)
        }
    }


def get_daily_schedule(date, user_id=DEFAULT_USER_ID):
    """Get complete schedule for a specific day"""
    from database import get_tasks_by_date
    
    day_of_week = date.weekday()
    
    # Get classes and tasks
    classes = get_classes_by_day(day_of_week, user_id)
    tasks = get_tasks_by_date(date, user_id)
    
    # Combine and sort by time
    schedule = []
    
    for cls in classes:
        schedule.append({
            'type': 'class',
            'time': cls['start_time'],
            'end_time': cls['end_time'],
            'title': cls['subject_name'],
            'details': f"{cls['class_type']} - {cls['location']}",
            'instructor': cls.get('instructor', ''),
            'color': cls.get('color_code', '#3498db'),
            'is_cancelled': cls.get('is_cancelled', False),
            'id': cls['class_id']
        })
    
    for task in tasks:
        if task['scheduled_start_time']:
            schedule.append({
                'type': 'task',
                'time': task['scheduled_start_time'],
                'end_time': task['scheduled_end_time'],
                'title': task['title'],
                'details': task['description'] or '',
                'priority': task['priority'],
                'color': task.get('color_code', '#e74c3c'),
                'is_completed': task.get('is_completed', False),
                'id': task['task_id']
            })
    
    # Sort by time
    schedule.sort(key=lambda x: x['time'] if x['time'] else time.max)
    
    return schedule
