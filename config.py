import os

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'college_timetable'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

# Default user ID (for single-user setup)
DEFAULT_USER_ID = 1

# Days of week mapping
DAYS_OF_WEEK = {
    0: 'Monday',
    1: 'Tuesday',
    2: 'Wednesday',
    3: 'Thursday',
    4: 'Friday',
    5: 'Saturday',
    6: 'Sunday'
}

# Priority levels
PRIORITY_LEVELS = ['Low', 'Medium', 'High', 'Urgent']

# Class types
CLASS_TYPES = ['Lecture', 'Lab', 'Tutorial', 'Seminar', 'Workshop']

# Recurrence types
RECURRENCE_TYPES = ['Daily', 'Weekly', 'Monthly']

# Color palette
COLORS = {
    'class': '#3498db',
    'task': '#e74c3c',
    'cancelled': '#95a5a6',
    'completed': '#27ae60'
}

# Notification settings
NOTIFICATION_SETTINGS = {
    'class_reminder_minutes': 15,
    'task_reminder_hours': 24
}

# Time slots for scheduling (24-hour format)
TIME_SLOTS = [
    '08:00', '08:30', '09:00', '09:30', '10:00', '10:30',
    '11:00', '11:30', '12:00', '12:30', '13:00', '13:30',
    '14:00', '14:30', '15:00', '15:30', '16:00', '16:30',
    '17:00', '17:30', '18:00', '18:30', '19:00', '19:30',
    '20:00', '20:30', '21:00'
]
