import { toast } from 'sonner'

export function useCopy() {
  const handleCopy = async (value: string): Promise<void> => {
    try {
      if (window.isSecureContext) {
        await navigator.clipboard.writeText(value)
      } else {
        const textArea = document.createElement('textarea')
        textArea.value = value

        textArea.style.position = 'fixed'
        textArea.style.left = '-9999px'
        textArea.style.top = '0'
        document.body.appendChild(textArea)

        textArea.focus()
        textArea.select()

        // @ts-ignore: execCommand is deprecated but the only way to copy in non-secure contexts
        const successful = document.execCommand('copy')
        document.body.removeChild(textArea)

        if (!successful) {
          throw new Error('Másolás sikertelen')
        }
      }
      toast.success('Vágólapra másolva')
    } catch {
      toast.error('Másolás sikertelen')
    }
  }

  return {
    handleCopy,
  }
}
