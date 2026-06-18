import { type ChangeEvent, useRef } from 'react'

import {
  chatImageAccept,
  type ChatImageAttachment,
} from '../services/imageAttachments'

type ChatImageAttachmentInputProps = {
  attachment: ChatImageAttachment | null
  disabled: boolean
  inputId: string
  isProcessing: boolean
  onRemoveImage: () => void
  onSelectImage: (file: File) => void | Promise<void>
}

function ChatImageAttachmentInput({
  attachment,
  disabled,
  inputId,
  isProcessing,
  onRemoveImage,
  onSelectImage,
}: ChatImageAttachmentInputProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0]
    event.currentTarget.value = ''

    if (file) {
      void onSelectImage(file)
    }
  }

  return (
    <div className="chat-image-attachment">
      <input
        accept={chatImageAccept}
        className="visually-hidden"
        disabled={disabled || isProcessing}
        id={inputId}
        onChange={handleFileChange}
        ref={inputRef}
        type="file"
      />
      <div className="chat-image-attachment__dock">
        <button
          className="chat-image-attachment__button"
          disabled={disabled || isProcessing}
          onClick={() => inputRef.current?.click()}
          title="Attach image"
          type="button"
          aria-label="Attach image"
        >
          <svg
            aria-hidden="true"
            focusable="false"
            viewBox="0 0 24 24"
          >
            <rect x="3" y="5" width="18" height="14" rx="2" />
            <circle cx="8.5" cy="10" r="1.5" />
            <path d="M21 15l-5-5L5 19" />
          </svg>
        </button>
        {isProcessing ? (
          <span className="chat-image-attachment__status" role="status">
            Attaching image...
          </span>
        ) : null}
      </div>

      {attachment ? (
        <div className="chat-image-attachment__preview">
          <div className="chat-image-attachment__preview-heading">
            <div>
              <strong>{attachment.fileName}</strong>
              <span>Ready to send with your prompt</span>
            </div>
            <button
              aria-label="Remove attached image"
              title="Remove attached image"
              disabled={disabled || isProcessing}
              onClick={onRemoveImage}
              type="button"
            >
              <span aria-hidden="true">x</span>
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default ChatImageAttachmentInput
