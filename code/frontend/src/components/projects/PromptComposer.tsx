import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/Button'
import { TextAreaField } from '@/components/ui/Field'
import { Alert } from '@/components/ui/Feedback'

interface PromptComposerProps {
  onSubmit: (prompt: string) => Promise<void>
  placeholder?: string
  submitLabel?: string
  hint?: string
  disabled?: boolean
  disabledReason?: string
}

export function PromptComposer({
  onSubmit,
  placeholder = 'Ex: criar uma tela de checkout com cupom de desconto...',
  submitLabel = 'Enviar para os agentes',
  hint,
  disabled = false,
  disabledReason,
}: PromptComposerProps) {
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const prompt = text.trim()
    if (!prompt || sending || disabled) return

    setSending(true)
    setError(null)
    try {
      await onSubmit(prompt)
      setText('')
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Falha ao enviar o prompt.')
    } finally {
      setSending(false)
    }
  }

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <TextAreaField
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={placeholder}
        disabled={disabled || sending}
        aria-label="Prompt para os agentes"
      />
      {error && <Alert>{error}</Alert>}
      <div className="composer__actions">
        <span className="composer__hint">{disabled ? disabledReason : hint}</span>
        <Button type="submit" loading={sending} disabled={disabled || !text.trim()}>
          {submitLabel} <span aria-hidden="true">→</span>
        </Button>
      </div>
    </form>
  )
}
