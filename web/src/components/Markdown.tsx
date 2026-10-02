import ReactMarkdown from 'react-markdown'
import { Link } from 'react-router-dom'
import remarkPlaceholder from '../lib/remarkPlaceholder'

export default function Markdown({ children }: { children: string }) {
  return (
    <div className="prose prose-neutral max-w-prose text-[16.5px] leading-relaxed prose-headings:font-semibold prose-headings:tracking-tight prose-headings:text-ink prose-p:text-ink/85 prose-li:text-ink/85 prose-strong:text-ink prose-a:text-accent prose-em:text-muted dark:prose-invert">
      <ReactMarkdown
        remarkPlugins={[remarkPlaceholder]}
        components={{
          a: ({ href = '', children }) =>
            href.startsWith('/') ? <Link to={href}>{children}</Link> : <a href={href} rel="noopener noreferrer">{children}</a>,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
