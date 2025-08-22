import { useEffect, useMemo, useState } from 'react'
import './App.css'

type Job = {
  id: number
  title: string
  company: string
  date_applied: string
}

const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

function App() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const jobsEndpoint = useMemo(() => `${API_BASE}/jobs`, [])

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

  useEffect(() => {
    loadJobs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const addTestJob = async () => {
    try {
      setCreating(true)
      setError(null)
      const today = new Date().toISOString().slice(0, 10)
      const res = await fetch(jobsEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'SWE Intern', company: 'Acme', date_applied: today }),
      })
      if (!res.ok) throw new Error(`Failed to create job: ${res.status}`)
      await loadJobs()
    } catch (e: any) {
      setError(e.message || 'Error creating job')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div style={{ maxWidth: 720, margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Job Applications</h1>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <button onClick={loadJobs} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
        <button onClick={addTestJob} disabled={creating}>
          {creating ? 'Adding…' : 'Add test application'}
        </button>
      </div>

      {error && (
        <div style={{ color: 'crimson', marginBottom: 12 }}>Error: {error}</div>
      )}

      {jobs.length === 0 ? (
        <p>No applications yet.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '8px' }}>Title</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '8px' }}>Company</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '8px' }}>Date Applied</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id}>
                <td style={{ borderBottom: '1px solid #eee', padding: '8px' }}>{j.title}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: '8px' }}>{j.company}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: '8px' }}>{j.date_applied}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default App
