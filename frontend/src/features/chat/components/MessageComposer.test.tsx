import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import MessageComposer from './MessageComposer'

function ControlledComposer({ initialValue = '' }: { initialValue?: string }) {
  const [value, setValue] = useState(initialValue)
  return <MessageComposer value={value} onChange={setValue} onSend={vi.fn()} />
}

describe('MessageComposer', () => {
  beforeEach(() => {
    Object.defineProperty(HTMLTextAreaElement.prototype, 'scrollHeight', {
      configurable: true,
      get() {
        const lines = (this as HTMLTextAreaElement).value.split('\n').length
        return lines * 24
      },
    })
  })

  afterEach(() => {
    Reflect.deleteProperty(HTMLTextAreaElement.prototype, 'scrollHeight')
  })

  it('auto-grows the textarea as content is added', async () => {
    const user = userEvent.setup()
    render(<ControlledComposer />)

    const textarea = screen.getByLabelText('Message') as HTMLTextAreaElement
    await user.type(textarea, 'Line one\nLine two\nLine three')

    expect(textarea.style.height).toBe('72px')
    expect(textarea.style.maxHeight).toBe('168px')
  })

  it('shrinks the textarea when content is deleted', async () => {
    const user = userEvent.setup()
    render(<ControlledComposer initialValue={'Line one\nLine two\nLine three'} />)

    const textarea = screen.getByLabelText('Message') as HTMLTextAreaElement
    expect(textarea.style.height).toBe('72px')

    await user.clear(textarea)
    await user.type(textarea, 'Short')

    expect(textarea.style.height).toBe('24px')
  })
})
