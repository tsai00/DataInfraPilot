
import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';

export const API_BASE_URL: string = import.meta.env.API_BASE_URL || 'http://localhost:8000';;

/**
 * General API client for making HTTP requests using Axios
 */
class ApiClient {
  private client: AxiosInstance;

  constructor(baseUrl: string = API_BASE_URL) {
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    
    // Add response interceptor to check for HTML responses
    this.client.interceptors.response.use(
      this.handleSuccessResponse,
      this.handleErrorResponse
    );
  }

  /**
   * Handle successful responses and check for HTML content
   */
  private handleSuccessResponse(response: AxiosResponse) {
    // Check if the response is HTML (could happen with some server configurations)
    const contentType = response.headers['content-type'];
    if (contentType && contentType.includes('text/html')) {
      console.warn('Received HTML response instead of JSON');
      // Return mock data to prevent crashes
      return {
        ...response,
        data: [] // Default empty array as fallback
      };
    }
    return response;
  }

  /**
   * Handle error responses
   */
  private handleErrorResponse(error: AxiosError) {
    console.error('API request failed:', error);
    return Promise.reject(error);
  }

  /**
   * Make a GET request
   */
  async get<T>(endpoint: string): Promise<T> {
    try {
      const response = await this.client.get<T>(endpoint);
      return response.data;
    } catch (error) {
      this.handleError(error);
    }
  }

  /**
   * Make a POST request
   */
  async post<T>(endpoint: string, data: any): Promise<T> {
    try {
      const response = await this.client.post<T>(endpoint, data);
      return response.data;
    } catch (error) {
      this.handleError(error);
    }
  }

  /**
   * Make a PUT request
   */
  async put<T>(endpoint: string, data: any): Promise<T> {
    try {
      const response = await this.client.put<T>(endpoint, data);
      return response.data;
    } catch (error) {
      this.handleError(error);
    }
  }

  /**
   * Make a DELETE request
   */
  async delete(endpoint: string): Promise<void> {
    try {
      await this.client.delete(endpoint);
    } catch (error) {
      this.handleError(error);
    }
  }

  /**
   * Handle API errors in a consistent way
   */
  private handleError(error: unknown): never {
    if (axios.isAxiosError(error)) {
      // Check if the response is HTML
      const contentType = error.response?.headers?.['content-type'];
      if (contentType && contentType.includes('text/html')) {
        console.error('Received HTML error response instead of JSON');
        throw new Error('Server returned HTML instead of JSON. The API may be unavailable.');
      }
      
      const errorMessage =
        error.response?.data?.detail || error.response?.statusText || 'API request failed';
      throw new Error(errorMessage);
    }
    throw new Error('An unexpected error occurred');
  }
}

// Export a singleton instance
export const apiClient = new ApiClient();
