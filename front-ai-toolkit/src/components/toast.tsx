import { toast } from "sonner";

interface CustomizedToastProps {
  type: "error" | "info" | "success";
  msg: string;
}

function CustomizedToast({ type, msg }: CustomizedToastProps) {
  switch (type) {
    case "error":
      return toast.error(msg, { position: "top-center", duration: 5000 });
    case "info":
      return toast.info(msg, { position: "top-center", duration: 5000 });
    case "success":
      return toast.success(msg, { position: "top-center", duration: 5000 });
  }
}

export default CustomizedToast;
