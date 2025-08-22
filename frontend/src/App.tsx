import { useEffect, useState } from 'react'
import './App.css'

type Job = {
  id: number
  title: string
  company: string
  date_applied: string
  status: string
}

type EditJob = {
  id: number
  title: string
  company: string
  date_applied: string
  status: string
}

type GeminiStatus = {
  api_available: boolean
  model_name: string
  max_tokens_per_request: number
  api_key_configured: boolean
}

const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

const STATUS_OPTIONS = [
  'Applied',
  'Interview Scheduled',
  'Interview Completed', 
  'Online Assessment',
  'Rejected',
  'Offer',
  'Accepted',
  'Withdrawn'
]

function App() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [editingJob, setEditingJob] = useState<EditJob | null>(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
  
  // Gemini AI state
  const [geminiStatus, setGeminiStatus] = useState<GeminiStatus | null>(null)
  const [showGeminiControls, setShowGeminiControls] = useState(false)
  const [advancedSettings, setAdvancedSettings] = useState({
    daysThreshold: 7,
    useGemini: true,
    maxResults: 50
  })
  const [testingGemini, setTestingGemini] = useState(false)
  const [testSubject, setTestSubject] = useState('Thank you for applying to Google')
  const [testBody, setTestBody] = useState('We have received your application for Software Engineer Intern position...')

  const jobsEndpoint = `${API_BASE}/jobs`

  const loadJobs = async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await fetch(jobsEndpoint)
      if (!res.ok) throw new Error(`Failed to load jobs: ${res.status}`)
      const data: Job[] = await res.json()
      setJobs(data)
    } catch (e: any) {
      setError(e.message || 'Error loading jobs')
    } finally {
      setLoading(false)
    }
  }

  const loadGeminiStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/gemini/status`)
      if (res.ok) {
        const data = await res.json()
        setGeminiStatus(data.gemini_status)
      }
    } catch (e) {
      console.log('Could not load Gemini status:', e)
    }
  }

  useEffect(() => {
    loadJobs()
    loadGeminiStatus()
  }, [])

  const addTestJob = async () => {
    try {
      setCreating(true)
      setError(null)
      setMessage(null)
      const today = new Date().toISOString().slice(0, 10)
      const res = await fetch(jobsEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'SWE Intern', company: 'Acme', date_applied: today }),
      })
      if (res.status === 409) {
        setMessage('Test application already exists')
      } else if (!res.ok) {
        throw new Error(`Failed to create job: ${res.status}`)
      } else {
        setMessage('Test application added successfully!')
        await loadJobs()
      }
    } catch (e: any) {
      setError(e.message || 'Error creating job')
    } finally {
      setCreating(false)
    }
  }

  const fetchEmails = async () => {
    try {
      setFetching(true)
      setError(null)
      setMessage(null)
      const res = await fetch(`${API_BASE}/gmail/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!res.ok) throw new Error(`Failed to fetch emails: ${res.status}`)
      const data = await res.json()
      setMessage(data.message || 'Emails processed successfully!')
      await loadJobs()
    } catch (e: any) {
      setError(e.message || 'Error fetching emails')
    } finally {
      setFetching(false)
    }
  }

  const fetchEmailsAdvanced = async () => {
    try {
      setFetching(true)
      setError(null)
      setMessage(null)
      
      const params = new URLSearchParams({
        days_threshold: advancedSettings.daysThreshold.toString(),
        use_gemini: advancedSettings.useGemini.toString(),
        max_results: advancedSettings.maxResults.toString()
      })
      
      const res = await fetch(`${API_BASE}/gmail/process-advanced?${params}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      
      if (!res.ok) throw new Error(`Failed to fetch emails: ${res.status}`)
      const data = await res.json()
      setMessage(data.message || 'Emails processed successfully!')
      await loadJobs()
    } catch (e: any) {
      setError(e.message || 'Error fetching emails')
    } finally {
      setFetching(false)
    }
  }

  const testGeminiAnalysis = async () => {
    try {
      setTestingGemini(true)
      setError(null)
      setMessage(null)
      
      const params = new URLSearchParams({
        subject: testSubject,
        body: testBody,
        from_email: 'test@example.com'
      })
      
      const res = await fetch(`${API_BASE}/gemini/test?${params}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      
      if (!res.ok) throw new Error(`Failed to test Gemini: ${res.status}`)
      const data = await res.json()
      
      if (data.success) {
        setMessage(`Gemini Analysis: ${JSON.stringify(data.analysis, null, 2)}`)
      } else {
        setError(data.message || 'Gemini test failed')
      }
    } catch (e: any) {
      setError(e.message || 'Error testing Gemini')
    } finally {
      setTestingGemini(false)
    }
  }

  const updateStatus = async (jobId: number, newStatus: string) => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      if (!res.ok) throw new Error(`Failed to update status: ${res.status}`)
      await loadJobs()
    } catch (e: any) {
      setError(e.message || 'Error updating status')
    }
  }

  const handleDeleteClick = (jobId: number) => {
    if (deleteConfirmId === jobId) {
      // Second click - actually delete
      deleteJob(jobId)
      setDeleteConfirmId(null)
    } else {
      // First click - show confirm state
      setDeleteConfirmId(jobId)
      // Auto-reset after 3 seconds
      setTimeout(() => {
        setDeleteConfirmId(null)
      }, 3000)
    }
  }

  const deleteJob = async (jobId: number) => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error(`Failed to delete job: ${res.status}`)
      setMessage('Job application deleted successfully!')
      await loadJobs()
    } catch (e: any) {
      setError(e.message || 'Error deleting job')
    }
  }

  const editJob = (job: Job) => {
    setEditingJob({
      id: job.id,
      title: job.title,
      company: job.company,
      date_applied: job.date_applied,
      status: job.status
    })
    setShowEditModal(true)
  }

  const saveEdit = async () => {
    if (!editingJob) return
    
    try {
      const res = await fetch(`${API_BASE}/jobs/${editingJob.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: editingJob.title,
          company: editingJob.company,
          date_applied: editingJob.date_applied,
          status: editingJob.status
        }),
      })
      if (!res.ok) throw new Error(`Failed to update job: ${res.status}`)
      setMessage('Job application updated successfully!')
      setShowEditModal(false)
      setEditingJob(null)
      await loadJobs()
    } catch (e: any) {
      setError(e.message || 'Error updating job')
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    })
  }

  return (
    <div className="app-container">
      <h1>Job Applications</h1>
      
      <div className="controls">
        <button onClick={loadJobs} disabled={loading || creating || fetching}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
        <button onClick={addTestJob} disabled={loading || creating || fetching}>
          {creating ? 'Adding...' : 'Add Test Application'}
        </button>
        <button onClick={fetchEmails} disabled={loading || creating || fetching}>
          {fetching ? 'Fetching Emails...' : 'Fetch Emails'}
        </button>
        <button 
          onClick={() => setShowGeminiControls(!showGeminiControls)}
          className="gemini-toggle-btn"
        >
          {showGeminiControls ? '🤖 Hide AI Controls' : '🤖 Show AI Controls'}
        </button>
      </div>

      {/* Gemini AI Controls */}
      {showGeminiControls && (
        <div className="gemini-controls">
          <div className="gemini-status">
            <h3>🤖 Gemini AI Status</h3>
            {geminiStatus ? (
              <div className="status-grid">
                <div className={`status-item ${geminiStatus.api_available ? 'available' : 'unavailable'}`}>
                  <span>API Status:</span>
                  <span>{geminiStatus.api_available ? '✅ Available' : '❌ Unavailable'}</span>
                </div>
                <div className="status-item">
                  <span>Model:</span>
                  <span>{geminiStatus.model_name}</span>
                </div>
                <div className="status-item">
                  <span>Max Tokens:</span>
                  <span>{geminiStatus.max_tokens_per_request.toLocaleString()}</span>
                </div>
                <div className={`status-item ${geminiStatus.api_key_configured ? 'available' : 'unavailable'}`}>
                  <span>API Key:</span>
                  <span>{geminiStatus.api_key_configured ? '✅ Configured' : '❌ Missing'}</span>
                </div>
              </div>
            ) : (
              <p>Loading Gemini status...</p>
            )}
          </div>

          <div className="advanced-settings">
            <h3>⚙️ Advanced Email Processing</h3>
            <div className="settings-grid">
              <div className="setting-item">
                <label>Days Threshold:</label>
                <select 
                  value={advancedSettings.daysThreshold}
                  onChange={(e) => setAdvancedSettings({
                    ...advancedSettings,
                    daysThreshold: parseInt(e.target.value)
                  })}
                >
                  <option value={1}>1 day</option>
                  <option value={3}>3 days</option>
                  <option value={7}>7 days (default)</option>
                  <option value={14}>14 days</option>
                  <option value={30}>30 days</option>
                </select>
                <small>Only analyze emails from the past N days</small>
              </div>
              
              <div className="setting-item">
                <label>Use Gemini AI:</label>
                <input
                  type="checkbox"
                  checked={advancedSettings.useGemini}
                  onChange={(e) => setAdvancedSettings({
                    ...advancedSettings,
                    useGemini: e.target.checked
                  })}
                />
                <small>Enable AI-powered email analysis</small>
              </div>
              
              <div className="setting-item">
                <label>Max Results:</label>
                <select 
                  value={advancedSettings.maxResults}
                  onChange={(e) => setAdvancedSettings({
                    ...advancedSettings,
                    maxResults: parseInt(e.target.value)
                  })}
                >
                  <option value={25}>25 emails</option>
                  <option value={50}>50 emails (default)</option>
                  <option value={100}>100 emails</option>
                  <option value={200}>200 emails</option>
                </select>
                <small>Maximum emails to process</small>
              </div>
            </div>
            
            <div className="advanced-actions">
              <button 
                onClick={fetchEmailsAdvanced} 
                disabled={loading || creating || fetching}
                className="advanced-fetch-btn"
              >
                {fetching ? 'Processing...' : '🚀 Process Emails (Advanced)'}
              </button>
            </div>
          </div>

          <div className="gemini-test">
            <h3>🧪 Test Gemini Analysis</h3>
            <div className="test-inputs">
              <div className="form-group">
                <label>Test Subject:</label>
                <input
                  type="text"
                  value={testSubject}
                  onChange={(e) => setTestSubject(e.target.value)}
                  placeholder="Email subject to test"
                />
              </div>
              <div className="form-group">
                <label>Test Body:</label>
                <textarea
                  value={testBody}
                  onChange={(e) => setTestBody(e.target.value)}
                  placeholder="Email body to test"
                  rows={3}
                />
              </div>
              <button 
                onClick={testGeminiAnalysis}
                disabled={testingGemini || !geminiStatus?.api_available}
                className="test-btn"
              >
                {testingGemini ? 'Testing...' : '🧪 Test Analysis'}
              </button>
            </div>
          </div>
        </div>
      )}

      {error && <div className="error-message">Error: {error}</div>}
      {message && <div className="success-message">{message}</div>}

      {jobs.length === 0 ? (
        <div className="empty-state">
          <p>No applications yet.</p>
          <p>Add a test application or fetch emails from Gmail to get started.</p>
        </div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Company</th>
                <th>Date Applied</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>{job.title}</td>
                  <td>{job.company}</td>
                  <td>{formatDate(job.date_applied)}</td>
                  <td>
                    <select 
                      value={job.status} 
                      onChange={(e) => updateStatus(job.id, e.target.value)}
                      className="status-select"
                    >
                      {STATUS_OPTIONS.map(status => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button 
                        onClick={() => editJob(job)}
                        className="edit-btn"
                        title="Edit"
                      >
                        ✏️
                      </button>
                      <button 
                        onClick={() => handleDeleteClick(job.id)}
                        className={`delete-btn ${deleteConfirmId === job.id ? 'confirm-mode' : ''}`}
                        title={deleteConfirmId === job.id ? 'Click again to confirm' : 'Delete'}
                      >
                        {deleteConfirmId === job.id ? '✓' : '🗑️'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && editingJob && (
        <div className="modal-overlay">
          <div className="modal">
            <h2>Edit Job Application</h2>
            <div className="form-group">
              <label>Title:</label>
              <input
                type="text"
                value={editingJob.title}
                onChange={(e) => setEditingJob({...editingJob, title: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>Company:</label>
              <input
                type="text"
                value={editingJob.company}
                onChange={(e) => setEditingJob({...editingJob, company: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>Date Applied:</label>
              <input
                type="date"
                value={editingJob.date_applied}
                onChange={(e) => setEditingJob({...editingJob, date_applied: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>Status:</label>
              <select
                value={editingJob.status}
                onChange={(e) => setEditingJob({...editingJob, status: e.target.value})}
              >
                {STATUS_OPTIONS.map(status => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </div>
            <div className="modal-actions">
              <button onClick={saveEdit} className="save-btn">Save</button>
              <button onClick={() => {setShowEditModal(false); setEditingJob(null)}} className="cancel-btn">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
