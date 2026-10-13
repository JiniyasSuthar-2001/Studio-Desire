export type UserRole =
  | "MASTER"
  | "OWNER"
  | "ADMIN"
  | "DESIGNER"
  | "PROJECT_MANAGER"
  | "EDITOR"
  | "UPLOADER"
  | "VIEWER"
  | "OBSERVER";

export interface AuthUser {
  id: number;
  username: string;
  role: UserRole;
  must_change_password: boolean;
  email?: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
  role: UserRole;
  must_change_password: boolean;
  user_id: number;
}
