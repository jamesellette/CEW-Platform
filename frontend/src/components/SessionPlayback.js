import React, { useState, useEffect, useCallback, useRef } from 'react';
import { recordingApi } from '../api';

// Maximum characters to display for command output
const MAX_OUTPUT_DISPLAY_LENGTH = 500;

/**
 * SessionPlayback component provides playback of recorded training sessions.
 * Allows instructors to review trainee actions for assessment and debriefing.
 */
export default function SessionPlayback({ sessionId, onClose }) {
  const [session, setSession] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentEventIndex, setCurrentEventIndex] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const playbackTimerRef = useRef(null);

  // Fetch playback data - only depends on sessionId since speed is handled client-side
  const fetchPlaybackData = useCallback(async () => {
    try {
      setLoading(true);
      // Fetch at 1x speed, client handles speed adjustment
      const response = await recordingApi.getPlayback(sessionId, 1.0);
      setSession(response.data.session);
      setEvents(response.data.events);
      setError(null);
    } catch (err) {
      setError('Failed to load playback data');
      console.error('Playback load error:', err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchPlaybackData();
  }, [fetchPlaybackData]);

  // Handle playback
  const startPlayback = useCallback(() => {
    if (currentEventIndex >= events.length) {
      setCurrentEventIndex(0);
    }
    setIsPlaying(true);
  }, [currentEventIndex, events.length]);

  const pausePlayback = useCallback(() => {
    setIsPlaying(false);
    if (playbackTimerRef.current) {
      clearTimeout(playbackTimerRef.current);
    }
  }, []);

  const resetPlayback = useCallback(() => {
    pausePlayback();
    setCurrentEventIndex(0);
  }, [pausePlayback]);

  // Playback effect
  useEffect(() => {
    if (!isPlaying || events.length === 0) return;

    const scheduleNextEvent = () => {
      if (currentEventIndex >= events.length - 1) {
        setIsPlaying(false);
        return;
      }

      const currentEvent = events[currentEventIndex];
      const nextEvent = events[currentEventIndex + 1];
      // Calculate time difference between consecutive events
      const timeDiff = nextEvent.elapsed_ms - currentEvent.elapsed_ms;
      const delay = timeDiff / playbackSpeed;

      playbackTimerRef.current = setTimeout(() => {
        setCurrentEventIndex(prev => prev + 1);
      }, Math.max(delay, 10)); // Minimum 10ms delay
    };

    scheduleNextEvent();

    return () => {
      if (playbackTimerRef.current) {
        clearTimeout(playbackTimerRef.current);
      }
    };
  }, [isPlaying, currentEventIndex, events, playbackSpeed]);

  const formatTime = (ms) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const getEventIcon = (eventType) => {
    const icons = {
      lab_started: '🚀',
      lab_stopped: '🛑',
      lab_paused: '⏸️',
      lab_resumed: '▶️',
      command_executed: '💻',
      terminal_input: '⌨️',
      terminal_output: '📤',
      user_action: '🖱️',
      objective_completed: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️',
    };
    return icons[eventType] || '📝';
  };

  const getEventColor = (eventType) => {
    const colors = {
      lab_started: '#28a745',
      lab_stopped: '#dc3545',
      command_executed: '#007bff',
      objective_completed: '#28a745',
      error: '#dc3545',
      warning: '#ffc107',
    };
    return colors[eventType] || '#6c757d';
  };

  if (loading) {
    return <div style={containerStyle}>Loading playback data...</div>;
  }

  if (error) {
    return (
      <div style={{ ...containerStyle, backgroundColor: '#f8d7da' }}>
        <p>{error}</p>
        <button onClick={fetchPlaybackData} style={buttonStyle}>Retry</button>
        {onClose && <button onClick={onClose} style={secondaryButtonStyle}>Close</button>}
      </div>
    );
  }

  const currentEvent = events[currentEventIndex];
  const progress = events.length > 0 ? (currentEventIndex / (events.length - 1)) * 100 : 0;

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <h2>📼 Session Playback</h2>
        <div style={sessionInfoStyle}>
          <span style={badgeStyle}>{session?.scenario_name}</span>
          <span style={userBadgeStyle}>👤 {session?.username}</span>
          <span style={durationBadgeStyle}>
            ⏱️ {Math.round(session?.duration_seconds || 0)}s
          </span>
        </div>
      </div>

      {/* Playback Controls */}
      <div style={controlsContainerStyle}>
        <div style={controlsStyle}>
          <button
            onClick={resetPlayback}
            style={controlButtonStyle}
            title="Reset"
          >
            ⏮️
          </button>
          {isPlaying ? (
            <button
              onClick={pausePlayback}
              style={controlButtonStyle}
              title="Pause"
            >
              ⏸️
            </button>
          ) : (
            <button
              onClick={startPlayback}
              style={controlButtonStyle}
              title="Play"
            >
              ▶️
            </button>
          )}
          <button
            onClick={() => setCurrentEventIndex(Math.min(currentEventIndex + 1, events.length - 1))}
            style={controlButtonStyle}
            title="Next Event"
          >
            ⏭️
          </button>

          <div style={speedControlStyle}>
            <label>Speed:</label>
            <select
              value={playbackSpeed}
              onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value))}
              style={selectStyle}
            >
              <option value="0.5">0.5x</option>
              <option value="1">1x</option>
              <option value="2">2x</option>
              <option value="5">5x</option>
              <option value="10">10x</option>
            </select>
          </div>
        </div>

        {/* Progress Bar */}
        <div style={progressContainerStyle}>
          <span style={timeStyle}>{formatTime(currentEvent?.elapsed_ms || 0)}</span>
          <div style={progressBarStyle}>
            <div style={{ ...progressFillStyle, width: `${progress}%` }}></div>
          </div>
          <span style={timeStyle}>
            {formatTime(events[events.length - 1]?.elapsed_ms || 0)}
          </span>
        </div>

        <div style={eventCountStyle}>
          Event {currentEventIndex + 1} of {events.length}
        </div>
      </div>

      {/* Current Event Display */}
      {currentEvent && (
        <div style={currentEventStyle}>
          <div style={eventHeaderStyle}>
            <span style={{ fontSize: '24px' }}>{getEventIcon(currentEvent.event_type)}</span>
            <span style={{ ...eventTypeBadge, backgroundColor: getEventColor(currentEvent.event_type) }}>
              {currentEvent.event_type.replace(/_/g, ' ').toUpperCase()}
            </span>
            <span style={timestampStyle}>
              {new Date(currentEvent.timestamp).toLocaleTimeString()}
            </span>
          </div>

          {currentEvent.hostname && (
            <div style={eventDetailStyle}>
              <span style={labelStyle}>Container:</span>
              <span style={valueStyle}>{currentEvent.hostname}</span>
            </div>
          )}

          {currentEvent.data?.command && (
            <div style={commandBlockStyle}>
              <span style={labelStyle}>Command:</span>
              <code style={codeStyle}>{currentEvent.data.command}</code>
            </div>
          )}

          {currentEvent.data?.output && (
            <div style={outputBlockStyle}>
              <span style={labelStyle}>Output:</span>
              <pre style={preStyle}>{currentEvent.data.output.slice(0, MAX_OUTPUT_DISPLAY_LENGTH)}</pre>
            </div>
          )}

          {currentEvent.data?.exit_code !== undefined && (
            <div style={eventDetailStyle}>
              <span style={labelStyle}>Exit Code:</span>
              <span style={currentEvent.data.exit_code === 0 ? successStyle : errorStyle}>
                {currentEvent.data.exit_code}
              </span>
            </div>
          )}

          {currentEvent.data?.action && (
            <div style={eventDetailStyle}>
              <span style={labelStyle}>Action:</span>
              <span style={valueStyle}>{currentEvent.data.action}</span>
            </div>
          )}
        </div>
      )}

      {/* Event Timeline */}
      <div style={timelineContainerStyle}>
        <h3 style={sectionTitleStyle}>Event Timeline</h3>
        <div style={timelineStyle}>
          {events.map((event, index) => (
            <div
              key={event.event_id}
              style={{
                ...timelineEventStyle,
                backgroundColor: index === currentEventIndex ? '#e3f2fd' : 'transparent',
                borderLeft: index === currentEventIndex ? '3px solid #007bff' : '3px solid #dee2e6',
              }}
              onClick={() => {
                pausePlayback();
                setCurrentEventIndex(index);
              }}
            >
              <span style={timelineIconStyle}>{getEventIcon(event.event_type)}</span>
              <span style={timelineTimeStyle}>{formatTime(event.elapsed_ms)}</span>
              <span style={timelineTypeStyle}>{event.event_type.replace(/_/g, ' ')}</span>
              {event.hostname && <span style={timelineHostStyle}>{event.hostname}</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div style={actionsStyle}>
        {onClose && (
          <button onClick={onClose} style={closeButtonStyle}>
            ✕ Close
          </button>
        )}
      </div>
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
  flexWrap: 'wrap',
  gap: '10px',
};

const sessionInfoStyle = {
  display: 'flex',
  gap: '10px',
  alignItems: 'center',
};

const badgeStyle = {
  padding: '4px 12px',
  borderRadius: '12px',
  fontSize: '12px',
  fontWeight: 'bold',
  backgroundColor: '#007bff',
  color: 'white',
};

const userBadgeStyle = {
  padding: '4px 12px',
  borderRadius: '12px',
  fontSize: '12px',
  backgroundColor: '#e9ecef',
  color: '#495057',
};

const durationBadgeStyle = {
  padding: '4px 12px',
  borderRadius: '12px',
  fontSize: '12px',
  backgroundColor: '#d4edda',
  color: '#155724',
};

const controlsContainerStyle = {
  backgroundColor: 'white',
  padding: '16px',
  borderRadius: '8px',
  marginBottom: '20px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const controlsStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  marginBottom: '12px',
};

const controlButtonStyle = {
  padding: '8px 16px',
  fontSize: '18px',
  backgroundColor: '#f8f9fa',
  border: '1px solid #dee2e6',
  borderRadius: '4px',
  cursor: 'pointer',
};

const speedControlStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  marginLeft: '20px',
};

const selectStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  border: '1px solid #dee2e6',
};

const progressContainerStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
};

const timeStyle = {
  fontSize: '12px',
  color: '#666',
  minWidth: '40px',
};

const progressBarStyle = {
  flex: 1,
  height: '8px',
  backgroundColor: '#e9ecef',
  borderRadius: '4px',
  overflow: 'hidden',
};

const progressFillStyle = {
  height: '100%',
  backgroundColor: '#007bff',
  borderRadius: '4px',
  transition: 'width 0.1s ease',
};

const eventCountStyle = {
  fontSize: '12px',
  color: '#666',
  textAlign: 'center',
  marginTop: '8px',
};

const currentEventStyle = {
  backgroundColor: 'white',
  padding: '16px',
  borderRadius: '8px',
  marginBottom: '20px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const eventHeaderStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  marginBottom: '12px',
  paddingBottom: '12px',
  borderBottom: '1px solid #eee',
};

const eventTypeBadge = {
  padding: '4px 12px',
  borderRadius: '4px',
  fontSize: '11px',
  fontWeight: 'bold',
  color: 'white',
};

const timestampStyle = {
  fontSize: '12px',
  color: '#666',
  marginLeft: 'auto',
};

const eventDetailStyle = {
  display: 'flex',
  gap: '8px',
  marginBottom: '8px',
};

const labelStyle = {
  fontWeight: 'bold',
  color: '#666',
  minWidth: '80px',
};

const valueStyle = {
  color: '#333',
};

const commandBlockStyle = {
  marginTop: '12px',
};

const codeStyle = {
  display: 'block',
  padding: '8px 12px',
  backgroundColor: '#282c34',
  color: '#abb2bf',
  borderRadius: '4px',
  fontFamily: 'monospace',
  fontSize: '13px',
  marginTop: '4px',
};

const outputBlockStyle = {
  marginTop: '12px',
};

const preStyle = {
  padding: '8px 12px',
  backgroundColor: '#f8f9fa',
  border: '1px solid #dee2e6',
  borderRadius: '4px',
  fontFamily: 'monospace',
  fontSize: '12px',
  overflow: 'auto',
  maxHeight: '200px',
  marginTop: '4px',
};

const successStyle = {
  color: '#28a745',
  fontWeight: 'bold',
};

const errorStyle = {
  color: '#dc3545',
  fontWeight: 'bold',
};

const timelineContainerStyle = {
  backgroundColor: 'white',
  padding: '16px',
  borderRadius: '8px',
  marginBottom: '20px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  maxHeight: '300px',
  overflow: 'auto',
};

const sectionTitleStyle = {
  margin: '0 0 12px 0',
  fontSize: '14px',
  fontWeight: '600',
  color: '#666',
};

const timelineStyle = {
  display: 'flex',
  flexDirection: 'column',
};

const timelineEventStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  padding: '8px 12px',
  cursor: 'pointer',
  transition: 'background-color 0.2s',
};

const timelineIconStyle = {
  fontSize: '14px',
};

const timelineTimeStyle = {
  fontSize: '11px',
  color: '#666',
  minWidth: '40px',
  fontFamily: 'monospace',
};

const timelineTypeStyle = {
  fontSize: '12px',
  color: '#333',
  flex: 1,
};

const timelineHostStyle = {
  fontSize: '11px',
  color: '#999',
  fontFamily: 'monospace',
};

const actionsStyle = {
  display: 'flex',
  gap: '10px',
  justifyContent: 'flex-end',
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

const secondaryButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#6c757d',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};

const closeButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#dc3545',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
};
