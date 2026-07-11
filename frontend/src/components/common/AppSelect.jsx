import * as React from "react";
import * as Select from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

const EMPTY_VALUE = "__gateprep_empty__";
const MAX_MENU_ITEMS = 8;

export default function AppSelect({
  value,
  onChange,
  options,
  placeholder = "Select",
  className,
  triggerClassName,
  contentClassName,
  testId,
}) {
  const normalizedValue = value === "" || value == null ? EMPTY_VALUE : String(value);
  const menuHeight = Math.min(options.length, MAX_MENU_ITEMS) * 30 + 8;

  return (
    <Select.Root
      value={normalizedValue}
      onValueChange={(next) => onChange(next === EMPTY_VALUE ? "" : next)}
    >
      <Select.Trigger
        data-testid={testId}
        className={cn(
          "group inline-flex h-8 min-w-[124px] items-center justify-between gap-2 rounded-md border border-white/5 bg-[#1a1a1d] px-2.5 text-sm font-semibold text-zinc-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.035),0_1px_2px_rgba(0,0,0,0.22)] outline-none transition-all",
          "hover:border-violet-400/35 hover:bg-[#202024] focus:border-violet-400/75 focus:ring-2 focus:ring-violet-500/25",
          "data-[state=open]:border-violet-400/80 data-[state=open]:bg-[#202024] data-[state=open]:ring-2 data-[state=open]:ring-violet-500/25",
          className,
          triggerClassName,
        )}
      >
        <Select.Value placeholder={placeholder} />
        <Select.Icon>
          <ChevronDown className="h-3.5 w-3.5 text-zinc-300 transition-transform group-data-[state=open]:rotate-180" />
        </Select.Icon>
      </Select.Trigger>

      <Select.Portal>
        <Select.Content
          position="popper"
          sideOffset={6}
          collisionPadding={12}
          style={{ "--app-select-menu-height": `${menuHeight}px` }}
          className={cn(
            "z-50 max-h-[min(var(--app-select-menu-height),var(--radix-select-content-available-height))] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border border-zinc-700/75 bg-[#202020]/98 text-zinc-100 shadow-[0_18px_45px_rgba(0,0,0,0.42)] backdrop-blur-xl",
            "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95 data-[state=open]:slide-in-from-top-1",
            contentClassName,
          )}
        >
          <Select.Viewport className="max-h-[min(var(--app-select-menu-height),var(--radix-select-content-available-height))] overflow-y-auto overscroll-contain p-1">
            {options.map((option) => {
              const itemValue = option.value === "" || option.value == null
                ? EMPTY_VALUE
                : String(option.value);
              return (
                <Select.Item
                  key={`${itemValue}-${option.label}`}
                  value={itemValue}
                  disabled={option.disabled}
                  className={cn(
                    "relative flex h-[30px] cursor-default select-none items-center rounded-[5px] py-1 pl-7 pr-2 text-sm font-medium outline-none transition-colors",
                    "text-zinc-100/90 focus:bg-zinc-700/70 focus:text-white data-[state=checked]:bg-zinc-700/80 data-[state=checked]:text-white",
                    "data-[disabled]:pointer-events-none data-[disabled]:opacity-40",
                  )}
                >
                  <span className="absolute left-2 h-3 w-3 rounded-[3px] border border-zinc-500/70 bg-zinc-900/40" />
                  <Select.ItemIndicator className="absolute left-2 inline-flex h-3 w-3 items-center justify-center rounded-[3px] border border-violet-400 bg-violet-500 text-white">
                    <Check className="h-2.5 w-2.5" />
                  </Select.ItemIndicator>
                  <Select.ItemText>{option.label}</Select.ItemText>
                </Select.Item>
              );
            })}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}
