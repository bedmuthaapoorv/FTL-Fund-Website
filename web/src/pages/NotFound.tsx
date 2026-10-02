import { Head } from 'vite-react-ssg'
import { Link } from 'react-router-dom'

export function Component() {
  return (
    <div className="container-page py-32">
      <Head><title>Not found</title><meta name="robots" content="noindex" /></Head>
      <p className="eyebrow mb-4">404</p>
      <h1 className="text-3xl font-semibold tracking-tight">This page does not exist.</h1>
      <Link to="/" className="link mt-6 inline-block">Return home</Link>
    </div>
  )
}
