import React, { useState, useEffect, useCallback } from 'react';
import { scheduleApi, scenarioApi } from '../api';

// Constants for display
const CALENDAR_EVENT_TITLE_MAX_LENGTH = 12;

/**
 * ScheduleManager component for creating and managing scheduled exercises.
 * Provides calendar view, upcoming schedules, and schedule creation form.
 */
export default function ScheduleManager({ user }) {
  const [activeTab, setActiveTab] = useState('upcoming');
  const [schedules, setSchedules] = useState([]);
  const [mySchedules, setMySchedules] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null); // For inline error messages
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState(null);
  const [calendarYear, setCalendarYear] = useState(new Date().getFullYear());
  const [calendarMonth, setCalendarMonth] = useState(new Date().getMonth() + 1);
  const [calendarData, setCalendarData] = useState(null);

  const isInstructor = ['admin', 'instructor'].includes(user?.role);

  // Form state
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    scenarioId: '',
    scenarioName: '',
    startDate: '',
    startTime: '',
    endDate: '',
    endTime: '',
    participants: '',
    notificationsEnabled: true,
    autoProvision: true,
    autoTeardown: true,
    recurrenceType: 'none',
    notes: '',
  });

  // Fetch upcoming schedules
  const fetchUpcoming = useCallback(async () => {
    try {
      const response = await scheduleApi.getUpcoming(14);
      setSchedules(response.data.schedules || []);
    } catch (err) {
      console.error('Failed to load schedules:', err);
    }
  }, []);

  // Fetch my schedules
  const fetchMySchedules = useCallback(async () => {
    try {
      const response = await scheduleApi.getMySchedules();
      setMySchedules(response.data.schedules || []);
    } catch (err) {
      console.error('Failed to load my schedules:', err);
    }
  }, []);

  // Fetch scenarios for dropdown
  const fetchScenarios = useCallback(async () => {
    try {
      const response = await scenarioApi.list();
      setScenarios(response.data || []);
    } catch (err) {
      console.error('Failed to load scenarios:', err);
    }
  }, []);

  // Fetch calendar data
  const fetchCalendar = useCallback(async () => {
    try {
      const response = await scheduleApi.getCalendar(calendarYear, calendarMonth);
      setCalendarData(response.data);
    } catch (err) {
      console.error('Failed to load calendar:', err);
    }
  }, [calendarYear, calendarMonth]);

  // Load all data
  const loadAllData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([
        fetchUpcoming(),
        fetchMySchedules(),
        fetchScenarios(),
        fetchCalendar()
      ]);
    } catch (err) {
      console.error('Failed to load schedule data:', err);
      setError('Failed to load schedule data');
    } finally {
      setLoading(false);
    }
  }, [fetchUpcoming, fetchMySchedules, fetchScenarios, fetchCalendar]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Reload calendar when month/year changes
  useEffect(() => {
    fetchCalendar();
  }, [fetchCalendar, calendarYear, calendarMonth]);

  // Handle form submission
  const handleCreateSchedule = async (e) => {
    e.preventDefault();
    
    const startDateTime = new Date(`${formData.startDate}T${formData.startTime}`).toISOString();
    const endDateTime = new Date(`${formData.endDate}T${formData.endTime}`).toISOString();
    
    const participants = formData.participants
      .split(',')
      .map(p => p.trim())
      .filter(p => p.length > 0);

    const recurrence = formData.recurrenceType !== 'none' ? {
      recurrence_type: formData.recurrenceType,
      interval: 1
    } : null;

    try {
      await scheduleApi.createSchedule({
        title: formData.title,
        description: formData.description,
        scenario_id: formData.scenarioId,
        scenario_name: formData.scenarioName,
        start_time: startDateTime,
        end_time: endDateTime,
        participants,
        notifications_enabled: formData.notificationsEnabled,
        auto_provision: formData.autoProvision,
        auto_teardown: formData.autoTeardown,
        recurrence,
        notes: formData.notes,
      });
      
      setShowCreateForm(false);
      resetForm();
      setActionError(null);
      await loadAllData();
    } catch (err) {
      console.error('Failed to create schedule:', err);
      setActionError('Failed to create schedule: ' + (err.response?.data?.detail || err.message));
    }
  };

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      scenarioId: '',
      scenarioName: '',
      startDate: '',
      startTime: '',
      endDate: '',
      endTime: '',
      participants: '',
      notificationsEnabled: true,
      autoProvision: true,
      autoTeardown: true,
      recurrenceType: 'none',
      notes: '',
    });
    setActionError(null);
  };

  const handleScenarioChange = (e) => {
    const selectedId = e.target.value;
    const scenario = scenarios.find(s => s.id === selectedId);
    setFormData(prev => ({
      ...prev,
      scenarioId: selectedId,
      scenarioName: scenario?.name || ''
    }));
  };

  const handleCancelSchedule = async (scheduleId) => {
    if (!window.confirm('Are you sure you want to cancel this scheduled exercise?')) return;
    
    try {
      await scheduleApi.cancelSchedule(scheduleId);
      setActionError(null);
      await loadAllData();
    } catch (err) {
      console.error('Failed to cancel schedule:', err);
      setActionError('Failed to cancel schedule. Please try again.');
    }
  };

  const handleStartSchedule = async (scheduleId) => {
    try {
      await scheduleApi.startExercise(scheduleId);
      setActionError(null);
      await loadAllData();
    } catch (err) {
      console.error('Failed to start schedule:', err);
      setActionError('Failed to start schedule. Please try again.');
    }
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString([], { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const getStatusColor = (status) => {
    const colors = {
      scheduled: '#007bff',
      running: '#28a745',
      completed: '#6c757d',
      cancelled: '#dc3545',
      failed: '#dc3545',
      draft: '#ffc107',
    };
    return colors[status] || '#6c757d';
  };

  const getMonthName = (month) => {
    const months = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'];
    return months[month - 1];
  };

  const navigateMonth = (delta) => {
    let newMonth = calendarMonth + delta;
    let newYear = calendarYear;
    
    if (newMonth < 1) {
      newMonth = 12;
      newYear--;
    } else if (newMonth > 12) {
      newMonth = 1;
      newYear++;
    }
    
    setCalendarMonth(newMonth);
    setCalendarYear(newYear);
  };

  // Generate calendar grid
  const generateCalendarGrid = () => {
    if (!calendarData) return [];
    
    const firstDay = new Date(calendarYear, calendarMonth - 1, 1).getDay();
    const daysInMonth = new Date(calendarYear, calendarMonth, 0).getDate();
    
    const grid = [];
    let week = [];
    
    // Add empty cells for days before the 1st
    for (let i = 0; i < firstDay; i++) {
      week.push(null);
    }
    
    // Add days
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${calendarYear}-${String(calendarMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      const daySchedules = calendarData.schedules_by_day?.[dateStr] || [];
      
      week.push({ day, schedules: daySchedules });
      
      if (week.length === 7) {
        grid.push(week);
        week = [];
      }
    }
    
    // Fill remaining days
    while (week.length < 7 && week.length > 0) {
      week.push(null);
    }
    if (week.length > 0) grid.push(week);
    
    return grid;
  };

  if (loading) {
    return <div style={containerStyle}>Loading schedules...</div>;
  }

  if (error) {
    return (
      <div style={{ ...containerStyle, backgroundColor: '#f8d7da' }}>
        <p>{error}</p>
        <button onClick={loadAllData} style={buttonStyle}>Retry</button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h2>📅 Exercise Schedule</h2>
        {isInstructor && (
          <button onClick={() => setShowCreateForm(true)} style={primaryButtonStyle}>
            + New Schedule
          </button>
        )}
      </div>

      {/* Action Error Message */}
      {actionError && (
        <div style={actionErrorStyle}>
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} style={dismissErrorStyle}>✕</button>
        </div>
      )}

      {/* Tabs */}
      <div style={tabsStyle}>
        <button
          onClick={() => setActiveTab('upcoming')}
          style={activeTab === 'upcoming' ? tabActiveStyle : tabStyle}
        >
          📋 Upcoming
        </button>
        <button
          onClick={() => setActiveTab('calendar')}
          style={activeTab === 'calendar' ? tabActiveStyle : tabStyle}
        >
          📆 Calendar
        </button>
        <button
          onClick={() => setActiveTab('mySchedules')}
          style={activeTab === 'mySchedules' ? tabActiveStyle : tabStyle}
        >
          👤 My Schedules
        </button>
      </div>

      {/* Upcoming Tab */}
      {activeTab === 'upcoming' && (
        <div style={contentStyle}>
          <h3>Upcoming Exercises (Next 2 Weeks)</h3>
          {schedules.length === 0 ? (
            <p style={emptyTextStyle}>No upcoming exercises scheduled.</p>
          ) : (
            <div style={scheduleListStyle}>
              {schedules.map((schedule) => (
                <div key={schedule.schedule_id} style={scheduleCardStyle}>
                  <div style={cardHeaderStyle}>
                    <span style={scheduleTitleStyle}>{schedule.title}</span>
                    <span style={{ 
                      ...statusBadgeStyle, 
                      backgroundColor: getStatusColor(schedule.status) 
                    }}>
                      {schedule.status}
                    </span>
                  </div>
                  <div style={cardBodyStyle}>
                    <div style={scheduleMetaStyle}>
                      <span>📝 {schedule.scenario_name}</span>
                    </div>
                    <div style={scheduleMetaStyle}>
                      <span>🕐 {formatDateTime(schedule.start_time)} - {formatDateTime(schedule.end_time)}</span>
                    </div>
                    <div style={scheduleMetaStyle}>
                      <span>👥 {schedule.participants?.length || 0} participants</span>
                    </div>
                    {schedule.description && (
                      <p style={descriptionStyle}>{schedule.description}</p>
                    )}
                  </div>
                  <div style={cardFooterStyle}>
                    <button
                      onClick={() => setSelectedSchedule(schedule)}
                      style={viewButtonStyle}
                    >
                      View Details
                    </button>
                    {isInstructor && schedule.status === 'scheduled' && (
                      <>
                        <button
                          onClick={() => handleStartSchedule(schedule.schedule_id)}
                          style={startButtonStyle}
                        >
                          ▶️ Start Now
                        </button>
                        <button
                          onClick={() => handleCancelSchedule(schedule.schedule_id)}
                          style={cancelButtonStyle}
                        >
                          Cancel
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Calendar Tab */}
      {activeTab === 'calendar' && (
        <div style={contentStyle}>
          <div style={calendarHeaderStyle}>
            <button onClick={() => navigateMonth(-1)} style={navButtonStyle}>◀</button>
            <h3>{getMonthName(calendarMonth)} {calendarYear}</h3>
            <button onClick={() => navigateMonth(1)} style={navButtonStyle}>▶</button>
          </div>
          
          <div style={calendarGridStyle}>
            {/* Day headers */}
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
              <div key={day} style={calendarDayHeaderStyle}>{day}</div>
            ))}
            
            {/* Calendar cells */}
            {generateCalendarGrid().map((week, weekIdx) => (
              week.map((cell, dayIdx) => (
                <div 
                  key={`${weekIdx}-${dayIdx}`} 
                  style={{
                    ...calendarCellStyle,
                    backgroundColor: cell?.schedules?.length ? '#e3f2fd' : 'white'
                  }}
                >
                  {cell && (
                    <>
                      <span style={calendarDayStyle}>{cell.day}</span>
                      {cell.schedules.length > 0 && (
                        <div style={calendarEventsStyle}>
                          {cell.schedules.slice(0, 2).map((s, i) => (
                            <div key={i} style={calendarEventStyle}>
                              {s.title?.length > CALENDAR_EVENT_TITLE_MAX_LENGTH 
                                ? s.title.substring(0, CALENDAR_EVENT_TITLE_MAX_LENGTH) + '...'
                                : s.title}
                            </div>
                          ))}
                          {cell.schedules.length > 2 && (
                            <span style={moreEventsStyle}>+{cell.schedules.length - 2} more</span>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))
            ))}
          </div>
        </div>
      )}

      {/* My Schedules Tab */}
      {activeTab === 'mySchedules' && (
        <div style={contentStyle}>
          <h3>Exercises I'm Participating In</h3>
          {mySchedules.length === 0 ? (
            <p style={emptyTextStyle}>You're not registered for any scheduled exercises.</p>
          ) : (
            <div style={scheduleListStyle}>
              {mySchedules.map((schedule) => (
                <div key={schedule.schedule_id} style={scheduleCardStyle}>
                  <div style={cardHeaderStyle}>
                    <span style={scheduleTitleStyle}>{schedule.title}</span>
                    <span style={{ 
                      ...statusBadgeStyle, 
                      backgroundColor: getStatusColor(schedule.status) 
                    }}>
                      {schedule.status}
                    </span>
                  </div>
                  <div style={cardBodyStyle}>
                    <div style={scheduleMetaStyle}>
                      <span>📝 {schedule.scenario_name}</span>
                    </div>
                    <div style={scheduleMetaStyle}>
                      <span>🕐 {formatDateTime(schedule.start_time)}</span>
                    </div>
                    <div style={scheduleMetaStyle}>
                      <span>👤 Created by: {schedule.created_by}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create Schedule Modal */}
      {showCreateForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>📅 Schedule New Exercise</h3>
              <button onClick={() => setShowCreateForm(false)} style={closeButtonStyle}>✕</button>
            </div>
            <form onSubmit={handleCreateSchedule} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  style={inputStyle}
                  required
                />
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Scenario *</label>
                <select
                  value={formData.scenarioId}
                  onChange={handleScenarioChange}
                  style={inputStyle}
                  required
                >
                  <option value="">Select a scenario...</option>
                  {scenarios.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  style={{ ...inputStyle, minHeight: '60px' }}
                />
              </div>
              
              <div style={formRowStyle}>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Start Date *</label>
                  <input
                    type="date"
                    value={formData.startDate}
                    onChange={(e) => setFormData(prev => ({ ...prev, startDate: e.target.value }))}
                    style={inputStyle}
                    required
                  />
                </div>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>Start Time *</label>
                  <input
                    type="time"
                    value={formData.startTime}
                    onChange={(e) => setFormData(prev => ({ ...prev, startTime: e.target.value }))}
                    style={inputStyle}
                    required
                  />
                </div>
              </div>
              
              <div style={formRowStyle}>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>End Date *</label>
                  <input
                    type="date"
                    value={formData.endDate}
                    onChange={(e) => setFormData(prev => ({ ...prev, endDate: e.target.value }))}
                    style={inputStyle}
                    required
                  />
                </div>
                <div style={formGroupStyle}>
                  <label style={labelStyle}>End Time *</label>
                  <input
                    type="time"
                    value={formData.endTime}
                    onChange={(e) => setFormData(prev => ({ ...prev, endTime: e.target.value }))}
                    style={inputStyle}
                    required
                  />
                </div>
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Participants (comma-separated usernames)</label>
                <input
                  type="text"
                  value={formData.participants}
                  onChange={(e) => setFormData(prev => ({ ...prev, participants: e.target.value }))}
                  style={inputStyle}
                  placeholder="user1, user2, user3"
                />
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Recurrence</label>
                <select
                  value={formData.recurrenceType}
                  onChange={(e) => setFormData(prev => ({ ...prev, recurrenceType: e.target.value }))}
                  style={inputStyle}
                >
                  <option value="none">No recurrence</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="biweekly">Bi-weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              
              <div style={checkboxGroupStyle}>
                <label style={checkboxLabelStyle}>
                  <input
                    type="checkbox"
                    checked={formData.notificationsEnabled}
                    onChange={(e) => setFormData(prev => ({ ...prev, notificationsEnabled: e.target.checked }))}
                  />
                  Enable notifications
                </label>
                <label style={checkboxLabelStyle}>
                  <input
                    type="checkbox"
                    checked={formData.autoProvision}
                    onChange={(e) => setFormData(prev => ({ ...prev, autoProvision: e.target.checked }))}
                  />
                  Auto-provision lab
                </label>
                <label style={checkboxLabelStyle}>
                  <input
                    type="checkbox"
                    checked={formData.autoTeardown}
                    onChange={(e) => setFormData(prev => ({ ...prev, autoTeardown: e.target.checked }))}
                  />
                  Auto-teardown lab
                </label>
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Notes</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  style={{ ...inputStyle, minHeight: '40px' }}
                />
              </div>
              
              <div style={formActionsStyle}>
                <button type="button" onClick={() => setShowCreateForm(false)} style={secondaryButtonStyle}>
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Create Schedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Schedule Detail Modal */}
      {selectedSchedule && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>📅 {selectedSchedule.title}</h3>
              <button onClick={() => setSelectedSchedule(null)} style={closeButtonStyle}>✕</button>
            </div>
            <div style={detailBodyStyle}>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Scenario:</span>
                <span>{selectedSchedule.scenario_name}</span>
              </div>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Status:</span>
                <span style={{ 
                  ...statusBadgeStyle, 
                  backgroundColor: getStatusColor(selectedSchedule.status) 
                }}>
                  {selectedSchedule.status}
                </span>
              </div>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Start:</span>
                <span>{formatDateTime(selectedSchedule.start_time)}</span>
              </div>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>End:</span>
                <span>{formatDateTime(selectedSchedule.end_time)}</span>
              </div>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Created by:</span>
                <span>{selectedSchedule.created_by}</span>
              </div>
              {selectedSchedule.description && (
                <div style={detailRowStyle}>
                  <span style={detailLabelStyle}>Description:</span>
                  <span>{selectedSchedule.description}</span>
                </div>
              )}
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Participants:</span>
                <span>
                  {selectedSchedule.participants?.length > 0 
                    ? selectedSchedule.participants.join(', ')
                    : 'No participants yet'}
                </span>
              </div>
              {selectedSchedule.notes && (
                <div style={detailRowStyle}>
                  <span style={detailLabelStyle}>Notes:</span>
                  <span>{selectedSchedule.notes}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Styles
const containerStyle = {
  padding: '20px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  marginBottom: '20px',
};

const headerStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '20px',
};

const actionErrorStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px 16px',
  backgroundColor: '#f8d7da',
  color: '#721c24',
  borderRadius: '4px',
  marginBottom: '16px',
  fontSize: '14px',
};

const dismissErrorStyle = {
  backgroundColor: 'transparent',
  border: 'none',
  color: '#721c24',
  cursor: 'pointer',
  fontSize: '16px',
  padding: '0 4px',
};

const tabsStyle = {
  display: 'flex',
  gap: '8px',
  marginBottom: '20px',
};

const tabStyle = {
  padding: '8px 16px',
  backgroundColor: '#e9ecef',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};

const tabActiveStyle = {
  ...tabStyle,
  backgroundColor: '#007bff',
  color: 'white',
};

const contentStyle = {
  marginTop: '20px',
};

const scheduleListStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
  gap: '16px',
};

const scheduleCardStyle = {
  backgroundColor: 'white',
  borderRadius: '8px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  overflow: 'hidden',
};

const cardHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px 16px',
  backgroundColor: '#f8f9fa',
  borderBottom: '1px solid #e9ecef',
};

const scheduleTitleStyle = {
  fontWeight: '600',
  fontSize: '14px',
};

const statusBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  fontWeight: 'bold',
  color: 'white',
  textTransform: 'uppercase',
};

const cardBodyStyle = {
  padding: '16px',
};

const scheduleMetaStyle = {
  fontSize: '13px',
  color: '#666',
  marginBottom: '8px',
};

const descriptionStyle = {
  fontSize: '13px',
  color: '#333',
  marginTop: '8px',
  borderTop: '1px solid #eee',
  paddingTop: '8px',
};

const cardFooterStyle = {
  padding: '12px 16px',
  borderTop: '1px solid #e9ecef',
  display: 'flex',
  gap: '8px',
};

const buttonStyle = {
  padding: '8px 16px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};

const primaryButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#28a745',
};

const secondaryButtonStyle = {
  ...buttonStyle,
  backgroundColor: '#6c757d',
};

const viewButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#17a2b8',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const startButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#28a745',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const cancelButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const emptyTextStyle = {
  color: '#666',
  fontStyle: 'italic',
};

// Calendar styles
const calendarHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '16px',
};

const navButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#e9ecef',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '16px',
};

const calendarGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(7, 1fr)',
  gap: '4px',
};

const calendarDayHeaderStyle = {
  textAlign: 'center',
  padding: '8px',
  fontWeight: 'bold',
  backgroundColor: '#f8f9fa',
  fontSize: '12px',
};

const calendarCellStyle = {
  minHeight: '80px',
  padding: '4px',
  border: '1px solid #e9ecef',
  borderRadius: '4px',
  fontSize: '12px',
};

const calendarDayStyle = {
  fontWeight: 'bold',
  color: '#333',
};

const calendarEventsStyle = {
  marginTop: '4px',
};

const calendarEventStyle = {
  backgroundColor: '#007bff',
  color: 'white',
  padding: '2px 4px',
  borderRadius: '2px',
  fontSize: '10px',
  marginBottom: '2px',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const moreEventsStyle = {
  fontSize: '10px',
  color: '#666',
};

// Modal styles
const modalOverlayStyle = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(0,0,0,0.5)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
};

const modalStyle = {
  backgroundColor: 'white',
  borderRadius: '8px',
  width: '90%',
  maxWidth: '600px',
  maxHeight: '90vh',
  overflow: 'auto',
};

const modalHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '16px',
  borderBottom: '1px solid #eee',
};

const closeButtonStyle = {
  backgroundColor: 'transparent',
  border: 'none',
  fontSize: '20px',
  cursor: 'pointer',
  color: '#666',
};

const formStyle = {
  padding: '16px',
};

const formGroupStyle = {
  marginBottom: '16px',
};

const formRowStyle = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: '16px',
};

const labelStyle = {
  display: 'block',
  marginBottom: '4px',
  fontWeight: '500',
  fontSize: '13px',
  color: '#333',
};

const inputStyle = {
  width: '100%',
  padding: '8px 12px',
  borderRadius: '4px',
  border: '1px solid #ced4da',
  fontSize: '14px',
  boxSizing: 'border-box',
};

const checkboxGroupStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
  marginBottom: '16px',
};

const checkboxLabelStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  fontSize: '13px',
  cursor: 'pointer',
};

const formActionsStyle = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: '8px',
  marginTop: '16px',
  paddingTop: '16px',
  borderTop: '1px solid #eee',
};

const detailBodyStyle = {
  padding: '16px',
};

const detailRowStyle = {
  display: 'flex',
  marginBottom: '12px',
  fontSize: '14px',
};

const detailLabelStyle = {
  fontWeight: '500',
  color: '#666',
  minWidth: '100px',
  marginRight: '8px',
};
