export function Brand({ size = 'md' }: { size?: 'md' | 'lg' }) {
  return (
    <div className={`brand${size === 'lg' ? ' brand--lg' : ''}`}>
      <span className="brand__mark" aria-hidden="true">
        ⚡
      </span>
      <span className="brand__name">Full Stack Agents</span>
    </div>
  )
}
