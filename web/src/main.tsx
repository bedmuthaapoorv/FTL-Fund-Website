import { ViteReactSSG } from 'vite-react-ssg'
import { routes } from './routes'
// Fonts are self-hosted: no third-party requests, and a tighter CSP.
import '@fontsource-variable/manrope'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/500.css'
import './styles.css'

export const createRoot = ViteReactSSG({ routes })
