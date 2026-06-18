export type ChatImageAttachment = {
  fileName: string
  mediaType: string
  image: string
}

const MAX_IMAGE_BYTES = 5 * 1024 * 1024
const ACCEPTED_IMAGE_TYPES = new Set([
  'image/gif',
  'image/jpeg',
  'image/png',
  'image/webp',
])

export const chatImageOnlyPrompt =
  'Please help me understand the attached image.'

export const chatImageAccept =
  'image/png,image/jpeg,image/webp,image/gif'

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.addEventListener('load', () => {
      if (typeof reader.result === 'string') {
        resolve(reader.result)
      } else {
        reject(new Error('The selected image could not be read.'))
      }
    })
    reader.addEventListener('error', () => {
      reject(new Error('The selected image could not be read.'))
    })
    reader.readAsDataURL(file)
  })
}

export function messageWithImageAttachment(
  message: string,
  attachment: ChatImageAttachment | null,
): string {
  if (!attachment) {
    return message
  }

  return [
    message,
    '',
    `Image attachment: ${attachment.fileName}`,
  ].join('\n')
}

export function truncateForAnalytics(text: string): string {
  return text.slice(0, 4000)
}

export async function prepareChatImage(
  file: File,
): Promise<ChatImageAttachment> {
  if (!ACCEPTED_IMAGE_TYPES.has(file.type)) {
    throw new Error('Use a PNG, JPEG, WebP, or GIF image.')
  }

  if (file.size > MAX_IMAGE_BYTES) {
    throw new Error('Use an image smaller than 5 MB.')
  }

  const image = await readFileAsDataUrl(file)

  return {
    fileName: file.name,
    mediaType: file.type,
    image,
  }
}
