import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <main style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>404 — Page Not Found</h1>
      <p style={{ marginTop: '1rem', color: '#666' }}>
        The page you requested does not exist.
      </p>
      <Link to="/" style={{ marginTop: '1rem', display: 'inline-block', color: '#0066cc' }}>
        Return home
      </Link>
    </main>
  )
}
