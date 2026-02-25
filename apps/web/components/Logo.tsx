/**
 * Logo — inline SVG logo mark for theNewslane.
 *
 * Renders a bold geometric "N" inside a rounded square.
 * Uses the brand primary colour from CSS custom properties.
 */

interface LogoProps {
  size?: number;
  className?: string;
}

export function Logo({ size = 28, className }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 512 512"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      className={className}
      style={{ display: 'block', flexShrink: 0 }}
    >
      <rect
        width="512"
        height="512"
        rx="96"
        fill="var(--color-primary)"
      />
      <path
        d="M152 384V128h48l112 168V128h48v256h-48L200 216v168h-48z"
        fill="#FFFFFF"
      />
    </svg>
  );
}
