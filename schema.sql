-- College Timetable Management System Database Schema

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS task_recurrence CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS timetable CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Users table (for future multi-user support)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Timetable table for storing class schedules
CREATE TABLE timetable (
    class_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    subject_name VARCHAR(200) NOT NULL,
    class_type VARCHAR(50), -- Lecture, Lab, Tutorial, etc.
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Monday, 6=Sunday
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    location VARCHAR(200),
    instructor VARCHAR(200),
    color_code VARCHAR(7) DEFAULT '#3498db', -- Hex color for UI
    is_cancelled BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_time_range CHECK (end_time > start_time)
);

-- Tasks table for managing user tasks
CREATE TABLE tasks (
    task_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    due_date TIMESTAMP,
    priority VARCHAR(20) CHECK (priority IN ('Low', 'Medium', 'High', 'Urgent')),
    estimated_duration INTEGER, -- in minutes
    scheduled_date DATE,
    scheduled_start_time TIME,
    scheduled_end_time TIME,
    is_completed BOOLEAN DEFAULT FALSE,
    is_recurring BOOLEAN DEFAULT FALSE,
    color_code VARCHAR(7) DEFAULT '#e74c3c',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Task recurrence table for recurring tasks
CREATE TABLE task_recurrence (
    recurrence_id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(task_id) ON DELETE CASCADE,
    recurrence_type VARCHAR(20) CHECK (recurrence_type IN ('Daily', 'Weekly', 'Monthly')),
    recurrence_interval INTEGER DEFAULT 1, -- Every X days/weeks/months
    recurrence_days INTEGER[], -- Array of days for weekly recurrence (0-6)
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notifications table
CREATE TABLE notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL, -- class_reminder, class_cancelled, task_due, schedule_conflict
    title VARCHAR(300) NOT NULL,
    message TEXT NOT NULL,
    related_class_id INTEGER REFERENCES timetable(class_id) ON DELETE CASCADE,
    related_task_id INTEGER REFERENCES tasks(task_id) ON DELETE CASCADE,
    is_read BOOLEAN DEFAULT FALSE,
    scheduled_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX idx_timetable_user_day ON timetable(user_id, day_of_week);
CREATE INDEX idx_timetable_active ON timetable(user_id, is_active, is_cancelled);
CREATE INDEX idx_tasks_user_due ON tasks(user_id, due_date);
CREATE INDEX idx_tasks_scheduled ON tasks(user_id, scheduled_date);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_timetable_updated_at BEFORE UPDATE ON timetable
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default user (for single-user setup)
INSERT INTO users (username, email) VALUES ('default_user', 'user@college.edu')
ON CONFLICT (username) DO NOTHING;

-- Insert sample timetable data
INSERT INTO timetable (user_id, subject_name, class_type, day_of_week, start_time, end_time, location, instructor, color_code) VALUES
(1, 'Data Structures', 'Lecture', 0, '09:00', '10:30', 'Room 101', 'Dr. Smith', '#3498db'),
(1, 'Database Management', 'Lecture', 0, '11:00', '12:30', 'Room 203', 'Prof. Johnson', '#2ecc71'),
(1, 'Web Development', 'Lab', 0, '14:00', '16:00', 'Lab 301', 'Dr. Williams', '#e74c3c'),
(1, 'Data Structures', 'Tutorial', 1, '10:00', '11:00', 'Room 105', 'TA Brown', '#3498db'),
(1, 'Machine Learning', 'Lecture', 1, '13:00', '14:30', 'Room 202', 'Dr. Davis', '#9b59b6'),
(1, 'Database Management', 'Lab', 2, '09:00', '11:00', 'Lab 302', 'Prof. Johnson', '#2ecc71'),
(1, 'Operating Systems', 'Lecture', 2, '14:00', '15:30', 'Room 104', 'Dr. Miller', '#f39c12'),
(1, 'Web Development', 'Lecture', 3, '09:00', '10:30', 'Room 201', 'Dr. Williams', '#e74c3c'),
(1, 'Machine Learning', 'Lab', 3, '11:00', '13:00', 'Lab 303', 'Dr. Davis', '#9b59b6'),
(1, 'Operating Systems', 'Tutorial', 4, '10:00', '11:00', 'Room 106', 'TA Wilson', '#f39c12'),
(1, 'Project Work', 'Lab', 4, '14:00', '17:00', 'Lab 304', 'All Faculty', '#1abc9c')
ON CONFLICT DO NOTHING;

-- Insert sample tasks
INSERT INTO tasks (user_id, title, description, due_date, priority, estimated_duration, color_code) VALUES
(1, 'Submit Data Structures Assignment', 'Complete assignment on Binary Trees', CURRENT_TIMESTAMP + INTERVAL '3 days', 'High', 120, '#e74c3c'),
(1, 'Prepare for Database Quiz', 'Review chapters 5-7 on Normalization', CURRENT_TIMESTAMP + INTERVAL '2 days', 'Medium', 90, '#f39c12'),
(1, 'Complete Web Dev Project Phase 1', 'Build responsive homepage', CURRENT_TIMESTAMP + INTERVAL '7 days', 'High', 180, '#3498db')
ON CONFLICT DO NOTHING;
