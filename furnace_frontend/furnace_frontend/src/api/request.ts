import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

interface ApiResponse<T = any> {
  data: T
  code: number
  message: string
}

class Request {
  private instance: AxiosInstance
  private baseURL: string = '/api'
  private timeout: number = 30000

  constructor() {
    this.instance = axios.create({
      baseURL: this.baseURL,
      timeout: this.timeout
    })

    this.instance.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    this.instance.interceptors.response.use(
      (response: AxiosResponse<ApiResponse>) => {
        const { data } = response
        if (data.code === 0) {
          return data.data
        } else {
          ElMessage.error(data.message || '请求失败')
          return Promise.reject(new Error(data.message || '请求失败'))
        }
      },
      (error) => {
        ElMessage.error(error.message || '网络错误')
        return Promise.reject(error)
      }
    )
  }

  public get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return this.instance.get(url, config)
  }

  public post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.instance.post(url, data, config)
  }

  public put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.instance.put(url, data, config)
  }

  public delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return this.instance.delete(url, config)
  }
}

export default new Request()
