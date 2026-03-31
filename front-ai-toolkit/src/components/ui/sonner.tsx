import {
  CircleCheckIcon,
  InfoIcon,
  Loader2Icon,
  OctagonXIcon,
  TriangleAlertIcon,
} from "lucide-react"
import { useTheme } from "next-themes"
import { Toaster as Sonner, type ToasterProps } from "sonner"

export function Toaster({ ...props }: ToasterProps) {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="size-4 text-green-500" />,
        info: <InfoIcon className="size-4 text-blue-500" />,
        warning: <TriangleAlertIcon className="size-4 text-yellow-500" />,
        error: <OctagonXIcon className="size-4 text-red-500" />,
        loading: <Loader2Icon className="size-4 animate-spin text-muted-foreground" />,
      }}
      toastOptions={{
        classNames: {
          toast:
            "toast group flex items-center gap-3 p-4 rounded-lg border shadow-lg",
          title: "text-sm font-semibold",
          description: "text-sm text-muted-foreground",
          actionButton:
            "bg-primary text-primary-foreground hover:bg-primary/90",
          cancelButton:
            "bg-muted text-muted-foreground hover:bg-muted/90",
          closeButton: "text-muted-foreground hover:text-foreground",
          success: "border-green-500/30 bg-green-50 dark:bg-green-950/30",
          info: "border-blue-500/30 bg-blue-50 dark:bg-blue-950/30",
          warning: "border-yellow-500/30 bg-yellow-50 dark:bg-yellow-950/30",
          error: "border-red-500/30 bg-red-50 dark:bg-red-950/30",
        },
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      {...props}
    />
  )
}
