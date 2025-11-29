import React, { useState, useEffect, useCallback } from 'react';
import { progressApi } from '../api';

/**
 * ProgressDashboard component displays trainee progress tracking information.
 * Shows exercise completion, skill assessments, leaderboards, and badges.
 */
export default function ProgressDashboard({ user }) {
  const [activeTab, setActiveTab] = useState('myProgress');
  const [myProgress, setMyProgress] = useState(null);
  const [myReport, setMyReport] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [allProfiles, setAllProfiles] = useState([]);
  const [badges, setBadges] = useState([]);
  const [skillCategories, setSkillCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [leaderboardMetric, setLeaderboardMetric] = useState('score');

  const isInstructor = ['admin', 'instructor'].includes(user?.role);

  // Fetch my progress
  const fetchMyProgress = useCallback(async () => {
    try {
      const [progressRes, reportRes] = await Promise.all([
        progressApi.getMyProgress(),
        progressApi.getMyReport()
      ]);
      setMyProgress(progressRes.data);
      setMyReport(reportRes.data);
    } catch (err) {
      console.error('Failed to load progress:', err);
    }
  }, []);

  // Fetch leaderboard
  const fetchLeaderboard = useCallback(async () => {
    try {
      const response = await progressApi.getLeaderboard(leaderboardMetric, 10);
      setLeaderboard(response.data.entries || []);
    } catch (err) {
      console.error('Failed to load leaderboard:', err);
    }
  }, [leaderboardMetric]);

  // Fetch all profiles (for instructors)
  const fetchAllProfiles = useCallback(async () => {
    if (!isInstructor) return;
    try {
      const response = await progressApi.getAllProfiles();
      setAllProfiles(response.data.profiles || []);
    } catch (err) {
      console.error('Failed to load profiles:', err);
    }
  }, [isInstructor]);

  // Fetch badges and categories
  const fetchMetadata = useCallback(async () => {
    try {
      const [badgesRes, categoriesRes] = await Promise.all([
        progressApi.getBadges(),
        progressApi.getSkillCategories()
      ]);
      setBadges(badgesRes.data.badges || []);
      setSkillCategories(categoriesRes.data.categories || []);
    } catch (err) {
      console.error('Failed to load metadata:', err);
    }
  }, []);

  // Load all data function - extracted for retry functionality
  const loadAllData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([
        fetchMyProgress(),
        fetchLeaderboard(),
        fetchAllProfiles(),
        fetchMetadata()
      ]);
    } catch (err) {
      console.error('Failed to load progress data:', err);
      setError('Failed to load progress data');
    } finally {
      setLoading(false);
    }
  }, [fetchMyProgress, fetchLeaderboard, fetchAllProfiles, fetchMetadata]);

  // Initial load
  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Reload leaderboard when metric changes
  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard, leaderboardMetric]);

  // View user details
  const handleViewUser = async (username) => {
    try {
      const [progressRes, reportRes, skillsRes] = await Promise.all([
        progressApi.getUserProgress(username),
        progressApi.getUserReport(username),
        progressApi.getUserSkills(username)
      ]);
      setSelectedUser({
        username,
        progress: progressRes.data,
        report: reportRes.data,
        skills: skillsRes.data.skills || []
      });
    } catch (err) {
      console.error('Failed to load user details:', err);
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0m';
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return <div style={containerStyle}>Loading progress data...</div>;
  }

  if (error) {
    return (
      <div style={{ ...containerStyle, backgroundColor: '#f8d7da' }}>
        <p>{error}</p>
        <button onClick={loadAllData} style={buttonStyle}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h2>📈 Progress Dashboard</h2>
        <div style={tabsStyle}>
          <button
            onClick={() => setActiveTab('myProgress')}
            style={activeTab === 'myProgress' ? tabActiveStyle : tabStyle}
          >
            My Progress
          </button>
          <button
            onClick={() => setActiveTab('leaderboard')}
            style={activeTab === 'leaderboard' ? tabActiveStyle : tabStyle}
          >
            🏆 Leaderboard
          </button>
          <button
            onClick={() => setActiveTab('badges')}
            style={activeTab === 'badges' ? tabActiveStyle : tabStyle}
          >
            🎖️ Badges
          </button>
          {isInstructor && (
            <button
              onClick={() => setActiveTab('trainees')}
              style={activeTab === 'trainees' ? tabActiveStyle : tabStyle}
            >
              👥 All Trainees
            </button>
          )}
        </div>
      </div>

      {/* My Progress Tab */}
      {activeTab === 'myProgress' && (
        <div style={contentStyle}>
          {/* Progress Summary */}
          <div style={gridStyle}>
            <div style={cardStyle}>
              <h3 style={cardTitleStyle}>📊 Summary</h3>
              <div style={statRowStyle}>
                <span>Exercises Completed:</span>
                <strong>{myReport?.exercises_completed || 0}</strong>
              </div>
              <div style={statRowStyle}>
                <span>Total Score:</span>
                <strong>{myReport?.total_score || 0}</strong>
              </div>
              <div style={statRowStyle}>
                <span>Training Time:</span>
                <strong>{formatDuration(myReport?.total_time_seconds)}</strong>
              </div>
              <div style={statRowStyle}>
                <span>Success Rate:</span>
                <strong>{Math.round((myReport?.success_rate || 0) * 100)}%</strong>
              </div>
            </div>

            <div style={cardStyle}>
              <h3 style={cardTitleStyle}>🎯 Current Level</h3>
              <div style={levelDisplayStyle}>
                <span style={levelNumberStyle}>{myProgress?.level || 1}</span>
                <span style={levelLabelStyle}>Level</span>
              </div>
              <div style={xpBarContainerStyle}>
                <div style={xpBarStyle(myProgress?.experience_percent || 0)}></div>
              </div>
              <div style={xpTextStyle}>
                {myProgress?.experience || 0} / {myProgress?.next_level_experience || 100} XP
              </div>
            </div>

            <div style={cardStyle}>
              <h3 style={cardTitleStyle}>🏅 Badges Earned</h3>
              <div style={badgeCountStyle}>
                {myProgress?.badges_earned?.length || 0}
              </div>
              <div style={badgeListStyle}>
                {(myProgress?.badges_earned || []).slice(0, 3).map((badge, idx) => (
                  <span key={idx} style={miniBadgeStyle}>{badge}</span>
                ))}
                {(myProgress?.badges_earned?.length || 0) > 3 && (
                  <span style={moreBadgesStyle}>+{myProgress.badges_earned.length - 3} more</span>
                )}
              </div>
            </div>
          </div>

          {/* Recent Exercises */}
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>📝 Recent Exercises</h3>
            {(myProgress?.recent_exercises || []).length === 0 ? (
              <p style={emptyTextStyle}>No exercises completed yet. Start training to track your progress!</p>
            ) : (
              <div style={exerciseListStyle}>
                {myProgress.recent_exercises.map((exercise, idx) => (
                  <div key={idx} style={exerciseItemStyle}>
                    <div style={exerciseNameStyle}>{exercise.exercise_name}</div>
                    <div style={exerciseMetaStyle}>
                      <span style={getStatusStyle(exercise.status)}>{exercise.status}</span>
                      <span>Score: {exercise.score || 0}</span>
                      <span>{formatDate(exercise.completed_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Skills */}
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>🛠️ Skills</h3>
            {(myProgress?.skills || []).length === 0 ? (
              <p style={emptyTextStyle}>Complete exercises to develop skills.</p>
            ) : (
              <div style={skillsGridStyle}>
                {myProgress.skills.map((skill, idx) => (
                  <div key={idx} style={skillCardStyle}>
                    <div style={skillNameStyle}>{skill.skill_name}</div>
                    <div style={skillCategoryStyle}>{skill.category}</div>
                    <div style={skillLevelBarContainer}>
                      <div style={skillLevelBar(skill.level * 20)}></div>
                    </div>
                    <div style={skillLevelText}>Level {skill.level}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Leaderboard Tab */}
      {activeTab === 'leaderboard' && (
        <div style={contentStyle}>
          <div style={leaderboardHeaderStyle}>
            <h3>🏆 Top Performers</h3>
            <select
              value={leaderboardMetric}
              onChange={(e) => setLeaderboardMetric(e.target.value)}
              style={selectStyle}
            >
              <option value="score">By Score</option>
              <option value="exercises">By Exercises</option>
              <option value="time">By Training Time</option>
            </select>
          </div>
          
          {leaderboard.length === 0 ? (
            <p style={emptyTextStyle}>No leaderboard data yet.</p>
          ) : (
            <div style={leaderboardListStyle}>
              {leaderboard.map((entry, idx) => (
                <div 
                  key={idx} 
                  style={{
                    ...leaderboardItemStyle,
                    backgroundColor: idx < 3 ? getRankColor(idx) : 'white'
                  }}
                >
                  <span style={rankStyle}>{idx + 1}</span>
                  <span style={leaderboardNameStyle}>{entry.username}</span>
                  <span style={leaderboardValueStyle}>
                    {leaderboardMetric === 'time' 
                      ? formatDuration(entry.value)
                      : entry.value}
                  </span>
                  {isInstructor && (
                    <button
                      onClick={() => handleViewUser(entry.username)}
                      style={viewButtonStyle}
                    >
                      View
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Badges Tab */}
      {activeTab === 'badges' && (
        <div style={contentStyle}>
          <h3>🎖️ Available Badges</h3>
          {badges.length === 0 ? (
            <p style={emptyTextStyle}>No badges defined yet.</p>
          ) : (
            <div style={badgesGridStyle}>
              {badges.map((badge, idx) => {
                const earned = (myProgress?.badges_earned || []).includes(badge.badge_id);
                return (
                  <div key={idx} style={{
                    ...badgeCardStyle,
                    opacity: earned ? 1 : 0.5
                  }}>
                    <div style={badgeIconStyle}>{earned ? '🏅' : '🔒'}</div>
                    <div style={badgeNameStyle}>{badge.name}</div>
                    <div style={badgeDescStyle}>{badge.description}</div>
                    <div style={badgeRequirementStyle}>
                      {badge.requirement}
                    </div>
                    {earned && <div style={earnedBadgeStyle}>✓ Earned</div>}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* All Trainees Tab (Instructors only) */}
      {activeTab === 'trainees' && isInstructor && (
        <div style={contentStyle}>
          <h3>👥 All Trainee Profiles</h3>
          {allProfiles.length === 0 ? (
            <p style={emptyTextStyle}>No trainee profiles found.</p>
          ) : (
            <div style={profilesListStyle}>
              {allProfiles.map((profile, idx) => (
                <div key={idx} style={profileCardStyle}>
                  <div style={profileHeaderStyle}>
                    <span style={profileNameStyle}>{profile.username}</span>
                    <span style={profileLevelStyle}>Lvl {profile.level || 1}</span>
                  </div>
                  <div style={profileStatsStyle}>
                    <div style={profileStatStyle}>
                      <span>Exercises:</span>
                      <strong>{profile.exercises_completed || 0}</strong>
                    </div>
                    <div style={profileStatStyle}>
                      <span>Score:</span>
                      <strong>{profile.total_score || 0}</strong>
                    </div>
                    <div style={profileStatStyle}>
                      <span>Badges:</span>
                      <strong>{profile.badges_count || 0}</strong>
                    </div>
                  </div>
                  <button
                    onClick={() => handleViewUser(profile.username)}
                    style={viewDetailButtonStyle}
                  >
                    View Details
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* User Detail Modal */}
      {selectedUser && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>👤 {selectedUser.username}'s Progress</h3>
              <button onClick={() => setSelectedUser(null)} style={closeButtonStyle}>✕</button>
            </div>
            <div style={modalBodyStyle}>
              <div style={modalGridStyle}>
                <div style={modalStatStyle}>
                  <span>Level</span>
                  <strong>{selectedUser.progress?.level || 1}</strong>
                </div>
                <div style={modalStatStyle}>
                  <span>Exercises</span>
                  <strong>{selectedUser.report?.exercises_completed || 0}</strong>
                </div>
                <div style={modalStatStyle}>
                  <span>Score</span>
                  <strong>{selectedUser.report?.total_score || 0}</strong>
                </div>
                <div style={modalStatStyle}>
                  <span>Success Rate</span>
                  <strong>{Math.round((selectedUser.report?.success_rate || 0) * 100)}%</strong>
                </div>
              </div>
              
              <h4 style={modalSectionTitle}>Skills</h4>
              {selectedUser.skills.length === 0 ? (
                <p style={emptyTextStyle}>No skills recorded.</p>
              ) : (
                <div style={modalSkillsStyle}>
                  {selectedUser.skills.map((skill, idx) => (
                    <div key={idx} style={modalSkillStyle}>
                      <span>{skill.skill_name}</span>
                      <span>Level {skill.level}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper functions

// Rank colors for leaderboard (gold, silver, bronze)
// Appending '20' adds 20% opacity in hex color format (12.5% opacity = 0x20 out of 0xFF)
const RANK_OPACITY_SUFFIX = '20';

const getRankColor = (rank) => {
  const colors = ['#ffd700', '#c0c0c0', '#cd7f32']; // gold, silver, bronze
  return colors[rank] + RANK_OPACITY_SUFFIX;
};

const getStatusStyle = (status) => ({
  padding: '2px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  backgroundColor: status === 'completed' ? '#d4edda' : 
                   status === 'failed' ? '#f8d7da' : '#fff3cd',
  color: status === 'completed' ? '#155724' : 
         status === 'failed' ? '#721c24' : '#856404',
});

// Styles
const containerStyle = {
  padding: '20px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
  marginBottom: '20px',
};

const headerStyle = {
  marginBottom: '20px',
};

const tabsStyle = {
  display: 'flex',
  gap: '8px',
  marginTop: '16px',
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

const gridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
  gap: '16px',
  marginBottom: '20px',
};

const cardStyle = {
  backgroundColor: 'white',
  padding: '16px',
  borderRadius: '8px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const cardTitleStyle = {
  margin: '0 0 12px 0',
  fontSize: '14px',
  color: '#666',
};

const statRowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  padding: '8px 0',
  borderBottom: '1px solid #eee',
  fontSize: '14px',
};

const levelDisplayStyle = {
  textAlign: 'center',
  marginBottom: '12px',
};

const levelNumberStyle = {
  fontSize: '48px',
  fontWeight: 'bold',
  color: '#007bff',
};

const levelLabelStyle = {
  display: 'block',
  fontSize: '14px',
  color: '#666',
};

const xpBarContainerStyle = {
  height: '8px',
  backgroundColor: '#e9ecef',
  borderRadius: '4px',
  overflow: 'hidden',
};

const xpBarStyle = (percent) => ({
  height: '100%',
  width: `${percent}%`,
  backgroundColor: '#28a745',
  transition: 'width 0.3s ease',
});

const xpTextStyle = {
  fontSize: '12px',
  color: '#666',
  textAlign: 'center',
  marginTop: '4px',
};

const badgeCountStyle = {
  fontSize: '36px',
  fontWeight: 'bold',
  textAlign: 'center',
  color: '#ffc107',
};

const badgeListStyle = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '4px',
  justifyContent: 'center',
  marginTop: '8px',
};

const miniBadgeStyle = {
  padding: '2px 8px',
  backgroundColor: '#ffc107',
  borderRadius: '12px',
  fontSize: '11px',
  color: '#333',
};

const moreBadgesStyle = {
  fontSize: '12px',
  color: '#666',
};

const sectionStyle = {
  marginTop: '24px',
};

const sectionTitleStyle = {
  marginBottom: '12px',
  color: '#333',
};

const emptyTextStyle = {
  color: '#666',
  fontStyle: 'italic',
};

const exerciseListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
};

const exerciseItemStyle = {
  backgroundColor: 'white',
  padding: '12px 16px',
  borderRadius: '8px',
  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
};

const exerciseNameStyle = {
  fontWeight: '600',
  marginBottom: '4px',
};

const exerciseMetaStyle = {
  display: 'flex',
  gap: '16px',
  fontSize: '12px',
  color: '#666',
};

const skillsGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
  gap: '12px',
};

const skillCardStyle = {
  backgroundColor: 'white',
  padding: '12px',
  borderRadius: '8px',
  textAlign: 'center',
};

const skillNameStyle = {
  fontWeight: '600',
  fontSize: '13px',
};

const skillCategoryStyle = {
  fontSize: '11px',
  color: '#666',
  marginBottom: '8px',
};

const skillLevelBarContainer = {
  height: '6px',
  backgroundColor: '#e9ecef',
  borderRadius: '3px',
  overflow: 'hidden',
};

const skillLevelBar = (percent) => ({
  height: '100%',
  width: `${Math.min(100, percent)}%`,
  backgroundColor: '#17a2b8',
});

const skillLevelText = {
  fontSize: '11px',
  color: '#666',
  marginTop: '4px',
};

const leaderboardHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '16px',
};

const selectStyle = {
  padding: '6px 12px',
  borderRadius: '4px',
  border: '1px solid #ced4da',
};

const leaderboardListStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
};

const leaderboardItemStyle = {
  display: 'flex',
  alignItems: 'center',
  padding: '12px 16px',
  borderRadius: '8px',
  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
};

const rankStyle = {
  width: '30px',
  fontWeight: 'bold',
  fontSize: '18px',
  color: '#666',
};

const leaderboardNameStyle = {
  flex: 1,
  fontWeight: '500',
};

const leaderboardValueStyle = {
  fontWeight: 'bold',
  color: '#007bff',
  marginRight: '16px',
};

const viewButtonStyle = {
  padding: '4px 12px',
  backgroundColor: '#6c757d',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const badgesGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
  gap: '16px',
};

const badgeCardStyle = {
  backgroundColor: 'white',
  padding: '16px',
  borderRadius: '8px',
  textAlign: 'center',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const badgeIconStyle = {
  fontSize: '36px',
  marginBottom: '8px',
};

const badgeNameStyle = {
  fontWeight: '600',
  marginBottom: '4px',
};

const badgeDescStyle = {
  fontSize: '12px',
  color: '#666',
  marginBottom: '8px',
};

const badgeRequirementStyle = {
  fontSize: '11px',
  color: '#999',
};

const earnedBadgeStyle = {
  marginTop: '8px',
  color: '#28a745',
  fontWeight: '600',
  fontSize: '12px',
};

const profilesListStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
  gap: '16px',
};

const profileCardStyle = {
  backgroundColor: 'white',
  padding: '16px',
  borderRadius: '8px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};

const profileHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px',
};

const profileNameStyle = {
  fontWeight: '600',
};

const profileLevelStyle = {
  backgroundColor: '#007bff',
  color: 'white',
  padding: '2px 8px',
  borderRadius: '12px',
  fontSize: '11px',
};

const profileStatsStyle = {
  marginBottom: '12px',
};

const profileStatStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '13px',
  padding: '4px 0',
};

const viewDetailButtonStyle = {
  width: '100%',
  padding: '8px',
  backgroundColor: '#17a2b8',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
};

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
  maxWidth: '500px',
  maxHeight: '80vh',
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

const modalBodyStyle = {
  padding: '16px',
};

const modalGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, 1fr)',
  gap: '12px',
  marginBottom: '16px',
};

const modalStatStyle = {
  textAlign: 'center',
  padding: '12px',
  backgroundColor: '#f8f9fa',
  borderRadius: '8px',
};

const modalSectionTitle = {
  marginTop: '16px',
  marginBottom: '8px',
  color: '#333',
};

const modalSkillsStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
};

const modalSkillStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  padding: '8px 12px',
  backgroundColor: '#f8f9fa',
  borderRadius: '4px',
  fontSize: '13px',
};

const buttonStyle = {
  padding: '8px 16px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
};
