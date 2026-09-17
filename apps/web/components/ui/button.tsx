import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
  { variants: [{ variant: "default", class: "bg-primary text-primary-foreground shadow-xs hover:bg-primary/90" }, { variant: "destructive", class: "bg-destructive text-white shadow-xs hover:bg-destructive/90" }, { variant: "outline", class: "border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground" }, { variant: "secondary", class: "bg-secondary text-secondary-foreground shadow-xs hover:bg-secondary/80" }, { variant: "ghost", class: "hover:bg-accent hover:text-accent-foreground" }, { variant: "link", class: "text-primary underline-offset-4 hover:underline" }, { size: "default", class: "h-9 px-4 py-2 has-[>svg]:px-3" }, { size: "sm", class: "h-8 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5" }, { size: "lg", class: "h-10 rounded-md px-8 has-[>svg]:px-6" }, { size: "icon", class: "size-9" }], defaultVariants: { variant: "default", size: "default" } } as any)
type ButtonVariant = "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
type ButtonSize = "default" | "sm" | "lg" | "icon"
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> { variant?: ButtonVariant; size?: ButtonSize; asChild?: boolean }
function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}
export { Button, buttonVariants }
