import { Link } from 'react-router-dom'

type LegalFooterLinksProps = {
  className?: string
  linkClassName?: string
}

export function LegalFooterLinks({
  className = '',
  linkClassName = 'text-brand-primary hover:underline dark:text-brand-accent',
}: LegalFooterLinksProps) {
  return (
    <p className={className}>
      <Link to="/terms" className={linkClassName}>
        Terms of Service
      </Link>
      <span className="mx-2 text-current/40" aria-hidden>
        ·
      </span>
      <Link to="/privacy" className={linkClassName}>
        Privacy Policy
      </Link>
    </p>
  )
}
