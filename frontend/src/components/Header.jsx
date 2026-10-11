export default function Header() {
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-5 sm:px-6">
        <div className="flex items-center gap-3">
          <span
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-sm font-semibold tracking-tight text-white"
            aria-hidden="true"
          >
            Ll
          </span>
          <div>
            <p className="font-serif text-xl font-semibold tracking-tight text-ink">
              LinguaLite
            </p>
            <p className="text-sm text-muted">Translation &amp; writing assistant</p>
          </div>
        </div>
        <p className="hidden text-sm text-muted sm:block">No account required</p>
      </div>
    </header>
  )
}
