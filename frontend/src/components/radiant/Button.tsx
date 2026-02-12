import * as Headless from '@headlessui/react'
import { clsx } from 'clsx'
import type { LinkProps } from 'react-router-dom'
import { RadiantLink } from './RadiantLink'

const variants = {
  primary: clsx(
    'inline-flex items-center justify-center px-4 py-2 rounded-full border border-transparent',
    'bg-brand-primary hover:bg-fikiri-400 text-white font-medium whitespace-nowrap',
    'shadow-md transition-colors duration-200',
    'disabled:opacity-40 disabled:cursor-not-allowed'
  ),
  secondary: clsx(
    'inline-flex items-center justify-center px-4 py-2 rounded-full border border-transparent',
    'bg-white dark:bg-gray-800 ring-1 ring-border text-foreground font-medium whitespace-nowrap',
    'hover:bg-muted transition-colors duration-200',
    'disabled:opacity-40 disabled:cursor-not-allowed'
  ),
  outline: clsx(
    'inline-flex items-center justify-center px-3 py-1.5 rounded-lg border border-transparent',
    'ring-1 ring-border text-foreground font-medium whitespace-nowrap text-sm',
    'hover:bg-muted transition-colors duration-200',
    'disabled:opacity-40 disabled:cursor-not-allowed'
  ),
}

type ButtonProps = {
  variant?: keyof typeof variants
} & (
  | (LinkProps & { to: string })
  | (Headless.ButtonProps & { to?: undefined })
)

export function Button({ variant = 'primary', className, to, ...props }: ButtonProps) {
  const combinedClassName = clsx(className, variants[variant])
  if (to !== undefined) {
    return <RadiantLink to={to} className={combinedClassName} {...(props as LinkProps)} />
  }
  return <Headless.Button {...(props as Headless.ButtonProps)} className={combinedClassName} />
}
