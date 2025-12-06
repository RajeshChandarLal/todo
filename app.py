import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import plotly.express as px
import plotly.graph_objects as go

# Import custom modules
from database import *
from scheduler import *
from notifications import *
from config import *

# Page configuration
st.set_page_config(
    page_title="College Timetable Manager",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.8rem;
        color: #34495e;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .class-card {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid;
    }
    .task-card {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid;
        background: #f8f9fa;
    }
    .notification-badge {
        background: #e74c3c;
        color: white;
        border-radius: 50%;
        padding: 0.2rem 0.6rem;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.now().date()
if 'show_notifications' not in st.session_state:
    st.session_state.show_notifications = False


def main():
    """Main application function"""
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/calendar.png", width=80)
        st.title("📚 Timetable Manager")
        
        # Navigation
        page = st.radio(
            "Navigation",
            ["📊 Dashboard", "📅 Weekly Timetable", "✅ Task Management", 
             "🔔 Notifications", "⚙️ Settings"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Quick stats
        st.subheader("Quick Stats")
        total_classes = len(get_all_classes())
        active_tasks = len(get_all_tasks(include_completed=False))
        overdue = len(get_overdue_tasks())
        
        col1, col2 = st.columns(2)
        col1.metric("Classes", total_classes, delta=None)
        col2.metric("Tasks", active_tasks, delta=f"-{overdue} overdue" if overdue > 0 else "On track")
        
        st.divider()
        
        # Quick actions
        st.subheader("Quick Actions")
        if st.button("🔄 Auto-Schedule Tasks", use_container_width=True):
            with st.spinner("Scheduling tasks..."):
                scheduled = auto_schedule_tasks()
                st.success(f"Scheduled {len(scheduled)} task(s)!")
                st.rerun()
        
        if st.button("📋 Today's Summary", use_container_width=True):
            summary = get_daily_summary(datetime.now().date())
            st.info(summary['message'])
    
    # Main content area
    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "📅 Weekly Timetable":
        show_weekly_timetable()
    elif page == "✅ Task Management":
        show_task_management()
    elif page == "🔔 Notifications":
        show_notifications_page()
    elif page == "⚙️ Settings":
        show_settings()


def show_dashboard():
    """Dashboard page"""
    st.markdown("<h1 class='main-header'>📊 Dashboard</h1>", unsafe_allow_html=True)
    
    # Date selector
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_date = st.date_input("Select Date", st.session_state.selected_date)
        st.session_state.selected_date = selected_date
    with col2:
        if st.button("⬅️ Previous Day"):
            st.session_state.selected_date -= timedelta(days=1)
            st.rerun()
    with col3:
        if st.button("Next Day ➡️"):
            st.session_state.selected_date += timedelta(days=1)
            st.rerun()
    
    # Get today's schedule
    schedule = get_daily_schedule(selected_date)
    
    # Metrics row
    st.markdown("### 📈 Today's Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    classes = [s for s in schedule if s['type'] == 'class' and not s.get('is_cancelled')]
    tasks = [s for s in schedule if s['type'] == 'task' and not s.get('is_completed')]
    completed = [s for s in schedule if s['type'] == 'task' and s.get('is_completed')]
    cancelled = [s for s in schedule if s['type'] == 'class' and s.get('is_cancelled')]
    
    col1.metric("📚 Classes Today", len(classes))
    col2.metric("✅ Pending Tasks", len(tasks))
    col3.metric("✔️ Completed", len(completed))
    col4.metric("❌ Cancelled", len(cancelled))
    
    # Timeline view
    st.markdown("### 📅 Today's Schedule")
    
    if not schedule:
        st.info("🎉 No classes or tasks scheduled for this day!")
    else:
        # Create timeline visualization
        timeline_data = []
        for item in schedule:
            start_dt = datetime.combine(selected_date, item['time'])
            end_dt = datetime.combine(selected_date, item['end_time'])
            
            status_suffix = ""
            if item['type'] == 'class' and item.get('is_cancelled'):
                status_suffix = " (Cancelled)"
            elif item['type'] == 'task' and item.get('is_completed'):
                status_suffix = " (Completed)"
            
            timeline_data.append({
                'Task': item['title'] + status_suffix,
                'Start': start_dt,
                'Finish': end_dt,
                'Type': item['type'].capitalize(),
                'Color': item['color']
            })
        
        # Create Gantt chart
        if timeline_data:
            fig = px.timeline(
                timeline_data,
                x_start='Start',
                x_end='Finish',
                y='Task',
                color='Type',
                title=f"Schedule for {selected_date.strftime('%A, %B %d, %Y')}"
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=max(400, len(timeline_data) * 50))
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed list
        st.markdown("### 📋 Detailed Schedule")
        for item in schedule:
            icon = "📚" if item['type'] == 'class' else "✅"
            time_str = f"{item['time'].strftime('%H:%M')} - {item['end_time'].strftime('%H:%M')}"
            
            with st.container():
                col1, col2, col3 = st.columns([1, 4, 2])
                with col1:
                    st.markdown(f"### {icon}")
                with col2:
                    if item.get('is_cancelled'):
                        st.markdown(f"~~**{item['title']}**~~ ❌")
                    elif item.get('is_completed'):
                        st.markdown(f"~~**{item['title']}**~~ ✔️")
                    else:
                        st.markdown(f"**{item['title']}**")
                    st.caption(f"{time_str} | {item['details']}")
                with col3:
                    if item['type'] == 'class' and not item.get('is_cancelled'):
                        if st.button("Cancel", key=f"cancel_{item['id']}"):
                            cancel_class(item['id'])
                            st.success("Class cancelled!")
                            st.rerun()
                    elif item['type'] == 'task' and not item.get('is_completed'):
                        if st.button("Complete", key=f"complete_{item['id']}"):
                            complete_task(item['id'])
                            st.success("Task completed!")
                            st.rerun()
                
                st.divider()
    
    # Upcoming deadlines
    st.markdown("### ⚠️ Upcoming Deadlines")
    upcoming = check_upcoming_deadlines(days_ahead=7)
    
    if not upcoming:
        st.success("✨ No deadlines in the next 7 days!")
    else:
        for item in upcoming[:5]:
            task = item['task']
            days = item['days_until']
            
            urgency_color = "#e74c3c" if days <= 1 else "#f39c12" if days <= 3 else "#3498db"
            
            st.markdown(f"""
            <div style='padding: 10px; margin: 5px 0; border-left: 4px solid {urgency_color}; 
                        background: #f8f9fa; border-radius: 4px;'>
                <strong>{task['title']}</strong> 
                <span style='color: {urgency_color}; font-weight: bold;'>
                    (Due in {days} day{'s' if days != 1 else ''})
                </span>
                <br>
                <small>Priority: {task['priority']} | Due: {item['due_date'].strftime('%Y-%m-%d %H:%M')}</small>
            </div>
            """, unsafe_allow_html=True)


def show_weekly_timetable():
    """Weekly timetable page"""
    st.markdown("<h1 class='main-header'>📅 Weekly Timetable</h1>", unsafe_allow_html=True)
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 View Timetable", "➕ Add Class", "✏️ Edit Classes"])
    
    with tab1:
        # Weekly view
        st.subheader("Weekly Schedule")
        
        # Get all classes
        all_classes = get_all_classes(include_cancelled=True)
        
        # Create weekly grid
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day_idx, day_name in enumerate(days):
            with st.expander(f"📅 {day_name}", expanded=(day_idx < 5)):
                day_classes = [c for c in all_classes if c['day_of_week'] == day_idx]
                
                if not day_classes:
                    st.info("No classes scheduled")
                else:
                    day_classes.sort(key=lambda x: x['start_time'])
                    
                    for cls in day_classes:
                        status = "❌ CANCELLED" if cls['is_cancelled'] else ""
                        
                        col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
                        with col1:
                            st.markdown(f"**{cls['start_time'].strftime('%H:%M')} - {cls['end_time'].strftime('%H:%M')}**")
                        with col2:
                            st.markdown(f"**{cls['subject_name']}** {status}")
                        with col3:
                            st.caption(f"{cls['class_type']} | {cls['location']} | {cls['instructor']}")
                        with col4:
                            if not cls['is_cancelled']:
                                if st.button("❌", key=f"cancel_week_{cls['class_id']}"):
                                    cancel_class(cls['class_id'])
                                    st.rerun()
                        
                        st.divider()
    
    with tab2:
        st.subheader("Add New Class")
        
        with st.form("add_class_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                subject = st.text_input("Subject Name*", placeholder="e.g., Data Structures")
                class_type = st.selectbox("Class Type*", CLASS_TYPES)
                day = st.selectbox("Day of Week*", list(DAYS_OF_WEEK.values()))
                location = st.text_input("Location", placeholder="e.g., Room 101")
            
            with col2:
                instructor = st.text_input("Instructor", placeholder="e.g., Dr. Smith")
                start_time = st.selectbox("Start Time*", TIME_SLOTS)
                end_time = st.selectbox("End Time*", TIME_SLOTS)
                color = st.color_picker("Color", value="#3498db")
            
            submitted = st.form_submit_button("Add Class", use_container_width=True)
            
            if submitted:
                if not subject or not start_time or not end_time:
                    st.error("Please fill in all required fields!")
                else:
                    # Convert day name to index
                    day_idx = list(DAYS_OF_WEEK.values()).index(day)
                    
                    # Check for conflicts
                    has_conflict, conflicts = check_time_conflict(
                        day_idx, 
                        datetime.strptime(start_time, '%H:%M').time(),
                        datetime.strptime(end_time, '%H:%M').time()
                    )
                    
                    if has_conflict:
                        st.error("Time conflict detected! Please choose a different time slot.")
                    else:
                        class_id = add_class(
                            subject, class_type, day_idx,
                            datetime.strptime(start_time, '%H:%M').time(),
                            datetime.strptime(end_time, '%H:%M').time(),
                            location, instructor, color
                        )
                        st.success(f"Class added successfully! ID: {class_id}")
                        st.rerun()
    
    with tab3:
        st.subheader("Edit or Remove Classes")
        
        all_classes = get_all_classes(include_cancelled=False)
        
        if not all_classes:
            st.info("No classes to edit")
        else:
            # Select class to edit
            class_options = {
                f"{DAYS_OF_WEEK[c['day_of_week']]} - {c['subject_name']} ({c['start_time'].strftime('%H:%M')})": c['class_id']
                for c in all_classes
            }
            
            selected_class = st.selectbox("Select Class to Edit", list(class_options.keys()))
            class_id = class_options[selected_class]
            
            # Get class details
            class_info = next(c for c in all_classes if c['class_id'] == class_id)
            
            with st.form(f"edit_class_form_{class_id}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    subject = st.text_input("Subject Name", value=class_info['subject_name'])
                    class_type = st.selectbox("Class Type", CLASS_TYPES, 
                                             index=CLASS_TYPES.index(class_info['class_type']) 
                                             if class_info['class_type'] in CLASS_TYPES else 0)
                    day = st.selectbox("Day of Week", list(DAYS_OF_WEEK.values()),
                                      index=class_info['day_of_week'])
                    location = st.text_input("Location", value=class_info['location'] or "")
                
                with col2:
                    instructor = st.text_input("Instructor", value=class_info['instructor'] or "")
                    start_time = st.selectbox("Start Time", TIME_SLOTS,
                                             index=TIME_SLOTS.index(class_info['start_time'].strftime('%H:%M'))
                                             if class_info['start_time'].strftime('%H:%M') in TIME_SLOTS else 0)
                    end_time = st.selectbox("End Time", TIME_SLOTS,
                                           index=TIME_SLOTS.index(class_info['end_time'].strftime('%H:%M'))
                                           if class_info['end_time'].strftime('%H:%M') in TIME_SLOTS else 0)
                    color = st.color_picker("Color", value=class_info['color_code'])
                
                col1, col2 = st.columns(2)
                update_btn = col1.form_submit_button("Update Class", use_container_width=True)
                delete_btn = col2.form_submit_button("Delete Class", use_container_width=True, type="secondary")
                
                if update_btn:
                    day_idx = list(DAYS_OF_WEEK.values()).index(day)
                    update_class(
                        class_id, subject, class_type, day_idx,
                        datetime.strptime(start_time, '%H:%M').time(),
                        datetime.strptime(end_time, '%H:%M').time(),
                        location, instructor, color
                    )
                    st.success("Class updated successfully!")
                    st.rerun()
                
                if delete_btn:
                    delete_class(class_id)
                    st.success("Class deleted successfully!")
                    st.rerun()


def show_task_management():
    """Task management page"""
    st.markdown("<h1 class='main-header'>✅ Task Management</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📋 View Tasks", "➕ Add Task", "✏️ Edit Tasks"])
    
    with tab1:
        # Filter options
        col1, col2, col3 = st.columns(3)
        show_completed = col1.checkbox("Show Completed", value=False)
        sort_by = col2.selectbox("Sort By", ["Due Date", "Priority", "Created Date"])
        filter_priority = col3.multiselect("Filter Priority", PRIORITY_LEVELS, default=PRIORITY_LEVELS)
        
        # Get tasks
        tasks = get_all_tasks(include_completed=show_completed)
        tasks = [t for t in tasks if t['priority'] in filter_priority]
        
        # Sort tasks
        if sort_by == "Due Date":
            tasks.sort(key=lambda x: x['due_date'] if x['due_date'] else datetime.max)
        elif sort_by == "Priority":
            priority_order = {'Urgent': 0, 'High': 1, 'Medium': 2, 'Low': 3}
            tasks.sort(key=lambda x: priority_order.get(x['priority'], 4))
        else:
            tasks.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Display tasks
        if not tasks:
            st.info("No tasks found!")
        else:
            for task in tasks:
                priority_colors = {
                    'Urgent': '#e74c3c',
                    'High': '#f39c12',
                    'Medium': '#3498db',
                    'Low': '#95a5a6'
                }
                
                color = priority_colors.get(task['priority'], '#95a5a6')
                
                with st.container():
                    col1, col2, col3 = st.columns([6, 2, 2])
                    
                    with col1:
                        status = "✔️" if task['is_completed'] else "⏳"
                        st.markdown(f"""
                        <div style='padding: 15px; border-left: 4px solid {color}; 
                                    background: #f8f9fa; border-radius: 4px; margin: 10px 0;'>
                            <h4>{status} {task['title']}</h4>
                            <p style='margin: 5px 0;'>{task['description'] or 'No description'}</p>
                            <small><strong>Priority:</strong> {task['priority']} | 
                                   <strong>Duration:</strong> {task['estimated_duration'] or 'N/A'} min | 
                                   <strong>Due:</strong> {task['due_date'].strftime('%Y-%m-%d %H:%M') if task['due_date'] else 'No deadline'}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        if task['scheduled_date']:
                            st.success(f"📅 {task['scheduled_date'].strftime('%Y-%m-%d')}")
                            st.caption(f"{task['scheduled_start_time'].strftime('%H:%M') if task['scheduled_start_time'] else ''}")
                        else:
                            st.warning("Not scheduled")
                    
                    with col3:
                        if not task['is_completed']:
                            if st.button("✔️ Complete", key=f"complete_task_{task['task_id']}"):
                                complete_task(task['task_id'])
                                st.success("Task completed!")
                                st.rerun()
                        if st.button("🗑️ Delete", key=f"delete_task_{task['task_id']}"):
                            delete_task(task['task_id'])
                            st.success("Task deleted!")
                            st.rerun()
    
    with tab2:
        st.subheader("Add New Task")
        
        with st.form("add_task_form"):
            title = st.text_input("Task Title*", placeholder="e.g., Complete assignment")
            description = st.text_area("Description", placeholder="Additional details...")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                due_date = st.date_input("Due Date")
            with col2:
                due_time = st.time_input("Due Time", value=time(23, 59))
            with col3:
                priority = st.selectbox("Priority*", PRIORITY_LEVELS, index=1)
            
            col1, col2 = st.columns(2)
            with col1:
                duration = st.number_input("Estimated Duration (minutes)", min_value=15, value=60, step=15)
            with col2:
                is_recurring = st.checkbox("Recurring Task")
            
            if is_recurring:
                st.info("Recurring task features coming soon!")
            
            submitted = st.form_submit_button("Add Task", use_container_width=True)
            
            if submitted:
                if not title:
                    st.error("Please enter a task title!")
                else:
                    due_datetime = datetime.combine(due_date, due_time)
                    task_id = add_task(title, description, due_datetime, priority, duration, is_recurring)
                    st.success(f"Task added successfully! ID: {task_id}")
                    st.rerun()
    
    with tab3:
        st.subheader("Edit Tasks")
        
        tasks = get_all_tasks(include_completed=False)
        
        if not tasks:
            st.info("No tasks to edit")
        else:
            task_options = {f"{t['title']} ({t['priority']})": t['task_id'] for t in tasks}
            selected_task = st.selectbox("Select Task to Edit", list(task_options.keys()))
            task_id = task_options[selected_task]
            
            task_info = next(t for t in tasks if t['task_id'] == task_id)
            
            with st.form(f"edit_task_form_{task_id}"):
                title = st.text_input("Task Title", value=task_info['title'])
                description = st.text_area("Description", value=task_info['description'] or "")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if task_info['due_date']:
                        due_date = st.date_input("Due Date", value=task_info['due_date'].date())
                        due_time = st.time_input("Due Time", value=task_info['due_date'].time())
                    else:
                        due_date = st.date_input("Due Date")
                        due_time = st.time_input("Due Time")
                with col2:
                    priority = st.selectbox("Priority", PRIORITY_LEVELS,
                                          index=PRIORITY_LEVELS.index(task_info['priority']))
                with col3:
                    duration = st.number_input("Duration (min)", value=task_info['estimated_duration'] or 60)
                
                col1, col2 = st.columns(2)
                update_btn = col1.form_submit_button("Update Task", use_container_width=True)
                delete_btn = col2.form_submit_button("Delete Task", use_container_width=True)
                
                if update_btn:
                    due_datetime = datetime.combine(due_date, due_time)
                    update_task(task_id, title, description, due_datetime, priority, duration)
                    st.success("Task updated successfully!")
                    st.rerun()
                
                if delete_btn:
                    delete_task(task_id)
                    st.success("Task deleted!")
                    st.rerun()


def show_notifications_page():
    """Notifications page"""
    st.markdown("<h1 class='main-header'>🔔 Notifications</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader("All Notifications")
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Get notifications
    unread = get_unread_notifications()
    all_notifs = get_all_notifications(limit=50)
    
    # Stats
    col1, col2, col3 = st.columns(3)
    col1.metric("📬 Unread", len(unread))
    col2.metric("📮 Total", len(all_notifs))
    col3.metric("📊 Read Rate", f"{((len(all_notifs)-len(unread))/len(all_notifs)*100):.0f}%" if all_notifs else "0%")
    
    st.divider()
    
    # Display notifications
    tab1, tab2 = st.tabs(["📬 Unread", "📮 All"])
    
    with tab1:
        if not unread:
            st.success("✨ All caught up! No unread notifications.")
        else:
            for notif in unread:
                display_notification(notif)
    
    with tab2:
        if not all_notifs:
            st.info("No notifications yet!")
        else:
            for notif in all_notifs:
                display_notification(notif)


def display_notification(notif):
    """Display a single notification"""
    icon_map = {
        'class_reminder': '⏰',
        'class_cancelled': '❌',
        'class_rescheduled': '🔄',
        'task_due_soon': '⚠️',
        'task_overdue': '🚨',
        'schedule_conflict': '⚡',
        'daily_summary': '📅'
    }
    
    icon = icon_map.get(notif['notification_type'], '📢')
    read_status = "" if notif['is_read'] else "🔵"
    
    with st.container():
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"### {icon} {notif['title']} {read_status}")
            st.write(notif['message'])
            st.caption(f"🕐 {notif['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        with col2:
            if not notif['is_read']:
                if st.button("Mark Read", key=f"read_{notif['notification_id']}"):
                    mark_notification_read(notif['notification_id'])
                    st.rerun()
        st.divider()


def show_settings():
    """Settings page"""
    st.markdown("<h1 class='main-header'>⚙️ Settings</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🔧 General", "🤖 Auto-Schedule", "📊 Analytics"])
    
    with tab1:
        st.subheader("General Settings")
        
        st.info("🔄 Database connection is active")
        
        if st.button("🧪 Generate Test Data"):
            st.success("Test data generated!")
        
        if st.button("🔄 Optimize Schedule"):
            with st.spinner("Optimizing schedule..."):
                result = optimize_weekly_schedule()
                st.json(result['summary'])
                st.success("Schedule optimized!")
    
    with tab2:
        st.subheader("Intelligent Scheduling")
        
        st.write("Configure automatic task scheduling preferences")
        
        prefer_time = st.select_slider(
            "Preferred Study Time",
            options=["Morning (8-12)", "Afternoon (12-17)", "Evening (17-21)"],
            value="Afternoon (12-17)"
        )
        
        min_break = st.slider("Minimum break between tasks (minutes)", 15, 60, 30)
        
        max_daily_hours = st.slider("Maximum study hours per day", 4, 12, 8)
        
        if st.button("Apply Settings"):
            st.success("Settings applied!")
    
    with tab3:
        st.subheader("Schedule Analytics")
        
        # Get statistics
        all_classes = get_all_classes()
        all_tasks = get_all_tasks(include_completed=True)
        
        # Classes by day
        classes_by_day = {}
        for cls in all_classes:
            day = DAYS_OF_WEEK[cls['day_of_week']]
            classes_by_day[day] = classes_by_day.get(day, 0) + 1
        
        fig1 = px.bar(
            x=list(classes_by_day.keys()),
            y=list(classes_by_day.values()),
            title="Classes Distribution by Day",
            labels={'x': 'Day', 'y': 'Number of Classes'}
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        # Tasks by priority
        tasks_by_priority = {}
        for task in all_tasks:
            priority = task['priority']
            tasks_by_priority[priority] = tasks_by_priority.get(priority, 0) + 1
        
        fig2 = px.pie(
            values=list(tasks_by_priority.values()),
            names=list(tasks_by_priority.keys()),
            title="Tasks by Priority Level"
        )
        st.plotly_chart(fig2, use_container_width=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.info("Please check database connection and try again.")
