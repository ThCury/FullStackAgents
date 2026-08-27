import { useId, type InputHTMLAttributes, type TextareaHTMLAttributes } from 'react'

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string | null
}

export function TextField({ label, error, ...rest }: TextFieldProps) {
  const id = useId()
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      <input id={id} className="input" {...rest} />
      {error && <span className="field__error">{error}</span>}
    </div>
  )
}

interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string | null
}

export function TextAreaField({ label, error, ...rest }: TextAreaFieldProps) {
  const id = useId()
  return (
    <div className="field">
      {label && (
        <label className="field__label" htmlFor={id}>
          {label}
        </label>
      )}
      <textarea id={id} className="textarea" {...rest} />
      {error && <span className="field__error">{error}</span>}
    </div>
  )
}
