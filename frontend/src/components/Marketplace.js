import React, { useState, useEffect, useCallback } from 'react';
import { marketplaceApi } from '../api';

/**
 * Marketplace component for browsing and managing scenario templates.
 * Allows users to discover, download, rate, and publish scenario templates.
 */
export default function Marketplace({ user }) {
  const [activeTab, setActiveTab] = useState('browse');
  const [templates, setTemplates] = useState([]);
  const [popularTemplates, setPopularTemplates] = useState([]);
  const [recentTemplates, setRecentTemplates] = useState([]);
  const [myTemplates, setMyTemplates] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [showPublishForm, setShowPublishForm] = useState(false);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');

  const isInstructor = ['admin', 'instructor'].includes(user?.role);

  // Form states
  const [publishForm, setPublishForm] = useState({
    name: '',
    description: '',
    category: '',
    tags: '',
    scenarioData: '',
  });

  const [reviewForm, setReviewForm] = useState({
    rating: 5,
    title: '',
    comment: '',
  });

  // Fetch all data
  const fetchTemplates = useCallback(async () => {
    try {
      const params = {};
      if (searchQuery) params.search = searchQuery;
      if (selectedCategory) params.category = selectedCategory;
      const response = await marketplaceApi.listTemplates(params);
      setTemplates(response.data.templates || []);
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  }, [searchQuery, selectedCategory]);

  const fetchPopular = useCallback(async () => {
    try {
      const response = await marketplaceApi.getPopular(6);
      setPopularTemplates(response.data.templates || []);
    } catch (err) {
      console.error('Failed to load popular templates:', err);
    }
  }, []);

  const fetchRecent = useCallback(async () => {
    try {
      const response = await marketplaceApi.getRecent(6);
      setRecentTemplates(response.data.templates || []);
    } catch (err) {
      console.error('Failed to load recent templates:', err);
    }
  }, []);

  const fetchMyTemplates = useCallback(async () => {
    try {
      const response = await marketplaceApi.getMyTemplates();
      setMyTemplates(response.data.templates || []);
    } catch (err) {
      console.error('Failed to load my templates:', err);
    }
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const response = await marketplaceApi.getCategories();
      setCategories(response.data.categories || []);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  }, []);

  const loadAllData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Load essential data on mount - templates are loaded separately by the search useEffect
      await Promise.all([
        fetchPopular(),
        fetchRecent(),
        fetchCategories()
      ]);
      // myTemplates loaded lazily when tab is selected
    } catch (err) {
      console.error('Failed to load marketplace data:', err);
      setError('Failed to load marketplace data');
    } finally {
      setLoading(false);
    }
  }, [fetchPopular, fetchRecent, fetchCategories]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Reload templates when search/filter changes (also handles initial load)
  useEffect(() => {
    if (!loading) {
      fetchTemplates();
    }
  }, [fetchTemplates, searchQuery, selectedCategory, loading]);

  // Lazy load myTemplates when tab is selected
  useEffect(() => {
    if (activeTab === 'myTemplates' && isInstructor && myTemplates.length === 0) {
      fetchMyTemplates();
    }
  }, [activeTab, isInstructor, myTemplates.length, fetchMyTemplates]);

  // View template details
  const handleViewTemplate = async (templateId) => {
    try {
      const response = await marketplaceApi.getTemplate(templateId);
      setSelectedTemplate(response.data);
    } catch (err) {
      console.error('Failed to load template details:', err);
      setActionError('Failed to load template details.');
    }
  };

  // Download/use template
  const handleDownloadTemplate = async (templateId) => {
    try {
      await marketplaceApi.downloadTemplate(templateId);
      setActionError(null);
      setSuccessMessage('Template added to your scenarios!');
      // Auto-clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Failed to download template:', err);
      setActionError('Failed to download template. Please try again.');
    }
  };

  // Publish new template
  const handlePublishTemplate = async (e) => {
    e.preventDefault();
    
    try {
      let scenarioData;
      try {
        scenarioData = JSON.parse(publishForm.scenarioData);
      } catch {
        setActionError('Invalid JSON in scenario data');
        return;
      }

      const tags = publishForm.tags.split(',').map(t => t.trim()).filter(t => t);
      
      await marketplaceApi.createTemplate({
        name: publishForm.name,
        description: publishForm.description,
        category: publishForm.category,
        tags,
        scenario_data: scenarioData,
      });
      
      setShowPublishForm(false);
      resetPublishForm();
      setActionError(null);
      await loadAllData();
    } catch (err) {
      console.error('Failed to publish template:', err);
      setActionError('Failed to publish template: ' + (err.response?.data?.detail || err.message));
    }
  };

  const resetPublishForm = () => {
    setPublishForm({
      name: '',
      description: '',
      category: '',
      tags: '',
      scenarioData: '',
    });
  };

  // Submit review
  const handleSubmitReview = async (e) => {
    e.preventDefault();
    
    if (!selectedTemplate) return;

    try {
      await marketplaceApi.addReview(
        selectedTemplate.template_id,
        reviewForm.rating,
        reviewForm.title,
        reviewForm.comment
      );
      
      setShowReviewForm(false);
      setReviewForm({ rating: 5, title: '', comment: '' });
      setActionError(null);
      // Reload template details
      await handleViewTemplate(selectedTemplate.template_id);
    } catch (err) {
      console.error('Failed to submit review:', err);
      setActionError('Failed to submit review. You may have already reviewed this template.');
    }
  };

  // Submit template for review (approval workflow)
  const handleSubmitForReview = async (templateId) => {
    try {
      await marketplaceApi.submitForReview(templateId);
      setActionError(null);
      await fetchMyTemplates();
    } catch (err) {
      console.error('Failed to submit for review:', err);
      setActionError('Failed to submit template for review.');
    }
  };

  const renderStars = (rating) => {
    const fullStars = Math.floor(rating);
    const hasHalf = rating % 1 >= 0.5;
    const stars = [];
    
    for (let i = 0; i < 5; i++) {
      if (i < fullStars) {
        stars.push(<span key={i} style={starFilledStyle}>★</span>);
      } else if (i === fullStars && hasHalf) {
        stars.push(<span key={i} style={starHalfStyle}>★</span>);
      } else {
        stars.push(<span key={i} style={starEmptyStyle}>☆</span>);
      }
    }
    return stars;
  };

  const getStatusColor = (status) => {
    const colors = {
      draft: '#ffc107',
      pending_review: '#17a2b8',
      approved: '#28a745',
      rejected: '#dc3545',
      deprecated: '#6c757d',
    };
    return colors[status] || '#6c757d';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return <div style={containerStyle}>Loading marketplace...</div>;
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
        <h2>🛒 Scenario Marketplace</h2>
        {isInstructor && (
          <button onClick={() => setShowPublishForm(true)} style={primaryButtonStyle}>
            + Publish Template
          </button>
        )}
      </div>

      {/* Success Message */}
      {successMessage && (
        <div style={successMessageStyle}>
          <span>✓ {successMessage}</span>
          <button onClick={() => setSuccessMessage(null)} style={dismissSuccessStyle}>✕</button>
        </div>
      )}

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
          onClick={() => setActiveTab('browse')}
          style={activeTab === 'browse' ? tabActiveStyle : tabStyle}
        >
          🔍 Browse
        </button>
        <button
          onClick={() => setActiveTab('popular')}
          style={activeTab === 'popular' ? tabActiveStyle : tabStyle}
        >
          🔥 Popular
        </button>
        <button
          onClick={() => setActiveTab('recent')}
          style={activeTab === 'recent' ? tabActiveStyle : tabStyle}
        >
          🆕 Recent
        </button>
        {isInstructor && (
          <button
            onClick={() => setActiveTab('myTemplates')}
            style={activeTab === 'myTemplates' ? tabActiveStyle : tabStyle}
          >
            📁 My Templates
          </button>
        )}
      </div>

      {/* Browse Tab with Search */}
      {activeTab === 'browse' && (
        <div style={contentStyle}>
          <div style={searchBarStyle}>
            <input
              type="text"
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={searchInputStyle}
            />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              style={categorySelectStyle}
            >
              <option value="">All Categories</option>
              {categories.map((cat, idx) => (
                <option key={idx} value={cat}>{cat}</option>
              ))}
            </select>
          </div>
          
          {templates.length === 0 ? (
            <p style={emptyTextStyle}>No templates found matching your criteria.</p>
          ) : (
            <div style={templateGridStyle}>
              {templates.map((template) => (
                <div key={template.template_id} style={templateCardStyle}>
                  <div style={cardHeaderStyle}>
                    <span style={templateNameStyle}>{template.name}</span>
                    {template.category && (
                      <span style={categoryBadgeStyle}>{template.category}</span>
                    )}
                  </div>
                  <div style={cardBodyStyle}>
                    <p style={descriptionStyle}>{template.description?.substring(0, 100)}...</p>
                    <div style={templateMetaStyle}>
                      <span>👤 {template.author_username || 'Unknown'}</span>
                      <span>{renderStars(template.average_rating || 0)} ({template.review_count || 0})</span>
                    </div>
                    <div style={templateMetaStyle}>
                      <span>📥 {template.download_count || 0} downloads</span>
                      <span>v{template.current_version || '1.0.0'}</span>
                    </div>
                  </div>
                  <div style={cardFooterStyle}>
                    <button
                      onClick={() => handleViewTemplate(template.template_id)}
                      style={viewButtonStyle}
                    >
                      View Details
                    </button>
                    <button
                      onClick={() => handleDownloadTemplate(template.template_id)}
                      style={downloadButtonStyle}
                    >
                      📥 Use
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Popular Tab */}
      {activeTab === 'popular' && (
        <div style={contentStyle}>
          <h3>🔥 Most Popular Templates</h3>
          {popularTemplates.length === 0 ? (
            <p style={emptyTextStyle}>No popular templates yet.</p>
          ) : (
            <div style={templateGridStyle}>
              {popularTemplates.map((template) => (
                <div key={template.template_id} style={templateCardStyle}>
                  <div style={cardHeaderStyle}>
                    <span style={templateNameStyle}>{template.name}</span>
                    <span style={downloadCountBadgeStyle}>📥 {template.download_count || 0}</span>
                  </div>
                  <div style={cardBodyStyle}>
                    <p style={descriptionStyle}>{template.description?.substring(0, 80)}...</p>
                    <div style={templateMetaStyle}>
                      <span>{renderStars(template.average_rating || 0)}</span>
                    </div>
                  </div>
                  <div style={cardFooterStyle}>
                    <button
                      onClick={() => handleViewTemplate(template.template_id)}
                      style={viewButtonStyle}
                    >
                      View
                    </button>
                    <button
                      onClick={() => handleDownloadTemplate(template.template_id)}
                      style={downloadButtonStyle}
                    >
                      Use
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Recent Tab */}
      {activeTab === 'recent' && (
        <div style={contentStyle}>
          <h3>🆕 Recently Added</h3>
          {recentTemplates.length === 0 ? (
            <p style={emptyTextStyle}>No recent templates.</p>
          ) : (
            <div style={templateGridStyle}>
              {recentTemplates.map((template) => (
                <div key={template.template_id} style={templateCardStyle}>
                  <div style={cardHeaderStyle}>
                    <span style={templateNameStyle}>{template.name}</span>
                    <span style={dateBadgeStyle}>{formatDate(template.created_at)}</span>
                  </div>
                  <div style={cardBodyStyle}>
                    <p style={descriptionStyle}>{template.description?.substring(0, 80)}...</p>
                    <div style={templateMetaStyle}>
                      <span>👤 {template.author_username || 'Unknown'}</span>
                    </div>
                  </div>
                  <div style={cardFooterStyle}>
                    <button
                      onClick={() => handleViewTemplate(template.template_id)}
                      style={viewButtonStyle}
                    >
                      View
                    </button>
                    <button
                      onClick={() => handleDownloadTemplate(template.template_id)}
                      style={downloadButtonStyle}
                    >
                      Use
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* My Templates Tab */}
      {activeTab === 'myTemplates' && isInstructor && (
        <div style={contentStyle}>
          <h3>📁 My Published Templates</h3>
          {myTemplates.length === 0 ? (
            <p style={emptyTextStyle}>You haven't published any templates yet.</p>
          ) : (
            <div style={templateGridStyle}>
              {myTemplates.map((template) => (
                <div key={template.template_id} style={templateCardStyle}>
                  <div style={cardHeaderStyle}>
                    <span style={templateNameStyle}>{template.name}</span>
                    <span style={{ 
                      ...statusBadgeStyle, 
                      backgroundColor: getStatusColor(template.status) 
                    }}>
                      {template.status}
                    </span>
                  </div>
                  <div style={cardBodyStyle}>
                    <div style={templateMetaStyle}>
                      <span>📥 {template.download_count || 0} downloads</span>
                      <span>v{template.current_version || '1.0.0'}</span>
                    </div>
                    <div style={templateMetaStyle}>
                      <span>{renderStars(template.average_rating || 0)} ({template.review_count || 0})</span>
                    </div>
                  </div>
                  <div style={cardFooterStyle}>
                    <button
                      onClick={() => handleViewTemplate(template.template_id)}
                      style={viewButtonStyle}
                    >
                      View
                    </button>
                    {template.status === 'draft' && (
                      <button
                        onClick={() => handleSubmitForReview(template.template_id)}
                        style={submitButtonStyle}
                      >
                        Submit for Review
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Publish Template Modal */}
      {showPublishForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>📤 Publish New Template</h3>
              <button onClick={() => setShowPublishForm(false)} style={closeButtonStyle}>✕</button>
            </div>
            <form onSubmit={handlePublishTemplate} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Template Name *</label>
                <input
                  type="text"
                  value={publishForm.name}
                  onChange={(e) => setPublishForm(prev => ({ ...prev, name: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., Advanced Network Attack Scenario"
                  required
                />
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Category *</label>
                <select
                  value={publishForm.category}
                  onChange={(e) => setPublishForm(prev => ({ ...prev, category: e.target.value }))}
                  style={inputStyle}
                  required
                >
                  <option value="">Select a category...</option>
                  {categories.length > 0 ? (
                    categories.map((cat, idx) => (
                      <option key={idx} value={cat}>{cat}</option>
                    ))
                  ) : (
                    // Fallback categories if API hasn't returned any
                    <>
                      <option value="Network Security">Network Security</option>
                      <option value="Web Application">Web Application</option>
                      <option value="RF/EW">RF/EW</option>
                      <option value="Digital Forensics">Digital Forensics</option>
                      <option value="Malware Analysis">Malware Analysis</option>
                      <option value="Red Team">Red Team</option>
                      <option value="Blue Team">Blue Team</option>
                      <option value="Other">Other</option>
                    </>
                  )}
                </select>
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Description *</label>
                <textarea
                  value={publishForm.description}
                  onChange={(e) => setPublishForm(prev => ({ ...prev, description: e.target.value }))}
                  style={{ ...inputStyle, minHeight: '80px' }}
                  placeholder="Describe what this template covers..."
                  required
                />
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Tags (comma-separated)</label>
                <input
                  type="text"
                  value={publishForm.tags}
                  onChange={(e) => setPublishForm(prev => ({ ...prev, tags: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., network, penetration testing, beginner"
                />
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Scenario Data (JSON) *</label>
                <textarea
                  value={publishForm.scenarioData}
                  onChange={(e) => setPublishForm(prev => ({ ...prev, scenarioData: e.target.value }))}
                  style={{ ...inputStyle, minHeight: '150px', fontFamily: 'monospace' }}
                  placeholder='{"name": "My Scenario", "containers": [...], "networks": [...]}'
                  required
                />
              </div>
              
              <div style={formActionsStyle}>
                <button type="button" onClick={() => setShowPublishForm(false)} style={secondaryButtonStyle}>
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Publish Template
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Template Detail Modal */}
      {selectedTemplate && !showReviewForm && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>{selectedTemplate.name}</h3>
              <button onClick={() => setSelectedTemplate(null)} style={closeButtonStyle}>✕</button>
            </div>
            <div style={detailBodyStyle}>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Author:</span>
                <span>{selectedTemplate.author_username || 'Unknown'}</span>
              </div>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Category:</span>
                <span style={categoryBadgeStyle}>{selectedTemplate.category}</span>
              </div>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Version:</span>
                <span>{selectedTemplate.current_version || '1.0.0'}</span>
              </div>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Rating:</span>
                <span>{renderStars(selectedTemplate.average_rating || 0)} ({selectedTemplate.review_count || 0} reviews)</span>
              </div>
              <div style={detailRowStyle}>
                <span style={detailLabelStyle}>Downloads:</span>
                <span>{selectedTemplate.download_count || 0}</span>
              </div>
              {selectedTemplate.description && (
                <div style={detailSectionStyle}>
                  <h4>Description</h4>
                  <p>{selectedTemplate.description}</p>
                </div>
              )}
              {selectedTemplate.tags?.length > 0 && (
                <div style={detailSectionStyle}>
                  <h4>Tags</h4>
                  <div style={tagsContainerStyle}>
                    {selectedTemplate.tags.map((tag, idx) => (
                      <span key={idx} style={tagStyle}>{tag}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Reviews Section */}
              <div style={detailSectionStyle}>
                <h4>Reviews</h4>
                <button 
                  onClick={() => setShowReviewForm(true)} 
                  style={addReviewButtonStyle}
                >
                  ✍️ Write a Review
                </button>
                {selectedTemplate.reviews?.length > 0 ? (
                  <div style={reviewsListStyle}>
                    {selectedTemplate.reviews.map((review, idx) => (
                      <div key={idx} style={reviewItemStyle}>
                        <div style={reviewHeaderStyle}>
                          <span style={reviewAuthorStyle}>👤 {review.author_username}</span>
                          <span>{renderStars(review.rating)}</span>
                        </div>
                        <div style={reviewTitleStyle}>{review.title}</div>
                        <p style={reviewCommentStyle}>{review.comment}</p>
                        <div style={reviewFooterStyle}>
                          <span>{formatDate(review.created_at)}</span>
                          <span>👍 {review.helpful_count || 0} helpful</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={emptyTextStyle}>No reviews yet. Be the first!</p>
                )}
              </div>

              <div style={detailActionsStyle}>
                <button
                  onClick={() => handleDownloadTemplate(selectedTemplate.template_id)}
                  style={downloadButtonLargeStyle}
                >
                  📥 Use This Template
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Review Form Modal */}
      {showReviewForm && selectedTemplate && (
        <div style={modalOverlayStyle}>
          <div style={modalStyle}>
            <div style={modalHeaderStyle}>
              <h3>✍️ Write a Review</h3>
              <button onClick={() => setShowReviewForm(false)} style={closeButtonStyle}>✕</button>
            </div>
            <form onSubmit={handleSubmitReview} style={formStyle}>
              <div style={formGroupStyle}>
                <label style={labelStyle}>Rating *</label>
                <div style={ratingInputStyle}>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <span
                      key={star}
                      onClick={() => setReviewForm(prev => ({ ...prev, rating: star }))}
                      style={{
                        ...starInputStyle,
                        color: star <= reviewForm.rating ? '#ffc107' : '#e9ecef'
                      }}
                    >
                      ★
                    </span>
                  ))}
                </div>
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Title *</label>
                <input
                  type="text"
                  value={reviewForm.title}
                  onChange={(e) => setReviewForm(prev => ({ ...prev, title: e.target.value }))}
                  style={inputStyle}
                  placeholder="Summarize your experience"
                  required
                />
              </div>
              
              <div style={formGroupStyle}>
                <label style={labelStyle}>Review *</label>
                <textarea
                  value={reviewForm.comment}
                  onChange={(e) => setReviewForm(prev => ({ ...prev, comment: e.target.value }))}
                  style={{ ...inputStyle, minHeight: '100px' }}
                  placeholder="Share your experience with this template..."
                  required
                />
              </div>
              
              <div style={formActionsStyle}>
                <button type="button" onClick={() => setShowReviewForm(false)} style={secondaryButtonStyle}>
                  Cancel
                </button>
                <button type="submit" style={primaryButtonStyle}>
                  Submit Review
                </button>
              </div>
            </form>
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

const successMessageStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px 16px',
  backgroundColor: '#d4edda',
  color: '#155724',
  borderRadius: '4px',
  marginBottom: '16px',
  fontSize: '14px',
};

const dismissSuccessStyle = {
  backgroundColor: 'transparent',
  border: 'none',
  color: '#155724',
  cursor: 'pointer',
  fontSize: '16px',
  padding: '0 4px',
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

const searchBarStyle = {
  display: 'flex',
  gap: '12px',
  marginBottom: '20px',
};

const searchInputStyle = {
  flex: 1,
  padding: '10px 16px',
  borderRadius: '4px',
  border: '1px solid #ced4da',
  fontSize: '14px',
};

const categorySelectStyle = {
  padding: '10px 16px',
  borderRadius: '4px',
  border: '1px solid #ced4da',
  fontSize: '14px',
  minWidth: '150px',
};

const templateGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
  gap: '16px',
};

const templateCardStyle = {
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

const templateNameStyle = {
  fontWeight: '600',
  fontSize: '14px',
};

const categoryBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  backgroundColor: '#e9ecef',
  color: '#495057',
};

const downloadCountBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  backgroundColor: '#28a745',
  color: 'white',
};

const dateBadgeStyle = {
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '11px',
  backgroundColor: '#17a2b8',
  color: 'white',
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

const descriptionStyle = {
  fontSize: '13px',
  color: '#666',
  marginBottom: '12px',
};

const templateMetaStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '12px',
  color: '#666',
  marginBottom: '4px',
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

const downloadButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#28a745',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const downloadButtonLargeStyle = {
  padding: '12px 24px',
  backgroundColor: '#28a745',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: '600',
};

const submitButtonStyle = {
  padding: '6px 12px',
  backgroundColor: '#007bff',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
};

const addReviewButtonStyle = {
  padding: '8px 16px',
  backgroundColor: '#ffc107',
  color: '#333',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '12px',
  marginBottom: '12px',
};

const emptyTextStyle = {
  color: '#666',
  fontStyle: 'italic',
};

const starFilledStyle = {
  color: '#ffc107',
  fontSize: '14px',
};

const starHalfStyle = {
  color: '#ffc107',
  fontSize: '14px',
  opacity: 0.5,
};

const starEmptyStyle = {
  color: '#e9ecef',
  fontSize: '14px',
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
  maxWidth: '700px',
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

const detailSectionStyle = {
  marginTop: '20px',
  paddingTop: '16px',
  borderTop: '1px solid #eee',
};

const tagsContainerStyle = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '8px',
  marginTop: '8px',
};

const tagStyle = {
  padding: '4px 12px',
  backgroundColor: '#e9ecef',
  borderRadius: '16px',
  fontSize: '12px',
  color: '#495057',
};

const detailActionsStyle = {
  marginTop: '20px',
  paddingTop: '16px',
  borderTop: '1px solid #eee',
  display: 'flex',
  justifyContent: 'center',
};

const reviewsListStyle = {
  marginTop: '12px',
};

const reviewItemStyle = {
  padding: '12px',
  backgroundColor: '#f8f9fa',
  borderRadius: '4px',
  marginBottom: '8px',
};

const reviewHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  marginBottom: '8px',
};

const reviewAuthorStyle = {
  fontWeight: '500',
  fontSize: '13px',
};

const reviewTitleStyle = {
  fontWeight: '600',
  fontSize: '14px',
  marginBottom: '4px',
};

const reviewCommentStyle = {
  fontSize: '13px',
  color: '#333',
  marginBottom: '8px',
};

const reviewFooterStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: '11px',
  color: '#666',
};

const ratingInputStyle = {
  display: 'flex',
  gap: '4px',
};

const starInputStyle = {
  fontSize: '28px',
  cursor: 'pointer',
};
