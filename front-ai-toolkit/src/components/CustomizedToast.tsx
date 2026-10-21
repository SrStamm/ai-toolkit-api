import { showToast, type ToastOptions } from "@/components/toast";

// Legacy export for backwards compatibility
export function CustomizedToast({ type, msg }: ToastOptions) {
  return showToast({ type, msg });
}

export default CustomizedToast;
