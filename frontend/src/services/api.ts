const API_BASE_URL = (import.meta as any).env.VITE_API_URL || "/api";

export interface Car {
  id: number;
  number: string;
  class_name: string;
  model: string;
}

export interface Run {
  id: number;
  car_id: number;
  start_time: string;
  finish_time?: string | null;
  raw_time?: number | null;
  start_photo_url?: string | null;
  finish_photo_url?: string | null;
  penalties: number;
  adjusted_time?: number | null;
  is_dnf: boolean;
  is_aborted: boolean;
  is_missed_trip: boolean;
  finish_confirmed: boolean;
  car?: Car;
}

export interface ResetDataResult {
  runs_deleted: number;
  photos_deleted: number;
}

export interface DeleteRunResult {
  run_id: number;
}

export interface ReleaseStartResult {
  is_start_held: boolean;
}

export interface HoldStatusResult {
  is_start_held: boolean;
}

export interface FinishTriggerStatusResult {
  is_finish_triggered: boolean;
  finish_triggered_at: string | null;
}

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
}

export async function getCars(): Promise<Car[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/cars`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Error fetching cars:", error);
    throw error;
  }
}

export async function startRun(
  car_id: number,
  photo: File
): Promise<Run> {
  try {
    const formData = new FormData();
    formData.append("car_id", car_id.toString());
    formData.append("photo", photo);

    const response = await fetch(`${API_BASE_URL}/start`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result: ApiResponse<Run> = await response.json();

    if (!result.success) {
      throw new Error(result.error?.message || "Failed to start run");
    }

    return result.data as Run;
  } catch (error) {
    console.error("Error starting run:", error);
    throw error;
  }
}

export async function finishRun(
  run_id: number,
  photo: File
): Promise<Run> {
  try {
    const formData = new FormData();
    formData.append("run_id", run_id.toString());
    formData.append("photo", photo);

    const response = await fetch(`${API_BASE_URL}/finish`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result: ApiResponse<Run> = await response.json();

    if (!result.success) {
      throw new Error(result.error?.message || "Failed to finish run");
    }

    return result.data as Run;
  } catch (error) {
    console.error("Error finishing run:", error);
    throw error;
  }
}

export async function getRuns(status?: string): Promise<Run[]> {
  try {
    let url = `${API_BASE_URL}/runs`;
    if (status) url += `?status=${status}`;

    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const result: ApiResponse<{ runs: Run[] }> = await response.json();

    if (!result.success) {
      throw new Error(result.error?.message || "Failed to fetch runs");
    }

    return result.data?.runs || [];
  } catch (error) {
    console.error("Error fetching runs:", error);
    throw error;
  }
}

export async function updateRun(
  run_id: number,
  update_data: {
    penalties?: number;
    is_dnf?: boolean;
    is_aborted?: boolean;
    is_missed_trip?: boolean;
  }
): Promise<Run> {
  try {
    const response = await fetch(`${API_BASE_URL}/runs/${run_id}/update`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(update_data),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result: ApiResponse<Run> = await response.json();

    if (!result.success) {
      throw new Error(result.error?.message || "Failed to update run");
    }

    return result.data as Run;
  } catch (error) {
    console.error("Error updating run:", error);
    throw error;
  }
}

export async function resetData(): Promise<ResetDataResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/admin/reset`, {
      method: "POST",
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result: ApiResponse<ResetDataResult> = await response.json();

    if (!result.success) {
      throw new Error(result.error?.message || "Failed to reset data");
    }

    return result.data as ResetDataResult;
  } catch (error) {
    console.error("Error resetting data:", error);
    throw error;
  }
}

export async function deleteRun(run_id: number): Promise<DeleteRunResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/runs/${run_id}`, {
      method: "DELETE",
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result: ApiResponse<DeleteRunResult> = await response.json();

    if (!result.success) {
      throw new Error(result.error?.message || "Failed to delete run");
    }

    return result.data as DeleteRunResult;
  } catch (error) {
    console.error("Error deleting run:", error);
    throw error;
  }
}

export async function releaseStart(): Promise<ReleaseStartResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/runs/release-start`, {
      method: "POST",
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result: ApiResponse<ReleaseStartResult> = await response.json();

    if (!result.success) {
      throw new Error(result.error?.message || "Failed to release start");
    }

    return result.data as ReleaseStartResult;
  } catch (error) {
    console.error("Error releasing start:", error);
    throw error;
  }
}

export async function holdStart(): Promise<HoldStatusResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/runs/hold-start`, {
      method: "POST",
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result: ApiResponse<HoldStatusResult> = await response.json();

    if (!result.success) {
      throw new Error(result.error?.message || "Failed to hold start");
    }

    return result.data as HoldStatusResult;
  } catch (error) {
    console.error("Error holding start:", error);
    throw error;
  }
}

export async function getHoldStatus(): Promise<HoldStatusResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/runs/hold-status`);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result: ApiResponse<HoldStatusResult> = await response.json();

    if (!result.success) {
      throw new Error(result.error?.message || "Failed to fetch hold status");
    }

    return result.data as HoldStatusResult;
  } catch (error) {
    console.error("Error fetching hold status:", error);
    throw error;
  }
}

export async function triggerFinish(): Promise<FinishTriggerStatusResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/runs/trigger-finish`, {
      method: "POST",
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result: ApiResponse<FinishTriggerStatusResult> = await response.json();

    if (!result.success) {
      throw new Error(result.error?.message || "Failed to trigger finish");
    }

    return result.data as FinishTriggerStatusResult;
  } catch (error) {
    console.error("Error triggering finish:", error);
    throw error;
  }
}

export async function getFinishTriggerStatus(): Promise<FinishTriggerStatusResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/runs/finish-trigger-status`);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result: ApiResponse<FinishTriggerStatusResult> = await response.json();

    if (!result.success) {
      throw new Error(result.error?.message || "Failed to fetch finish trigger status");
    }

    return result.data as FinishTriggerStatusResult;
  } catch (error) {
    console.error("Error fetching finish trigger status:", error);
    throw error;
  }
}
