import * as React from "react"
import * as DialogPrimitive from "@radix-ui/react-dialog"
import { X } from "lucide-react"

import { cn } from "@/lib/utils"

const Dialog = DialogPrimitive.Root

const DialogTrigger = DialogPrimitive.Trigger

const DialogPortal = DialogPrimitive.Portal

const DialogClose = DialogPrimitive.Close

const DialogOverlay = React.forwardRef(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-black/80  data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props} />
))
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName

// The TonConnect wallet list (#tc-widget-root) opens ABOVE a dialog (deposit / withdraw / buy) but lives outside it.
// Radix treated a tap there as "outside": it closed the dialog, and while the dialog was open body pointer-events:none
// made the wallet list untappable — «Другие кошельки» / Tonkeeper did nothing, only the QR worked. Taps inside the
// wallet list are ignored here. Radix reports the tap on «click», when TonConnect has already redrawn its view and the
// tapped node is detached — so where the pointer went down is remembered at pointerdown time.
const TC_SEL = '#tc-widget-root, tc-root, [data-tc-modal], [data-tc-wallets-modal-container]';
let lastTcPointer = 0;
if (typeof document !== 'undefined') {
  document.addEventListener('pointerdown', (e) => {
    const t = e.target;
    lastTcPointer = t && t.closest && t.closest(TC_SEL) ? Date.now() : 0;
  }, true);
}
const inWalletModal = (e) => {
  const t = e?.detail?.originalEvent?.target || e?.target;
  if (t && t.closest && t.closest(TC_SEL)) return true;
  // the last pointer-down was in the wallet list (a tap anywhere else resets this before Radix sees it)
  return lastTcPointer > 0 && Date.now() - lastTcPointer < 3000;
};
const guardOutside = (handler) => (e) => {
  if (inWalletModal(e)) { e.preventDefault(); return; }
  if (handler) handler(e);
};

const DialogContent = React.forwardRef(({ className, children, hideCloseButton = false, overlayClassName, onPointerDownOutside, onInteractOutside, onFocusOutside, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay className={overlayClassName} />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-[calc(100%-1.5rem)] max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 rounded-2xl data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]",
        className
      )}
      onPointerDownOutside={guardOutside(onPointerDownOutside)}
      onInteractOutside={guardOutside(onInteractOutside)}
      onFocusOutside={guardOutside(onFocusOutside)}
      {...props}>
      {children}
      {!hideCloseButton && (
        <DialogPrimitive.Close
          className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </DialogPrimitive.Close>
      )}
    </DialogPrimitive.Content>
  </DialogPortal>
))
DialogContent.displayName = DialogPrimitive.Content.displayName

const DialogHeader = ({
  className,
  ...props
}) => (
  <div
    className={cn("flex flex-col space-y-1.5 text-center sm:text-left", className)}
    {...props} />
)
DialogHeader.displayName = "DialogHeader"

const DialogFooter = ({
  className,
  ...props
}) => (
  <div
    className={cn("flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-0 sm:space-x-2", className)}
    {...props} />
)
DialogFooter.displayName = "DialogFooter"

const DialogTitle = React.forwardRef(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold leading-none tracking-tight", className)}
    {...props} />
))
DialogTitle.displayName = DialogPrimitive.Title.displayName

const DialogDescription = React.forwardRef(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props} />
))
DialogDescription.displayName = DialogPrimitive.Description.displayName

export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
}
