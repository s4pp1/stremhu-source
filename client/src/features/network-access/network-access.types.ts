export type NetworkAccessDialog = {
  type: 'NETWORK_ACCESS'
}

export type NetworkAccessDefaultValues = {
  connection: 'idle' | 'pending' | 'success' | 'error'
  enebledlocalIp: boolean
  address: string
}
