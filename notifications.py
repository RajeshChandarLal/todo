from datetime import datetime, timedelta
from database import (
    get_all_classes, get_all_tasks, create_notification,
    get_unread_notifications, DEFAULT_USER_ID
)
from config import NOTIFICATION_SETTINGS


def generate_class_reminders(user_id=DEFAULT_USER_ID):
    """Generate reminders for upcoming classes"""
    classes = get_all_classes(user_id)
    now = datetime.now()
    today = now.date()
    current_day = today.weekday()
    
    reminders = []
    
    for cls in classes:
        if cls['is_cancelled']:
            continue
        
        # Check if class is today
        if cls['day_of_week'] == current_day:
            class_start = datetime.combine(today, cls['start_time'])
            time_until_class = (class_start - now).total_seconds() / 60
            
            # Remind 15 minutes before
            if 0 < time_until_class <= NOTIFICATION_SETTINGS['class_reminder_minutes']:
                notification_id = create_notification(
                    user_id,
                    'class_reminder',
                    f"Class Starting Soon: {cls['subject_name']}",
                    f"{cls['class_type']} at {cls['location']} starts in "
                    f"{int(time_until_class)} minutes",
                    related_class_id=cls['class_id']
                )
                reminders.append(notification_id)
    
    return reminders


def generate_task_reminders(user_id=DEFAULT_USER_ID):
    """Generate reminders for tasks approaching deadline"""
    tasks = get_all_tasks(user_id, include_completed=False)
    now = datetime.now()
    
    reminders = []
    
    for task in tasks:
        if not task['due_date']:
            continue
        
        due_date = task['due_date']
        if isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date)
        
        hours_until_due = (due_date - now).total_seconds() / 3600
        
        # Remind at different intervals based on urgency
        if hours_until_due < 0:
            # Overdue
            notification_id = create_notification(
                user_id,
                'task_overdue',
                f"Overdue: {task['title']}",
                f"This task was due on {due_date.strftime('%Y-%m-%d %H:%M')}",
                related_task_id=task['task_id']
            )
            reminders.append(notification_id)
        elif 0 < hours_until_due <= 24:
            # Due within 24 hours
            notification_id = create_notification(
                user_id,
                'task_due_soon',
                f"Due Soon: {task['title']}",
                f"This task is due in {int(hours_until_due)} hours",
                related_task_id=task['task_id']
            )
            reminders.append(notification_id)
    
    return reminders


def get_daily_summary(date, user_id=DEFAULT_USER_ID):
    """Generate daily summary of schedule"""
    from scheduler import get_daily_schedule
    
    schedule = get_daily_schedule(date, user_id)
    
    classes_count = len([s for s in schedule if s['type'] == 'class'])
    tasks_count = len([s for s in schedule if s['type'] == 'task'])
    cancelled_count = len([s for s in schedule if s['type'] == 'class' and s.get('is_cancelled', False)])
    
    summary = {
        'date': date,
        'total_events': len(schedule),
        'classes': classes_count,
        'tasks': tasks_count,
        'cancelled_classes': cancelled_count,
        'schedule': schedule
    }
    
    # Create formatted summary message
    if len(schedule) == 0:
        summary['message'] = "🎉 No classes or tasks scheduled for today!"
    else:
        message = f"📅 Schedule for {date.strftime('%A, %B %d, %Y')}\\n\\n"
        message += f"📚 {classes_count} class(es)\\n"
        message += f"✅ {tasks_count} task(s)\\n"
        
        if cancelled_count > 0:
            message += f"❌ {cancelled_count} cancelled class(es)\\n"
        
        message += "\\n📋 Events:\\n"
        for event in schedule[:5]:  # Show first 5 events
            icon = "📚" if event['type'] == 'class' else "✅"
            status = " (Cancelled)" if event.get('is_cancelled') else ""
            message += f"{icon} {event['time'].strftime('%H:%M')} - {event['title']}{status}\\n"
        
        if len(schedule) > 5:
            message += f"... and {len(schedule) - 5} more events"
        
        summary['message'] = message
    
    return summary


def check_upcoming_deadlines(days_ahead=7, user_id=DEFAULT_USER_ID):
    """Check for upcoming task deadlines"""
    tasks = get_all_tasks(user_id, include_completed=False)
    now = datetime.now()
    future_date = now + timedelta(days=days_ahead)
    
    upcoming = []
    
    for task in tasks:
        if task['due_date']:
            due_date = task['due_date']
            if isinstance(due_date, str):
                due_date = datetime.fromisoformat(due_date)
            
            if now <= due_date <= future_date:
                days_until = (due_date - now).days
                upcoming.append({
                    'task': task,
                    'due_date': due_date,
                    'days_until': days_until
                })
    
    # Sort by due date
    upcoming.sort(key=lambda x: x['due_date'])
    
    return upcoming


def format_notification_html(notifications):
    """Format notifications as HTML for display"""
    if not notifications:
        return "<p style='color: #7f8c8d;'>No new notifications</p>"
    
    html = "<div class='notifications-container'>"
    
    for notif in notifications:
        icon_map = {
            'class_reminder': '⏰',
            'class_cancelled': '❌',
            'class_rescheduled': '🔄',
            'task_due_soon': '⚠️',
            'task_overdue': '🚨',
            'schedule_conflict': '⚡'
        }
        
        icon = icon_map.get(notif['notification_type'], '📢')
        
        # Format timestamp
        created = notif['created_at']
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        time_ago = get_time_ago(created)
        
        html += f"""
        <div class='notification-item' style='
            padding: 10px;
            margin: 5px 0;
            border-left: 3px solid #3498db;
            background: #ecf0f1;
            border-radius: 4px;
        '>
            <div style='display: flex; align-items: center;'>
                <span style='font-size: 24px; margin-right: 10px;'>{icon}</span>
                <div style='flex: 1;'>
                    <strong>{notif['title']}</strong>
                    <p style='margin: 5px 0; color: #34495e;'>{notif['message']}</p>
                    <small style='color: #7f8c8d;'>{time_ago}</small>
                </div>
            </div>
        </div>
        """
    
    html += "</div>"
    return html


def get_time_ago(timestamp):
    """Get human-readable time ago string"""
    now = datetime.now()
    
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)
    
    diff = now - timestamp
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"


def send_daily_summary_notification(date, user_id=DEFAULT_USER_ID):
    """Send daily summary as notification"""
    summary = get_daily_summary(date, user_id)
    
    notification_id = create_notification(
        user_id,
        'daily_summary',
        f"Daily Summary - {date.strftime('%A, %B %d')}",
        summary['message']
    )
    
    return notification_id
