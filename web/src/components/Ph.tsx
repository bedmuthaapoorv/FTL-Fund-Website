/** Inline marker for an unconfirmed factual claim in TSX copy. */
export default function Ph({ children }: { children?: React.ReactNode }) {
  return <span className="placeholder-tag">[PLACEHOLDER{children ? <>: {children}</> : null}]</span>
}
