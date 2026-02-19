import { toast } from 'sonner'

export function useCopy() {
  const handleCopy = async (value: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(value)
      toast.success('Vágólapra másolva')
    } catch {
      toast.error('Másolás sikertelen')
    }
  }

  return {
    handleCopy,
  }
}
