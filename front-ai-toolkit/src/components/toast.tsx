import { toast } from "sonner";

interface ToastOptions {
  type: "error" | "info" | "success";
  msg: string;
  position?: "top-center" | "top-left" | "top-right" | "bottom-center" | "bottom-left" | "bottom-right";
  duration?: number;
}

export function showToast({ type, msg, position = "top-center", duration = 5000 }: ToastOptions) {
  switch (type) {
    case "error":
      return toast.error(msg, { position, duration });
    case "info":
      return toast.info(msg, { position, duration });
    case "success":
      return toast.success(msg, { position, duration });
  }
}

export function showToastError(msg: string, options?: Partial<ToastOptions>) {
  return showToast({ type: "error", msg, ...options });
}

export function showToastSuccess(msg: string, options?: Partial<ToastOptions>) {
  return showToast({ type: "success", msg, ...options });
}

export function showToastInfo(msg: string, options?: Partial<ToastOptions>) {
  return showToast({ type: "info", msg, ...options });
}

// Legacy export for backwards compatibility
export default function CustomizedToast({ type, msg }: ToastOptions) {
  return showToast({ type, msg });
}
