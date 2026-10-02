import { Head } from 'vite-react-ssg'
import PageHeader from '../components/PageHeader'

// Replaced by the real login flow in Phase 2.
export function Component() {
  return (
    <>
      <Head><title>Investor login</title><meta name="robots" content="noindex" /></Head>
      <PageHeader eyebrow="Investors" title="Investor login">The investor portal is not yet available.</PageHeader>
    </>
  )
}
