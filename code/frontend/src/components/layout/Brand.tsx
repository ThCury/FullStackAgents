export function Brand({ size = 'md' }: { size?: 'md' | 'lg' }) {
  return (
    <div className={`brand${size === 'lg' ? ' brand--lg' : ''}`}>
      <img className="brand__mark" src="/virtual.png" alt="" />
      <span className="brand__name">Full Stack Agents</span>
    </div>
  )
}
