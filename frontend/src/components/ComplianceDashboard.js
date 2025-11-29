import React, { useState, useEffect, useCallback } from 'react';
import { complianceApi } from '../api';

/**
 * Compliance Dashboard component.
 * Provides NIST Framework mapping, training tracking, and compliance reporting.
 */
export default function ComplianceDashboard({ user }) {
  const [activeTab, setActiveTab] = useState('summary');
  const [summary, setSummary] = useState(null);
  const [certifications, setCertifications] = useState([]);
  const [trainingRecords, setTrainingRecords] = useState([]);
  const [trainingHours, setTrainingHours] = useState(null);
  const [nistMappings, setNistMappings] = useState([]);
  const [nistFunctions, setNistFunctions] = useState([]);
  const [certRequirements, setCertRequirements] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  const isInstructorOrAdmin = ['admin', 'instructor'].includes(user?.role);

  // Load compliance summary
  const loadSummary = useCallback(async () => {
    try {
      const response = await complianceApi.getMySummary();
      setSummary(response.data);
    } catch (err) {
      console.error('Failed to load compliance summary:', err);
    }
  }, []);

  // Load certifications
  const loadCertifications = useCallback(async () => {
    try {
      const response = await complianceApi.getMyCertifications();
      setCertifications(response.data || []);
    } catch (err) {
      console.error('Failed to load certifications:', err);
    }
  }, []);

  // Load training records
  const loadTrainingRecords = useCallback(async () => {
    try {
      const response = await complianceApi.getMyTrainingRecords();
      setTrainingRecords(response.data || []);
    } catch (err) {
      console.error('Failed to load training records:', err);
    }
  }, []);

  // Load training hours
  const loadTrainingHours = useCallback(async () => {
    try {
      const response = await complianceApi.getMyTrainingHours();
      setTrainingHours(response.data);
    } catch (err) {
      console.error('Failed to load training hours:', err);
    }
  }, []);

  // Load NIST data
  const loadNISTData = useCallback(async () => {
    try {
      const [functionsRes, mappingsRes] = await Promise.all([
        complianceApi.getNISTFunctions(),
        complianceApi.listNISTMappings()
      ]);
      setNistFunctions(functionsRes.data || []);
      setNistMappings(mappingsRes.data || []);
    } catch (err) {
      console.error('Failed to load NIST data:', err);
    }
  }, []);

  // Load certification requirements
  const loadCertRequirements = useCallback(async () => {
    try {
      const response = await complianceApi.listCertificationRequirements();
      setCertRequirements(response.data || []);
    } catch (err) {
      console.error('Failed to load certification requirements:', err);
    }
  }, []);

  // Load reports
  const loadReports = useCallback(async () => {
    if (!isInstructorOrAdmin) return;
    try {
      const response = await complianceApi.listReports();
      setReports(response.data || []);
    } catch (err) {
      console.error('Failed to load reports:', err);
    }
  }, [isInstructorOrAdmin]);

  // Load all data
  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      await Promise.all([
        loadSummary(),
        loadCertifications(),
        loadTrainingRecords(),
        loadTrainingHours(),
        loadNISTData(),
        loadCertRequirements(),
        loadReports()
      ]);
      setLoading(false);
    };
    loadAll();
  }, [loadSummary, loadCertifications, loadTrainingRecords, loadTrainingHours, loadNISTData, loadCertRequirements, loadReports]);

  // Enroll in certification
  const handleEnroll = async (requirementId) => {
    try {
      await complianceApi.enrollInCertification(requirementId);
      await loadCertifications();
      await loadSummary();
    } catch (err) {
      setError('Failed to enroll in certification');
    }
  };

  // Generate individual report
  const handleGenerateReport = async () => {
    try {
      const response = await complianceApi.generateIndividualReport({});
      setSuccessMessage(`Report generated successfully (ID: ${response.data.report_id})`);
      setTimeout(() => setSuccessMessage(null), 5000);
      await loadReports();
    } catch (err) {
      setError('Failed to generate report');
    }
  };

  // Export report
  const handleExportReport = async (reportId, format) => {
    try {
      const response = await complianceApi.exportReport(reportId, format);
      const blob = new Blob([response.data], { 
        type: format === 'json' ? 'application/json' : 'text/csv' 
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `compliance_report.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to export report');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'compliant': return '#28a745';
      case 'partial': return '#ffc107';
      case 'non_compliant': return '#dc3545';
      case 'pending': return '#6c757d';
      case 'expired': return '#dc3545';
      default: return '#6c757d';
    }
  };

  if (loading) {
    return <div style={loadingStyle}>Loading compliance data...</div>;
  }

  return (
    <div style={containerStyle}>
      <h2>📋 Compliance Dashboard</h2>
      
      {error && (
        <div style={errorStyle}>
          {error}
          <button onClick={() => setError(null)} style={dismissBtnStyle}>×</button>
        </div>
      )}

      {successMessage && (
        <div style={successStyle}>
          {successMessage}
          <button onClick={() => setSuccessMessage(null)} style={dismissBtnStyle}>×</button>
        </div>
      )}

      {/* Tabs */}
      <div style={tabsStyle}>
        <button
          onClick={() => setActiveTab('summary')}
          style={activeTab === 'summary' ? activeTabStyle : tabStyle}
        >
          Summary
        </button>
        <button
          onClick={() => setActiveTab('training')}
          style={activeTab === 'training' ? activeTabStyle : tabStyle}
        >
          Training Records
        </button>
        <button
          onClick={() => setActiveTab('certifications')}
          style={activeTab === 'certifications' ? activeTabStyle : tabStyle}
        >
          Certifications
        </button>
        <button
          onClick={() => setActiveTab('nist')}
          style={activeTab === 'nist' ? activeTabStyle : tabStyle}
        >
          NIST Framework
        </button>
        {isInstructorOrAdmin && (
          <button
            onClick={() => setActiveTab('reports')}
            style={activeTab === 'reports' ? activeTabStyle : tabStyle}
          >
            Reports
          </button>
        )}
      </div>

      {/* Summary Tab */}
      {activeTab === 'summary' && (
        <div style={tabContentStyle}>
          <h3>Compliance Summary</h3>
          
          {summary && (
            <div style={summaryGridStyle}>
              <div style={summaryCardStyle}>
                <div style={summaryValueStyle}>{summary.total_training_hours?.toFixed(1) || '0'}</div>
                <div style={summaryLabelStyle}>Total Training Hours</div>
              </div>
              <div style={summaryCardStyle}>
                <div style={summaryValueStyle}>{summary.total_certifications || 0}</div>
                <div style={summaryLabelStyle}>Active Certifications</div>
              </div>
              <div style={summaryCardStyle}>
                <div style={{ ...summaryValueStyle, color: '#28a745' }}>
                  {summary.by_status?.compliant || 0}
                </div>
                <div style={summaryLabelStyle}>Compliant</div>
              </div>
              <div style={summaryCardStyle}>
                <div style={{ ...summaryValueStyle, color: '#ffc107' }}>
                  {summary.by_status?.partial || 0}
                </div>
                <div style={summaryLabelStyle}>In Progress</div>
              </div>
            </div>
          )}

          {/* Training Hours Breakdown */}
          {trainingHours && (
            <div style={sectionStyle}>
              <h4>Training Hours by NIST Function</h4>
              <div style={chartContainerStyle}>
                {Object.entries(trainingHours.by_function || {}).map(([func, hours]) => (
                  <div key={func} style={barContainerStyle}>
                    <div style={barLabelStyle}>{func.toUpperCase()}</div>
                    <div style={barBackgroundStyle}>
                      <div 
                        style={{
                          ...barFillStyle,
                          width: `${Math.min((hours / 10) * 100, 100)}%`
                        }}
                      />
                    </div>
                    <div style={barValueStyle}>{hours.toFixed(1)}h</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Training Records Tab */}
      {activeTab === 'training' && (
        <div style={tabContentStyle}>
          <h3>Training Records</h3>
          
          {trainingRecords.length === 0 ? (
            <p style={emptyStyle}>No training records yet. Complete scenarios to build your training history.</p>
          ) : (
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>Scenario</th>
                  <th style={thStyle}>Date</th>
                  <th style={thStyle}>Duration</th>
                  <th style={thStyle}>Score</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Verified</th>
                </tr>
              </thead>
              <tbody>
                {trainingRecords.map((record) => (
                  <tr key={record.record_id}>
                    <td style={tdStyle}>{record.scenario_name}</td>
                    <td style={tdStyle}>
                      {new Date(record.started_at).toLocaleDateString()}
                    </td>
                    <td style={tdStyle}>{record.duration_minutes?.toFixed(0) || 0} min</td>
                    <td style={tdStyle}>{record.score?.toFixed(1) || '-'}</td>
                    <td style={tdStyle}>
                      <span style={{
                        ...statusBadgeStyle,
                        backgroundColor: record.passed ? '#28a745' : '#ffc107'
                      }}>
                        {record.passed ? 'Passed' : 'In Progress'}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      {record.verified_by ? (
                        <span style={{ color: '#28a745' }}>✓ {record.verified_by}</span>
                      ) : (
                        <span style={{ color: '#6c757d' }}>Pending</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Certifications Tab */}
      {activeTab === 'certifications' && (
        <div style={tabContentStyle}>
          <h3>Certification Tracking</h3>
          
          {/* Active Certifications */}
          <h4>Your Certifications</h4>
          {certifications.length === 0 ? (
            <p style={emptyStyle}>You haven't enrolled in any certifications yet.</p>
          ) : (
            <div style={certGridStyle}>
              {certifications.map((cert) => (
                <div key={cert.tracker_id} style={certCardStyle}>
                  <div style={certHeaderStyle}>
                    <span style={certNameStyle}>{cert.certification_name}</span>
                    <span style={{
                      ...statusBadgeStyle,
                      backgroundColor: getStatusColor(cert.status)
                    }}>
                      {cert.status}
                    </span>
                  </div>
                  <div style={progressContainerStyle}>
                    <div style={progressBarStyle}>
                      <div 
                        style={{
                          ...progressFillStyle,
                          width: `${cert.progress_percent || 0}%`,
                          backgroundColor: getStatusColor(cert.status)
                        }}
                      />
                    </div>
                    <span style={progressTextStyle}>
                      {cert.hours_completed?.toFixed(1) || 0} / {cert.hours_required} hours
                    </span>
                  </div>
                  <div style={certDateStyle}>
                    Due: {new Date(cert.end_date).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Available Certifications */}
          <h4 style={{ marginTop: '24px' }}>Available Certifications</h4>
          <div style={certGridStyle}>
            {certRequirements.map((req) => (
              <div key={req.requirement_id} style={certCardStyle}>
                <div style={certHeaderStyle}>
                  <span style={certNameStyle}>{req.certification_name}</span>
                  <span style={certTypeStyle}>{req.certification_type}</span>
                </div>
                <p style={certDescStyle}>{req.description}</p>
                <div style={certDetailsStyle}>
                  <span>📚 {req.hours_required} hours over {req.period_months} months</span>
                </div>
                <button 
                  onClick={() => handleEnroll(req.requirement_id)}
                  style={enrollBtnStyle}
                >
                  Enroll
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* NIST Framework Tab */}
      {activeTab === 'nist' && (
        <div style={tabContentStyle}>
          <h3>NIST Cybersecurity Framework</h3>
          
          <p style={infoTextStyle}>
            The NIST Cybersecurity Framework provides a policy framework for computer security
            guidance for organizations. Scenarios are mapped to NIST categories to track your
            learning across all cybersecurity domains.
          </p>

          <div style={nistGridStyle}>
            {nistFunctions.map((func) => (
              <div key={func.value} style={nistCardStyle}>
                <div style={nistHeaderStyle}>
                  <span style={nistFuncNameStyle}>{func.name}</span>
                </div>
                <p style={nistDescStyle}>{func.description}</p>
                <div style={nistMappingCountStyle}>
                  {nistMappings.filter(m => m.nist_function === func.value).length} scenarios mapped
                </div>
              </div>
            ))}
          </div>

          {/* Scenario Mappings */}
          {nistMappings.length > 0 && (
            <div style={sectionStyle}>
              <h4>Scenario NIST Mappings</h4>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Scenario</th>
                    <th style={thStyle}>Function</th>
                    <th style={thStyle}>Categories</th>
                    <th style={thStyle}>Learning Objectives</th>
                  </tr>
                </thead>
                <tbody>
                  {nistMappings.map((mapping) => (
                    <tr key={mapping.mapping_id}>
                      <td style={tdStyle}>{mapping.scenario_name}</td>
                      <td style={tdStyle}>
                        <span style={nistFuncBadgeStyle}>{mapping.nist_function}</span>
                      </td>
                      <td style={tdStyle}>
                        {mapping.nist_categories.map((cat) => (
                          <span key={cat} style={nistCatBadgeStyle}>{cat}</span>
                        ))}
                      </td>
                      <td style={tdStyle}>
                        {mapping.learning_objectives?.length || 0} objectives
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Reports Tab (Admin/Instructor only) */}
      {activeTab === 'reports' && isInstructorOrAdmin && (
        <div style={tabContentStyle}>
          <h3>Compliance Reports</h3>
          
          <div style={actionsStyle}>
            <button onClick={handleGenerateReport} style={primaryBtnStyle}>
              📊 Generate My Report
            </button>
          </div>

          {reports.length === 0 ? (
            <p style={emptyStyle}>No reports generated yet.</p>
          ) : (
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>Report</th>
                  <th style={thStyle}>Type</th>
                  <th style={thStyle}>Generated</th>
                  <th style={thStyle}>Period</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => (
                  <tr key={report.report_id}>
                    <td style={tdStyle}>{report.title}</td>
                    <td style={tdStyle}>
                      <span style={reportTypeBadgeStyle}>{report.report_type}</span>
                    </td>
                    <td style={tdStyle}>
                      {new Date(report.generated_at).toLocaleString()}
                    </td>
                    <td style={tdStyle}>
                      {new Date(report.period_start).toLocaleDateString()} - {' '}
                      {new Date(report.period_end).toLocaleDateString()}
                    </td>
                    <td style={tdStyle}>
                      <button 
                        onClick={() => handleExportReport(report.report_id, 'json')}
                        style={smallBtnStyle}
                      >
                        JSON
                      </button>
                      <button 
                        onClick={() => handleExportReport(report.report_id, 'csv')}
                        style={smallBtnStyle}
                      >
                        CSV
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

// Styles
const containerStyle = {
  padding: '20px',
};

const loadingStyle = {
  textAlign: 'center',
  padding: '40px',
  color: '#666',
};

const errorStyle = {
  backgroundColor: '#f8d7da',
  color: '#721c24',
  padding: '12px 16px',
  borderRadius: '8px',
  marginBottom: '16px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

const successStyle = {
  backgroundColor: '#d4edda',
  color: '#155724',
  padding: '12px 16px',
  borderRadius: '8px',
  marginBottom: '16px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

const dismissBtnStyle = {
  background: 'none',
  border: 'none',
  fontSize: '20px',
  cursor: 'pointer',
  color: 'inherit',
};

const tabsStyle = {
  display: 'flex',
  gap: '8px',
  marginBottom: '20px',
  borderBottom: '2px solid #dee2e6',
  paddingBottom: '12px',
  overflowX: 'auto',
};

const tabStyle = {
  padding: '10px 20px',
  border: 'none',
  background: '#f8f9fa',
  borderRadius: '8px 8px 0 0',
  cursor: 'pointer',
  fontSize: '14px',
  whiteSpace: 'nowrap',
};

const activeTabStyle = {
  ...tabStyle,
  background: '#007bff',
  color: 'white',
};

const tabContentStyle = {
  padding: '20px 0',
};

const summaryGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
  gap: '16px',
  marginBottom: '24px',
};

const summaryCardStyle = {
  background: '#f8f9fa',
  borderRadius: '12px',
  padding: '20px',
  textAlign: 'center',
};

const summaryValueStyle = {
  fontSize: '32px',
  fontWeight: 'bold',
  color: '#007bff',
};

const summaryLabelStyle = {
  fontSize: '14px',
  color: '#666',
  marginTop: '8px',
};

const sectionStyle = {
  marginTop: '24px',
};

const chartContainerStyle = {
  marginTop: '16px',
};

const barContainerStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  marginBottom: '12px',
};

const barLabelStyle = {
  width: '80px',
  fontSize: '12px',
  fontWeight: '600',
};

const barBackgroundStyle = {
  flex: 1,
  height: '24px',
  backgroundColor: '#e9ecef',
  borderRadius: '12px',
  overflow: 'hidden',
};

const barFillStyle = {
  height: '100%',
  backgroundColor: '#007bff',
  borderRadius: '12px',
  transition: 'width 0.3s ease',
};

const barValueStyle = {
  width: '60px',
  fontSize: '14px',
  textAlign: 'right',
};

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  marginTop: '16px',
};

const thStyle = {
  textAlign: 'left',
  padding: '12px',
  borderBottom: '2px solid #dee2e6',
  fontSize: '14px',
  fontWeight: '600',
};

const tdStyle = {
  padding: '12px',
  borderBottom: '1px solid #dee2e6',
  fontSize: '14px',
};

const statusBadgeStyle = {
  display: 'inline-block',
  padding: '4px 8px',
  borderRadius: '12px',
  fontSize: '12px',
  color: 'white',
  textTransform: 'capitalize',
};

const emptyStyle = {
  textAlign: 'center',
  color: '#666',
  padding: '40px',
  background: '#f8f9fa',
  borderRadius: '8px',
};

const certGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
  gap: '16px',
  marginTop: '16px',
};

const certCardStyle = {
  border: '1px solid #dee2e6',
  borderRadius: '12px',
  padding: '16px',
};

const certHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px',
};

const certNameStyle = {
  fontWeight: '600',
  fontSize: '16px',
};

const certTypeStyle = {
  fontSize: '12px',
  color: '#666',
  textTransform: 'uppercase',
};

const certDescStyle = {
  fontSize: '14px',
  color: '#666',
  marginBottom: '12px',
};

const certDetailsStyle = {
  fontSize: '13px',
  color: '#333',
  marginBottom: '12px',
};

const certDateStyle = {
  fontSize: '12px',
  color: '#666',
};

const progressContainerStyle = {
  marginBottom: '8px',
};

const progressBarStyle = {
  height: '8px',
  backgroundColor: '#e9ecef',
  borderRadius: '4px',
  overflow: 'hidden',
  marginBottom: '4px',
};

const progressFillStyle = {
  height: '100%',
  borderRadius: '4px',
  transition: 'width 0.3s ease',
};

const progressTextStyle = {
  fontSize: '12px',
  color: '#666',
};

const enrollBtnStyle = {
  width: '100%',
  padding: '10px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '14px',
  marginTop: '12px',
};

const infoTextStyle = {
  color: '#666',
  fontSize: '14px',
  lineHeight: '1.6',
  marginBottom: '24px',
};

const nistGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: '16px',
};

const nistCardStyle = {
  border: '1px solid #dee2e6',
  borderRadius: '12px',
  padding: '16px',
  backgroundColor: '#f8f9fa',
};

const nistHeaderStyle = {
  marginBottom: '12px',
};

const nistFuncNameStyle = {
  fontWeight: '600',
  fontSize: '16px',
  color: '#007bff',
};

const nistDescStyle = {
  fontSize: '13px',
  color: '#666',
  marginBottom: '12px',
};

const nistMappingCountStyle = {
  fontSize: '12px',
  color: '#28a745',
  fontWeight: '600',
};

const nistFuncBadgeStyle = {
  display: 'inline-block',
  padding: '4px 8px',
  backgroundColor: '#007bff',
  color: 'white',
  borderRadius: '12px',
  fontSize: '11px',
  textTransform: 'uppercase',
};

const nistCatBadgeStyle = {
  display: 'inline-block',
  padding: '2px 6px',
  backgroundColor: '#e9ecef',
  borderRadius: '4px',
  fontSize: '11px',
  marginRight: '4px',
  marginBottom: '4px',
};

const actionsStyle = {
  marginBottom: '20px',
};

const primaryBtnStyle = {
  padding: '12px 24px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  cursor: 'pointer',
  fontSize: '14px',
};

const reportTypeBadgeStyle = {
  display: 'inline-block',
  padding: '4px 8px',
  backgroundColor: '#17a2b8',
  color: 'white',
  borderRadius: '12px',
  fontSize: '11px',
  textTransform: 'capitalize',
};

const smallBtnStyle = {
  padding: '6px 12px',
  backgroundColor: '#6c757d',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
  marginRight: '4px',
};
