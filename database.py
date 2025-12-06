import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import streamlit as st
from config import DB_CONFIG, DEFAULT_USER_ID
from datetime import datetime, timedelta


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def execute_query(query, params=None, fetch=True):
    """Execute a query and return results"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            if fetch:
                return cur.fetchall()
            return None


def execute_single(query, params=None):
    """Execute a query and return single result"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            return cur.fetchone()


# ==================== TIMETABLE FUNCTIONS ====================

def get_all_classes(user_id=DEFAULT_USER_ID, include_cancelled=False):
    """Get all classes for a user"""
    query = """
        SELECT * FROM timetable 
        WHERE user_id = %s AND is_active = TRUE
    """
    if not include_cancelled:
        query += " AND is_cancelled = FALSE"
    query += " ORDER BY day_of_week, start_time"
    return execute_query(query, (user_id,))


def get_classes_by_day(day_of_week, user_id=DEFAULT_USER_ID):
    """Get classes for a specific day"""
    query = """
        SELECT * FROM timetable 
        WHERE user_id = %s AND day_of_week = %s 
        AND is_active = TRUE AND is_cancelled = FALSE
        ORDER BY start_time
    """
    return execute_query(query, (user_id, day_of_week))


def add_class(subject_name, class_type, day_of_week, start_time, end_time, 
              location, instructor, color_code, user_id=DEFAULT_USER_ID):
    """Add a new class to timetable"""
    query = """
        INSERT INTO timetable 
        (user_id, subject_name, class_type, day_of_week, start_time, end_time, 
         location, instructor, color_code)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING class_id
    """
    result = execute_single(query, (user_id, subject_name, class_type, day_of_week,
                                    start_time, end_time, location, instructor, color_code))
    return result['class_id'] if result else None


def update_class(class_id, subject_name, class_type, day_of_week, start_time, 
                end_time, location, instructor, color_code):
    """Update an existing class"""
    query = """
        UPDATE timetable 
        SET subject_name = %s, class_type = %s, day_of_week = %s,
            start_time = %s, end_time = %s, location = %s,
            instructor = %s, color_code = %s
        WHERE class_id = %s
    """
    execute_query(query, (subject_name, class_type, day_of_week, start_time,
                         end_time, location, instructor, color_code, class_id), fetch=False)


def delete_class(class_id):
    """Soft delete a class"""
    query = "UPDATE timetable SET is_active = FALSE WHERE class_id = %s"
    execute_query(query, (class_id,), fetch=False)


def cancel_class(class_id):
    """Mark a class as cancelled"""
    query = "UPDATE timetable SET is_cancelled = TRUE WHERE class_id = %s"
    execute_query(query, (class_id,), fetch=False)
    
    # Create notification
    create_notification(
        DEFAULT_USER_ID,
        'class_cancelled',
        'Class Cancelled',
        'A class has been cancelled. Check your schedule for updates.',
        related_class_id=class_id
    )


def reschedule_class(class_id, new_day, new_start_time, new_end_time):
    """Reschedule a class to a new time"""
    query = """
        UPDATE timetable 
        SET day_of_week = %s, start_time = %s, end_time = %s, is_cancelled = FALSE
        WHERE class_id = %s
    """
    execute_query(query, (new_day, new_start_time, new_end_time, class_id), fetch=False)
    
    # Create notification
    create_notification(
        DEFAULT_USER_ID,
        'class_rescheduled',
        'Class Rescheduled',
        f'A class has been rescheduled to a new time.',
        related_class_id=class_id
    )


# ==================== TASK FUNCTIONS ====================

def get_all_tasks(user_id=DEFAULT_USER_ID, include_completed=False):
    """Get all tasks for a user"""
    query = """
        SELECT * FROM tasks 
        WHERE user_id = %s
    """
    if not include_completed:
        query += " AND is_completed = FALSE"
    query += " ORDER BY due_date NULLS LAST, priority DESC"
    return execute_query(query, (user_id,))


def get_tasks_by_date(date, user_id=DEFAULT_USER_ID):
    """Get tasks scheduled for a specific date"""
    query = """
        SELECT * FROM tasks 
        WHERE user_id = %s AND scheduled_date = %s
        ORDER BY scheduled_start_time NULLS LAST
    """
    return execute_query(query, (user_id, date))


def get_overdue_tasks(user_id=DEFAULT_USER_ID):
    """Get overdue tasks"""
    query = """
        SELECT * FROM tasks 
        WHERE user_id = %s 
        AND is_completed = FALSE 
        AND due_date < CURRENT_TIMESTAMP
        ORDER BY due_date
    """
    return execute_query(query, (user_id,))


def add_task(title, description, due_date, priority, estimated_duration,
             is_recurring=False, user_id=DEFAULT_USER_ID):
    """Add a new task"""
    query = """
        INSERT INTO tasks 
        (user_id, title, description, due_date, priority, estimated_duration, is_recurring)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING task_id
    """
    result = execute_single(query, (user_id, title, description, due_date,
                                    priority, estimated_duration, is_recurring))
    return result['task_id'] if result else None


def update_task(task_id, title, description, due_date, priority, estimated_duration):
    """Update an existing task"""
    query = """
        UPDATE tasks 
        SET title = %s, description = %s, due_date = %s,
            priority = %s, estimated_duration = %s
        WHERE task_id = %s
    """
    execute_query(query, (title, description, due_date, priority,
                         estimated_duration, task_id), fetch=False)


def schedule_task(task_id, scheduled_date, scheduled_start_time, scheduled_end_time):
    """Schedule a task to a specific time slot"""
    query = """
        UPDATE tasks 
        SET scheduled_date = %s, scheduled_start_time = %s, scheduled_end_time = %s
        WHERE task_id = %s
    """
    execute_query(query, (scheduled_date, scheduled_start_time,
                         scheduled_end_time, task_id), fetch=False)


def complete_task(task_id):
    """Mark a task as completed"""
    query = """
        UPDATE tasks 
        SET is_completed = TRUE, completed_at = CURRENT_TIMESTAMP
        WHERE task_id = %s
    """
    execute_query(query, (task_id,), fetch=False)


def delete_task(task_id):
    """Delete a task"""
    query = "DELETE FROM tasks WHERE task_id = %s"
    execute_query(query, (task_id,), fetch=False)


def add_task_recurrence(task_id, recurrence_type, interval, recurrence_days, end_date):
    """Add recurrence pattern to a task"""
    query = """
        INSERT INTO task_recurrence 
        (task_id, recurrence_type, recurrence_interval, recurrence_days, end_date)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING recurrence_id
    """
    result = execute_single(query, (task_id, recurrence_type, interval,
                                    recurrence_days, end_date))
    return result['recurrence_id'] if result else None


# ==================== NOTIFICATION FUNCTIONS ====================

def create_notification(user_id, notification_type, title, message,
                       related_class_id=None, related_task_id=None):
    """Create a new notification"""
    query = """
        INSERT INTO notifications 
        (user_id, notification_type, title, message, related_class_id, related_task_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING notification_id
    """
    result = execute_single(query, (user_id, notification_type, title, message,
                                    related_class_id, related_task_id))
    return result['notification_id'] if result else None


def get_unread_notifications(user_id=DEFAULT_USER_ID):
    """Get unread notifications"""
    query = """
        SELECT * FROM notifications 
        WHERE user_id = %s AND is_read = FALSE
        ORDER BY created_at DESC
    """
    return execute_query(query, (user_id,))


def mark_notification_read(notification_id):
    """Mark a notification as read"""
    query = "UPDATE notifications SET is_read = TRUE WHERE notification_id = %s"
    execute_query(query, (notification_id,), fetch=False)


def get_all_notifications(user_id=DEFAULT_USER_ID, limit=50):
    """Get all notifications"""
    query = """
        SELECT * FROM notifications 
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    return execute_query(query, (user_id, limit))


# ==================== SCHEDULING FUNCTIONS ====================

def check_time_conflict(day_of_week, start_time, end_time, user_id=DEFAULT_USER_ID, 
                       exclude_class_id=None):
    """Check if there's a scheduling conflict"""
    query = """
        SELECT * FROM timetable 
        WHERE user_id = %s 
        AND day_of_week = %s 
        AND is_active = TRUE 
        AND is_cancelled = FALSE
        AND (
            (start_time <= %s AND end_time > %s) OR
            (start_time < %s AND end_time >= %s) OR
            (start_time >= %s AND end_time <= %s)
        )
    """
    params = [user_id, day_of_week, start_time, start_time, end_time, end_time,
              start_time, end_time]
    
    if exclude_class_id:
        query += " AND class_id != %s"
        params.append(exclude_class_id)
    
    conflicts = execute_query(query, tuple(params))
    return len(conflicts) > 0, conflicts


def get_free_slots(day_of_week, duration_minutes, user_id=DEFAULT_USER_ID):
    """Find free time slots of specified duration"""
    classes = get_classes_by_day(day_of_week, user_id)
    
    # Define day boundaries (8 AM to 9 PM)
    day_start = datetime.strptime('08:00', '%H:%M').time()
    day_end = datetime.strptime('21:00', '%H:%M').time()
    
    free_slots = []
    current_time = day_start
    
    # Sort classes by start time
    sorted_classes = sorted(classes, key=lambda x: x['start_time'])
    
    for class_info in sorted_classes:
        class_start = class_info['start_time']
        
        # Convert to datetime for comparison
        current_dt = datetime.combine(datetime.today(), current_time)
        class_start_dt = datetime.combine(datetime.today(), class_start)
        
        # Check if there's enough time before this class
        time_diff = (class_start_dt - current_dt).total_seconds() / 60
        
        if time_diff >= duration_minutes:
            free_slots.append({
                'start': current_time,
                'end': class_start,
                'duration': int(time_diff)
            })
        
        # Move current time to after this class
        current_time = class_info['end_time']
    
    # Check remaining time after last class
    current_dt = datetime.combine(datetime.today(), current_time)
    day_end_dt = datetime.combine(datetime.today(), day_end)
    remaining_time = (day_end_dt - current_dt).total_seconds() / 60
    
    if remaining_time >= duration_minutes:
        free_slots.append({
            'start': current_time,
            'end': day_end,
            'duration': int(remaining_time)
        })
    
    return free_slots
