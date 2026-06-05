import axios from 'axios'
import { API_BASE } from './config'
import { getAccessToken } from './authStorage'

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 10_000,
})

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

