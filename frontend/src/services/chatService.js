/**
 * Chat entity API service.
 * Handles AI Farmer Copilot conversation requests against FastAPI /api/v1/chat endpoint.
 */

import { request } from './api';

export const chatService = {
  /**
   * Send a query to Kisan AI Copilot.
   * @param {{
   *   message: string,
   *   crop_id?: number|null,
   *   language?: 'en'|'mr'|'hi',
   *   current_path?: string,
   *   workflow_state?: any,
   *   history?: Array<{ role: 'user'|'assistant'|'system', content: string }>
   * }} payload
   * @returns {Promise<{
   *   reply: string,
   *   intent: string,
   *   detected_language: string,
   *   crop_id: number|null,
   *   crop_name: string|null,
   *   farm_name: string|null,
   *   action_type: string|null,
   *   action_payload: any,
   *   tutorial_steps: Array<any>|null,
   *   confirmation_needed: boolean,
   *   confirmation_data: any,
   *   timestamp: string,
   *   suggested_actions: Array<{ label: string, action_type: string, payload: any }>
   * }>}
   */
  async sendMessage({
    message,
    crop_id = null,
    language = 'en',
    current_path = '/',
    workflow_state = null,
    history = [],
  }) {
    return request('/api/v1/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        crop_id: crop_id ? Number(crop_id) : null,
        language,
        current_path,
        workflow_state,
        history,
      }),
    });
  },
};

export default chatService;
