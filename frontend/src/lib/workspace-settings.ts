import { apiClient } from './api-client';

export interface WorkspaceSettings {
  workspace_id: string;
  tone_level: number;
  style_json: Record<string, string>;
  blocklist_json: string[];
  approval_threshold?: number | null;
}

export interface WorkspaceSettingsUpdate {
  tone_level?: number;
  style_json?: Record<string, string>;
  blocklist_json?: string[];
  approval_threshold?: number | null;
}

export async function getWorkspaceSettings(workspaceId: string): Promise<WorkspaceSettings> {
  const response = await apiClient.get<WorkspaceSettings>(`/workspace-settings/${workspaceId}`);
  return response.data;
}

export async function updateWorkspaceSettings(
  workspaceId: string,
  settings: WorkspaceSettingsUpdate
): Promise<WorkspaceSettings> {
  const response = await apiClient.put<WorkspaceSettings>(`/workspace-settings/${workspaceId}`, settings);
  return response.data;
}
